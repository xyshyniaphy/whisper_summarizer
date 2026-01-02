"""
PPTX API エンドポイントテスト

PowerPointプレゼンテーション生成機能を検証する。
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.db.session import SessionLocal


@pytest.mark.integration
class TestGeneratePPTXEndpoint:
    """PPTX生成エンドポイントのテスト"""

    def test_generate_pptx_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしで生成するとエラーになるテスト"""
        response = test_client.post(f"/api/transcriptions/{uuid.uuid4()}/generate-pptx")
        assert response.status_code in [401, 403]

    def test_generate_pptx_transcription_not_found(self, real_auth_client: TestClient) -> None:
        """存在しない転写IDで404を返すテスト"""
        non_existent = str(uuid.uuid4())
        response = real_auth_client.post(f"/api/transcriptions/{non_existent}/generate-pptx")
        assert response.status_code == 404

    def test_generate_pptx_missing_summary(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """要約がない場合に400エラーを返すテスト"""
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

            response = real_auth_client.post(f"/api/transcriptions/{trans_id}/generate-pptx")
            assert response.status_code == 400
        finally:
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()

    def test_generate_pptx_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """PPTX生成が成功するテスト"""
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
                summary_text="# テスト要約\n\n- ポイント1\n- ポイント2"
            )
            db.add(summary)
            db.commit()

            # Marpサービスをモック
            with patch("app.api.transcriptions.PPTXService") as mock_pptx_service:
                mock_service = MagicMock()
                mock_service.generate_pptx.return_value = "/app/output/test.pptx"
                mock_pptx_service.return_value = mock_service

                response = real_auth_client.post(f"/api/transcriptions/{trans_id}/generate-pptx")
                # バックグラウンドタスクなので202 Accepted
                assert response.status_code == 202
        finally:
            db.query(Summary).filter(Summary.transcription_id == trans_id).delete()
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()


@pytest.mark.integration
class TestPPTXStatusEndpoint:
    """PPTXステータス確認エンドポイントのテスト"""

    def test_get_pptx_status_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしでステータス取得するとエラーになるテスト"""
        response = test_client.get(f"/api/transcriptions/{uuid.uuid4()}/pptx-status")
        assert response.status_code in [401, 403]

    def test_get_pptx_status_transcription_not_found(self, real_auth_client: TestClient) -> None:
        """存在しない転写IDで404を返すテスト"""
        non_existent = str(uuid.uuid4())
        response = real_auth_client.get(f"/api/transcriptions/{non_existent}/pptx-status")
        assert response.status_code == 404

    def test_get_pptx_status_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """ステータス取得が成功するテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed",
                pptx_status="ready"
            )
            db.add(transcription)
            db.commit()

            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/pptx-status")
            assert response.status_code == 200
            data = response.json()
            assert "status" in data
            assert data["status"] == "ready"
        finally:
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()

    def test_get_pptx_status_not_started(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """未開始のステータスを正しく返すテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed",
                pptx_status="not-started"
            )
            db.add(transcription)
            db.commit()

            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/pptx-status")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "not-started"
        finally:
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()

    def test_get_pptx_status_error(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """エラーステータスを正しく返すテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed",
                pptx_status="error",
                pptx_error_message="生成に失敗しました"
            )
            db.add(transcription)
            db.commit()

            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/pptx-status")
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "error"
            assert "error_message" in data
        finally:
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()
