"""
Admin API Missing Coverage Tests

Tests for uncovered error handling paths in admin.py to improve coverage from 92%.
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone
from app.models.user import User


@pytest.fixture
def admin_user_for_tests(db_session: Session) -> dict:
    """Create admin user for tests."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"admin-test-{str(uid)[:8]}@example.com",
        is_active=True,
        is_admin=True,
        activated_at=datetime.now(timezone.utc)
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
def admin_auth_client_for_tests(admin_user_for_tests: dict, db_session: Session) -> TestClient:
    """Admin authenticated test client."""
    from app.main import app
    from app.core.supabase import get_current_active_user
    from app.api.deps import require_admin

    async def override_auth():
        return {
            "id": admin_user_for_tests["id"],
            "email": admin_user_for_tests["email"],
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"is_admin": True, "is_active": True}
        }

    def override_require_admin():
        return db_session.query(User).filter(User.id == admin_user_for_tests["raw_uuid"]).first()

    app.dependency_overrides[get_current_active_user] = override_auth
    app.dependency_overrides[require_admin] = override_require_admin

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.mark.integration
class TestChannelMemberErrorCases:
    """Test channel membership error handling paths."""

    def test_assign_user_to_nonexistent_channel_returns_404(self, admin_auth_client_for_tests: TestClient) -> None:
        """Assigning user to non-existent channel returns 404."""
        fake_channel_id = str(uuid.uuid4())

        # Get a valid user_id (the admin_auth_client_for_tests user)
        response = admin_auth_client_for_tests.get("/api/admin/users")
        users = response.json()
        if users and len(users) > 0:
            user_id = users[0]["id"]

            response = admin_auth_client_for_tests.post(
                f"/api/admin/channels/{fake_channel_id}/members",
                json={"user_id": user_id}
            )
            assert response.status_code == 404

    def test_assign_nonexistent_user_to_channel_returns_404(self, admin_auth_client_for_tests: TestClient, admin_user_for_tests: dict, db_session: Session) -> None:
        """Assigning non-existent user to channel returns 404."""
        from app.models.channel import Channel
        from app.models.user import User

        # Create a test channel using the admin user from fixture
        channel = Channel(
            id=uuid.uuid4(),
            name="Test Channel for Error",
            description="Test channel",
            created_by=admin_user_for_tests["raw_uuid"]
        )
        db_session.add(channel)
        db_session.commit()

        try:
            fake_user_id = str(uuid.uuid4())
            response = admin_auth_client_for_tests.post(
                f"/api/admin/channels/{channel.id}/members",
                json={"user_id": fake_user_id}
            )
            assert response.status_code == 404
        finally:
            db_session.query(Channel).filter(Channel.id == channel.id).delete()
            db_session.commit()

    def test_assign_already_assigned_user_returns_400(self, admin_auth_client_for_tests: TestClient, admin_user_for_tests: dict, db_session: Session) -> None:
        """Assigning already assigned user returns 400 error."""
        from app.models.channel import Channel, ChannelMembership
        from app.models.user import User

        # Create a test user and channel
        test_user_id = uuid.uuid4()
        test_user = User(id=test_user_id, email=f"test-assign-{str(test_user_id)[:8]}@example.com", is_active=True)
        db_session.add(test_user)

        channel_id = uuid.uuid4()
        channel = Channel(
            id=channel_id,
            name="Test Channel for Dup",
            description="Test channel",
            created_by=admin_user_for_tests["raw_uuid"]
        )
        db_session.add(channel)
        db_session.commit()

        # First assignment
        admin_auth_client_for_tests.post(
            f"/api/admin/channels/{channel_id}/members",
            json={"user_id": str(test_user_id)}
        )

        # Second assignment (should fail)
        response = admin_auth_client_for_tests.post(
            f"/api/admin/channels/{channel_id}/members",
            json={"user_id": str(test_user_id)}
        )
        assert response.status_code == 400
        assert "already assigned" in response.json()["detail"].lower()

        # Cleanup
        db_session.query(ChannelMembership).filter(ChannelMembership.channel_id == channel_id).delete()
        db_session.query(Channel).filter(Channel.id == channel_id).delete()
        db_session.query(User).filter(User.id == test_user_id).delete()
        db_session.commit()

    def test_remove_nonexistent_membership_returns_404(self, admin_auth_client_for_tests: TestClient, admin_user_for_tests: dict, db_session: Session) -> None:
        """Removing non-existent channel membership returns 404."""
        from app.models.channel import Channel

        channel_id = uuid.uuid4()
        channel = Channel(
            id=channel_id,
            name="Test Channel Remove",
            description="Test channel",
            created_by=admin_user_for_tests["raw_uuid"]
        )
        db_session.add(channel)
        db_session.commit()

        try:
            fake_user_id = str(uuid.uuid4())
            response = admin_auth_client_for_tests.delete(
                f"/api/admin/channels/{channel_id}/members/{fake_user_id}"
            )
            assert response.status_code == 404
        finally:
            db_session.query(Channel).filter(Channel.id == channel_id).delete()
            db_session.commit()


@pytest.mark.integration
class TestChannelDetailErrorCases:
    """Test channel detail endpoint error handling."""

    def test_get_nonexistent_channel_detail_returns_404(self, admin_auth_client_for_tests: TestClient) -> None:
        """Getting detail for non-existent channel returns 404."""
        fake_channel_id = str(uuid.uuid4())
        response = admin_auth_client_for_tests.get(f"/api/admin/channels/{fake_channel_id}")
        assert response.status_code == 404


@pytest.mark.integration
class TestAudioChannelAssignmentErrors:
    """Test audio channel assignment error handling."""

    def test_assign_audio_to_nonexistent_audio_returns_404(self, admin_auth_client_for_tests: TestClient) -> None:
        """Assigning non-existent audio to channels returns 404."""
        fake_audio_id = str(uuid.uuid4())
        response = admin_auth_client_for_tests.post(
            f"/api/admin/audio/{fake_audio_id}/channels",
            json={"channel_ids": []}
        )
        assert response.status_code == 404

    def test_assign_audio_to_nonexistent_channels_returns_400(self, admin_auth_client_for_tests: TestClient, admin_user_for_tests: dict, db_session: Session) -> None:
        """Assigning audio to non-existent channels returns 400."""
        from app.models.transcription import Transcription

        # Create a test transcription
        trans_id = uuid.uuid4()
        trans = Transcription(
            id=trans_id,
            user_id=admin_user_for_tests["raw_uuid"],
            file_name="test_assign.mp3",
            stage="completed"
        )
        db_session.add(trans)
        db_session.commit()

        try:
            # Use non-existent channel IDs
            fake_channel_ids = [str(uuid.uuid4()), str(uuid.uuid4())]
            response = admin_auth_client_for_tests.post(
                f"/api/admin/audio/{trans_id}/channels",
                json={"channel_ids": fake_channel_ids}
            )
            assert response.status_code == 400
            assert "channels not found" in response.json()["detail"].lower()
        finally:
            db_session.query(Transcription).filter(Transcription.id == trans_id).delete()
            db_session.commit()

    def test_get_channels_for_nonexistent_audio_returns_404(self, admin_auth_client_for_tests: TestClient) -> None:
        """Getting channels for non-existent audio returns 404."""
        fake_audio_id = str(uuid.uuid4())
        response = admin_auth_client_for_tests.get(f"/api/admin/audio/{fake_audio_id}/channels")
        assert response.status_code == 404
