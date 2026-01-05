#!/bin/bash
# 開発環境起動スクリプト (Server/Runner Architecture)

set -e

echo "======================================"
echo "Whisper Summarizer 開発環境"
echo "Server/Runner Architecture"
echo "======================================"

# .envファイルの確認
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  .envファイルが見つかりません"
    echo ""
    echo ".env.sampleをコピーして.envを作成してください:"
    echo "  cp .env.sample .env"
    echo ""
    echo "その後、以下の環境変数を設定してください:"
    echo "  - SUPABASE_URL"
    echo "  - SUPABASE_ANON_KEY"
    echo "  - SUPABASE_SERVICE_ROLE_KEY"
    echo "  - GLM_API_KEY (moved to runner)"
    echo "  - RUNNER_API_KEY"
    echo ""
    exit 1
fi

# 必須環境変数のチェック
source .env

missing_vars=()

if [ -z "$SUPABASE_URL" ]; then
    missing_vars+=("SUPABASE_URL")
fi

if [ -z "$SUPABASE_ANON_KEY" ]; then
    missing_vars+=("SUPABASE_ANON_KEY")
fi

if [ -z "$SUPABASE_SERVICE_ROLE_KEY" ]; then
    missing_vars+=("SUPABASE_SERVICE_ROLE_KEY")
fi

if [ -z "$RUNNER_API_KEY" ]; then
    missing_vars+=("RUNNER_API_KEY")
fi

if [ ${#missing_vars[@]} -gt 0 ]; then
    echo ""
    echo "❌ 以下の環境変数が設定されていません:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    echo ""
    echo ".envファイルを編集してください"
    exit 1
fi

echo ""
echo "✅ 環境変数チェック: OK"
echo ""

# ベースイメージの確認
BASE_IMAGE="whisper-summarizer-fastwhisper-base:latest"
if ! docker image inspect "$BASE_IMAGE" &> /dev/null; then
    echo ""
    echo "⚠️  ベースイメージが見つかりません: $BASE_IMAGE"
    echo ""
    echo "初回起動前にベースイメージをビルドしてください:"
    echo "  ./build_fastwhisper_base.sh"
    echo ""
    echo "ベースイメージには以下が含まれます:"
    echo "  - faster-whisper large-v3-turbo モデル (~3GB)"
    echo "  - NVIDIA CUDA cuDNN Runtime"
    echo ""
    echo "ビルドには約10-15分かかります"
    echo ""
    echo "注意: サーバーはGPU不要ですが、ランナーにはGPUが必要です"
    exit 1
fi

echo "✅ ベースイメージチェック: OK"
echo ""

# Docker Composeファイルの確認
if [ ! -f "docker-compose.dev.yml" ]; then
    echo "❌ docker-compose.dev.ymlが見つかりません"
    exit 1
fi

# 起動モードの選択
MODE="${1:-up}"

case $MODE in
    "up")
        echo "開発環境を起動します (フォアグラウンド)..."
        echo ""
        echo "アクセスURL:"
        echo "  - フロントエンド: http://localhost:3000"
        echo "  - サーバーAPI: http://localhost:8000"
        echo "  - API Docs: http://localhost:8000/docs"
        echo "  - Runner API (http://localhost:8000/api/runner/*)"
        echo ""
        echo "停止するには Ctrl+C を押してください"
        echo ""
        sleep 2
        docker compose -f docker-compose.dev.yml up --build
        ;;

    "up-d")
        echo "開発環境を起動します (バックグラウンド)..."
        docker compose -f docker-compose.dev.yml up -d --build

        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ 起動完了!"
            echo ""
            echo "サービス構成:"
            echo "  - server:    軽量APIサーバー (GPU不要)"
            echo "  - runner:   GPU処理ランナー (faster-whisper + GLM)"
            echo "  - frontend: Reactフロントエンド"
            echo "  - postgres: データベース"
            echo ""
            echo "アクセスURL:"
            echo "  - フロントエンド: http://localhost:3000"
            echo "  - サーバーAPI: http://localhost:8000"
            echo "  - API Docs: http://localhost:8000/docs"
            echo ""
            echo "ログを確認:"
            echo "  docker compose -f docker-compose.dev.yml logs -f         # 全サービス"
            echo "  docker compose -f docker-compose.dev.yml logs -f server  # サーバーのみ"
            echo "  docker compose -f docker-compose.dev.yml logs -f runner  # ランナーのみ"
            echo ""
            echo "停止: docker compose -f docker-compose.dev.yml down"
        fi
        ;;

    "down")
        echo "開発環境を停止します..."
        docker compose -f docker-compose.dev.yml down
        echo "✅ 停止完了"
        ;;

    "restart")
        echo "開発環境を再起動します..."
        docker compose -f docker-compose.dev.yml restart ${2:-}
        echo "✅ 再起動完了"
        ;;

    "logs")
        SERVICE="${2:-}"
        if [ -n "$SERVICE" ]; then
            echo "[$SERVICE] ログを表示します (Ctrl+C で終了)..."
            docker compose -f docker-compose.dev.yml logs -f "$SERVICE"
        else
            echo "ログを表示します (Ctrl+C で終了)..."
            docker compose -f docker-compose.dev.yml logs -f
        fi
        ;;

    "runner-logs")
        echo "Runner ログを表示します (Ctrl+C で終了)..."
        docker compose -f docker-compose.dev.yml logs -f runner
        ;;

    "server-logs")
        echo "Server ログを表示します (Ctrl+C で終了)..."
        docker compose -f docker-compose.dev.yml logs -f server
        ;;

    "ps")
        echo "コンテナの状態:"
        docker compose -f docker-compose.dev.yml ps
        ;;

    "clean")
        echo "全てのコンテナとボリュームを削除します..."
        read -p "本当に削除しますか? (y/N): " confirm
        if [ "$confirm" == "y" ] || [ "$confirm" == "Y" ]; then
            docker compose -f docker-compose.dev.yml down -v
            echo "✅ クリーンアップ完了"
        else
            echo "キャンセルしました"
        fi
        ;;

    "rebuild")
        echo "キャッシュなしで再ビルドします..."
        docker compose -f docker-compose.dev.yml build --no-cache
        docker compose -f docker-compose.dev.yml up -d
        echo "✅ 再ビルド完了"
        ;;

    *)
        echo "Whisper Summarizer 開発環境管理ツール"
        echo "Server/Runner Architecture"
        echo ""
        echo "使用方法:"
        echo "  ./run_dev.sh [コマンド]"
        echo ""
        echo "コマンド:"
        echo "  up           - フォアグラウンドで起動 (デフォルト)"
        echo "  up-d         - バックグラウンドで起動"
        echo "  down         - 停止"
        echo "  restart      - 再起動"
        echo "  logs [SERVICE] - ログ表示 (オプションでサービス指定)"
        echo "  server-logs  - サーバーログのみ表示"
        echo "  runner-logs  - ランナーログのみ表示"
        echo "  ps           - コンテナ状態確認"
        echo "  clean        - 全削除 (ボリューム含む)"
        echo "  rebuild      - キャッシュなしで再ビルド"
        echo ""
        echo "例:"
        echo "  ./run_dev.sh              # フォアグラウンドで起動"
        echo "  ./run_dev.sh up-d         # バックグラウンドで起動"
        echo "  ./run_dev.sh logs         # 全ログ表示"
        echo "  ./run_dev.sh runner-logs  # ランナーログ表示"
        echo "  ./run_dev.sh down         # 停止"
        exit 1
        ;;
esac
