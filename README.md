# Whisper Summarizer

音声文字起こし・要約システム - Server/Runner 分散アーキテクチャ版

## 概要

Whisper Summarizerは、音声ファイルを自動で文字起こしし、GLM-4.5-Air API (OpenAI-compatible) による要約を生成するWebアプリケーションです。

**🎯 新アーキテクチャ**: サーバーとランナーを分離し、スケーラビリティとコスト効率を大幅に改善しました。

### 主な機能

- **音声文字起こし**: faster-whisper (CTranslate2 + cuDNN) によるGPU加速処理
- **AI要約生成**: GLM-4.5-Air (OpenAI-compatible API) による高品質な要約
- **音声管理**: アップロードした音声と文字起こし結果の削除機能
- **ユーザー認証**: Supabase Authによる安全な認証
- **分散処理**: 軽量サーバー (VPS) + GPUランナー (別サーバー)

### アーキテクチャ

```
フロントエンド (Vite:3000) → サーバー (FastAPI, ~150MB) ←→ ランナー (GPU, ~8GB)
                           ↓                              ↓
                      PostgreSQL                faster-whisper + GLM
```

**メリット**:
- ✅ **サーバーはGPU不要** - 安価なVPSで動作可能
- ✅ **水平スケーリング** - 複数のランナーを追加可能
- ✅ **独立デプロイ** - サーバーとランナーを別々に更新可能
- ✅ **コスト最適化** - GPUはランナーのみで使用

### 技術スタック

| コンポーネント | サーバー | ランナー |
|---|---|---|
| ベースイメージ | python:3.12-slim (~150MB) | fastwhisper-base (~8GB) |
| バックエンド | FastAPI + Python 3.12 | faster-whisper + GLM |
| 音声処理 | なし | faster-whisper (cuDNN) |
| AI要約 | なし | GLM-4.5-Air API |
| データベース | PostgreSQL 18 Alpine | - |
| 認証 | Supabase Auth | - |

### Dockerイメージサイズ

| イメージ | サイズ | 説明 |
|---|---|---|
| whisper_summarizer-server | ~150MB | FastAPIサーバー (GPU不要) ⭐ NEW |
| whisper_summarizer-runner | ~8GB | GPU処理用ランナー (faster-whisper + GLM) ⭐ NEW |
| whisper_summarizer-frontend | 380MB | React + Vite (開発) / Nginx (本番) |
| postgres | ~250MB | PostgreSQL 18 Alpine (開発のみ) |

**アーキテクチャ改善:**
- サーバーはGPU不要 - 安価なVPSで運用可能
- ランナーはGPUサーバーで動作 - 必要に応じてスケール
- 処理完了後に音声ファイルを自動削除 - ディスク容量節約

## セットアップ

### 前提条件

