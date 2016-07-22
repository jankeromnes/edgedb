##
# Copyright (c) 2016 MagicStack Inc.
# All rights reserved.
#
# See LICENSE for details.
##


import re

from edgedb.lang.common.datastructures import xvalue
from edgedb.lang.common import lexer

from .keywords import edge_schema_keywords


__all__ = ('EdgeSchemaLexer', 'EdgeIndentationError')


class EdgeIndentationError(lexer.LexError):
    pass


STATE_KEEP = 0
STATE_WS_SENSITIVE = 1
STATE_WS_INSENSITIVE = 2
STATE_RAW_STRING = 3


re_decdigit = r"[0-9]"
re_decdigit_ = r"[0-9_]"
re_intpart = r"(?:{dec}(?:{dec_}*{dec})?)".format(dec_=re_decdigit_,
                                                  dec=re_decdigit)
re_exppart = r"(?:[eE](?:[\+\-])?{int})".format(int=re_intpart)
re_dquote = r'\$([A-Za-z\200-\377_][0-9]*)*\$'


Rule = lexer.Rule


class EdgeSchemaLexer(lexer.Lexer):

    start_state = STATE_WS_SENSITIVE

    NL = 'NEWLINE'
    MULTILINE_TOKENS = frozenset(('STRING', 'RAWSTRING'))
    RE_FLAGS = re.X | re.M

    # Basic keywords
    keyword_rules = [Rule(token=tok[0],
                          next_state=STATE_KEEP,
                          regexp=lexer.group(val))
                     for val, tok in edge_schema_keywords.items()]

    common_rules = keyword_rules + [
        Rule(token='COMMENT',
             next_state=STATE_KEEP,
             regexp=r'\#[^\n]*$'),

        Rule(token='WS',
             next_state=STATE_KEEP,
             regexp=r'[^\S\n]+'),

        Rule(token='NEWLINE',
             next_state=STATE_KEEP,
             regexp=r'\n'),

        Rule(token='LPAREN',
             next_state=STATE_WS_INSENSITIVE,
             regexp=r'\('),

        Rule(token='RPAREN',
             next_state=STATE_WS_SENSITIVE,
             regexp=r'\)'),

        Rule(token='LSBRACKET',
             next_state=STATE_WS_INSENSITIVE,
             regexp=r'\['),

        Rule(token='RSBRACKET',
             next_state=STATE_WS_SENSITIVE,
             regexp=r'\]'),

        Rule(token='LCBRACKET',
             next_state=STATE_WS_INSENSITIVE,
             regexp=r'\{'),

        Rule(token='RCBRACKET',
             next_state=STATE_WS_SENSITIVE,
             regexp=r'\}'),

        Rule(token='COMMA',
             next_state=STATE_KEEP,
             regexp=r'\,'),

        Rule(token='DOUBLECOLON',
             next_state=STATE_KEEP,
             regexp=r'::'),

        Rule(token='TURNSTILE',
             next_state=STATE_RAW_STRING,
             regexp=r':='),

        Rule(token='COLON',
             next_state=STATE_KEEP,
             regexp=r':'),

        Rule(token='ARROW',
             next_state=STATE_KEEP,
             regexp=r'->'),

        Rule(token='MAPPING',
             next_state=STATE_KEEP,
             regexp=r'[1*][1*]'),

        Rule(token='ICONST',
             next_state=STATE_KEEP,
             regexp=r'\d+(?![eE.0-9])'),

        Rule(token='FCONST',
             next_state=STATE_KEEP,
             regexp=r'''
                    (?: \d+ (?:\.\d*)?
                        |
                        \. \d+
                    ) {exppart}
                '''.format(exppart=re_exppart)),

        Rule(token='FCONST',
             next_state=STATE_KEEP,
             regexp=r'''
                (?: \d+\.(?!\.)\d*
                    |
                    \.\d+)
             '''),

        Rule(token='DOT',
             next_state=STATE_KEEP,
             regexp=r'\.'),

        Rule(token='STRING',
             next_state=STATE_KEEP,
             regexp=r'''
                (?P<Q>
                    # capture the opening quote in group Q
                    (
                        ' |
                        {dollar_quote}
                    )
                )
                (?:
                    .*?
                )
                (?P=Q)      # match closing quote type with whatever is in Q
             '''.format(dollar_quote=re_dquote)),

        Rule(token='IDENT',
             next_state=STATE_KEEP,
             regexp=r'''
                    (?:[^\W\d]|\$)
                    (?:\w|\$)*
                '''),
    ]

    states = {
        STATE_WS_SENSITIVE: list(common_rules),
        STATE_WS_INSENSITIVE: list(common_rules),
        STATE_RAW_STRING: [
            Rule(token='NEWLINE',
                 next_state=STATE_KEEP,
                 regexp=r'(?<=:=)\s*\n'),

            Rule(token='RAWSTRING',
                 next_state=STATE_WS_SENSITIVE,
                 regexp=r'(?<=:=)[^\n]+?$'),

            Rule(token='RAWSTRING',
                 next_state=STATE_KEEP,
                 regexp=r'^[^\S\n]*\n'),

            Rule(token='RAWLEADWS',
                 next_state=STATE_KEEP,
                 regexp=r'^[^\S\n]+'),

            Rule(token='RAWSTRING',
                 next_state=STATE_KEEP,
                 regexp=r'.*?(?:\n|.$)'),
        ]
    }

    def get_start_tokens(self):
        '''Yield a number of start tokens.'''
        return ()

    def get_eof_tokens(self):
        '''Yield a number of EOF tokens.'''
        if self.logical_line_started:
            yield self.token_from_text('NL', '')

        if len(self.indent) > 1:
            # decrease indentation level at the end of input
            while self.indent[-1] > 0:
                self.indent.pop()
                yield self.token_from_text('DEDENT', '')

    def insert_token(self, toktype, token, pos='start'):
        return xvalue('', type=toktype, text='',
                      start=token.attrs[pos],
                      end=token.attrs[pos],
                      filename=self.filename)

    def token_generator(self, token):
        """Given the current lexer token, yield one or more tokens."""

        tok_type = token.attrs['type']

        # handle indentation
        #
        if (self._state == STATE_WS_SENSITIVE and
                not self.logical_line_started and
                tok_type not in {'NEWLINE', 'WS', 'COMMENT'}):

            # we have potential indentation change
            last_indent = self.indent[-1]
            cur_indent = token.attrs['start'].column - 1

            if cur_indent > last_indent:
                # increase indentation level
                self.indent.append(cur_indent)
                yield self.insert_token('INDENT', token)

            elif cur_indent < last_indent:
                # decrease indentation level
                while self.indent[-1] > cur_indent:
                    self.indent.pop()
                    if self.indent[-1] < cur_indent:
                        # indentation level mismatch
                        raise EdgeIndentationError(
                            'Incorrect unindent at {position}',
                            line=token.attrs['start'].line,
                            col=token.attrs['start'].column,
                            filename=self.filename)

                    yield self.insert_token('DEDENT', token)

        # indentation of raw strings
        #
        elif self._state == STATE_RAW_STRING:
            last_indent = self.indent[-1]
            cur_indent = len(token.value)

            if not self.logical_line_started and tok_type != 'NEWLINE':
                # we MUST indent here
                if (tok_type == 'RAWLEADWS' and
                        cur_indent > last_indent):
                    # increase indentation level
                    self.indent.append(cur_indent)
                    yield self.insert_token('INDENT', token, 'end')

                elif token.value.strip():
                    # indentation level mismatch
                    raise EdgeIndentationError(
                        'Incorrect indentation at {position}',
                        line=token.attrs['end'].line,
                        col=token.attrs['end'].column,
                        filename=self.filename)

            elif (tok_type == 'RAWLEADWS' and
                    cur_indent < last_indent):
                # check indentation level of each RAWLEADWS,
                # exiting the current state and issuing a NL and DEDENT
                # tokens if indentation falls below starting value
                #
                yield self.insert_token('NL', token)

                while self.indent[-1] > cur_indent:
                    self.indent.pop()
                    if self.indent[-1] < cur_indent:
                        # indentation level mismatch
                        raise EdgeIndentationError(
                            'Incorrect unindent at {position}',
                            line=token.attrs['end'].line,
                            col=token.attrs['end'].column,
                            filename=self.filename)

                    yield self.insert_token('DEDENT', token, 'end')

                self._next_state = STATE_WS_SENSITIVE
                # alter the token type
                token.attrs['type'] = 'WS'

        # handle logical newline
        #
        if (self.logical_line_started and
                self._state in (STATE_WS_SENSITIVE, STATE_RAW_STRING) and
                tok_type == 'NEWLINE'):
            yield self.insert_token('NL', token)
            self.logical_line_started = False

        elif tok_type not in {'NEWLINE', 'WS', 'COMMENT'}:
            self.logical_line_started = True

        yield token

    def lex(self):
        """Lexes the src.

        Generator. Yields tokens (as defined by the rules).

        May yield special start and EOF tokens.
        May raise UnknownTokenError exception."""

        self.indent = [0]
        self.logical_line_started = True
        self.prevtok = None
        self._next_state = None
        src = self.inputstr

        for tok in self.get_start_tokens():
            yield tok

        while self.start < self.end:
            for match in self.re_states[self._state].finditer(src, self.start):
                rule_id = match.lastgroup

                txt = match.group(rule_id)

                if rule_id == 'err':
                    # Error group -- no rule has been matched
                    self.handle_error(txt)

                rule = Rule._map[rule_id]
                rule_token = rule.token

                token = self.token_from_text(rule_token, txt)

                for tok in self.token_generator(token):
                    yield tok

                if rule.next_state and rule.next_state != self._state:
                    # Rule dictates that the lexer state should be
                    # switched
                    self._state = rule.next_state
                    break
                elif self._next_state is not None:
                    self._state = self._next_state
                    self._next_state = None
                    break

        # End of file
        for tok in self.get_eof_tokens():
            yield tok