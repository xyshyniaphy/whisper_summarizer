# Whisper Summarizer

音声文字起こし・要約システム - GLM4.7 & Supabase統合版

## 概要

Whisper Summarizerは、音声ファイルを自動で文字起こしし、AI(GLM4.7)による要約を生成するWebアプリケーションです。

### 主な機能

- **音声文字起こし**: Whisper.cpp (v3-turbo) によるCPU処理
- **AI要約生成**: GLM4.7による高品質な要約
- **ユーザー認証**: Supabase Authによる安全な認証
- **マイクロサービス構成**: Docker Composeによる統合環境

### 技術スタック

| コンポーネント | 技術 |
|---|---|
| フロントエンド | React 19 + TypeScript + Vite + Mantine |
| バックエンド | FastAPI + Python 3.12 |
| 音声処理 | Whisper.cpp (CPU専用) |
| AI要約 | GLM4.7 API |
| 認証 | Supabase Auth |
| データベース | PostgreSQL 16 |
| コンテナ | Docker + Docker Compose |

## セットアップ

### 前提条件

- Docker & Docker Compose
- Supabaseプロジェクト (https://supabase.com)
- GLM4.7 APIキー

### 環境変数の設定

1. `.env.sample`をコピーして`.env`を作成:
```bash
cp .env.sample .env
```

2. `.env`を編集して以下を設定:
```bash
# Supabase設定 (Supabaseダッシュボードから取得)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# GLM4.7 API設定
GLM_API_KEY=your_glm_api_key
GLM_API_ENDPOINT=https://api.glm.ai/v1
GLM_MODEL=glm-4.0-turbo

# データベース (デフォルト値で可)
POSTGRES_DB=whisper_summarizer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres
```

### Whisper.cppベースイメージのビルド (オプション)

初回起動時や、Whisper.cppのDockerfileを変更した場合:

```bash
# Whisper.cppベースイメージをビルド
./build_whisper.sh

# キャッシュなしでビルド
./build_whisper.sh --no-cache
```

### 開発環境の起動

**方法1: スクリプトを使用 (推奨)**

```bash
# フォアグラウンドで起動
./run_dev.sh

# バックグラウンドで起動
./run_dev.sh up-d

# ログを表示
./run_dev.sh logs

# 停止
./run_dev.sh down

# その他のコマンド
./run_dev.sh         # ヘルプ表示
```

`run_dev.sh`は以下をチェックします:
- `.env`ファイルの存在
- 必須環境変数の設定 (SUPABASE_URL, GLM_API_KEY等)

**方法2: Docker Composeを直接使用**

```bash
# 開発環境を起動 (ホットリロード有効)
docker-compose -f docker-compose.dev.yml up --build

# バックグラウンドで起動
docker-compose -f docker-compose.dev.yml up -d --build
```

### アクセスURL

| サービス | URL |
|---|---|
| フロントエンド | http://localhost:3000 |
| バックエンドAPI | http://localhost:8000 |
| API ドキュメント | http://localhost:8000/docs |
| Whisper.cppサービス | http://localhost:8001 |
| PostgreSQL | localhost:5432 |

### 本番環境の起動

```bash
# 本番環境を起動
docker-compose up -d --build

# ログを確認
docker-compose logs -f
```

## ディレクトリ構造

```
whisper_summarizer/
├── frontend/              # Reactフロントエンド
│   ├── src/
│   │   ├── components/   # UIコンポーネント
│   │   ├── pages/        # ページコンポーネント
│   │   ├── services/     # Supabaseクライアント
│   │   ├── hooks/        # カスタムフック (useAuth等)
│   │   └── types/        # TypeScript型定義
│   ├── Dockerfile
│   └── package.json
│
├── backend/               # FastAPIバックエンド
│   ├── app/
│   │   ├── api/          # APIエンドポイント
│   │   ├── core/         # 設定・Supabase・GLM統合
│   │   ├── models/       # データベースモデル
│   │   └── schemas/      # Pydanticスキーマ
│   ├── Dockerfile
│   └── requirements.txt
│
├── whispercpp/            # Whisper.cpp音声処理
│   ├── process_audio.py  # FastAPIサーバー
│   ├── entrypoint.sh     # 起動スクリプト
│   ├── Dockerfile        # マルチステージビルド
│   ├── data/             # 入力音声ファイル
│   ├── output/           # 文字起こし結果
│   └── models/           # Whisperモデル (ビルド時)
│
├── docker-compose.yml     # 本番環境
├── docker-compose.dev.yml # 開発環境
└── .env.sample           # 環境変数テンプレート
```

## クイックスタート

```bash
# 1. 環境変数を設定
cp .env.sample .env
# .envを編集してSupabaseとGLM4.7のAPIキーを設定

# 2. 開発環境を起動
./run_dev.sh up-d

# 3. ブラウザでアクセス
# http://localhost:3000
```

詳細は以下のセクションを参照してください。

---

## 使い方

### 1. ユーザー登録

1. http://localhost:3000 にアクセス
2. 「サインアップ」をクリック
3. メールアドレスとパスワードを入力
4. Supabaseから確認メールが届くので、リンクをクリック

### 2. ログイン

1. メールアドレスとパスワードでログイン
2. ダッシュボードにリダイレクト

### 3. 音声ファイルのアップロード (実装中)

- サポート形式: m4a, mp3, wav, aac, flac, ogg
- 最大ファイルサイズ: 未設定

### 4. 文字起こし・要約の確認 (実装中)

- 文字起こし結果をタイムスタンプ付きで表示
- GLM4.7による要約を表示

## 開発

### ホットリロード

開発環境では、ソースコードの変更が即座に反映されます:

- **フロントエンド**: `./frontend` → Vite Dev Server
- **バックエンド**: `./backend` → Uvicorn --reload
- **Whisper.cpp**: `./whispercpp` → Uvicorn --reload

### ログの確認

```bash
# 全サービスのログ
docker-compose -f docker-compose.dev.yml logs -f

# 特定のサービスのログ
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml logs -f frontend
docker-compose -f docker-compose.dev.yml logs -f whispercpp
```

### コンテナに入る

```bash
# バックエンドコンテナ
docker-compose -f docker-compose.dev.yml exec backend bash

# フロントエンドコンテナ
docker-compose -f docker-compose.dev.yml exec frontend sh
```

## API仕様

詳細なAPI仕様は、http://localhost:8000/docs で確認できます。

### 主要エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| POST | `/api/auth/signup` | ユーザー登録 |
| POST | `/api/auth/login` | ログイン |
| POST | `/api/auth/logout` | ログアウト |
| GET | `/api/users/me` | 現在のユーザー情報 |
| POST | `/api/audio/upload` | 音声アップロード |
| GET | `/api/transcriptions` | 文字起こしリスト |

## トラブルシューティング

### ポートが既に使用されている

```bash
# 使用中のポートを確認
sudo lsof -i :3000
sudo lsof -i :8000
sudo lsof -i :8001

# プロセスを終了
sudo kill -9 <PID>
```

### Dockerイメージを再ビルド

```bash
# キャッシュなしでビルド
docker-compose -f docker-compose.dev.yml build --no-cache

# 全てのボリュームを削除して再起動
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up --build
```

### Whisper.cppモデルのダウンロードエラー

Dockerイメージのビルド時にモデルダウンロードが失敗する場合:

1. 手動でモデルをダウンロード:
```bash
cd whispercpp/models
wget https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-large-v3-turbo.bin
```

2. Dockerfileを編集してCOPYに変更

## ライセンス

MIT License

## リンク

- [Whisper.cpp](https://github.com/ggerganov/whisper.cpp)
- [Supabase](https://supabase.com)
- [FastAPI](https://fastapi.tiangolo.com)
- [React](https://react.dev)
