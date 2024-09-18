# Start from the minimal Ubuntu 22.04 image
FROM ubuntu:22.04

# Set environment variables to avoid interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install curl, Node.js, npm, and essential dependencies for tileserver-gl
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    build-essential \
    pkg-config \
    xvfb \
    libglfw3-dev \
    libuv1-dev \
    libjpeg-turbo8 \
    libicu70 \
    libcairo2-dev \
    libpango1.0-dev \
    libjpeg-dev \
    libgif-dev \
    librsvg2-dev \
    gir1.2-rsvg-2.0 \
    librsvg2-2 \
    librsvg2-common \
    libcurl4-openssl-dev \
    libpixman-1-dev \
    libpixman-1-0 \
    git \
    && curl -sL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && npm install -g tileserver-gl \
    && apt-get remove --purge -y git curl build-essential \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create a working directory
WORKDIR /data

# Expose the default port for tileserver-gl
EXPOSE 9100

# Command to start tileserver-gl with the configuration file and keep the container running
CMD ["tileserver-gl", "--config", "/data/config.json", "--port", "9100", "--verbose"]
