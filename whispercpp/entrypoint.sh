#!/bin/bash
# Whisper.cpp エントリーポイントスクリプト

set -e

echo "Whisper.cpp サービスを起動しています..."
echo "モデル: /app/models/ggml-large-v3-turbo.bin"
echo "CPU スレッド数: ${WHISPER_THREADS:-4}"

# 環境変数のデフォルト値
export WHISPER_MODEL=${WHISPER_MODEL:-ggml-large-v3-turbo.bin}
export WHISPER_LANGUAGE=${WHISPER_LANGUAGE:-ja}
export WHISPER_THREADS=${WHISPER_THREADS:-4}

# データディレクトリの確認
if [ ! -d "/app/data" ]; then
    mkdir -p /app/data
fi

if [ ! -d "/app/output" ]; then
    mkdir -p /app/output
fi

# モデルファイルの確認
if [ ! -f "/app/models/${WHISPER_MODEL}" ]; then
    echo "エラー: モデルファイルが見つかりません: /app/models/${WHISPER_MODEL}"
    exit 1
fi

echo "セットアップ完了。処理を開始します。"

# メインコマンドを実行
exec "$@"
