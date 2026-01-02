# Backend Dockerfile - FastAPI + Python 3.12 + uv
# ビルダー: Ubuntu 24.04 + uv
# ランタイム: whisper-summarizer-fastwhisper-base (CUDA cuDNN + Model + Marp)

# Build argument for base image (allows overriding if needed)
ARG BASE_IMAGE=whisper-summarizer-fastwhisper-base:latest

# ========================================
# Stage 1: UV Builder (Ubuntu 24.04)
# ========================================
FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Python 3.12とuvのインストール
RUN apt-get update && apt-get install -y \
    python3.12 \
    curl \
    ca-certificates \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

# Python 3.12をデフォルトに設定
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# uvをインストール
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# uvのパスを環境変数に追加
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# 依存関係ファイルをコピー
COPY requirements.txt .
COPY pyproject.toml .

# uvで依存関係をインストール (venv作成) - 本番用のみ
# Note: faster-whisper is in base image, but we include it here for consistency
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install python-docx && \
    uv pip install APScheduler>=3.10.0 && \
    uv pip install -r requirements.txt

# ========================================
# Stage 2: Lint Stage (Quality Check)
# ========================================
FROM ubuntu:24.04 AS lint

ENV DEBIAN_FRONTEND=noninteractive
ENV PATH="/root/.local/bin:$PATH"

# Python 3.12とuvのインストール
RUN apt-get update && apt-get install -y \
    python3.12 \
    curl \
    ca-certificates \
    pandoc \
    && rm -rf /var/lib/apt/lists/*

RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

RUN curl -LsSf https://astral.sh/uv/install.sh | sh

WORKDIR /app

# venvをコピー
COPY --from=builder /opt/venv /opt/venv

# 依存関係ファイルをコピー
COPY pyproject.toml .

# ソースコードをコピー（Lint対象）
COPY app ./app

# RuffによるLintとFormatチェックを実行
RUN . /opt/venv/bin/activate && uv pip install ruff && \
    ruff check . && \
    ruff format --check .

# ========================================
# Stage 3: Runtime (Base image with CUDA cuDNN + Model + Marp)
# ========================================
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# Python 3.12, CUDA cuDNN, faster-whisper model, Marp CLI, Chrome are already in base image
# Just need to add application-specific dependencies to the existing venv

WORKDIR /app

# Copy venv from builder stage
COPY --from=builder /opt/venv /opt/venv

# アプリケーションコードをコピー
COPY . .

# データディレクトリを作成 (already in base image, but ensuring)
RUN mkdir -p /tmp/uploads /app/data /app/output

# ポート公開
EXPOSE 8000

# エントリーポイントとコマンドを明示的に設定
ENTRYPOINT []
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
