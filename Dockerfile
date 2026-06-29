FROM ubuntu:22.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    make \
    git \
    curl \
    wget \
    python3.10 \
    python3-venv \
    python3-pip \
    nodejs \
    npm \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Upgrade Node.js to 22
RUN npm install -g n && n 22

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app

# Create virtual environment and install Python deps
RUN python3 -m venv .venv && \
    .venv/bin/pip install --upgrade pip && \
    .venv/bin/pip install -r requirements.txt

# Install Remotion composer
RUN cd remotion-composer && npm install

# Make entrypoint
RUN echo '#!/bin/bash\nsource .venv/bin/activate\nexec "$@"' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["make", "demo"]