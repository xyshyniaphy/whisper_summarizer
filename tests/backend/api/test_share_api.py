"""
Share API エンドポイントテスト

文字起こしの共有リンク作成、公開アクセス機能を検証する。
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from app.models.transcription import Transcription
from app.models.user import User
from app.models.share_link import ShareLink
from app.db.session import SessionLocal


@pytest.mark.integration
class TestCreateShareLinkEndpoint:
    """共有リンク作成エンドポイントのテスト"""

    def test_create_share_link_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしでリンク作成するとエラーになるテスト"""
        response = test_client.post(f"/api/transcriptions/{uuid.uuid4()}/share")
        assert response.status_code in [401, 403]

    def test_create_share_link_transcription_not_found(self, real_auth_client: TestClient) -> None:
        """存在しない転写IDで404を返すテスト"""
        non_existent = str(uuid.uuid4())
        response = real_auth_client.post(f"/api/transcriptions/{non_existent}/share")
        assert response.status_code == 404

    def test_create_share_link_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """共有リンク作成が成功するテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["raw_uuid"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)
            db.commit()

            response = real_auth_client.post(f"/api/transcriptions/{trans_id}/share")
            assert response.status_code in [200, 201]
            data = response.json()
            assert "share_token" in data or "share_url" in data
        finally:
            db.query(ShareLink).filter(ShareLink.transcription_id == trans_id).delete()
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()

    def test_create_share_link_with_expiration(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """有効期限付きリンク作成が成功するテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["raw_uuid"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)
            db.commit()

            # 7日後に期限切れ
            import datetime
            expires_at = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7)).isoformat()

            response = real_auth_client.post(
                f"/api/transcriptions/{trans_id}/share",
                json={"expires_in_days": 7}
            )
            assert response.status_code in [200, 201]
            data = response.json()
            assert "share_token" in data or "share_url" in data
        finally:
            db.query(ShareLink).filter(ShareLink.transcription_id == trans_id).delete()
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()


@pytest.mark.integration
class TestAccessSharedTranscriptionEndpoint:
    """公開共有エンドポイントのテスト"""

    def test_get_shared_transcription_no_auth_required(self, test_client: TestClient) -> None:
        """認証なしで共有転写にアクセスできるテスト"""
        # トークンなしでアクセス可能
        response = test_client.get(f"/api/shared/{uuid.uuid4()}")
        # 404はOK（存在しないトークン）、401/403はNG（認証不要）
        assert response.status_code != 401
        assert response.status_code != 403

    def test_get_shared_transcription_invalid_token(self, test_client: TestClient) -> None:
        """無効なトークンで404を返すテスト"""
        response = test_client.get("/api/shared/invalid_token_12345")
        assert response.status_code == 404

    def test_get_shared_transcription_success(self, test_client: TestClient, real_auth_user: dict) -> None:
        """共有転写取得が成功するテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            # Create user first (real_auth_user fixture only returns dict, doesn't create DB entry)
            user = User(
                id=real_auth_user["raw_uuid"],
                email=real_auth_user["email"],
                is_active=True
            )
            db.add(user)
            db.commit()

            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["raw_uuid"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)
            db.commit()

            # 共有リンク作成
            share_link = ShareLink(
                id=str(uuid.uuid4()),
                transcription_id=trans_id,
                share_token="test_token_12345"
            )
            db.add(share_link)
            db.commit()

            # 認証なしでアクセス
            response = test_client.get("/api/shared/test_token_12345")
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == trans_id
            assert data["file_name"] == "test.wav"
        finally:
            db.query(ShareLink).filter(ShareLink.transcription_id == trans_id).delete()
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.query(User).filter(User.id == real_auth_user["raw_uuid"]).delete()
            db.commit()
            db.close()

    def test_get_shared_transcription_expired_link(self, test_client: TestClient, real_auth_user: dict) -> None:
        """期限切れリンクで410を返すテスト"""
        # テスト用データ作成
        import datetime
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            # Create user first
            user = User(
                id=real_auth_user["raw_uuid"],
                email=real_auth_user["email"],
                is_active=True
            )
            db.add(user)
            db.commit()

            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["raw_uuid"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)
            db.commit()

            # 期限切れの共有リンク
            expired_link = ShareLink(
                id=str(uuid.uuid4()),
                transcription_id=trans_id,
                share_token="expired_token",
                expires_at=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=1)
            )
            db.add(expired_link)
            db.commit()

            response = test_client.get("/api/shared/expired_token")
            assert response.status_code == 410
        finally:
            db.query(ShareLink).filter(ShareLink.transcription_id == trans_id).delete()
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.query(User).filter(User.id == real_auth_user["raw_uuid"]).delete()
            db.commit()
            db.close()
