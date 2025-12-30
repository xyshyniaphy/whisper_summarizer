# テスト環境セットアップガイド

Whisper Summarizerプロジェクトのテスト環境についての詳細ガイドです。

## ディレクトリ構造

```text
tests/
├── docker-compose.test.yml  # テスト用Docker Compose設定
├── backend/
│   ├── Dockerfile            # バックエンドテスト用Dockerfile
│   ├── api/                  # APIテスト
│   ├── services/             # サービステスト
│   └── conftest.py           # Pytest共通設定
├── frontend/
│   ├── Dockerfile            # フロントエンドテスト用Dockerfile
│   ├── components/           # コンポーネントテスト
│   ├── hooks/                # フックテスト
│   └── setup.ts              # Vitest設定
└── e2e/
    ├── Dockerfile            # E2Eテスト用Dockerfile
    ├── playwright.config.ts  # Playwright設定
    └── tests/                # E2Eテストシナリオ
```

## セットアップ

### 1. 環境変数の設定

プロジェクトルートの `.env` ファイルが必要です。

### 2. Dockerイメージのビルド

```bash
cd tests
docker-compose -f docker-compose.test.yml build

# または便利スクリプトを使用
./run.sh build
```

## テスト実行

### 便利スクリプト（推奨）

`run.sh` スクリプトを使用すると簡単にテストを実行できます：

```bash
cd tests

# すべてのテストを実行
./run.sh all

# または単に
./run.sh

# 個別のテストを実行
./run.sh backend
./run.sh frontend
./run.sh e2e

# イメージをビルド
./run.sh build

# クリーンアップ
./run.sh clean
```

### 手動実行

### バックエンドテスト

```bash
# すべてのバックエンドテストを実行
docker-compose -f docker-compose.test.yml run --rm backend-test

# カバレッジレポートを確認
# レポートは ../backend/htmlcov/index.html に生成されます

# 特定のテストを実行
docker-compose -f docker-compose.test.yml run --rm backend-test \
  pytest tests/backend/api/test_auth_api.py -v
```

### フロントエンドテスト

```bash
# すべてのフロントエンドテストを実行
docker-compose -f docker-compose.test.yml run --rm frontend-test

# ウォッチモードで実行
docker-compose -f docker-compose.test.yml run --rm frontend-test \
  npm run test -- --watch
```

### E2Eテスト

```bash
# E2Eテストを実行（開発環境が起動している必要があります）
docker-compose -f docker-compose.test.yml run --rm e2e-test
```

## トラブルシューティング

### イメージビルドエラー

ベースイメージ（whisper-summarizer-whispercpp）が存在しない場合:

```bash
cd ..
./run_dev.sh build
```

### テスト実行エラー

コンテナ内でシェルを起動してデバッグ:

```bash
docker-compose -f docker-compose.test.yml run --rm --entrypoint /bin/sh backend-test
```

## CI/CD統合

GitHub Actionsなどで使用する場合の例:

```yaml
- name: Run Backend Tests
  run: |
    cd tests
    docker-compose -f docker-compose.test.yml run --rm backend-test
```
