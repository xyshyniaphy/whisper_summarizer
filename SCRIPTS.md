# Whisper Summarizer - 開発スクリプト

## スクリプト一覧

### 1. build_whisper.sh

Whisper.cppベースイメージをビルドします。

**使用方法:**
```bash
# 通常のビルド (キャッシュ使用)
./build_whisper.sh

# キャッシュなしでビルド
./build_whisper.sh --no-cache
```

**実行内容:**
- whispercpp/Dockerfileを使用してマルチステージビルド
- v3-turbo ct2モデルをダウンロード
- Whisper.cppをCPU専用でビルド
- 最終イメージサイズを表示

---

### 2. run_dev.sh

開発環境を管理します。

**使用方法:**
```bash
./run_dev.sh [コマンド]
```

**コマンド一覧:**

| コマンド | 説明 |
|---------|------|
| `up` | フォアグラウンドで起動 (デフォルト) |
| `up-d` | バックグラウンドで起動 |
| `down` | 停止 |
| `restart` | 再起動 |
| `logs` | ログ表示 |
| `ps` | コンテナ状態確認 |
| `clean` | 全削除 (ボリューム含む) |
| `rebuild` | キャッシュなしで再ビルド |

**実行前チェック:**
- `.env`ファイルの存在確認
- 必須環境変数の検証:
  - `SUPABASE_URL`
  - `SUPABASE_ANON_KEY`
  - `SUPABASE_SERVICE_ROLE_KEY`
  - `GLM_API_KEY`

**起動後のアクセスURL:**
- フロントエンド: http://localhost:3000
- バックエンドAPI: http://localhost:3080
- API Docs: http://localhost:3080/docs
- Whisper.cpp: http://localhost:8001

---

## 使用例

### 初回セットアップ

```bash
# 1. 環境変数を設定
cp .env.sample .env
vim .env  # SupabaseとGLM4.7のAPIキーを設定

# 2. Whisper.cppイメージをビルド (オプション)
./build_whisper.sh

# 3. 開発環境を起動
./run_dev.sh up-d

# 4. ログを確認
./run_dev.sh logs
```

### 日常的な開発

```bash
# 起動
./run_dev.sh up-d

# コード変更 (自動でホットリロード)

# ログ確認
./run_dev.sh logs

# 停止
./run_dev.sh down
```

### トラブルシューティング

```bash
# 全削除して再起動
./run_dev.sh clean
./run_dev.sh up-d

# キャッシュなしで再ビルド
./run_dev.sh rebuild

# Whisper.cppを再ビルド
./build_whisper.sh --no-cache
./run_dev.sh restart
```

---

## 注意事項

### 権限

スクリプトには実行権限が必要です:
```bash
chmod +x build_whisper.sh run_dev.sh
```

### 環境変数

`.env`ファイルが存在しない、または必須環境変数が設定されていない場合、`run_dev.sh`はエラーを表示して終了します。

### Docker

これらのスクリプトはDocker/Docker Composeが必要です:
```bash
# Dockerのバージョン確認
docker --version
docker-compose --version
```
