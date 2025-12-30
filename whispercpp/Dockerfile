# Whisper.cpp Dockerfile - 純粋なC++バイナリイメージ + 静的FFmpeg
# CPU専用 + v3-turbo ct2モデル事前ダウンロード

# ========================================
# Stage 1: Model Downloader
# ========================================
FROM ubuntu:24.04 AS model-downloader

ENV DEBIAN_FRONTEND=noninteractive

# 基本ツールのインストール
RUN apt-get update && apt-get install -y \
    wget \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /models

# Whisper v3-turbo ct2モデルをダウンロード
RUN wget -O ggml-large-v3-turbo.bin \
    https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin

# ========================================
# Stage 2: FFmpeg Downloader
# ========================================
FROM ubuntu:24.04 AS ffmpeg-downloader

ENV DEBIAN_FRONTEND=noninteractive

# 基本ツールのインストール
RUN apt-get update && apt-get install -y \
    wget \
    xz-utils \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp

# 静的FFmpegバイナリをダウンロード
RUN wget https://johnvansickle.com/ffmpeg/releases/ffmpeg-release-amd64-static.tar.xz && \
    tar xf ffmpeg-release-amd64-static.tar.xz && \
    mkdir -p /ffmpeg-bin && \
    find . -name "ffmpeg" -exec cp {} /ffmpeg-bin/ffmpeg \; && \
    find . -name "ffprobe" -exec cp {} /ffmpeg-bin/ffprobe \; && \
    chmod +x /ffmpeg-bin/ffmpeg /ffmpeg-bin/ffprobe

# ========================================
# Stage 3: Builder
# ========================================
FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# ビルドツールのインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    cmake \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Whisper.cppをクローン
RUN git clone https://github.com/ggerganov/whisper.cpp.git .

# CMakeでビルド
RUN mkdir build && \
    cd build && \
    cmake .. && \
    cmake --build . --config Release

# ========================================
# Stage 4: Runtime (最小構成)
# ========================================
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive

# 最小限のランタイム依存関係のみインストール
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 静的FFmpegバイナリをコピー
COPY --from=ffmpeg-downloader /ffmpeg-bin/ffmpeg /usr/local/bin/ffmpeg
COPY --from=ffmpeg-downloader /ffmpeg-bin/ffprobe /usr/local/bin/ffprobe

# Whisper.cppバイナリをコピー
COPY --from=builder /build/build/bin/whisper-cli /usr/local/bin/whisper-cli

# 共有ライブラリをコピー (libwhisper.so, libggml.so など)
COPY --from=builder /build/build/src/libwhisper.so* /usr/lib/
COPY --from=builder /build/build/ggml/src/libggml*.so* /usr/lib/

# ライブラリキャッシュを更新
RUN ldconfig


# モデルをコピー
COPY --from=model-downloader /models/ggml-large-v3-turbo.bin /usr/local/share/whisper-models/

# データディレクトリを作成
RUN mkdir -p /app/data /app/output

# エントリーポイントはWhisper.cppバイナリ
# エントリーポイントはWhisper.cppバイナリ
ENTRYPOINT ["/usr/local/bin/whisper-cli"]


# デフォルトコマンド (ヘルプ表示)
CMD ["--help"]
