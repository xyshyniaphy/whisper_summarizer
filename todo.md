# Whisper Summarizer - TODO

最終更新: 2025-12-29

## 完了項目 ✅

### Docker環境構築
- [x] Whisper.cppベースイメージの最適化 (3.46GB、28%削減)
- [x] 静的FFmpegの統合
- [x] uvベースのバックエンドビルド
- [x] PostgreSQLからSupabase PostgreSQLへの移行
- [x] docker-compose.yml、docker-compose.dev.ymlの作成
- [x] 開発環境の起動確認 (http://localhost:8000, http://localhost:3000)
- [x] README.mdの更新

### バックエンド基本実装
- [x] FastAPI基本構造
- [x] Supabase認証統合
- [x] GLM4.7クライアント実装
- [x] Whisper.cppサービス統合 (backend内で直接呼び出し)
- [x] データベース設定 (Supabase PostgreSQL)

### フロントエンド基本実装
- [x] React基本構造
- [x] Supabase認証UI
- [x] ルーティング設定

---

## 次にやるべきこと 🚀

### 1. データベーススキーマの実装 (優先度: 高)

#### タスク:
- [ ] SQLAlchemyモデルの作成
  - [ ] Usersテーブル
  - [ ] Transcriptionsテーブル
  - [ ] Summariesテーブル
- [ ] Alembicマイグレーションの実行
  - [ ] 初期マイグレーションファイル作成
  - [ ] Supabase PostgreSQLへのマイグレーション適用
- [ ] データベース接続のテスト

#### 予想時間: 2-3時間

#### 参考:
- `backend/app/models/` ディレクトリ
- `backend/alembic.ini`
- Supabase Dashboard: Settings > Database

---

### 2. 音声アップロード機能の実装 (優先度: 高)

#### バックエンド:
- [ ] `/api/audio/upload` エンドポイントの完成
  - [ ] 音声ファイルバリデーション (形式、サイズ)
  - [ ] Whisper.cppサービス呼び出し
  - [ ] データベースへの保存
  - [ ] エラーハンドリング
- [ ] `/api/transcriptions/{id}` エンドポイント (取得)
- [ ] `/api/transcriptions` エンドポイント (リスト)

#### フロントエンド:
- [ ] 音声アップロードUIの実装
  - [ ] ファイル選択コンポーネント
  - [ ] ドラッグ&ドロップ対応
  - [ ] アップロード進捗表示
  - [ ] エラー表示
- [ ] 文字起こし結果表示画面
  - [ ] タイムスタンプ付きテキスト表示
  - [ ] SRT形式のダウンロード

#### 予想時間: 4-6時間

---

### 3. GLM4.7要約機能の実装 (優先度: 中)

#### バックエンド:
- [ ] `/api/summaries/generate` エンドポイント
  - [ ] 文字起こしテキストの取得
  - [ ] GLM4.7 API呼び出し
  - [ ] 要約結果の保存
  - [ ] エラーハンドリング (API制限、タイムアウト等)
- [ ] `/api/summaries/{transcription_id}` エンドポイント

#### フロントエンド:
- [ ] 要約生成ボタン
- [ ] 要約結果表示
- [ ] ローディング状態の表示

#### 予想時間: 3-4時間

---

### 4. 認証フローのテスト (優先度: 中)

#### タスク:
- [ ] サインアップフローのテスト
  - [ ] メール確認フロー
  - [ ] エラーケース (重複メール等)
- [ ] ログインフローのテスト
- [ ] ログアウトのテスト
- [ ] 保護されたルートのテスト
- [ ] トークンリフレッシュのテスト

#### 予想時間: 2-3時間

---

### 5. UIの改善 (優先度: 低)

#### タスク:
- [ ] ダッシュボードUIの実装
  - [ ] 文字起こし履歴一覧
  - [ ] 検索機能
  - [ ] フィルタリング機能
- [ ] レスポンシブデザインの調整
- [ ] ダークモード対応
- [ ] ローディング・エラー状態の改善

#### 予想時間: 4-6時間

---

### 6. テストの実装 (優先度: 低)

#### バックエンド:
- [ ] ユニットテスト (pytest)
  - [ ] APIエンドポイント
  - [ ] Whisper.cppサービス
  - [ ] GLM4.7クライアント
- [ ] 統合テスト

#### フロントエンド:
- [ ] コンポーネントテスト (Vitest)
- [ ] E2Eテスト (Playwright)

#### 予想時間: 6-8時間

---

### 7. 本番環境の準備 (優先度: 低)

#### タスク:
- [ ] docker-compose.ymlの最終調整
- [ ] 環境変数の本番設定
- [ ] Nginxの本番設定
- [ ] ログ設定
- [ ] モニタリング設定
- [ ] バックアップ戦略

#### 予想時間: 3-4時間

---

## 技術的な課題・検討事項 💡

### パフォーマンス最適化
- [ ] Whisper.cpp処理の非同期化 (Celery等)
- [ ] 長時間音声ファイルの処理戦略
- [ ] キャッシュ戦略 (Redis等)

### セキュリティ
- [ ] ファイルアップロードのセキュリティ強化
- [ ] レート制限の実装
- [ ] CORS設定の見直し

### スケーラビリティ
- [ ] 複数ワーカーでのWhisper.cpp処理
- [ ] ファイルストレージの検討 (Supabase Storage等)

---

## 即座にできること (Quick Wins) 🎯

1. **ヘルスチェックエンドポイントの追加** (15分)
   ```python
   @app.get("/health")
   async def health():
       return {"status": "ok"}
   ```

2. **環境変数の検証** (30分)
   - バックエンド起動時に必須環境変数をチェック
   - 不足している場合はエラーメッセージを表示

3. **ログ設定の改善** (30分)
   - 構造化ログ (JSON形式)
   - ログレベルの環境変数化

4. **API Docsのカスタマイズ** (30分)
   - タイトル、説明の追加
   - 認証情報の設定

---

## 開発環境コマンド 🛠️

```bash
# 開発環境起動
./run_dev.sh up-d

# ログ確認
./run_dev.sh logs

# コンテナ状態確認
./run_dev.sh ps

# 停止
./run_dev.sh down

# 完全再ビルド
./run_dev.sh rebuild
```

## 参考リンク 📚

- [Implementation Plan](file:///home/lmr/.gemini/antigravity/brain/c2b540b2-7552-4127-98b3-45f005b22efe/implementation_plan.md)
- [Walkthrough](file:///home/lmr/.gemini/antigravity/brain/c2b540b2-7552-4127-98b3-45f005b22efe/walkthrough.md)
- [Task Management](file:///home/lmr/.gemini/antigravity/brain/c2b540b2-7552-4127-98b3-45f005b22efe/task.md)
- [Project Spec](file:///home/lmr/ws/whisper_summarizer/spec.md)
- [README](file:///home/lmr/ws/whisper_summarizer/README.md)
