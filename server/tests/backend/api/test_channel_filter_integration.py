"""
Transcriptions API Channel Filtering Integration Tests

Test for transcriptions.py line 122 - channel filter JOIN operation.
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.user import User
from app.models.transcription import Transcription, TranscriptionStatus
from app.models.channel import Channel, ChannelMembership, TranscriptionChannel


@pytest.fixture
def user_with_channels(db_session: Session) -> dict:
    """Create user with channel memberships."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"test-channels-{str(uid)[:8]}@example.com",
        is_active=True,
        is_admin=False,
        activated_at=datetime.now(timezone.utc)
    )
    db_session.add(user)
    db_session.flush()

    # Create Channel 1
    cid1 = uuid.uuid4()
    channel1 = Channel(
        id=cid1,
        name="Test Channel 1",
        description="First test channel"
    )
    db_session.add(channel1)
    db_session.flush()

    # Create Channel 2
    cid2 = uuid.uuid4()
    channel2 = Channel(
        id=cid2,
        name="Test Channel 2",
        description="Second test channel"
    )
    db_session.add(channel2)
    db_session.flush()

    # Add user to both channels
    membership1 = ChannelMembership(channel_id=cid1, user_id=uid)
    membership2 = ChannelMembership(channel_id=cid2, user_id=uid)
    db_session.add(membership1)
    db_session.add(membership2)
    db_session.commit()

    return {
        "id": str(uid),
        "email": user.email,
        "raw_uuid": uid,
        "channel1_id": str(cid1),
        "channel2_id": str(cid2),
        "channel1_raw": cid1,
        "channel2_raw": cid2
    }


@pytest.fixture
def auth_client_for_channels(user_with_channels: dict, db_session: Session) -> TestClient:
    """Authenticated test client for channel filtering tests."""
    from app.main import app
    from app.core.supabase import get_current_user

    async def override_auth():
        return {
            "id": user_with_channels["id"],
            "email": user_with_channels["email"],
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"is_admin": False, "is_active": True}
        }

    # Override the correct dependency - get_current_user from supabase module
    app.dependency_overrides[get_current_user] = override_auth

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.mark.integration
class TestTranscriptionsChannelFilter:
    """Test transcriptions list with channel filtering."""

    def test_list_transcriptions_with_channel_filter_hits_line_122(
        self,
        auth_client_for_channels: TestClient,
        user_with_channels: dict,
        db_session: Session
    ) -> None:
        """
        List transcriptions filtered by channel_id.
        
        This targets transcriptions.py line 122:
        ```python
        query = query.join(TranscriptionChannel).filter(
            TranscriptionChannel.channel_id == channel_id
        )
        ```
        """
        # Create transcription assigned to channel 1
        tid1 = uuid.uuid4()
        trans1 = Transcription(
            id=tid1,
            user_id=user_with_channels["raw_uuid"],
            file_name="test_channel_1.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans1)
        db_session.flush()

        # Assign to channel 1
        tc1 = TranscriptionChannel(
            transcription_id=tid1, 
            channel_id=user_with_channels["channel1_raw"]
        )
        db_session.add(tc1)
        db_session.flush()

        # Create another transcription assigned to channel 2
        tid2 = uuid.uuid4()
        trans2 = Transcription(
            id=tid2,
            user_id=user_with_channels["raw_uuid"],
            file_name="test_channel_2.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans2)
        db_session.flush()

        # Assign to channel 2
        tc2 = TranscriptionChannel(
            transcription_id=tid2, 
            channel_id=user_with_channels["channel2_raw"]
        )
        db_session.add(tc2)
        db_session.commit()

        try:
            # List transcriptions filtered by channel 1
            # This should hit line 122 (the JOIN operation)
            response = auth_client_for_channels.get(
                f"/api/transcriptions?channel_id={user_with_channels['channel1_id']}"
            )

            assert response.status_code == 200
            data = response.json()

            # Should return at least the transcription from channel 1
            assert data["total"] >= 1
            file_names = [t["file_name"] for t in data["data"]]
            assert "test_channel_1.mp3" in file_names

        finally:
            # Cleanup
            db_session.query(TranscriptionChannel).filter(
                TranscriptionChannel.transcription_id.in_([tid1, tid2])
            ).delete()
            db_session.query(Transcription).filter(
                Transcription.id.in_([tid1, tid2])
            ).delete()
            db_session.query(ChannelMembership).filter(
                ChannelMembership.user_id == user_with_channels["raw_uuid"]
            ).delete()
            db_session.query(Channel).filter(
                Channel.id.in_([user_with_channels["channel1_raw"], user_with_channels["channel2_raw"]])
            ).delete()
            db_session.query(User).filter(User.id == user_with_channels["raw_uuid"]).delete()
            db_session.commit()
