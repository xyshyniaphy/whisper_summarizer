# Frontend Dockerfile - React + TypeScript + Vite
# マルチステージビルドで開発・本番両対応

# ========================================
# Stage 1: Dependencies Installer
# ========================================
FROM node:20-alpine AS deps

WORKDIR /app

# package.jsonをコピー
COPY package.json ./

# 依存関係をインストール (package-lock.jsonがない場合は生成)
RUN npm install

# ========================================
# Stage 2: Builder (本番用)
# ========================================
FROM node:20-alpine AS builder

WORKDIR /app

# 依存関係をコピー
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Viteビルド
RUN npm run build

# ========================================
# Stage 3: Production Runtime (Nginx)
# ========================================
FROM nginx:alpine AS production

# Nginxの設定ファイルをコピー
COPY nginx.conf /etc/nginx/conf.d/default.conf

# ビルド成果物をコピー
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# ========================================
# Stage 4: Development Runtime (Vite Dev Server)
# ========================================
FROM node:20-alpine AS development

WORKDIR /app

# 依存関係をコピー
COPY --from=deps /app/node_modules ./node_modules
COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
