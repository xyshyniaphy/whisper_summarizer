# Frontend Test Dockerfile - テスト用パッケージ追加版
# ベース: 既存のfrontend/Dockerfileと同じ構成 + テストパッケージ

# ========================================
# Stage 1: Dependencies Installer
# ========================================
FROM node:20-alpine AS deps

WORKDIR /app

# package.jsonをコピー
COPY frontend/package.json ./

# 依存関係をインストール
RUN npm install

# テスト用パッケージを追加インストール
RUN npm install --save-dev \
    vitest@^2.1.8 \
    @testing-library/react@^16.1.0 \
    @testing-library/jest-dom@^6.6.3 \
    @testing-library/user-event@^14.5.2 \
    jsdom@^25.0.1 \
    @vitest/ui@^2.1.8 \
    @vitest/coverage-v8@^2.1.8

# ========================================
# Stage 2: Test Runtime
# ========================================
FROM node:20-alpine AS test

WORKDIR /app

# 依存関係をコピー（テストパッケージ含む）
COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .

EXPOSE 3000

CMD ["npm", "run", "test"]
