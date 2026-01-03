# Backend Test Dockerfile
# Base: whisper-summarizer-fastwhisper-base (CUDA cuDNN + Python + Model)

# Use the fastwhisper base image
FROM whisper-summarizer-fastwhisper-base:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Install uv for package management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# Copy requirements.txt
COPY backend/requirements.txt .

# Create venv and install dependencies
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install backend dependencies
RUN uv pip install -r requirements.txt

# Install test dependencies
RUN uv pip install \
    pytest==8.3.4 \
    pytest-asyncio==0.25.0 \
    pytest-cov==6.0.0 \
    pytest-mock==3.14.0

# Copy backend code
COPY backend/ .

# Expose FastAPI port
EXPOSE 8000

# Default command: run pytest
CMD ["pytest"]
