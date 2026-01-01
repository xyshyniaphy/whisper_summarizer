# Whisper Summarizer

音声文字起こし・要約システム - faster-whisper (cuDNN) & Supabase統合版

## 概要

Whisper Summarizerは、音声ファイルを自動で文字起こしし、Google Gemini 2.0 Flash APIによる要約を生成するWebアプリケーションです。

### 主な機能

- **音声文字起こし**: faster-whisper (CTranslate2 + cuDNN) によるGPU加速処理
- **AI要約生成**: Google Gemini 2.0 Flash による高品質な要約
- **音声管理**: アップロードした音声と文字起こし結果の削除機能
- **ユーザー認証**: Supabase Authによる安全な認証
- **Docker Compose**: シンプルな2コンテナ構成

### 技術スタック

| コンポーネント | 技術 |
|---|---|
| フロントエンド | React 19 + TypeScript + Vite + Tailwind CSS |
| ステート管理 | Jotai (atomic state) |
| UIコンポーネント | Tailwind CSS + lucide-react (icons) |
| バックエンド | FastAPI + Python 3.12 + uv |
| 音声処理 | faster-whisper (CTranslate2 + cuDNN) |
| AI要約 | Google Gemini 2.0 Flash |
| 認証 | Supabase Auth (JWT) |
| データベース | PostgreSQL 18 Alpine (開発) / Supabase PostgreSQL (本番) |
| ファイル保存 | ローカルファイルシステム (gzip圧縮) |
| コンテナ | Docker + Docker Compose |

### Dockerイメージサイズ

| イメージ | サイズ | 説明 |
|---|---|---|
| whisper_summarizer-backend | ~8GB | FastAPI + Python + CUDA cuDNN Runtime + faster-whisper |
| whisper_summarizer-frontend | 380MB | React + Vite (開発) / Nginx (本番) |
| postgres | ~250MB | PostgreSQL 18 Alpine (開発のみ) |

**アーキテクチャ改善:**
- whisper.cpp (3.46GB) の別コンテナが不要に
- faster-whisperはPythonライブラリとしてバックエンドに統合
- cuDNN最適化カーネルによりGPU性能が向上 (40-60x vs 20-30x)

## セットアップ

### 前提条件

