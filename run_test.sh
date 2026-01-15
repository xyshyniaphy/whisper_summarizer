#!/bin/bash
# テスト実行スクリプト - Whisper Summarizer Test Runner

set -e

# カラー出力設定
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 関数: ヘルプメッセージを表示
show_help() {
    echo -e "${BLUE}Whisper Summarizer テスト実行スクリプト${NC}"
    echo ""
    echo "使用方法: ./run_test.sh [コマンド]"
    echo ""
    echo "コマンド:"
    echo "  build            テストイメージをビルド"
    echo "  backend          バックエンドテストのみ実行"
    echo "  frontend         フロントエンドテストのみ実行"
    echo "  e2e              E2Eテストのみ実行 (開発環境)"
    echo "  e2e-dev          E2Eテストを開発環境で実行"
    echo "  e2e-prd          E2Eテストを本番環境で実行 (SSHトンネル経由)"
    echo "  all              すべてのテストを実行（デフォルト）"
    echo "  clean            テストコンテナとボリュームをクリーンアップ"
    echo "  help             このヘルプメッセージを表示"
    echo ""
}

# 関数: イメージをビルド
build_images() {
    echo -e "${BLUE}テストイメージをビルド中...${NC}"
    docker compose -f tests/docker-compose.test.yml build
    echo -e "${GREEN}✓ ビルド完了${NC}"
}

# 関数: バックエンドテストを実行
run_backend_tests() {
    echo -e "${BLUE}バックエンドテストを実行中...${NC}"
    docker compose -f tests/docker-compose.test.yml run --rm backend-test
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ バックエンドテスト成功${NC}"
        return 0
    else
        echo -e "${RED}✗ バックエンドテスト失敗${NC}"
        return 1
    fi
}

# 関数: フロントエンドテストを実行
run_frontend_tests() {
    echo -e "${BLUE}フロントエンドテストを実行中...${NC}"
    docker compose -f tests/docker-compose.test.yml run --rm frontend-test
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ フロントエンドテスト成功${NC}"
        return 0
    else
        echo -e "${RED}✗ フロントエンドテスト失敗${NC}"
        return 1
    fi
}

# 関数: E2Eテストを実行
run_e2e_tests() {
    echo -e "${BLUE}E2Eテストを実行中...${NC}"
    echo -e "${YELLOW}注意: 開発環境が起動している必要があります${NC}"
    docker compose -f tests/docker-compose.test.yml run --rm e2e-test
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ E2Eテスト成功${NC}"
        return 0
    else
        echo -e "${RED}✗ E2Eテスト失敗${NC}"
        return 1
    fi
}

# 関数: すべてのテストを実行
run_all_tests() {
    echo -e "${BLUE}すべてのテストを実行中...${NC}"
    echo ""

    FAILED=0

    # バックエンドテスト
    run_backend_tests || FAILED=$((FAILED + 1))
    echo ""

    # フロントエンドテスト
    run_frontend_tests || FAILED=$((FAILED + 1))
    echo ""

    # E2Eテスト
    run_e2e_tests || FAILED=$((FAILED + 1))
    echo ""

    # 結果サマリー
    echo -e "${BLUE}==================== テスト結果 ====================${NC}"
    if [ $FAILED -eq 0 ]; then
        echo -e "${GREEN}✓ すべてのテストが成功しました！${NC}"
        return 0
    else
        echo -e "${RED}✗ ${FAILED} 個のテストスイートが失敗しました${NC}"
        return 1
    fi
}

# 関数: クリーンアップ
cleanup() {
    echo -e "${BLUE}テストコンテナとボリュームをクリーンアップ中...${NC}"
    docker compose -f tests/docker-compose.test.yml down -v
    echo -e "${GREEN}✓ クリーンアップ完了${NC}"
}

# メイン処理
main() {
    # docker-compose.test.ymlの存在を確認
    if [ ! -f "tests/docker-compose.test.yml" ]; then
        echo -e "${RED}エラー: tests/docker-compose.test.yml が見つかりません${NC}"
        exit 1
    fi

    # 引数に応じて処理を分岐
    case "${1:-all}" in
        build)
            build_images
            ;;
        backend)
            run_backend_tests
            ;;
        frontend)
            run_frontend_tests
            ;;
        e2e)
            run_e2e_tests
            ;;
        e2e-dev)
            bash tests/run_e2e_dev.sh "${2:-}"
            ;;
        e2e-prd)
            bash tests/run_e2e_prd.sh "${@:2}"
            ;;
        all)
            run_all_tests
            ;;
        clean)
            cleanup
            ;;
        help)
            show_help
            ;;
        *)
            echo -e "${RED}エラー: 不明なコマンド: $1${NC}"
            echo ""
            show_help
            exit 1
            ;;
    esac
}

# スクリプト実行
main "$@"
