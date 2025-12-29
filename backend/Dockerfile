# Backend Dockerfile - FastAPI + Python 3.12 + uv + Whisper.cpp
# マルチステージビルド: uvで高速化、Whisper.cppバイナリ統合

# ========================================
# Stage 1: Whisper.cpp Base
# ========================================
FROM whisper-summarizer-whispercpp:latest AS whispercpp

# ========================================
# Stage 2: UV Builder
# ========================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# requirements.txtをコピー
COPY requirements.txt .

# uvで依存関係をインストール (venv作成)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install -r requirements.txt

# ========================================
# Stage 3: Runtime
# ========================================
FROM python:3.12-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# FFmpegとランタイム依存関係をインストール
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# venvをコピー (uvでビルド済み)
COPY --from=builder /opt/venv /opt/venv

# Whisper.cppバイナリとモデルをコピー
COPY --from=whispercpp /app/whisper-main /app/whisper-main
COPY --from=whispercpp /app/models /app/models

# アプリケーションコードをコピー
COPY . .

# データディレクトリを作成
RUN mkdir -p /tmp/uploads /app/data /app/output

# ポート公開
EXPOSE 8000

# Uvicornでアプリケーションを起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
