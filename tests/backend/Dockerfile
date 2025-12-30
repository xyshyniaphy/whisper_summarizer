# Backend Test Dockerfile - テスト用パッケージ追加版
# ベース: 既存のbackend/Dockerfileと同じ構成 + テストパッケージ

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
    && rm -rf /var/lib/apt/lists/*

# Python 3.12をデフォルトに設定
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

# uvをインストール
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# uvのパスを環境変数に追加
ENV PATH="/root/.local/bin:$PATH"

WORKDIR /app

# requirements.txtをコピー
COPY backend/requirements.txt .

# テスト用requirements.txtを作成
RUN echo "pytest==8.3.4" >> requirements-test.txt && \
    echo "pytest-asyncio==0.25.0" >> requirements-test.txt && \
    echo "pytest-cov==6.0.0" >> requirements-test.txt && \
    echo "pytest-mock==3.14.0" >> requirements-test.txt

# uvで依存関係をインストール (本番 + テスト)
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install -r requirements.txt && \
    uv pip install -r requirements-test.txt

# ========================================
# Stage 2: Runtime (whisper-summarizer-whispercpp)
# ========================================
FROM whisper-summarizer-whispercpp:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# ランタイム依存関係のみインストール
RUN apt-get update && apt-get install -y \
    python3.12 \
    libgomp1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python 3.12をデフォルトに設定
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

WORKDIR /app

# venvをコピー (uvでビルド済み、テストパッケージ含む)
COPY --from=builder /opt/venv /opt/venv

# アプリケーションコードをコピー
COPY backend/ .

# データディレクトリを作成
RUN mkdir -p /tmp/uploads /app/data /app/output

# ポート公開
EXPOSE 8000

# エントリーポイントとコマンドを明示的に設定
ENTRYPOINT []
CMD ["pytest"]
