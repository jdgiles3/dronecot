FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# Install Python 3.11 and Node.js for drone detection system
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    python3.12 \
    python3.12-venv \
    python3-pip \
    nodejs \
    npm \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Create symlinks for python
RUN ln -sf /usr/bin/python3.12 /usr/bin/python3 \
    && ln -sf /usr/bin/python3.12 /usr/bin/python
