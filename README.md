# Whisper Summarizer

音声文字起こし・要約システム - GLM4.7 & Supabase統合版

## 概要

Whisper Summarizerは、音声ファイルを自動で文字起こしし、AI(GLM4.7)による要約を生成するWebアプリケーションです。

### 主な機能

- **音声文字起こし**: Whisper.cpp (v3-turbo) によるCPU処理
- **AI要約生成**: GLM4.7による高品質な要約
- **音声管理**: アップロードした音声と文字起こし結果の削除機能
- **ユーザー認証**: Supabase Authによる安全な認証
- **マイクロサービス構成**: Docker Composeによる統合環境

### 技術スタック

| コンポーネント | 技術 |
|---|---|
| フロントエンド | React 19 + TypeScript + Vite + Mantine |
| バックエンド | FastAPI + Python 3.12 + uv |
| 音声処理 | Whisper.cpp v3-turbo (CPU専用) + 静的FFmpeg |
| AI要約 | GLM4.7 API |
| 認証 | Supabase Auth |
| データベース | Supabase PostgreSQL (マネージド) |
| コンテナ | Docker + Docker Compose |

### Dockerイメージサイズ

| イメージ | サイズ | 説明 |
|---|---|---|
| whisper-summarizer-whispercpp | 3.46GB | Whisper.cpp + 静的FFmpeg + v3-turboモデル |
| whisper_summarizer-backend | 3.68GB | FastAPI + Python + Whisper.cpp統合 |
| whisper_summarizer-frontend | 380MB | React + Vite (開発) / Nginx (本番) |

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

# Supabase PostgreSQL接続文字列
# SupabaseダッシュボードのSettings > Database > Connection Stringから取得
DATABASE_URL=postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres

# Whisper設定
WHISPER_LANGUAGE=zh  # 文字起こし言語 (zh, ja, en 等)
WHISPER_THREADS=4    # Whisper処理に使用するスレッド数 (CPUコア数に合わせて調整)
```

### Whisper.cppベースイメージのビルド

Whisper.cppベースイメージは初回起動時に自動ビルドされますが、手動でビルドすることも可能です:

```bash
# Whisper.cppベースイメージをビルド (キャッシュ使用)
./build_whisper.sh

# キャッシュなしでビルド
./build_whisper.sh --no-cache
```

**イメージの特徴:**
- サイズ: 3.46GB (静的FFmpeg使用により28%削減)
- v3-turbo ct2モデル事前ダウンロード
- CPU専用ビルド
- 静的FFmpeg (77MB) + FFprobe統合

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
├── whispercpp/            # Whisper.cppベースイメージ
│   ├── Dockerfile        # マルチステージビルド (静的FFmpeg統合)
│   └── models/           # Whisperモデル (ビルド時ダウンロード)
│
├── data/                 # データ保存用 (Dockerボリュームマウント)
│   ├── uploads/          # アップロードされた音声ファイル
│   └── output/           # 文字起こし結果
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

### 5. 音声の削除 (New)

- 文字起こし履歴リストから、不要なアイテムを削除できます (ゴミ箱アイコン)
- 関連する音声ファイルと文字起こしデータもサーバーから削除されます



## 開発

### 便利なスクリプト

`run_dev.sh`は開発環境の管理を簡単にします:

```bash
# フォアグラウンドで起動 (ログをリアルタイム表示)
./run_dev.sh

# バックグラウンドで起動
./run_dev.sh up-d

# ログを表示
./run_dev.sh logs

# コンテナの状態を確認
./run_dev.sh ps

# 再起動
./run_dev.sh restart

# 停止
./run_dev.sh down

# 全削除 (ボリューム含む)
./run_dev.sh clean

# キャッシュなしで再ビルド
./run_dev.sh rebuild
```

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

## テスト

プロジェクトには包括的な自動テストが実装されています。

### バックエンドテスト (Pytest)

```bash
# テストを実行
cd backend
uv run pytest

# 特定のテストを実行
uv run pytest ../tests/backend/api/test_auth_api.py

# マーカーでフィルター
uv run pytest -m unit          # 単体テストのみ
uv run pytest -m integration   # 統合テストのみ
```

### フロントエンドテスト (Vitest)

```bash
# テストを実行
cd frontend
npm test

# ウォッチモード
npm test -- --watch
```

### E2Eテスト (Playwright)

```bash
# 依存関係をインストール
cd tests/e2e
npm install

# Playwrightブラウザをインストール (初回のみ)
npx playwright install

# E2Eテストを実行 (開発環境が起動している必要がある)
npm test
```

**注意**: E2Eテストを実行する前に、開発環境を起動してください:
```bash
./run_dev.sh up-d
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
