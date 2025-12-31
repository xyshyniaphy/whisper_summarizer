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

# 依存関係ファイルをコピー
COPY requirements.txt .
COPY pyproject.toml .

# uvで依存関係をインストール (venv作成) - 本番用のみ
RUN uv venv /opt/venv && \
    . /opt/venv/bin/activate && \
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
# Stage 3: Runtime (whisper-summarizer-whispercpp)
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
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js 22 LTS for Marp CLI
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && \
    apt-get install -y nodejs && \
    npm install -g @marp-team/marp-cli && \
    node --version && npm --version && marp --version

# Install Chromium for Marp CLI (using direct download for Docker compatibility)
RUN apt-get update && apt-get install -y \
    wget gnupg \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/googlechrome-linux-keyring.gpg \
    && sh -c 'echo "deb [arch=amd64 signed-by=/usr/share/keyrings/googlechrome-linux-keyring.gpg] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list' \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set Chrome path for Marp/Puppeteer
ENV CHROME_PATH=/usr/bin/google-chrome
ENV CHROME_BIN=/usr/bin/google-chrome
ENV PUPPETEER_SKIP_CHROMIUM_DOWNLOAD=true
ENV PUPPETEER_EXECUTABLE_PATH=/usr/bin/google-chrome

# Python 3.12をデフォルトに設定
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.12 1 && \
    update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.12 1

WORKDIR /app

# venvをコピー (本番用依存関係のみ、Ruffなし)
COPY --from=builder /opt/venv /opt/venv

# アプリケーションコードをコピー
COPY . .

# データディレクトリを作成
RUN mkdir -p /tmp/uploads /app/data /app/output

# ポート公開
EXPOSE 8000

# エントリーポイントとコマンドを明示的に設定
ENTRYPOINT []
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
