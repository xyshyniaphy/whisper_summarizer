# Backend Dockerfile - FastAPI + Python 3.12 + uv + Whisper.cpp統合
# ビルダー: Ubuntu 24.04 + uv
# ランタイム: whisper-summarizer-whispercpp (Whisper.cpp + FFmpeg含む)

# ========================================
# Stage 1: UV Builder (Ubuntu 24.04)
# ========================================
FROM ubuntu:24.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Python 3.12とuvのインストール (pip, venvはaptでインストールしない)
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
COPY requirements.txt .

# uvで依存関係をインストール (venv作成)
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
    uv pip install -r requirements.txt

# ========================================
# Stage 2: Runtime (whisper-summarizer-whispercpp)
# ========================================
FROM whisper-summarizer-whispercpp:latest

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PATH="/opt/venv/bin:$PATH"

# ランタイム依存関係のみインストール (Python本体はインストールしない -> ユーザー指示によりaptでインストール)
# 指示: install python 3.12 from apt only, do not install pip , do not install venv.
RUN apt-get update && apt-get install -y \
    python3.12 \
    libgomp1 \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Python 3.12をデフォルトに設定 (venvのsymlink先 /usr/bin/python を確保するため必須)
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

WORKDIR /app

# venvをコピー (uvでビルド済み)
COPY --from=builder /opt/venv /opt/venv

# アプリケーションコードをコピー
COPY . .

# データディレクトリを作成
RUN mkdir -p /tmp/uploads /app/data /app/output

# ポート公開
EXPOSE 8000

# エントリーポイントとコマンドを明示的に設定 (Whisper.cppベースイメージのENTRYPOINTを上書き)
ENTRYPOINT []
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
