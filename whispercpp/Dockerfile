# Whisper.cpp Dockerfile - マルチステージビルド
# Ubuntu 24.04 + Python 3.12 + CPU専用 + v3-turbo ct2モデル

# ========================================
# Stage 1: Model Downloader
# ========================================
FROM ubuntu:24.04 AS model-downloader

ENV DEBIAN_FRONTEND=noninteractive

# 基本ツールのインストール
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /models

# Whisper v3-turbo ct2モデルをダウンロード
# Hugging Faceから直接ダウンロード
RUN wget -O ggml-large-v3-turbo.bin \
    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin

# ========================================
# Stage 2: Builder
# ========================================
FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# ビルドツールのインストール (C++コンパイラ、make、git)
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Whisper.cppをクローン
RUN git clone https://github.com/ggerganov/whisper.cpp.git .

# CPU専用でビルド (CUDAなし)
RUN make

# ========================================
# Stage 3: Runtime
# ========================================
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

# Python 3.12とランタイム依存関係のインストール
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    python3-pip \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Python 3.12をデフォルトに設定
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

WORKDIR /app

# ビルド済みバイナリとモデルをコピー
COPY --from=builder /build/main /app/whisper-main
COPY --from=model-downloader /models/ggml-large-v3-turbo.bin /app/models/

# Python依存関係のインストール
RUN pip3 install --no-cache-dir \
    fastapi \
    uvicorn[standard] \
    python-multipart \
    httpx \
    pydantic

# 音声処理スクリプトをコピー
COPY process_audio.py /app/
COPY entrypoint.sh /app/

# 実行権限を付与
RUN chmod +x /app/entrypoint.sh

# データディレクトリを作成
RUN mkdir -p /app/data /app/output

# ポート公開
EXPOSE 8001

# エントリーポイント
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["python", "process_audio.py"]
