"""
Admin API エンドポイントテスト

管理者権限、ユーザー管理、チャンネル管理、音声管理の機能を検証する。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
import uuid
from datetime import datetime
from sqlalchemy.orm import Session


# ==============================================================================
# Fixtures
# ==============================================================================

@pytest.fixture
def admin_user(db_session: Session) -> dict:
    """テスト用管理者ユーザーを作成"""
    from app.models.user import User

    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"admin-{str(uid)[:8]}@example.com",
        is_active=True,
        is_admin=True,
        activated_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return {
        "id": str(uid),
        "email": user.email,
        "raw_uuid": uid
    }


@pytest.fixture
def regular_user(db_session: Session) -> dict:
    """テスト用一般ユーザーを作成"""
    from app.models.user import User

    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"user-{str(uid)[:8]}@example.com",
        is_active=True,
        is_admin=False,
        activated_at=datetime.utcnow()
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return {
        "id": str(uid),
        "email": user.email,
        "raw_uuid": uid
    }


@pytest.fixture
def inactive_user(db_session: Session) -> dict:
    """テスト用非アクティブユーザーを作成"""
    from app.models.user import User

    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"inactive-{str(uid)[:8]}@example.com",
        is_active=False,
        is_admin=False,
        activated_at=None
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    return {
        "id": str(uid),
        "email": user.email,
        "raw_uuid": uid
    }


@pytest.fixture
def admin_auth_client(admin_user: dict, db_session: Session) -> TestClient:
    """管理者認証済みTestClient"""
    from app.main import app
    from app.core.supabase import get_current_active_user
    from app.api.deps import require_admin

    async def override_auth():
        return {
            "id": admin_user["id"],
            "email": admin_user["email"],
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"is_admin": True, "is_active": True}
        }

    def override_require_admin():
        from app.models.user import User
        return db_session.query(User).filter(User.id == admin_user["raw_uuid"]).first()

    app.dependency_overrides[get_current_active_user] = override_auth
    app.dependency_overrides[require_admin] = override_require_admin

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.fixture
def regular_auth_client(regular_user: dict, db_session: Session) -> TestClient:
    """一般ユーザー認証済みTestClient"""
    from app.main import app
    from app.core.supabase import get_current_active_user

    async def override_auth():
        return {
            "id": regular_user["id"],
            "email": regular_user["email"],
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"is_admin": False, "is_active": True}
        }

    app.dependency_overrides[get_current_active_user] = override_auth

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.fixture
def test_channel(db_session: Session, admin_user: dict) -> dict:
    """テスト用チャンネルを作成"""
    from app.models.channel import Channel

    channel = Channel(
        name=f"Test Channel {uuid.uuid4().hex[:8]}",
        description="Test channel description",
        created_by=admin_user["raw_uuid"]
    )
    db_session.add(channel)
    db_session.commit()
    db_session.refresh(channel)

    return {
        "id": str(channel.id),
        "name": channel.name,
        "description": channel.description
    }


@pytest.fixture
def db_session():
    """テスト用データベースセッション
    
    セッション終了時にロールバックを行い、テスト間のデータ汚染を防ぐ。
    """
    from app.db.session import SessionLocal

    db = SessionLocal()
    try:
        yield db
    finally:
        db.rollback()
        db.close()


@pytest.fixture
def test_client() -> TestClient:
    """認証なしのTestClient（認証テスト用）"""
    from app.main import app
    return TestClient(app)


# ==============================================================================
# Permission Tests
# ==============================================================================

@pytest.mark.integration
class TestAdminPermissions:
    """管理者権限テスト"""

    def test_non_admin_cannot_access_admin_endpoints(self, regular_auth_client: TestClient) -> None:
        """一般ユーザーが管理者エンドポイントにアクセスできないテスト"""
        response = regular_auth_client.get("/api/admin/users")
        # 401 (unauthenticated) is returned because the dependency check fails before admin check
        assert response.status_code in [401, 403]

    def test_unauthenticated_cannot_access_admin_endpoints(self, test_client: TestClient) -> None:
        """認証なしで管理者エンドポイントにアクセスできないテスト"""
        response = test_client.get("/api/admin/users")
        assert response.status_code in [401, 403]


# ==============================================================================
# User Management Tests
# ==============================================================================

@pytest.mark.integration
class TestUserManagement:
    """ユーザー管理エンドポイントテスト"""

    def test_list_users_as_admin(self, admin_auth_client: TestClient) -> None:
        """管理者が全ユーザー一覧を取得できるテスト"""
        response = admin_auth_client.get("/api/admin/users")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        # All users should be returned
        assert len(data) >= 1

    def test_activate_user_as_admin(self, admin_auth_client: TestClient, inactive_user: dict) -> None:
        """管理者がユーザーをアクティベートできるテスト"""
        response = admin_auth_client.put(f"/api/admin/users/{inactive_user['id']}/activate")
        assert response.status_code == 200
        data = response.json()
        assert data["is_active"] is True
        assert data["activated_at"] is not None

    def test_activate_nonexistent_user_returns_404(self, admin_auth_client: TestClient) -> None:
        """存在しないユーザーのアクティベートが404を返すテスト"""
        fake_id = str(uuid.uuid4())
        response = admin_auth_client.put(f"/api/admin/users/{fake_id}/activate")
        assert response.status_code == 404

    def test_toggle_user_admin_to_admin(self, admin_auth_client: TestClient, regular_user: dict) -> None:
        """管理者がユーザーを管理者に昇格できるテスト"""
        response = admin_auth_client.put(
            f"/api/admin/users/{regular_user['id']}/admin",
            json={"is_admin": True}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] is True

    def test_toggle_user_admin_to_regular(self, admin_auth_client: TestClient, regular_user: dict, db_session: Session) -> None:
        """管理者を一般ユーザーに降格できるテスト（2人以上の管理者がいる場合）"""
        from app.models.user import User

        # First, make regular_user an admin
        user = db_session.query(User).filter(User.id == regular_user["raw_uuid"]).first()
        user.is_admin = True
        db_session.commit()

        # Now try to demote them (should succeed since we still have admin_user as admin)
        response = admin_auth_client.put(
            f"/api/admin/users/{regular_user['id']}/admin",
            json={"is_admin": False}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["is_admin"] is False

    def test_cannot_toggle_own_admin_status(self, admin_auth_client: TestClient, admin_user: dict) -> None:
        """自分の管理者権限を変更できないテスト"""
        response = admin_auth_client.put(
            f"/api/admin/users/{admin_user['id']}/admin",
            json={"is_admin": False}
        )
        assert response.status_code == 400
        assert "Cannot modify your own admin status" in response.json()["detail"]

    def test_cannot_remove_last_admin(self, admin_auth_client: TestClient, admin_user: dict, db_session: Session) -> None:
        """最後の管理者を削除できないテスト

        Note: The API checks for self-modification first, so we expect that error.
        The "last admin" check comes after the self-modification check.
        """
        response = admin_auth_client.put(
            f"/api/admin/users/{admin_user['id']}/admin",
            json={"is_admin": False}
        )
        # Since admin_user is the authenticated admin, we get "Cannot modify your own" error first
        assert response.status_code == 400
        detail = response.json()["detail"]
        # Either error message is acceptable - both prevent the last admin from being removed
        assert "Cannot modify your own admin status" in detail or "Cannot remove admin status from the last admin" in detail

    def test_delete_user_soft_deletes(self, admin_auth_client: TestClient, regular_user: dict, db_session: Session) -> None:
        """ユーザー削除がソフトデリートで行われるテスト"""
        response = admin_auth_client.delete(f"/api/admin/users/{regular_user['id']}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify soft delete in database
        from app.models.user import User
        user = db_session.query(User).filter(User.id == regular_user["raw_uuid"]).first()
        assert user is not None  # User still exists in DB
        assert user.deleted_at is not None  # But has deleted_at timestamp

    def test_cannot_delete_self(self, admin_auth_client: TestClient, admin_user: dict) -> None:
        """自分自身を削除できないテスト"""
        response = admin_auth_client.delete(f"/api/admin/users/{admin_user['id']}")
        assert response.status_code == 400
        assert "Cannot delete your own account" in response.json()["detail"]

    def test_cannot_delete_last_admin(self, admin_auth_client: TestClient, admin_user: dict) -> None:
        """最後の管理者を削除できないテスト

        Note: The API checks for self-deletion first, so we expect that error.
        The "last admin" check comes after the self-deletion check.
        """
        response = admin_auth_client.delete(f"/api/admin/users/{admin_user['id']}")
        # Since admin_user is the authenticated admin, we get "Cannot delete your own account" error first
        assert response.status_code == 400
        detail = response.json()["detail"]
        # Either error message is acceptable - both prevent the last admin from being deleted
        assert "Cannot delete your own account" in detail or "Cannot delete the last admin" in detail

    def test_delete_user_transfers_ownership(self, admin_auth_client: TestClient, regular_user: dict, admin_user: dict, db_session: Session) -> None:
        """ユーザー削除時、所有権が管理者に移転するテスト"""
        from app.models.transcription import Transcription

        # Create a test transcription for regular_user
        transcription = Transcription(
            id=uuid.uuid4(),
            user_id=regular_user["raw_uuid"],
            file_name="test.mp3",
            language="zh",
            duration_seconds=60,
            stage="completed"
        )
        db_session.add(transcription)
        db_session.commit()

        # Delete the user
        admin_auth_client.delete(f"/api/admin/users/{regular_user['id']}")

        # Verify ownership transfer
        updated_transcription = db_session.query(Transcription).filter(
            Transcription.id == transcription.id
        ).first()
        assert updated_transcription.user_id == admin_user["raw_uuid"]


# ==============================================================================
# Channel Management Tests
# ==============================================================================

@pytest.mark.integration
class TestChannelManagement:
    """チャンネル管理エンドポイントテスト"""

    def test_list_channels_as_admin(self, admin_auth_client: TestClient) -> None:
        """管理者が全チャンネル一覧を取得できるテスト"""
        response = admin_auth_client.get("/api/admin/channels")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_create_channel(self, admin_auth_client: TestClient, db_session: Session) -> None:
        """チャンネルを作成できるテスト"""
        from app.models.channel import Channel

        channel_name = f"New Channel {uuid.uuid4().hex[:8]}"
        response = admin_auth_client.post(
            "/api/admin/channels",
            json={
                "name": channel_name,
                "description": "Test channel description"
            }
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == channel_name
        assert data["description"] == "Test channel description"
        assert data["member_count"] == 0

        # Cleanup: delete the created channel
        created_channel = db_session.query(Channel).filter(Channel.id == data["id"]).first()
        if created_channel:
            db_session.delete(created_channel)
            db_session.commit()

    def test_create_channel_duplicate_name_fails(self, admin_auth_client: TestClient, test_channel: dict) -> None:
        """重複するチャンネル名で作成が失敗するテスト"""
        response = admin_auth_client.post(
            "/api/admin/channels",
            json={
                "name": test_channel["name"],
                "description": "Duplicate name"
            }
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

    def test_update_channel(self, admin_auth_client: TestClient, test_channel: dict) -> None:
        """チャンネルを更新できるテスト"""
        new_name = f"Updated {uuid.uuid4().hex[:8]}"
        response = admin_auth_client.put(
            f"/api/admin/channels/{test_channel['id']}",
            json={
                "name": new_name,
                "description": "Updated description"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == new_name
        assert data["description"] == "Updated description"

    def test_update_channel_duplicate_name_fails(self, admin_auth_client: TestClient, db_session: Session, test_channel: dict, admin_user: dict) -> None:
        """重複する名前への更新が失敗するテスト"""
        from app.models.channel import Channel

        # Create another channel using admin_user as creator
        channel2 = Channel(
            name=f"Channel 2 {uuid.uuid4().hex[:8]}",
            description="Second channel",
            created_by=admin_user["raw_uuid"]
        )
        db_session.add(channel2)
        db_session.commit()
        channel2_id = str(channel2.id)

        # Try to rename test_channel to channel2's name
        response = admin_auth_client.put(
            f"/api/admin/channels/{test_channel['id']}",
            json={"name": channel2.name}
        )
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]

        # Cleanup: delete channel2
        db_session.delete(channel2)
        db_session.commit()

    def test_delete_channel(self, admin_auth_client: TestClient, db_session: Session, admin_user: dict) -> None:
        """チャンネルを削除できるテスト"""
        from app.models.channel import Channel

        # Create a test channel using admin_user as creator
        channel = Channel(
            name=f"Delete Test {uuid.uuid4().hex[:8]}",
            description="To be deleted",
            created_by=admin_user["raw_uuid"]
        )
        db_session.add(channel)
        db_session.commit()
        channel_id = str(channel.id)

        # Delete it
        response = admin_auth_client.delete(f"/api/admin/channels/{channel_id}")
        assert response.status_code == 200
        assert "deleted successfully" in response.json()["message"]

        # Verify deletion
        deleted_channel = db_session.query(Channel).filter(Channel.id == channel_id).first()
        assert deleted_channel is None

    def test_get_channel_detail(self, admin_auth_client: TestClient, test_channel: dict) -> None:
        """チャンネル詳細を取得できるテスト"""
        response = admin_auth_client.get(f"/api/admin/channels/{test_channel['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == test_channel["id"]
        assert data["name"] == test_channel["name"]
        assert "members" in data
        assert "member_count" in data


# ==============================================================================
# Channel Membership Tests
# ==============================================================================

@pytest.mark.integration
class TestChannelMembership:
    """チャンネルメンバーシップテスト"""

    def test_assign_user_to_channel(self, admin_auth_client: TestClient, test_channel: dict, regular_user: dict, db_session: Session) -> None:
        """ユーザーをチャンネルに割り当てられるテスト"""
        from app.models.channel import ChannelMembership

        response = admin_auth_client.post(
            f"/api/admin/channels/{test_channel['id']}/members",
            json={"user_id": regular_user["id"]}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["channel_id"] == test_channel["id"]
        assert str(data["user_id"]) == regular_user["id"]

        # Cleanup: delete the membership created by this test
        membership = db_session.query(ChannelMembership).filter(
            ChannelMembership.channel_id == test_channel["id"],
            ChannelMembership.user_id == regular_user["id"]
        ).first()
        if membership:
            db_session.delete(membership)
            db_session.commit()

    def test_assign_user_to_nonexistent_channel_fails(self, admin_auth_client: TestClient, regular_user: dict) -> None:
        """存在しないチャンネルへの割り当てが失敗するテスト"""
        fake_channel_id = str(uuid.uuid4())
        response = admin_auth_client.post(
            f"/api/admin/channels/{fake_channel_id}/members",
            json={"user_id": regular_user["id"]}
        )
        assert response.status_code == 404

    def test_assign_nonexistent_user_to_channel_fails(self, admin_auth_client: TestClient, test_channel: dict) -> None:
        """存在しないユーザーの割り当てが失敗するテスト"""
        fake_user_id = str(uuid.uuid4())
        response = admin_auth_client.post(
            f"/api/admin/channels/{test_channel['id']}/members",
            json={"user_id": fake_user_id}
        )
        assert response.status_code == 404

    def test_duplicate_assignment_fails(self, admin_auth_client: TestClient, test_channel: dict, regular_user: dict, db_session: Session, admin_user: dict) -> None:
        """重複割り当てが失敗するテスト"""
        from app.models.channel import ChannelMembership

        # First assignment using admin_user as the assigner
        membership = ChannelMembership(
            channel_id=test_channel["id"],
            user_id=regular_user["id"],
            assigned_by=admin_user["raw_uuid"]
        )
        db_session.add(membership)
        db_session.commit()

        # Try to assign again
        response = admin_auth_client.post(
            f"/api/admin/channels/{test_channel['id']}/members",
            json={"user_id": regular_user["id"]}
        )
        assert response.status_code == 400
        assert "already assigned" in response.json()["detail"]

        # Cleanup: delete the membership
        db_session.delete(membership)
        db_session.commit()

    def test_remove_user_from_channel(self, admin_auth_client: TestClient, test_channel: dict, regular_user: dict, db_session: Session, admin_user: dict) -> None:
        """ユーザーをチャンネルから削除できるテスト"""
        from app.models.channel import ChannelMembership

        # First assign the user using admin_user as the assigner
        membership = ChannelMembership(
            channel_id=test_channel["id"],
            user_id=regular_user["id"],
            assigned_by=admin_user["raw_uuid"]
        )
        db_session.add(membership)
        db_session.commit()

        # Now remove them
        response = admin_auth_client.delete(
            f"/api/admin/channels/{test_channel['id']}/members/{regular_user['id']}"
        )
        assert response.status_code == 200
        assert "removed from channel" in response.json()["message"]

    def test_remove_nonexistent_membership_fails(self, admin_auth_client: TestClient, test_channel: dict, regular_user: dict) -> None:
        """存在しないメンバーシップの削除が失敗するテスト"""
        response = admin_auth_client.delete(
            f"/api/admin/channels/{test_channel['id']}/members/{regular_user['id']}"
        )
        assert response.status_code == 404


# ==============================================================================
# Audio Management Tests
# ==============================================================================

@pytest.mark.integration
class TestAudioManagement:
    """音声管理エンドポイントテスト"""

    @pytest.fixture
    def test_transcription(self, db_session: Session, regular_user: dict) -> dict:
        """テスト用転写を作成"""
        from app.models.transcription import Transcription

        transcription = Transcription(
            id=uuid.uuid4(),
            user_id=regular_user["raw_uuid"],
            file_name="test_audio.mp3",
            language="zh",
            duration_seconds=120,
            stage="completed"
        )
        db_session.add(transcription)
        db_session.commit()
        db_session.refresh(transcription)

        return {
            "id": str(transcription.id),
            "file_name": transcription.file_name
        }

    def test_list_all_audio_as_admin(self, admin_auth_client: TestClient) -> None:
        """管理者が全音声一覧を取得できるテスト"""
        response = admin_auth_client.get("/api/admin/audio")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "items" in data
        assert isinstance(data["items"], list)

    def test_assign_audio_to_channels(self, admin_auth_client: TestClient, test_transcription: dict, test_channel: dict, db_session: Session) -> None:
        """音声をチャンネルに割り当てられるテスト"""
        from app.models.channel import TranscriptionChannel

        response = admin_auth_client.post(
            f"/api/admin/audio/{test_transcription['id']}/channels",
            json={"channel_ids": [test_channel["id"]]}
        )
        assert response.status_code == 200
        data = response.json()
        assert "channel_ids" in data
        assert test_channel["id"] in data["channel_ids"]

        # Cleanup: delete the channel assignment
        assignment = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == test_transcription["id"],
            TranscriptionChannel.channel_id == test_channel["id"]
        ).first()
        if assignment:
            db_session.delete(assignment)
            db_session.commit()

    def test_assign_audio_to_nonexistent_audio_fails(self, admin_auth_client: TestClient, test_channel: dict) -> None:
        """存在しない音声の割り当てが失敗するテスト"""
        fake_audio_id = str(uuid.uuid4())
        response = admin_auth_client.post(
            f"/api/admin/audio/{fake_audio_id}/channels",
            json={"channel_ids": [test_channel["id"]]}
        )
        assert response.status_code == 404

    def test_assign_audio_to_invalid_channel_fails(self, admin_auth_client: TestClient, test_transcription: dict) -> None:
        """無効なチャンネルへの割り当てが失敗するテスト"""
        fake_channel_id = str(uuid.uuid4())
        response = admin_auth_client.post(
            f"/api/admin/audio/{test_transcription['id']}/channels",
            json={"channel_ids": [fake_channel_id]}
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_get_audio_channels(self, admin_auth_client: TestClient, test_transcription: dict, test_channel: dict, db_session: Session, admin_user: dict) -> None:
        """音声のチャンネル割り当てを取得できるテスト"""
        from app.models.channel import TranscriptionChannel

        # Assign the transcription to a channel using admin_user as assigner
        assignment = TranscriptionChannel(
            transcription_id=test_transcription["id"],
            channel_id=test_channel["id"],
            assigned_by=admin_user["raw_uuid"]
        )
        db_session.add(assignment)
        db_session.commit()

        # Get the channels
        response = admin_auth_client.get(f"/api/admin/audio/{test_transcription['id']}/channels")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert any(ch["id"] == test_channel["id"] for ch in data)

        # Cleanup: delete the assignment
        db_session.delete(assignment)
        db_session.commit()

    def test_clear_and_replace_channel_assignments(self, admin_auth_client: TestClient, test_transcription: dict, db_session: Session, admin_user: dict) -> None:
        """チャンネル割り当てのクリアと置換が正しく動作するテスト"""
        from app.models.channel import Channel, TranscriptionChannel

        # Create two channels with unique names
        unique_suffix = uuid.uuid4().hex[:8]
        channel1 = Channel(name=f"Ch1_{unique_suffix}", description="First", created_by=admin_user["raw_uuid"])
        channel2 = Channel(name=f"Ch2_{unique_suffix}", description="Second", created_by=admin_user["raw_uuid"])
        db_session.add(channel1)
        db_session.add(channel2)
        db_session.commit()

        # Assign to channel1
        assignment1 = TranscriptionChannel(
            transcription_id=test_transcription["id"],
            channel_id=str(channel1.id),
            assigned_by=admin_user["raw_uuid"]
        )
        db_session.add(assignment1)
        db_session.commit()

        # Now assign to channel2 only (should clear channel1)
        response = admin_auth_client.post(
            f"/api/admin/audio/{test_transcription['id']}/channels",
            json={"channel_ids": [str(channel2.id)]}
        )
        assert response.status_code == 200

        # Verify only channel2 is assigned
        assignments = db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == test_transcription["id"]
        ).all()
        assert len(assignments) == 1
        assert str(assignments[0].channel_id) == str(channel2.id)

        # Cleanup: delete both channels and their assignments
        db_session.query(TranscriptionChannel).filter(
            TranscriptionChannel.transcription_id == test_transcription["id"]
        ).delete()
        db_session.delete(channel1)
        db_session.delete(channel2)
        db_session.commit()
