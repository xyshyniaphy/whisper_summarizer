# fastwhisper Base Image - CUDA cuDNN + Python + Model
# Multi-stage build: Model downloaded in separate stage, then copied to base

# ========================================
# Stage 1: Model Downloader (discarded after copy)
# ========================================
FROM ubuntu:24.04 AS model-downloader

ENV DEBIAN_FRONTEND=noninteractive

# Install Python and curl
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-dev \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Create model directory
RUN mkdir -p /tmp/whisper_models

# Install faster-whisper and download model
RUN uv venv /tmp/venv && \
    . /tmp/venv/bin/activate && \
    uv pip install faster-whisper && \
    echo "Downloading faster-whisper model: large-v3-turbo..." && \
    python -c "from faster_whisper import WhisperModel; model = WhisperModel('large-v3-turbo', device='cpu', compute_type='int8', download_root='/tmp/whisper_models'); print('Model downloaded successfully!')" && \
    echo "Model files:" && \
    ls -lah /tmp/whisper_models/ && \
    du -sh /tmp/whisper_models/

# ========================================
# Stage 2: Base Image (runtime only)
# ========================================
FROM nvidia/cuda:12.9.1-cudnn-runtime-ubuntu24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

LABEL description="Base image with CUDA cuDNN, Python, and faster-whisper model"
LABEL version="1.0"

# Install Python 3.12, curl, fonts (minimal - no pip/venv/dev)
RUN apt-get update && apt-get install -y \
    python3.12 \
    libgomp1 \
    ca-certificates \
    curl \
    fontconfig \
    fonts-noto-cjk \
    fonts-noto-cjk-extra \
    wget \
    xz-utils \
    && fc-cache -fv \
    && rm -rf /var/lib/apt/lists/*

# Install static ffmpeg (for pydub audio processing)
RUN wget -q https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar xf ffmpeg-release-amd64-static.tar.xz && \
    cp ffmpeg-*/ffmpeg /usr/local/bin/ffmpeg && \
    cp ffmpeg-*/ffprobe /usr/local/bin/ffprobe && \
    chmod +x /usr/local/bin/ffmpeg /usr/local/bin/ffprobe && \
    rm -rf ffmpeg-release-amd64-static.tar.xz ffmpeg-*

# Set Python 3.12 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# ========================================
# Stage 3: Copy Model from Downloader Stage
# ========================================
# Copy only the model files (not the venv or other build artifacts)
COPY --from=model-downloader /tmp/whisper_models /tmp/whisper_models

# ========================================
# Stage 5: Setup Working Directory
# ========================================
WORKDIR /app

# Create data directories
RUN mkdir -p /tmp/uploads /app/data /app/output

# Expose port for FastAPI
EXPOSE 8000

# ========================================
# Verification
# ========================================
RUN echo "=== Base Image Build Verification ===" && \
    echo "Python: $(python --version)" && \
    echo "Model files:" && \
    ls -lah /tmp/whisper_models/ && \
    echo "======================================="

LABEL build_date="2024-12-31"
LABEL faster_whisper_model="large-v3-turbo"
LABEL cuda_version="12.9.1"
LABEL cudnn_version="9"
