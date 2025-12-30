#!/bin/bash
set -euo pipefail

# dataフォルダ配下の一時ファイルをクリアするスクリプト

# カラー出力用
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}=== データキャッシュクリア ===${NC}"
echo ""

# dataディレクトリの存在確認
if [ ! -d "data" ]; then
  echo -e "${RED}エラー: dataディレクトリが見つかりません${NC}"
  exit 1
fi

# クリア対象のディレクトリ
UPLOAD_DIR="data/uploads"
OUTPUT_DIR="data/output"

# 削除対象ファイルの確認
TOTAL_FILES=0
if [ -d "$UPLOAD_DIR" ]; then
  UPLOAD_COUNT=$(find "$UPLOAD_DIR" -type f 2>/dev/null | wc -l)
  TOTAL_FILES=$((TOTAL_FILES + UPLOAD_COUNT))
else
  UPLOAD_COUNT=0
fi

if [ -d "$OUTPUT_DIR" ]; then
  OUTPUT_COUNT=$(find "$OUTPUT_DIR" -type f 2>/dev/null | wc -l)
  TOTAL_FILES=$((TOTAL_FILES + OUTPUT_COUNT))
else
  OUTPUT_COUNT=0
fi

if [ "$TOTAL_FILES" -eq 0 ]; then
  echo -e "${GREEN}✓ 削除対象のファイルはありません${NC}"
  exit 0
fi

# 削除確認
echo "削除対象:"
echo "  アップロードファイル: $UPLOAD_COUNT ファイル"
echo "  出力ファイル: $OUTPUT_COUNT ファイル"
echo "  合計: $TOTAL_FILES ファイル"
echo ""
read -p "これらのファイルを削除しますか? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
  echo -e "${YELLOW}キャンセルしました${NC}"
  exit 0
fi

# アップロードファイルのクリア
if [ -d "$UPLOAD_DIR" ] && [ "$UPLOAD_COUNT" -gt 0 ]; then
  echo -e "${YELLOW}アップロードファイルを削除中... ($UPLOAD_COUNT ファイル)${NC}"
  sudo find "$UPLOAD_DIR" -type f -delete
  echo -e "${GREEN}✓ アップロードファイルを削除しました${NC}"
fi

# 出力ファイルのクリア
if [ -d "$OUTPUT_DIR" ] && [ "$OUTPUT_COUNT" -gt 0 ]; then
  echo -e "${YELLOW}出力ファイルを削除中... ($OUTPUT_COUNT ファイル)${NC}"
  sudo find "$OUTPUT_DIR" -type f -delete
  echo -e "${GREEN}✓ 出力ファイルを削除しました${NC}"
fi

# ディレクトリサイズの表示
echo ""
echo -e "${GREEN}=== クリア完了 ===${NC}"
echo ""
echo "現在のディレクトリサイズ:"
du -sh data/ 2>/dev/null || echo "  data/: 0B"
if [ -d "$UPLOAD_DIR" ]; then
  du -sh "$UPLOAD_DIR" 2>/dev/null || echo "  $UPLOAD_DIR: 0B"
fi
if [ -d "$OUTPUT_DIR" ]; then
  du -sh "$OUTPUT_DIR" 2>/dev/null || echo "  $OUTPUT_DIR: 0B"
fi

echo ""
echo -e "${GREEN}✓ キャッシュクリアが完了しました${NC}"
