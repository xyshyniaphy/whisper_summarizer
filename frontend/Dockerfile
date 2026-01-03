# Frontend Dockerfile - React + TypeScript + Vite
# マルチステージビルドで開発・本番両対応

# Build arguments for Vite environment variables
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY

# ========================================
# Stage 1: Dependencies Installer
# ========================================
FROM oven/bun:1-alpine AS deps

WORKDIR /app

# package.jsonをコピー
COPY package.json bun.lockb* ./

# 依存関係をインストール (bun install)
RUN bun install

# ========================================
# Stage 2: Lint Stage (Quality Check)
# ========================================
FROM oven/bun:1-alpine AS lint

WORKDIR /app

# 依存関係をコピー
COPY --from=deps /app/node_modules ./node_modules
COPY package.json bun.lockb* ./
COPY eslint.config.ts ./
COPY tsconfig.json ./
COPY tsconfig.node.json ./

# ソースコードをコピー（Lint対象）
COPY src ./src

# ESLintとTypeScriptチェックを実行
RUN bun run lint
RUN bun run type-check

# ========================================
# Stage 3: Builder (本番用)
# ========================================
FROM oven/bun:1-alpine AS builder

# Declare build args again for this stage
ARG VITE_SUPABASE_URL
ARG VITE_SUPABASE_ANON_KEY

# Set as environment variables for Vite build
ENV VITE_SUPABASE_URL=${VITE_SUPABASE_URL}
ENV VITE_SUPABASE_ANON_KEY=${VITE_SUPABASE_ANON_KEY}

WORKDIR /app

# 依存関係をコピー
COPY --from=deps /app/node_modules ./node_modules
COPY . .

# Viteビルド
RUN bun run build

# ========================================
# Stage 4: Production Runtime (Nginx)
# ========================================
FROM nginx:alpine AS production

# Nginxの設定ファイルをコピー
COPY nginx.conf /etc/nginx/conf.d/default.conf

# ビルド成果物をコピー
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]

# ========================================
# Stage 5: Development Runtime (Vite Dev Server)
# ========================================
FROM oven/bun:1-alpine AS development

WORKDIR /app

# 依存関係をコピー
COPY --from=deps /app/node_modules ./node_modules
COPY . .

EXPOSE 3000

CMD ["bun", "run", "dev", "--", "--host", "0.0.0.0"]
