# Base image with faster-whisper and CUDA cuDNN
FROM whisper-summarizer-fastwhisper-base:latest

WORKDIR /app

# Install pip (base image is minimal runtime only)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Break out of externally managed environment (Ubuntu/Debian PEP 668)
RUN rm -f /usr/lib/python3.12/EXTERNALLY-MANAGED

# Install additional Python dependencies
COPY requirements.txt .
RUN uv pip install --system --no-cache-dir -r requirements.txt

# Copy application
COPY ./app ./app

# Create data directory (shared with server via volume mount)
RUN mkdir -p /app/data/uploads /app/data/transcribes

# Health check
HEALTHCHECK --interval=60s --timeout=30s --start-period=30s --retries=3 \
    CMD pgrep -f "python.*poller" || exit 1

# Run poller (this is a long-running process)
CMD ["python", "-m", "app.worker.poller"]
