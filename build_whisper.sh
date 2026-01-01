#!/bin/bash
# Whisper.cppベースイメージビルドスクリプト
# Usage: ./build_whisper.sh [--cuda] [--no-cache]

set -e

# 引数解析
BUILD_CUDA=false
NO_CACHE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        --cuda)
            BUILD_CUDA=true
            shift
            ;;
        --no-cache)
            NO_CACHE="--no-cache"
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: ./build_whisper.sh [--cuda] [--no-cache]"
            exit 1
            ;;
    esac
done

echo "======================================"
echo "Whisper.cpp ベースイメージをビルド"
echo "======================================"

# カレントディレクトリの確認
if [ ! -d "whispercpp" ]; then
    echo "エラー: whispercppディレクトリが見つかりません"
    echo "プロジェクトルートで実行してください"
    exit 1
fi

# ビルド設定の決定
if [ "$BUILD_CUDA" = true ]; then
    DOCKERFILE="whispercpp/Dockerfile.cuda"
    IMAGE_NAME="whisper-summarizer-whispercpp:cuda"
    ACCELERATOR="GPU (CUDA)"
    # GPU Requirements notice
    echo ""
    echo "🚨 GPU BUILD REQUIREMENTS:"
    echo "   - NVIDIA GPU with Compute Capability 7.0+"
    echo "   - NVIDIA Driver 470+"
    echo "   - nvidia-container-toolkit installed"
    echo ""
else
    DOCKERFILE="whispercpp/Dockerfile"
    IMAGE_NAME="whisper-summarizer-whispercpp:latest"
    ACCELERATOR="CPUのみ"
fi

# Dockerfileの確認
if [ ! -f "$DOCKERFILE" ]; then
    echo "エラー: $DOCKERFILEが見つかりません"
    exit 1
fi

echo ""
echo "ビルド設定:"
echo "  - Dockerfile: $DOCKERFILE"
echo "  - イメージ名: $IMAGE_NAME"
echo "  - モデル: v3-turbo ct2"
echo "  - ベース: Ubuntu 24.04"
echo "  - 加速: $ACCELERATOR"
if [ "$BUILD_CUDA" = true ]; then
    echo "  - 性能目安 (RTX 3080): 5分音声→30-45秒 (CPU比: 20-30倍)"
fi
echo ""

# キャッシュなしでビルドするかどうか
if [ -n "$NO_CACHE" ]; then
    echo "キャッシュなしでビルドします..."
    docker build $NO_CACHE -t $IMAGE_NAME -f $DOCKERFILE ./whispercpp
else
    echo "ビルドを開始します (キャッシュ使用)..."
    echo "※ キャッシュなしでビルドする場合: ./build_whisper.sh $([ "$BUILD_CUDA" = true ] && echo "--cuda ")--no-cache"
    docker build -t $IMAGE_NAME -f $DOCKERFILE ./whispercpp
fi

# ビルド結果の確認
if [ $? -eq 0 ]; then
    echo ""
    echo "======================================"
    echo "✅ ビルド完了!"
    echo "======================================"
    echo ""
    echo "イメージ情報:"
    docker images $IMAGE_NAME
    echo ""
    echo "サイズ:"
    docker images $IMAGE_NAME --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"

    # CUDAビルドの場合、追加のヒントを表示
    if [ "$BUILD_CUDA" = true ]; then
        echo ""
        echo "🔧 次のステップ:"
        echo "   1. docker-compose.ymlでgpu: enabled設定を確認"
        echo "   2. docker compose up -d --force-recreate backend"
        echo ""
        echo "💡 CPU版ビルド:"
        echo "   ./build_whisper.sh"
    fi
else
    echo ""
    echo "======================================"
    echo "❌ ビルド失敗"
    echo "======================================"
    exit 1
fi