- Docker & Docker Compose
- Supabaseプロジェクト (https://supabase.com)
- Google Gemini APIキー

**GPUオプション（推奨）:**
- NVIDIA GPU (Compute Capability 7.0+、RTX 3080推奨)
- NVIDIA Driver 470+ (CUDA 11.4+)
- nvidia-container-toolkit (インストール方法: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html)

**GPUはデフォルトで有効** - バックエンドは `nvidia/cuda:12.9.1-cudnn-runtime-ubuntu24.04` ベースイメージを使用します。CPUのみを使用する場合は `.env` で設定変更可能です。

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

# Google Gemini API設定 (要約生成用)
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-2.0-flash-exp  # 使用モデル (gemini-2.0-flash-exp, gemini-1.5-pro 等)
REVIEW_LANGUAGE=zh                 # 要約生成言語 (zh, ja, en)
GEMINI_API_ENDPOINT=               # オプション: カスタムエンドポイントを使用する場合のみ設定

# データベース設定 (開発環境ではPostgreSQL 18 Alpineを使用)
# 本番環境でSupabase PostgreSQLを使用する場合はDATABASE_URLを設定してください
POSTGRES_DB=whisper_summarizer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# バックエンド設定
CORS_ORIGINS=http://localhost:3000

# faster-whisper設定 (GPU加速)
FASTER_WHISPER_DEVICE=cuda              # cuda (GPU) または cpu
FASTER_WHISPER_COMPUTE_TYPE=float16     # float16 (GPU), float32 (GPU), int8 (CPU)
FASTER_WHISPER_MODEL_SIZE=large-v3-turbo
WHISPER_LANGUAGE=zh                     # 文字起こし言語 (auto, zh, ja, en 等)
WHISPER_THREADS=4                       # 処理に使用するスレッド数

# Audio Chunking (長音声の高速文字起こし)
ENABLE_CHUNKING=true              # チャンキング機能の有効化
CHUNK_SIZE_MINUTES=10             # チャンクの長さ（分）- 推奨: CPUで5-10、GPUで10-15
CHUNK_OVERLAP_SECONDS=15          # チャンク間のオーバーラップ（秒）- VAD有効時15秒、固定分割時30秒
MAX_CONCURRENT_CHUNKS=4           # 並列処理するチャンク数 - GPU: 4-8推奨
USE_VAD_SPLIT=true                # 無音検出によるスマート分割
VAD_SILENCE_THRESHOLD=-30         # 無音と判定する閾値
VAD_MIN_SILENCE_DURATION=0.5      # 分割点として判定する最小無音時間（秒）
MERGE_STRATEGY=lcs                # マージ戦略: lcs（テキストベース）、timestamp（シンプル）
```

### ベースイメージのビルド（初回のみ）

**初回起動前に**、faster-whisperモデルとMarp CLIを含むベースイメージをビルドする必要があります:

```bash
# ベースイメージをビルド (~10-15分、モデルダウンロード含む)
./build_fastwhisper_base.sh

# 出力例:
# - Image: whisper-summarizer-fastwhisper-base:latest
# - Size: ~8-10 GB (CUDA cuDNN + 3GB model + Marp + Chrome)
```

**ベースイメージの内容:**
- NVIDIA CUDA 12.9.1 cuDNN Runtime
- Python 3.12 + uv + faster-whisper
- **事前ダウンロード済み** `large-v3-turbo` モデル (~3GB)
- Node.js 22 + Marp CLI + Chromium

**ベースイメージの再ビルドが必要な場合:**
- モデルの更新が必要な時
- Marp CLIのバージョンを更新する時
- 依存関係を大きく変更する時

```bash
# キャッシュなしで再ビルド
./build_fastwhisper_base.sh --no-cache
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
- 必須環境変数の設定 (SUPABASE_URL, GEMINI_API_KEY等)

### GPU設定の確認

**GPUはデフォルトで有効**です。以下のコマンドでGPUが使用されていることを確認できます:

```bash
# コンテナ内でGPUを確認
docker-compose -f docker-compose.dev.yml exec backend nvidia-smi

# バックエンドログでGPU使用状況を確認
docker-compose -f docker-compose.dev.yml logs backend | grep -i cuda
```

**CPUのみを使用する場合:**
`.env` で以下を設定:
```bash
FASTER_WHISPER_DEVICE=cpu
FASTER_WHISPER_COMPUTE_TYPE=int8
```

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
| バックエンドAPI | http://localhost:3000/api/* (Viteプロキシ経由) |
| API ドキュメント | http://localhost:3000/api/docs (Viteプロキシ経由) |

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
├── backend/               # FastAPIバックエンド (faster-whisper統合)
│   ├── app/
│   │   ├── api/          # APIエンドポイント
│   │   ├── services/     # faster-whisper + Gemini + Storage統合
│   │   ├── core/         # 設定・Supabase統合
│   │   ├── models/       # データベースモデル
│   │   └── schemas/      # Pydanticスキーマ
│   ├── Dockerfile        # CUDA cuDNN Runtimeベース
│   └── requirements.txt  # faster-whisper依存関係
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
# .envを編集してSupabaseとGoogle GeminiのAPIキーを設定

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

- 文字起こし結果をタイムスタンプ付きで表示 (最初の200行)
- Google Gemini 2.0 Flash による要約を表示 (Overview / Key Points / Details)
- ダウンロード機能 (テキスト形式 .txt / 字幕形式 .srt)

### 5. 音声の削除

- 文字起こし履歴リストから、不要なアイテムを削除できます (ゴミ箱アイコン)
- 削除条件:
  - **完了したアイテム**: いつでも削除可能
  - **失敗したアイテム**: いつでも削除可能
  - **処理中のアイテム**: 24時間経過後のみ削除可能
- 関連する音声ファイルと文字起こしデータもサーバーから削除されます
- データベースのカスケード削除により、関連する要約データやAPIログも自動的に削除されます



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

### キャッシュのクリア

`data/` ディレクトリ配下のアップロードファイル、出力ファイル、およびテスト結果（スクリーンショット、レポート）を一括で削除するには、以下のスクリプトを使用します:

```bash
./clear_cache.sh
```

### ホットリロード

開発環境では、ソースコードの変更が即座に反映されます:

- **フロントエンド**: `./frontend` → Vite Dev Server
- **バックエンド**: `./backend` → Uvicorn --reload (faster-whisperモデルは起動時にロード)

### ログの確認

```bash
# 全サービスのログ
docker-compose -f docker-compose.dev.yml logs -f

# 特定のサービスのログ
docker-compose -f docker-compose.dev.yml logs -f backend
docker-compose -f docker-compose.dev.yml logs -f frontend
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

### Dockerテスト環境 (推奨)

独立したDockerコンテナで全てのテストを実行できます:

```bash
cd tests

# 全てのテストを実行 (バックエンド + フロントエンド + E2E)
./run.sh all

# バックエンドテストのみ
./run.sh backend

# フロントエンドテストのみ
./run.sh frontend

# E2Eテストのみ (開発環境が必要)
./run.sh e2e

# テストイメージをビルド
./run.sh build

# テストコンテナとボリュームをクリーンアップ
./run.sh clean
```

**テスト結果の確認:**
- バックエンド: カバレッジレポートは `backend/htmlcov/index.html`
- フロントエンド: Vitestの標準出力
- E2E: Playwrightレポートは `tests/e2e/playwright-report/index.html` (ホスト側 `data/playwright-report/`)
- E2Eスクリーンショット: ホスト側 `data/screenshots/` (失敗時は `data/screenshots/failures/`)

**現在のカバレッジ状況:**
- バックエンド: **73.37%** (目標: 70%以上) ✅
- テスト総数: 19件 (全てパス)

### バックエンドテスト (Pytest)

ローカル環境でテストを実行する場合:

```bash
# テストを実行
cd backend
uv run pytest

# カバレッジ付きで実行
uv run pytest --cov=app --cov-report=html --cov-report=term

# 特定のテストを実行
uv run pytest ../tests/backend/api/test_auth_api.py

# マーカーでフィルター
uv run pytest -m unit          # 単体テストのみ
uv run pytest -m integration   # 統合テストのみ
```

**テストの構成:**
- `tests/backend/api/` - APIエンドポイントのテスト
- `tests/backend/services/` - サービスレイヤーのテスト
- `tests/backend/integration/` - 統合テスト

### フロントエンドテスト (Vitest)

```bash
# テストを実行
cd frontend
npm test

# ウォッチモード
npm test -- --watch

# カバレッジ付きで実行
npm test -- --coverage
```

**テストの構成:**
- `tests/frontend/hooks/` - カスタムフックのテスト
- `tests/frontend/components/` - コンポーネントのテスト

### E2Eテスト (Playwright)

```bash
# 依存関係をインストール
cd tests/e2e
npm install

# Playwrightブラウザをインストール (初回のみ)
npx playwright install

# E2Eテストを実行 (開発環境が起動している必要がある)
npm test

# UIモードで実行
npm run test:ui

# ヘッドフルモード (ブラウザを表示)
npm run test:headed
```

**注意**: E2Eテストを実行する前に、開発環境を起動してください:
```bash
./run_dev.sh up-d
```

**テストの構成:**
- `tests/e2e/tests/auth.spec.ts` - 認証フローのE2Eテスト
- `tests/e2e/tests/transcription.spec.ts` - 文字起こしフローのE2Eテスト

## API仕様

詳細なAPI仕様は、http://localhost:3000/api/docs で確認できます。

### 主要エンドポイント

| メソッド | パス | 説明 |
|---|---|---|
| POST | `/api/auth/signup` | ユーザー登録 |
| POST | `/api/auth/login` | ログイン |
| POST | `/api/auth/logout` | ログアウト |
| GET | `/api/users/me` | 現在のユーザー情報 |
| POST | `/api/audio/upload` | 音声アップロード |
| GET | `/api/transcriptions` | 文字起こしリスト |
| GET | `/api/transcriptions/{id}` | 文字起こし詳細 |
| DELETE | `/api/transcriptions/{id}` | 文字起こし削除 (カスケード) |
| POST | `/api/transcriptions/{id}/generate-pptx` | PPTX生成 (Marp) |
| GET | `/api/transcriptions/{id}/download?format=txt` | テキストダウンロード |
| GET | `/api/transcriptions/{id}/download?format=srt` | 字幕ダウンロード |
| GET | `/api/transcriptions/{id}/download?format=pptx` | PowerPointダウンロード |

## Audio Chunking (長音声の高速文字起こし)

長音声ファイル（10分以上）の文字起こし速度を向上させるため、チャンキング機能を実装しています。

### 機能概要

- **並列処理**: 音声を複数のチャンクに分割して同時に処理
- **VAD分割**: Voice Activity Detectionによる無音区間でのスマート分割
- **LCSマージ**: Longest Common Subsequenceアルゴリズムによるオーバーラップ領域の正確な結合

### パフォーマンス比較

**CPU (Intel/AMD) vs GPU (NVIDIA RTX 3080 with faster-whisper + cuDNN):**

| ファイル長 | CPU (並列数: 2) | GPU (並列数: 4-6) | 高速化 |
|-----------|----------------|-------------------|--------|
| 5分チャンク | ~15分 | ~15-20秒 | **40-60x** |
| 10分 | ~18分 | ~30-40秒 | **27-36x** |
| 20分 | ~36分 | ~1-1.5分 | **24-36x** |
| 60分 | ~108分 | ~3-4分 | **27-36x** |

※ faster-whisper with cuDNNはwhisper.cppより約2倍高速 (20-30x vs 40-60x)
※ 実際の速度はGPU性能、VRAM、言語、音質によって変動します

**チャンキング効果 (CPU):**

| ファイル長 | 従来 (単一) | チャンキング (並列数: 2) |
|-----------|------------|------------------------|
| 10分 | ~30分 | ~18分 (1.7x) |
| 20分 | ~60分 | ~36分 (1.7x) |
| 60分 | ~180分 | ~108分 (1.7x) |

※ GPUの場合、チャンキング効果はより顕著 (2-4x)

### 設定パラメータ

| パラメータ | デフォルト | 説明 |
|-----------|-----------|------|
| `ENABLE_CHUNKING` | true | チャンキング機能の有効化 |
| `CHUNK_SIZE_MINUTES` | 10 | チャンクの目標長さ（分） |
| `CHUNK_OVERLAP_SECONDS` | 15 | チャンク間のオーバーラップ（秒） |
| `MAX_CONCURRENT_CHUNKS` | 2 | 並列処理するチャンク数 |
| `USE_VAD_SPLIT` | true | 無音検出によるスマート分割 |
| `MERGE_STRATEGY` | lcs | マージ戦略 (`lcs` または `timestamp`) |

### 推奨設定

**faster-whisper (CPU only):**
```bash
FASTER_WHISPER_DEVICE=cpu
FASTER_WHISPER_COMPUTE_TYPE=int8
CHUNK_SIZE_MINUTES=10
MAX_CONCURRENT_CHUNKS=2
CHUNK_OVERLAP_SECONDS=15
USE_VAD_SPLIT=true
```

**faster-whisper (GPU with cuDNN - RTX 3080 etc.):**
```bash
FASTER_WHISPER_DEVICE=cuda
FASTER_WHISPER_COMPUTE_TYPE=float16
CHUNK_SIZE_MINUTES=15
MAX_CONCURRENT_CHUNKS=4-6      # RTX 3080 8GB: 4-6, RTX 3090 10GB+: 6-8
CHUNK_OVERLAP_SECONDS=15
USE_VAD_SPLIT=true
```

## トラブルシューティング

### GPUが認識されない

```bash
# ホストマシンでGPUを確認
nvidia-smi

# nvidia-container-runtimeがインストールされているか確認
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# コンテナ内でGPUを確認
docker-compose -f docker-compose.dev.yml exec backend nvidia-smi
```

**エラー: `could not select device driver`**
- nvidia-container-toolkitをインストール: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
- Dockerデーモンを再起動: `sudo systemctl restart docker`

### ポートが既に使用されている

```bash
# 使用中のポートを確認
sudo lsof -i :3000
sudo lsof -i :3080
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

### faster-whisperモデルのダウンロード

faster-whisperモデルは初回使用時に自動的に `/tmp/whisper_models` にダウンロードされます:
- モデルサイズ: large-v3-turbo ~3GB
- ダウンロード元: Hugging Face
- 一度ダウンロードされるとキャッシュされます

## ライセンス

MIT License

## リンク

- [faster-whisper](https://github.com/ggerganov/whisper.cpp) - CTranslate2による高速化
- [CTranslate2](https://github.com/OpenNMT/CTranslate2) - 最適化推論エンジン
- [Supabase](https://supabase.com)
- [FastAPI](https://fastapi.tiangolo.com)
- [React](https://react.dev)
