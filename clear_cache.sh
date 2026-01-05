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
UPLOAD_DIR="data/server/uploads"
OUTPUT_DIR="data/runner/transcribes"
SCREENSHOTS_DIR="data/screenshots"
REPORT_DIR="data/playwright-report"
TEST_RESULTS_DIR="data/test-results"

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

if [ -d "$SCREENSHOTS_DIR" ]; then
  SCREENSHOTS_COUNT=$(find "$SCREENSHOTS_DIR" -type f 2>/dev/null | wc -l)
  TOTAL_FILES=$((TOTAL_FILES + SCREENSHOTS_COUNT))
else
  SCREENSHOTS_COUNT=0
fi

if [ -d "$REPORT_DIR" ]; then
  REPORT_COUNT=$(find "$REPORT_DIR" -type f 2>/dev/null | wc -l)
  TOTAL_FILES=$((TOTAL_FILES + REPORT_COUNT))
else
  REPORT_COUNT=0
fi

if [ -d "$TEST_RESULTS_DIR" ]; then
  RESULTS_COUNT=$(find "$TEST_RESULTS_DIR" -type f 2>/dev/null | wc -l)
  TOTAL_FILES=$((TOTAL_FILES + RESULTS_COUNT))
else
  RESULTS_COUNT=0
fi

if [ "$TOTAL_FILES" -eq 0 ]; then
  echo -e "${GREEN}✓ 削除対象のファイルはありません${NC}"
  exit 0
fi

# 削除確認
echo "削除対象:"
echo "  アップロードファイル: $UPLOAD_COUNT ファイル"
echo "  出力ファイル: $OUTPUT_COUNT ファイル"
echo "  スクリーンショット: $SCREENSHOTS_COUNT ファイル"
echo "  Playwrightレポート: $REPORT_COUNT ファイル"
echo "  テスト結果: $RESULTS_COUNT ファイル"
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

# スクリーンショットのクリア
if [ -d "$SCREENSHOTS_DIR" ] && [ "$SCREENSHOTS_COUNT" -gt 0 ]; then
  echo -e "${YELLOW}スクリーンショットを削除中... ($SCREENSHOTS_COUNT ファイル)${NC}"
  sudo rm -rf "$SCREENSHOTS_DIR"/*
  echo -e "${GREEN}✓ スクリーンショットを削除しました${NC}"
fi

# Playwrightレポートのクリア
if [ -d "$REPORT_DIR" ] && [ "$REPORT_COUNT" -gt 0 ]; then
  echo -e "${YELLOW}Playwrightレポートを削除中... ($REPORT_COUNT ファイル)${NC}"
  sudo rm -rf "$REPORT_DIR"/*
  echo -e "${GREEN}✓ Playwrightレポートを削除しました${NC}"
fi

# テスト結果のクリア
if [ -d "$TEST_RESULTS_DIR" ] && [ "$RESULTS_COUNT" -gt 0 ]; then
  echo -e "${YELLOW}テスト結果を削除中... ($RESULTS_COUNT ファイル)${NC}"
  sudo rm -rf "$TEST_RESULTS_DIR"/*
  echo -e "${GREEN}✓ テスト結果を削除しました${NC}"
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
if [ -d "$SCREENSHOTS_DIR" ]; then
  du -sh "$SCREENSHOTS_DIR" 2>/dev/null || echo "  $SCREENSHOTS_DIR: 0B"
fi
if [ -d "$REPORT_DIR" ]; then
  du -sh "$REPORT_DIR" 2>/dev/null || echo "  $REPORT_DIR: 0B"
fi
if [ -d "$TEST_RESULTS_DIR" ]; then
  du -sh "$TEST_RESULTS_DIR" 2>/dev/null || echo "  $TEST_RESULTS_DIR: 0B"
fi

echo ""
echo -e "${GREEN}✓ キャッシュクリアが完了しました${NC}"
