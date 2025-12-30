# E2E Test Dockerfile
FROM mcr.microsoft.com/playwright:v1.41.0-focal

WORKDIR /app

# package.jsonとpackage-lock.jsonをコピー
COPY package.json ./

# 依存関係をインストール
RUN npm install

# テストコードをコピー
COPY . .

# Playwrightブラウザは既にベースイメージに含まれている
CMD ["npx", "playwright", "test"]
