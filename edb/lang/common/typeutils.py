#
# This source file is part of the EdgeDB open source project.
#
# Copyright 2011-present MagicStack Inc. and the EdgeDB authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#


import collections.abc
import functools


@functools.lru_cache(1024)
def _is_container_type(cls):
    return (
        issubclass(cls, (collections.abc.Container)) and
        not issubclass(cls, (str, bytes, bytearray, memoryview))
    )


@functools.lru_cache(1024)
def _is_iterable_type(cls):
    return (
        issubclass(cls, collections.abc.Iterable)
    )


def is_container(obj):
    cls = obj.__class__
    return _is_container_type(cls) and _is_iterable_type(cls)


def is_container_type(type_):
    return isinstance(type_, type) and _is_container_type(type_)
