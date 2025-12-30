# 統合テスト実行ガイド

## 概要

`tests/backend/integration/test_full_workflow.py` は、実際のテストデータを使用して音声アップロードから文字起こし、削除までの完全なワークフローをテストします。

## テスト内容

1. **音声ファイルアップロード**: `testdata/audio1074124412.conved_2min.m4a` (84KB)をアップロード
2. **文字起こし完了待機**: 最大5分間、5秒ごとにステータスをポーリング
3. **結果検証**: 文字起こし結果が10バイト以上であることを確認
4. **削除**: 文字起こしを削除し、削除を確認

## 前提条件

### 必須設定

統合テストは実際のSupabaseデータベースとWhisper.cppを使用するため、以下の環境変数が必要です：

```bash
# .envファイルに以下を設定
DATABASE_URL=postgresql://...  # Supabase PostgreSQL URL
SUPABASE_URL=https://...
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
```

### テストデータ

テストデータファイルが存在することを確認してください：
```bash
ls -lh testdata/audio1074124412.conved_2min.m4a
```

## 実行方法

### Docker環境で実行

```bash
cd tests

# 統合テストのみ実行（カバレッジなし、出力表示あり）
docker compose -f docker-compose.test.yml run --rm \
  backend-test pytest tests/backend/integration/ -v -s --no-cov

# 統合テストをスキップして他のテストを実行
docker compose -f docker-compose.test.yml run --rm \
  backend-test pytest -m "not integration" -v
```

### ローカル環境で実行

```bash
cd backend

# 統合テストのみ実行
pytest ../tests/backend/integration/test_full_workflow.py -v -s --no-cov

# すべてのテストを実行（統合テスト含む）
pytest ../tests/backend -v -s --no-cov
```

## マーカー

統合テストには以下のマーカーが付いています：

- `@pytest.mark.integration`: 外部サービス統合テスト
- `@pytest.mark.slow`: 実行に時間がかかるテスト（最大5分）

## トラブルシューティング

### データベース接続エラー

```
sqlalchemy.exc.OperationalError: connection to server at "localhost" failed
```

**解決方法**: `.env`ファイルに正しいSupabase PostgreSQL接続情報を設定してください。

### タイムアウトエラー

文字起こし処理に5分以上かかる場合、テストは失敗します。

**解決方法**: `test_full_workflow.py`の`max_wait_time`を延長してください。

### テストデータが見つからない

```
AssertionError: テストファイルが見つかりません
```

**解決方法**: プロジェクトルートに`testdata/audio1074124412.conved_2min.m4a`が存在することを確認してください。

## 期待される出力

成功時の出力例：

```
✓ 音声ファイルをアップロードしました (ID: 123)
文字起こし処理を待機中...
✓ 文字起こしが完了しました (45秒経過)
✓ 文字起こし結果を検証しました (1234バイト)
  テキストプレビュー: これはテストの文字起こし結果です...
✓ 文字起こしを削除しました (ID: 123)
✓ 削除を確認しました

=== テスト完了 ===
PASSED
```
