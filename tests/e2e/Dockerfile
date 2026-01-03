# E2E Test Dockerfile
FROM mcr.microsoft.com/playwright:v1.41.0-focal

WORKDIR /app

# Install bun
RUN npm install -g bun

# package.jsonとbun.lockbをコピー
COPY package.json ./

# 依存関係をインストール
RUN bun install

# テストコードをコピー
COPY . .

# Playwrightブラウザは既にベースイメージに含まれている
CMD ["bun", "run", "test"]
