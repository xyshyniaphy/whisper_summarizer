# Backend Dockerfile - FastAPI + Python 3.12 + Ubuntu 24.04
# マルチステージビルドで依存関係をキャッシュ

# ========================================
# Stage 1: Dependencies Builder
# ========================================
FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Python 3.12とビルドツールのインストール
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Python 3.12をデフォルトに設定
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

WORKDIR /build

# requirements.txtをコピーして依存関係をインストール
COPY requirements.txt .
RUN pip3 install --no-cache-dir --user -r requirements.txt

# ========================================
# Stage 2: Runtime
# ========================================
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PATH=/root/.local/bin:$PATH

# Python 3.12ランタイムのみインストール
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    && rm -rf /var/lib/apt/lists/*

# Python 3.12をデフォルトに設定
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

WORKDIR /app

# ビルドステージから依存関係をコピー
COPY --from=builder /root/.local /root/.local

# アプリケーションコードをコピー
COPY . .

# ポート公開
EXPOSE 8000

# Uvicornでアプリケーションを起動
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
