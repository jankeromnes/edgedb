FROM gitpod/workspace-full

# Install PostgresSQL build dependencies.
# Source: https://www.manniwood.com/postgresql_93_compile_install_howto/index.html
RUN sudo apt-get update \
 && sudo apt-get install -y \
  flex \
  bison build-essential \
  libreadline6-dev \
  zlib1g-dev \
  libossp-uuid-dev \
 && sudo rm -rf /var/lib/apt/lists/*
