"""
DOCXダウンロードAPI エンドポイントテスト

AI摘要（DOCX）のダウンロード機能を検証する。
実DBと実ファイル操作を行う統合テスト。
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.db.session import SessionLocal


@pytest.mark.integration
class TestDownloadDocxAPI:
    """DOCXダウンロードAPI統合テスト"""

    def setup_transcription_with_summary(self, user_id: str, summary_text: str) -> str:
        """テスト用の文字起こしデータと要約を作成するヘルパー"""
        db = SessionLocal()
        trans_id = str(uuid.uuid4())

        try:
            # DBデータ作成
            transcription = Transcription(
                id=trans_id,
                user_id=user_id,
                file_name=f"test_docx_{trans_id}.wav"
                # Note: original_text is a read-only property that reads from storage
                # Note: status field doesn't exist on Transcription model
            )
            db.add(transcription)
            db.commit()
            db.refresh(transcription)

            # 要約を作成
            summary = Summary(
                id=str(uuid.uuid4()),
                transcription_id=trans_id,
                summary_text=summary_text
            )
            db.add(summary)
            db.commit()

            return trans_id
        finally:
            db.close()

    def teardown_transcription_with_summary(self, trans_id: str):
        """テストデータのクリーンアップ（要約付き）"""
        db = SessionLocal()
        try:
            db.query(Summary).filter(Summary.transcription_id == trans_id).delete()
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
        finally:
            db.close()

    def test_download_docx_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """DOCXファイルのダウンロード成功テスト（日本語・中国語混在）"""
        summary_text = """# 会議議事録

## 概要
本会議では**プロジェクトの進捗状況**について議論しました。

## 主な議論事項

- フロントエンドの実装状況
- バックエンドAPIの設計
- データベースの最適化

## 結論

次回のミーティングは_来週月曜日_に予定されています。
"""

        trans_id = self.setup_transcription_with_summary(real_auth_user["id"], summary_text)
        try:
            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download-docx")
            assert response.status_code == 200
            assert "application/vnd.openxmlformats-officedocument.wordprocessingml.document" in response.headers["content-type"]
            # The filename may be URL-encoded, so check for both encoded and unencoded versions
            disposition = response.headers["content-disposition"]
            assert f"test_docx_{trans_id}-" in disposition or f"test_docx_{trans_id}-%E6%91%98%E8%A6%81" in disposition
            assert len(response.content) > 0
            assert response.content[:2] == b'PK'
        finally:
            self.teardown_transcription_with_summary(trans_id)

    def test_download_docx_chinese_only(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """中国語のみの要約のDOCXダウンロードテスト"""
        summary_text = """# 会议纪要

## 摘要
本次会议讨论了**项目进展情况**。

## 讨论要点

- 前端开发进度
- 后端API设计
- 数据库优化

## 结论

下周_一_继续讨论。
"""

        trans_id = self.setup_transcription_with_summary(real_auth_user["id"], summary_text)
        try:
            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download-docx")
            assert response.status_code == 200
            assert len(response.content) > 0
            assert response.content[:2] == b'PK'
        finally:
            self.teardown_transcription_with_summary(trans_id)

    def test_download_docx_no_summary(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """要約がない場合の404テスト"""
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test_no_summary.wav"
                # Note: status field doesn't exist on Transcription model
            )
            db.add(transcription)
            db.commit()

            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download-docx")
            assert response.status_code == 404
            assert "未找到摘要数据" in response.json()["detail"]

        finally:
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()

    def test_download_docx_empty_summary_list(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """要約リストが空の場合の404テスト"""
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test_empty_summary.wav"
                # Note: status field doesn't exist on Transcription model
            )
            db.add(transcription)
            db.commit()

            db.query(Summary).filter(Summary.transcription_id == trans_id).delete()
            db.commit()

            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download-docx")
            assert response.status_code == 404
            assert "未找到摘要数据" in response.json()["detail"]

        finally:
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()

    def test_download_docx_not_found_transcription(self, real_auth_client: TestClient) -> None:
        """存在しない転写IDでの404テスト"""
        non_existent = str(uuid.uuid4())
        response = real_auth_client.get(f"/api/transcriptions/{non_existent}/download-docx")
        assert response.status_code == 404

    def test_download_docx_markdown_parsing(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """Markdownパースのテスト（見出し、リスト、フォーマット）"""
        summary_text = """# タイトル1
## タイトル2
### タイトル3

- リスト項目1
- リスト項目2
* アスタリスクリスト
+ プラスリスト

通常テキスト**太字テキスト**通常テキスト
イタリック前_イタリックテキスト_イタリック後
"""

        trans_id = self.setup_transcription_with_summary(real_auth_user["id"], summary_text)
        try:
            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download-docx")
            assert response.status_code == 200
            assert len(response.content) > 0
            assert response.content[:2] == b'PK'
        finally:
            self.teardown_transcription_with_summary(trans_id)
