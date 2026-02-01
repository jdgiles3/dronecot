FROM mcr.microsoft.com/devcontainers/base:ubuntu-24.04

# Install OpenCV dependencies (libgl1 replaces libgl1-mesa-glx in Ubuntu 24.04)
RUN apt-get update && export DEBIAN_FRONTEND=noninteractive \
    && apt-get -y install --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*