- Docker & Docker Compose
- Supabaseプロジェクト (https://supabase.com)
- GLM APIキー (https://z.ai/ - 国際プラットフォーム)

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

**サーバー設定 (.env)** - GPU不要:
```bash
# データベース設定
POSTGRES_DB=whisper_summarizer
POSTGRES_USER=postgres
POSTGRES_PASSWORD=postgres

# Supabase設定 (Supabaseダッシュボードから取得)
SUPABASE_URL=https://xxxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...

# ランナー認証 (サーバーとランナーで同じ値を設定)
RUNNER_API_KEY=your-super-secret-runner-api-key

# サーバー設定
CORS_ORIGINS=http://localhost:3000
```

**ランナー設定 (runner/.env)** - GPUが必要:
```bash
# サーバー接続 (サーバーのURLを指定)
SERVER_URL=http://localhost:8000  # 本番環境: https://your-server.com
RUNNER_API_KEY=your-super-secret-runner-api-key  # サーバーと同じ値
RUNNER_ID=runner-gpu-01

# ポーリング設定
POLL_INTERVAL_SECONDS=10          # ジョブ取得間隔 (秒)
MAX_CONCURRENT_JOBS=2             # 並列処理数 (GPU: 2-4推奨)

# faster-whisper設定 (GPU加速)
FASTER_WHISPER_DEVICE=cuda                  # cuda (GPU) または cpu
FASTER_WHISPER_COMPUTE_TYPE=int8_float16     # int8_float16 (推奨, GPU), int8 (CPU)
FASTER_WHISPER_MODEL_SIZE=large-v3-turbo
WHISPER_LANGUAGE=zh                         # 文字起こし言語
WHISPER_THREADS=4                           # 処理スレッド数

# Audio Chunking (長音声の高速文字起こし)
ENABLE_CHUNKING=true              # チャンキング有効
CHUNK_SIZE_MINUTES=10             # チャンク長さ（分）
CHUNK_OVERLAP_SECONDS=15          # オーバーラップ（秒）
MAX_CONCURRENT_CHUNKS=4           # 並列チャンク数 (GPU: 4-8推奨)
USE_VAD_SPLIT=true                # 無音検出分割
VAD_SILENCE_THRESHOLD=-30         # 無音閾値
VAD_MIN_SILENCE_DURATION=0.5      # 最小無音時間
MERGE_STRATEGY=lcs                # マージ戦略

# GLM API設定 (OpenAI-compatible)
GLM_API_KEY=your_glm_api_key      # https://z.ai/ から取得
GLM_MODEL=GLM-4.5-Air             # 使用モデル
GLM_BASE_URL=https://api.z.ai/api/paas/v4/  # 国際エンドポイント
REVIEW_LANGUAGE=zh                 # 要約言語 (zh, ja, en)
```

### ベースイメージのビルド（初回のみ）

**ランナー用**、faster-whisperモデルを含むベースイメージをビルドする必要があります:

```bash
# ランナー ベースイメージをビルド (~10-15分、モデルダウンロード含む)
./build_fastwhisper_base.sh

# 出力例:
# - Image: whisper-summarizer-fastwhisper-base:latest
# - Size: ~5-7 GB (CUDA cuDNN + 3GB model)
```

**ベースイメージの内容:**
- NVIDIA CUDA 12.9.1 cuDNN Runtime
- Python 3.12 + uv + faster-whisper
- **事前ダウンロード済み** `large-v3-turbo` モデル (~3GB)

**※ サーバーはGPU不要で、ベースイメージは不要です** (python:3.12-slimを使用)

**ベースイメージの再ビルドが必要な場合:**
- モデルの更新が必要な時
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
├── server/                # 軽量サーバー (GPU不要) ⭐ NEW
│   ├── app/
│   │   ├── api/          # APIエンドポイント (auth, audio, transcriptions, admin, runner)
│   │   ├── services/     # Storage統合のみ
│   │   ├── core/         # 設定・Supabase統合
│   │   ├── models/       # データベースモデル
│   │   └── schemas/      # Pydanticスキーマ
│   ├── Dockerfile        # python:3.12-slim ベース
│   └── requirements.txt  # 軽量依存関係のみ
│
├── runner/                # GPU処理ランナー ⭐ NEW
│   ├── app/
│   │   ├── worker/       # ポーリングワーカー
│   │   ├── services/     # faster-whisper + GLM + Storage統合
│   │   ├── config.py     # ランナー設定
│   │   └── models/       # ジョブスキーマ
│   ├── Dockerfile        # fastwhisper-base ベース
│   └── requirements.txt  # faster-whisper依存関係
│
├── data/                 # データ保存用 (Dockerボリュームマウント)
│   ├── uploads/          # アップロードされた音声ファイル (処理後に自動削除)
│   └── transcribes/      # 文字起こし結果 (gzip圧縮)
│
├── docker-compose.yml             # 本番環境 (server + runner)
├── docker-compose.dev.yml         # 開発環境 (server + runner)
├── docker-compose.runner.yml      # ランナー専用 (別サーバー用)
└── .env.sample                   # 環境変数テンプレート
```

## クイックスタート

### 開発環境 (Server + Runner 同一マシン)

```bash
# 1. 環境変数を設定
cp .env.sample .env
# .envを編集してSupabaseとGLM APIキーを設定

# 2. ランナー用環境変数を設定
cp runner/.env.sample runner/.env
# runner/.envを編集してSERVER_URLとRUNNER_API_KEYを設定

# 3. ランナー用ベースイメージをビルド (初回のみ、~10-15分)
./build_fastwhisper_base.sh

# 4. 開発環境を起動
./run_dev.sh up-d

# 5. ブラウザでアクセス
# http://localhost:3000
```

### 本番環境 (ServerとRunnerを別々にデプロイ)

**サーバー (GPU不要):**
```bash
# サーバー環境変数を設定
cp .env.sample .env
# .envを編集

# サーバーを起動
docker-compose up -d --build server
```

**ランナー (GPUが必要):**
```bash
# ランナー環境変数を設定
cp runner/.env.sample runner/.env
# runner/.envを編集 (SERVER_URLはサーバーのURLに変更)

# ランナーを起動
docker-compose -f docker-compose.runner.yml up -d --build
```

詳細は以下のセクションを参照してください。

---

## 使い方

### 1. ユーザー登録

1. http://localhost:3000 にアクセス
2. 「Sign in with Google」でサインアップ
3. Googleアカウントで認証
4. **重要**: 新規ユーザーは管理者の承認が必要（非アクティブ状態）

### 2. アカウントのアクティベーション

- 管理者がダッシュボードからユーザーをアクティベート
- アクティベートされたユーザーのみがシステムを利用可能

### 3. ログイン

1. Googleアカウントでログイン
2. ダッシュボードにリダイレクト

### 4. 音声ファイルのアップロード

- サポート形式: m4a, mp3, wav, aac, flac, ogg
- 最大ファイルサイズ: 未設定

### 5. 文字起こし・要約の確認

- 文字起こし結果をタイムスタンプ付きで表示 (最初の200行)
- GLM-4.5-Air による要約を表示
- ダウンロード機能 (テキスト形式 .txt / 字幕形式 .srt)

### 6. 音声の削除

- 文字起こし履歴リストから、不要なアイテムを削除できます (ゴミ箱アイコン)
- 削除条件:
  - **完了したアイテム**: いつでも削除可能
  - **失敗したアイテム**: いつでも削除可能
  - **処理中のアイテム**: 24時間経過後のみ削除可能
- 関連する音声ファイルと文字起こしデータもサーバーから削除されます
- データベースのカスケード削除により、関連する要約データやAPIログも自動的に削除されます

---

## ユーザー管理・チャンネル管理

このシステムには、ユーザー管理とチャンネル（フォルダ）機能が含まれています。

### ユーザー認証フロー

1. **Google OAuthでサインアップ**
   - 新規ユーザーはGoogleアカウントでサインアップ
   - サインアップ直後は「非アクティブ」状態（管理者の承認が必要）

2. **アカウントのアクティベーション**
   - 管理者がダッシュボードからユーザーをアクティベート
   - アクティベートされたユーザーのみがシステムを利用可能

3. **ユーザーロール**
   - **一般ユーザー**: 自分のコンテンツ + 所属チャンネルのコンテンツのみ閲覧可能
   - **管理者**: すべてのコンテンツを閲覧可能 + ユーザー・チャンネル管理機能

### 管理者ダッシュボード

管理者のみがアクセス可能なダッシュボード (`/dashboard`) で以下の管理機能を提供します:

#### ユーザー管理タブ
- **ユーザー一覧**: すべてのユーザーのステータスを表示
  - アクティベーション状況 (待機中/アクティブ)
  - 管理者権限の有無
  - 登録日時、アクティベーション日時
- **ユーザーアクション**:
  - アクティベート: 非アクティブユーザーを有効化
  - 管理者権限の付与/剥奪 (自分自身の権限は変更不可、最後の管理者保護)
  - 削除: ソフトデリート (所有権は管理者に移転、自分自身・最後の管理者は削除不可)

#### チャンネル管理タブ
- **チャンネル一覧**: すべてのチャンネルとメンバー数を表示
- **チャンネル作成/編集/削除**:
  - チャンネル名と説明を設定
  - 重複するチャンネル名は不可
- **メンバー管理**:
  - チャンネルにユーザーを割り当て (管理者のみ操作可能)
  - ユーザーは自分でチャンネルに参加/脱退できない

#### 音声管理タブ
- **すべての音声一覧**: システム内のすべての音声ファイルを表示
- **チャンネル割り当て**:
  - 音声を複数のチャンネルに同時に割り当て可能
  - 既存の割り当ては上書きされます

### コンテンツの閲覧権限

| ロール | 閲覧可能なコンテンツ |
|--------|-------------------|
| **管理者** | すべての音声ファイル (チャンネルに関係なく) |
| **一般ユーザー** | 自分がアップロードした音声 + 所属チャンネルに割り当てられた音声 |

### 初回管理者設定

初回の管理者ユーザーを設定するには、以下のスクリプトを使用します:

```bash
# 開発環境 (Docker)
./scripts/set_first_admin.sh user@example.com

# 本番環境 (DATABASE_URL設定済み)
DATABASE_URL="postgresql://..." ./scripts/set_first_admin.sh user@example.com
```

このスクリプトは以下を行います:
- 指定したメールアドレスのユーザーを管理者に昇格
- アカウントをアクティベート

**注意**: 初回の管理者設定後、ダッシュボードから他のユーザーを管理者に昇格させることができます。

### チャンネル機能の利用

チャンネル機能は、ユーザーがコンテンツを整理し、適切なメンバーと共有するための機能です。

#### 転写リストでのチャンネルフィルター

転写リストページ (`/transcriptions`) では、チャンネルフィルターを使用してコンテンツを絞り込めます:

- **全部内容**: すべての閲覧可能なコンテンツを表示（管理者は全コンテンツ、一般ユーザーは自分の+所属チャンネル）
- **个人内容**: 自分がアップロードしたコンテンツのみ表示
- **チャンネル別**: 特定のチャンネルに割り当てられたコンテンツのみ表示

各転写アイテムにはチャンネルバッジが表示されます:
- **个人**: チャンネルに割り当てられていない個人コンテンツ
- **チャンネル名**: 割り当てられているチャンネル（複数の場合は「+N」で表示）

#### 転写詳細でのチャンネル割り当て

転写詳細ページ (`/transcriptions/{id}`) では、転写をチャンネルに割り当てることができます:

- **「管理频道」ボタン**: 転写の所有者または管理者が利用可能
- **チャンネル選択モーダル**: 複数のチャンネルを同時に選択可能
- **検索機能**: チャンネル名で検索してフィルタリング
- **即時反映**: 保存後、すぐにチャンネルメンバーが閲覧可能に

### API エンドポイント (管理用)

管理用APIエンドポイントはすべて管理者のみがアクセス可能です:

**ユーザー管理** (`/api/admin/users`):
- `GET /api/admin/users` - ユーザー一覧取得
- `PUT /api/admin/users/{user_id}/activate` - ユーザーをアクティベート
- `PUT /api/admin/users/{user_id}/admin` - 管理者権限の切り替え
- `DELETE /api/admin/users/{user_id}` - ユーザーを削除

**チャンネル管理** (`/api/admin/channels`):
- `GET /api/admin/channels` - チャンネル一覧取得
- `POST /api/admin/channels` - チャンネル作成
- `PUT /api/admin/channels/{channel_id}` - チャンネル更新
- `DELETE /api/admin/channels/{channel_id}` - チャンネル削除
- `GET /api/admin/channels/{channel_id}` - チャンネル詳細とメンバー一覧
- `POST /api/admin/channels/{channel_id}/members` - ユーザーをチャンネルに割り当て
- `DELETE /api/admin/channels/{channel_id}/members/{user_id}` - ユーザーをチャンネルから削除

**音声管理** (`/api/admin/audio`):
- `GET /api/admin/audio` - すべての音声一覧取得
- `POST /api/admin/audio/{audio_id}/channels` - 音声をチャンネルに割り当て
- `GET /api/admin/audio/{audio_id}/channels` - 音声のチャンネル割り当て取得


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
- **サーバー**: `./server` → Uvicorn --reload (軽量、起動が高速)
- **ランナー**: `./runner` → 自動再起動 (設定変更時に反映)

### ログの確認

```bash
# 全サービスのログ
docker-compose -f docker-compose.dev.yml logs -f

# 特定のサービスのログ
docker-compose -f docker-compose.dev.yml logs -f server
docker-compose -f docker-compose.dev.yml logs -f runner
docker-compose -f docker-compose.dev.yml logs -f frontend
```

### コンテナに入る

```bash
# サーバーコンテナ
docker-compose -f docker-compose.dev.yml exec server bash

# ランナーコンテナ
docker-compose -f docker-compose.dev.yml exec runner bash

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
- サーバー: カバレッジレポートは `server/htmlcov/index.html`
- フロントエンド: Vitestの標準出力
- E2E: Playwrightレポートは `tests/e2e/playwright-report/index.html` (ホスト側 `data/playwright-report/`)
- E2Eスクリーンショット: ホスト側 `data/screenshots/` (失敗時は `data/screenshots/failures/`)

**現在のカバレッジ状況:**
- サーバー: **~240 comprehensive tests** ✅
  - test_runner_api.py: ~55 tests (Runner API, edge cases, race conditions, data consistency)
  - test_audio_upload.py: ~90 tests (Upload, formats, validation, error handling)
  - test_transcriptions_api.py: ~45 tests (CRUD, downloads, chat, share, channels)
  - test_admin_api.py: ~30 tests (User/channel/audio management)
  - test_integration.py: ~20 tests (E2E workflows, performance, security)
- フロントエンド: **73.6%** (319/433 tests passing, 114 failing)
- テスト総数: ~240件 (サーバー) + 433件 (フロントエンド) = **~673件**

### サーバーテスト (Pytest)

ローカル環境でテストを実行する場合:

```bash
# テストを実行
cd server
uv run pytest

# カバレッジ付きで実行
uv run pytest --cov=app --cov-report=html --cov-report=term

# 特定のテストを実行
uv run pytest tests/backend/test_runner_api.py
uv run pytest tests/backend/test_transcriptions_api.py -v

# 特定のテスト関数を実行
uv run pytest tests/backend/test_runner_api.py::TestRunnerAuthentication::test_get_jobs_requires_auth -v

# マーカーでフィルター
uv run pytest -m unit          # 単体テストのみ
uv run pytest -m integration   # 統合テストのみ
```

**テストの構成:**

| テストファイル | エンドポイント数 | テスト数 | 説明 |
|---|---|---|---|
| `test_runner_api.py` | 6 | ~55 | Runner API (認証、ジョブ管理、ハートビート) + エッジケース + レース条件 + データ整合性 |
| `test_audio_upload.py` | 2 | ~90 | 音声アップロード + フォーマット検証 + エラーハンドリング + エッジケース |
| `test_transcriptions_api.py` | 14 | ~45 | 転写API (CRUD、ダウンロード、チャット、共有、チャンネル) |
| `test_admin_api.py` | 15 | ~30 | 管理者API (ユーザー、チャンネル、音声管理) |
| `test_integration.py` | E2E | ~20 | エンドツーエンドワークフロー + パフォーマンス + セキュリティ |

**テストカテゴリ:**

1. **認証テスト**: すべてのエンドポイントで認証必須
2. **バリデーション**: UUID形式、ステータス値、ページネーションパラメータ
3. **エラーハンドリング**: 404、400、401、403、422、500レスポンス
4. **エッジケース**: 空値、非常に長い値、負の値、重複
5. **レース条件**: 重複ジョブ要求、同時更新、状態遷移
6. **データ整合性**: データベース更新、タイムスタンプ、カスケード削除
7. **E2Eワークフロー**: アップロード→処理→完了、失敗ハンドリング

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
- `tests/e2e/tests/channel-assignment.spec.ts` - チャンネル割り当てシナリオのE2Eテスト

**チャンネル割り当てE2Eテスト内容:**
- チャンネル一覧表示と検索機能
- 単一・複数チャンネルの選択と割り当て
- 割り当てのキャンセル
- チャンネル変更シナリオ（新規チャンネルへの変更、元のチャンネルに戻す、全解除）
- APIエラー時のエラーメッセージ表示

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
| GET | `/api/transcriptions/{id}/download?format=txt` | テキストダウンロード |
| GET | `/api/transcriptions/{id}/download?format=srt` | 字幕ダウンロード |
| GET | `/api/transcriptions/{id}/channels` | 転写のチャンネル取得 |
| POST | `/api/transcriptions/{id}/channels` | 転写をチャンネルに割り当て |

### Runner APIエンドポイント ⭐ NEW

ランナーからサーバーへアクセスするためのエンドポイントです (API Key認証が必要):

| メソッド | パス | 説明 |
|---|---|---|
| GET | `/api/runner/jobs` | 保留中のジョブを取得 |
| POST | `/api/runner/jobs/{id}/start` | ジョブを処理開始 |
| GET | `/api/runner/audio/{id}` | 音声ファイルをダウンロード |
| POST | `/api/runner/jobs/{id}/complete` | ジョブ完了結果を送信 |
| POST | `/api/runner/jobs/{id}/fail` | ジョブ失敗を報告 |
| POST | `/api/runner/heartbeat` | ランナー稼動状態を報告 |

**リクエスト例:**

```bash
# ジョブを取得
curl -H "Authorization: Bearer RUNNER_API_KEY" \
  http://server:8000/api/runner/jobs?status=pending&limit=10

# ジョブを開始
curl -X POST -H "Authorization: Bearer RUNNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"runner_id": "runner-gpu-01"}' \
  http://server:8000/api/runner/jobs/abc123/start

# ジョブを完了
curl -X POST -H "Authorization: Bearer RUNNER_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"text": "転写テキスト...", "summary": "要約...", "processing_time_seconds": 45}' \
  http://server:8000/api/runner/jobs/abc123/complete
```

## Audio Chunking (長音声の高速文字起こし)

ランナー側で長音声ファイル（10分以上）の文字起こし速度を向上させるため、チャンキング機能を実装しています。

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
FASTER_WHISPER_COMPUTE_TYPE=int8_float16    # 推奨: メモリ効率と精度のバランス
# または float16 (より高速だがVRAM使用量が増加)
CHUNK_SIZE_MINUTES=15
MAX_CONCURRENT_CHUNKS=4-6      # RTX 3080 8GB: 4-6, RTX 3090 10GB+: 6-8
CHUNK_OVERLAP_SECONDS=15
USE_VAD_SPLIT=true
```

## トラブルシューティング

### ランナーのGPUが認識されない

```bash
# ホストマシンでGPUを確認
nvidia-smi

# nvidia-container-runtimeがインストールされているか確認
docker run --rm --gpus all nvidia/cuda:12.4.0-base-ubuntu22.04 nvidia-smi

# ランナーコンテナ内でGPUを確認
docker-compose -f docker-compose.dev.yml exec runner nvidia-smi
```

**エラー: `could not select device driver`**
- nvidia-container-toolkitをインストール: https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/install-guide.html
- Dockerデーモンを再起動: `sudo systemctl restart docker`

**注意**: サーバーはGPU不要です。GPUの問題はランナー側のみです。

### ポートが既に使用されている

```bash
# 使用中のポートを確認
sudo lsof -i :3000
sudo lsof -i :3080
sudo lsof -i :8000

# プロセスを終了
sudo kill -9 <PID>
```

### Dockerイメージを再ビルド

**サーバー (軽量、高速ビルド):**
```bash
# キャッシュなしでビルド
docker-compose -f docker-compose.dev.yml build --no-cache server

# 全てのボリュームを削除して再起動
docker-compose -f docker-compose.dev.yml down -v
docker-compose -f docker-compose.dev.yml up --build
```

**ランナー (ベースイメージが必要):**
```bash
# ベースイメージを再ビルド (モデル再ダウンロード含む)
./build_fastwhisper_base.sh --no-cache

# ランナーをビルド
docker-compose -f docker-compose.dev.yml build --no-cache runner
```

### ランナーがサーバーに接続できない

**問題**: ランナーが `Connection refused` エラーを表示

**解決策**:
1. サーバーが起動しているか確認: `docker-compose ps`
2. `runner/.env` の `SERVER_URL` が正しいか確認
   - 開発環境: `http://server:8000` (Docker内部ネットワーク)
   - 本番環境: `https://your-server.com` (実際のサーバーURL)
3. `RUNNER_API_KEY` がサーバーの `.env` と一致しているか確認

### faster-whisperモデルのダウンロード

faster-whisperモデルは初回使用時に自動的にベースイメージに含まれています:
- モデルサイズ: large-v3-turbo ~3GB
- ベースイメージビルド時に事前ダウンロード
- 一度ビルドされるとキャッシュされます

**再ビルドが必要な場合**:
```bash
./build_fastwhisper_base.sh --no-cache
```

## ライセンス

MIT License

## リンク

- [faster-whisper](https://github.com/ggerganov/whisper.cpp) - CTranslate2による高速化
- [CTranslate2](https://github.com/OpenNMT/CTranslate2) - 最適化推論エンジン
- [Supabase](https://supabase.com)
- [FastAPI](https://fastapi.tiangolo.com)
- [React](https://react.dev)
