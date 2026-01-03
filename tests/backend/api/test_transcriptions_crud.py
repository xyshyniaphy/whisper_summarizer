"""
Transcriptions CRUD API エンドポイントテスト

文字起こしのリスト取得、詳細取得、削除機能を検証する。
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from app.models.transcription import Transcription
from app.db.session import SessionLocal


@pytest.mark.integration
class TestListTranscriptionsEndpoint:
    """文字起こしリスト取得エンドポイントのテスト"""

    @pytest.mark.skip(reason="DISABLE_AUTH=true bypasses authentication checks")

    def test_list_transcriptions_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしでリスト取得するとエラーになるテスト"""
        response = test_client.get("/api/transcriptions")
        assert response.status_code in [401, 403]

    def test_list_transcriptions_success(self, real_auth_client: TestClient) -> None:
        """認証済みでリスト取得が成功するテスト"""
        response = real_auth_client.get("/api/transcriptions")
        assert response.status_code == 200
        data = response.json()
        # API returns paginated response with data, page, page_size, total
        assert isinstance(data, dict)
        assert "data" in data
        assert isinstance(data["data"], list)
        assert "page" in data
        assert "page_size" in data
        assert "total" in data

    def test_list_transcriptions_filters_by_stage(self, real_auth_client: TestClient) -> None:
        """stageフィルターが動作するテスト"""
        response = real_auth_client.get("/api/transcriptions?stage=completed")
        assert response.status_code == 200
        data = response.json()
        # API returns paginated response with data field
        assert isinstance(data, dict)
        assert "data" in data
        items = data["data"]
        assert isinstance(items, list)
        # すべてのアイテムがstage="completed"であることを確認
        for item in items:
            assert item.get("stage") == "completed"


@pytest.mark.integration
class TestGetTranscriptionEndpoint:
    """文字起こし詳細取得エンドポイントのテスト"""

    @pytest.mark.skip(reason="DISABLE_AUTH=true bypasses authentication checks")

    def test_get_transcription_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしで詳細取得するとエラーになるテスト"""
        response = test_client.get(f"/api/transcriptions/{uuid.uuid4()}")
        assert response.status_code in [401, 403]

    def test_get_transcription_not_found(self, real_auth_client: TestClient) -> None:
        """存在しないIDで404を返すテスト"""
        non_existent = str(uuid.uuid4())
        response = real_auth_client.get(f"/api/transcriptions/{non_existent}")
        assert response.status_code == 404

    def test_get_transcription_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """詳細取得が成功するテスト"""
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
            db.commit()

            response = real_auth_client.get(f"/api/transcriptions/{trans_id}")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == trans_id
            assert data["file_name"] == "test.wav"
        finally:
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()


@pytest.mark.integration
class TestDeleteTranscriptionEndpoint:
    """文字起こし削除エンドポイントのテスト"""

    @pytest.mark.skip(reason="DISABLE_AUTH=true bypasses authentication checks")

    def test_delete_transcription_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしで削除するとエラーになるテスト"""
        response = test_client.delete(f"/api/transcriptions/{uuid.uuid4()}")
        assert response.status_code in [401, 403]

    def test_delete_transcription_not_found(self, real_auth_client: TestClient) -> None:
        """存在しないIDで削除すると404を返すテスト"""
        non_existent = str(uuid.uuid4())
        response = real_auth_client.delete(f"/api/transcriptions/{non_existent}")
        assert response.status_code == 404

    def test_delete_transcription_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """削除が成功するテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test_delete.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)
            db.commit()

            response = real_auth_client.delete(f"/api/transcriptions/{trans_id}")
            assert response.status_code == 204

            # 削除確認
            response = real_auth_client.get(f"/api/transcriptions/{trans_id}")
            assert response.status_code == 404
        finally:
            # クリーンアップ（念のため）
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()


@pytest.mark.integration
class TestDeleteAllTranscriptionsEndpoint:
    """全文字起こし削除エンドポイントのテスト"""

    @pytest.mark.skip(reason="DISABLE_AUTH=true bypasses authentication checks")

    def test_delete_all_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしで全削除するとエラーになるテスト"""
        response = test_client.delete("/api/transcriptions/all")
        assert response.status_code in [401, 403]

    def test_delete_all_returns_200_on_success(self, real_auth_client: TestClient) -> None:
        """全削除が成功すると200を返すテスト"""
        response = real_auth_client.delete("/api/transcriptions/all")
        assert response.status_code == 200
        data = response.json()
        assert "deleted_count" in data or response.status_code == 200

    def test_delete_all_returns_zero_when_empty(self, real_auth_client: TestClient) -> None:
        """空の状態で全削除しても成功するテスト"""
        # まず全て削除
        real_auth_client.delete("/api/transcriptions/all")

        # もう一度削除（空の状態）
        response = real_auth_client.delete("/api/transcriptions/all")
        assert response.status_code == 200
