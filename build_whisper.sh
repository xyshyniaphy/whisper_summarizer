#!/bin/bash
# Whisper.cppベースイメージビルドスクリプト

set -e

echo "======================================"
echo "Whisper.cpp ベースイメージをビルド"
echo "======================================"

# カレントディレクトリの確認
if [ ! -d "whispercpp" ]; then
    echo "エラー: whispercppディレクトリが見つかりません"
    echo "プロジェクトルートで実行してください"
    exit 1
fi

# Dockerfileの確認
if [ ! -f "whispercpp/Dockerfile" ]; then
    echo "エラー: whispercpp/Dockerfileが見つかりません"
    exit 1
fi

echo ""
echo "ビルド設定:"
echo "  - イメージ名: whisper-summarizer-whispercpp"
echo "  - モデル: v3-turbo ct2"
echo "  - ベース: Ubuntu 24.04 + Python 3.12"
echo "  - 処理: CPU専用"
echo ""

# キャッシュなしでビルドするかどうか
if [ "$1" == "--no-cache" ]; then
    echo "キャッシュなしでビルドします..."
    docker build --no-cache -t whisper-summarizer-whispercpp:latest ./whispercpp
else
    echo "ビルドを開始します (キャッシュ使用)..."
    echo "※ キャッシュなしでビルドする場合: ./build_whisper.sh --no-cache"
    docker build -t whisper-summarizer-whispercpp:latest ./whispercpp
fi

# ビルド結果の確認
if [ $? -eq 0 ]; then
    echo ""
    echo "======================================"
    echo "✅ ビルド完了!"
    echo "======================================"
    echo ""
    echo "イメージ情報:"
    docker images whisper-summarizer-whispercpp:latest
    echo ""
    echo "イメージサイズ:"
    docker images whisper-summarizer-whispercpp:latest --format "table {{.Repository}}\t{{.Tag}}\t{{.Size}}"
else
    echo ""
    echo "======================================"
    echo "❌ ビルド失敗"
    echo "======================================"
    exit 1
fi
