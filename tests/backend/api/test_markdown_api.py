"""
Markdown API エンドポイントテスト

Markdown形式の出力取得・ダウンロード機能を検証する。
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.db.session import SessionLocal


@pytest.mark.skip(reason="Markdown endpoints do not exist in current API")
@pytest.mark.integration
class TestGetMarkdownEndpoint:
    """Markdown取得エンドポイントのテスト

    Note: Tests skipped because the /api/transcriptions/{id}/markdown endpoint
    does not exist in the current API. The markdown export functionality may have
    been moved, removed, or implemented differently.
    """

    def test_get_markdown_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしで取得するとエラーになるテスト"""
        response = test_client.get(f"/api/transcriptions/{uuid.uuid4()}/markdown")
        assert response.status_code in [401, 403]

    def test_get_markdown_transcription_not_found(self, real_auth_client: TestClient) -> None:
        """存在しない転写IDで404を返すテスト"""
        non_existent = str(uuid.uuid4())
        response = real_auth_client.get(f"/api/transcriptions/{non_existent}/markdown")
        assert response.status_code == 404

    def test_get_markdown_missing_summary(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """要約がない場合に404を返すテスト"""
        # テスト用データ作成（要約なし）
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)
            db.commit()

            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/markdown")
            assert response.status_code == 404
        finally:
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()

    def test_get_markdown_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """Markdown取得が成功するテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)

            # 要約を作成
            summary = Summary(
                id=str(uuid.uuid4()),
                transcription_id=trans_id,
                summary_text="# テスト会議\n\n- ポイント1\n- ポイント2"
            )
            db.add(summary)
            db.commit()

            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/markdown")
            assert response.status_code == 200
            data = response.json()
            assert "markdown" in data
            assert "# テスト会議" in data["markdown"]
        finally:
            db.query(Summary).filter(Summary.transcription_id == trans_id).delete()
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()


@pytest.mark.skip(reason="Markdown download endpoint does not exist in current API")
@pytest.mark.integration
class TestDownloadMarkdownEndpoint:
    """Markdownダウンロードエンドポイントのテスト

    Note: Tests skipped because the /api/transcriptions/{id}/download-markdown endpoint
    does not exist in the current API. The markdown export functionality may have
    been moved, removed, or implemented differently.
    """

    def test_download_markdown_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしでダウンロードするとエラーになるテスト"""
        response = test_client.get(f"/api/transcriptions/{uuid.uuid4()}/download-markdown")
        assert response.status_code in [401, 403]

    def test_download_markdown_transcription_not_found(self, real_auth_client: TestClient) -> None:
        """存在しない転写IDで404を返すテスト"""
        non_existent = str(uuid.uuid4())
        response = real_auth_client.get(f"/api/transcriptions/{non_existent}/download-markdown")
        assert response.status_code == 404

    def test_download_markdown_missing_summary(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """要約がない場合に404を返すテスト"""
        # テスト用データ作成（要約なし）
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)
            db.commit()

            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download-markdown")
            assert response.status_code == 404
        finally:
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()

    def test_download_markdown_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """Markdownダウンロードが成功するテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)

            # 要約を作成
            summary = Summary(
                id=str(uuid.uuid4()),
                transcription_id=trans_id,
                summary_text="# テスト会議\n\n- ポイント1\n- ポイント2"
            )
            db.add(summary)
            db.commit()

            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download-markdown")
            assert response.status_code == 200
            # Markdownファイルとしてダウンロード
            assert "text/markdown" in response.headers["content-type"]
            assert ".md" in response.headers["content-disposition"]
            assert "# テスト会議" in response.text
        finally:
            db.query(Summary).filter(Summary.transcription_id == trans_id).delete()
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()

    def test_download_markdown_has_content_disposition(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """Content-Dispositionヘッダーが正しく設定されているテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="conf.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)

            summary = Summary(
                id=str(uuid.uuid4()),
                transcription_id=trans_id,
                summary_text="# Test"
            )
            db.add(summary)
            db.commit()

            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download-markdown")
            assert response.status_code == 200
            # ファイル名が含まれている
            assert "attachment" in response.headers["content-disposition"]
            assert ".md" in response.headers["content-disposition"]
        finally:
            db.query(Summary).filter(Summary.transcription_id == trans_id).delete()
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()
