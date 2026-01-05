"""
Tests for Admin API endpoints.

Tests user management, channel management, and audio management endpoints.
All admin endpoints require admin privileges.
"""

import pytest
from uuid import uuid4
from fastapi.testclient import TestClient

from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User
from app.models.channel import Channel, ChannelMembership


# ============================================================================
# Fixtures for Admin Tests
# ============================================================================

@pytest.fixture
def admin_user(db_session):
    """Create an admin user for testing."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"admin-{user_id.hex[:8]}@example.com",
        is_active=True,
        is_admin=True
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def regular_user(db_session):
    """Create a regular user for testing."""
    user_id = uuid4()
    user = User(
        id=user_id,
        email=f"user-{user_id.hex[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def admin_client(test_client, admin_user):
    """Create a test client with admin authentication."""
    from app.core.supabase import get_current_user
    from app.api.deps import get_current_db_user, require_admin
    from app.main import app

    # Mock authentication chain to return admin user
    async def mock_get_current_user():
        return {
            "id": str(admin_user.id),
            "email": admin_user.email,
            "email_confirmed_at": "2025-01-01T00:00:00Z"
        }

    async def mock_get_current_db_user():
        return admin_user

    async def mock_require_admin():
        return admin_user

    # Override all auth dependencies
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_db_user] = mock_get_current_db_user
    app.dependency_overrides[require_admin] = mock_require_admin

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


# ============================================================================
# User Management Endpoints (GET /api/admin/users, etc.)
# ============================================================================

def test_list_users_as_admin(admin_client, db_session):
    """Test listing all users as admin."""
    # Create multiple users
    for i in range(5):
        user = User(
            id=uuid4(),
            email=f"user{i}@example.com",
            is_active=(i % 2 == 0),  # Alternate active/inactive
            is_admin=False
        )
        db_session.add(user)
    db_session.commit()

    response = admin_client.get("/api/admin/users")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 5  # At least our test users


def test_activate_user(admin_client, db_session, regular_user):
    """Test activating a user."""
    # Start with inactive user
    regular_user.is_active = False
    db_session.commit()

    response = admin_client.put(f"/api/admin/users/{regular_user.id}/activate")
    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is True

    # Verify in database
    db_session.refresh(regular_user)
    assert regular_user.is_active is True


def test_activate_already_active_user(admin_client, regular_user):
    """Test activating an already active user."""
    # User is already active
    response = admin_client.put(f"/api/admin/users/{regular_user.id}/activate")
    assert response.status_code == 200  # Should still succeed


def test_toggle_admin_status(admin_client, db_session, regular_user):
    """Test toggling user admin status."""
    assert regular_user.is_admin is False

    # Grant admin
    response = admin_client.put(
        f"/api/admin/users/{regular_user.id}/admin",
        json={"is_admin": True}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is True

    # Verify in database
    db_session.refresh(regular_user)
    assert regular_user.is_admin is True

    # Revoke admin
    response = admin_client.put(
        f"/api/admin/users/{regular_user.id}/admin",
        json={"is_admin": False}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["is_admin"] is False


def test_delete_user(admin_client, db_session, regular_user):
    """Test soft deleting a user."""
    user_id = regular_user.id
    assert regular_user.deleted_at is None

    response = admin_client.delete(f"/api/admin/users/{user_id}")
    assert response.status_code == 200

    # Verify soft delete
    db_session.refresh(regular_user)
    assert regular_user.deleted_at is not None


def test_delete_user_not_found(admin_client):
    """Test deleting a non-existent user."""
    fake_id = uuid4()
    response = admin_client.delete(f"/api/admin/users/{fake_id}")
    assert response.status_code == 404


# ============================================================================
# Channel Management Endpoints (GET/POST/PUT/DELETE /api/admin/channels)
# ============================================================================

def test_list_channels(admin_client, db_session, admin_user):
    """Test listing all channels."""
    # Create test channels
    for i in range(3):
        channel = Channel(
            id=uuid4(),
            name=f"Channel {i}",
            description=f"Test channel {i}",
            created_by=admin_user.id
        )
        db_session.add(channel)
    db_session.commit()

    response = admin_client.get("/api/admin/channels")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3


def test_create_channel(admin_client):
    """Test creating a new channel."""
    channel_data = {
        "name": "Test Channel",
        "description": "Test channel description"
    }

    response = admin_client.post("/api/admin/channels", json=channel_data)
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Channel"
    assert data["description"] == "Test channel description"
    assert "id" in data


def test_create_channel_duplicate_name(admin_client, db_session, admin_user):
    """Test creating channel with duplicate name."""
    # Create existing channel
    channel = Channel(
        id=uuid4(),
        name="Duplicate Name",
        created_by=admin_user.id
    )
    db_session.add(channel)
    db_session.commit()

    channel_data = {
        "name": "Duplicate Name",
        "description": "Different description"
    }

    response = admin_client.post("/api/admin/channels", json=channel_data)
    assert response.status_code == 400  # Bad request for duplicate name


def test_update_channel(admin_client, db_session, admin_user):
    """Test updating a channel."""
    channel = Channel(
        id=uuid4(),
        name="Original Name",
        description="Original description",
        created_by=admin_user.id
    )
    db_session.add(channel)
    db_session.commit()

    update_data = {
        "name": "Updated Name",
        "description": "Updated description"
    }

    response = admin_client.put(f"/api/admin/channels/{channel.id}", json=update_data)
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated Name"
    assert data["description"] == "Updated description"

    # Verify in database
    db_session.refresh(channel)
    assert channel.name == "Updated Name"


def test_update_channel_not_found(admin_client):
    """Test updating a non-existent channel."""
    fake_id = uuid4()
    update_data = {"name": "New Name"}

    response = admin_client.put(f"/api/admin/channels/{fake_id}", json=update_data)
    assert response.status_code == 404


def test_delete_channel(admin_client, db_session, admin_user):
    """Test deleting a channel."""
    channel = Channel(
        id=uuid4(),
        name="To Delete",
        created_by=admin_user.id
    )
    db_session.add(channel)
    db_session.commit()

    channel_id = channel.id
    response = admin_client.delete(f"/api/admin/channels/{channel_id}")
    assert response.status_code == 200

    # Verify deletion (CASCADE should delete memberships)
    remaining = db_session.query(Channel).filter(Channel.id == channel_id).first()
    assert remaining is None


def test_delete_channel_not_found(admin_client):
    """Test deleting a non-existent channel."""
    fake_id = uuid4()
    response = admin_client.delete(f"/api/admin/channels/{fake_id}")
    assert response.status_code == 404


# ============================================================================
# Channel Members Endpoints
# ============================================================================

def test_add_channel_member(admin_client, db_session, admin_user, regular_user):
    """Test adding a user to a channel."""
    channel = Channel(
        id=uuid4(),
        name="Test Channel",
        created_by=admin_user.id
    )
    db_session.add(channel)
    db_session.commit()

    response = admin_client.post(
        f"/api/admin/channels/{channel.id}/members",
        json={"user_id": str(regular_user.id)}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user_id"] == str(regular_user.id)
    assert data["channel_id"] == str(channel.id)

    # Verify membership was created
    membership = db_session.query(ChannelMembership).filter(
        ChannelMembership.channel_id == channel.id,
        ChannelMembership.user_id == regular_user.id
    ).first()
    assert membership is not None


def test_add_channel_member_already_exists(admin_client, db_session, admin_user, regular_user):
    """Test adding a user who is already a channel member."""
    channel = Channel(
        id=uuid4(),
        name="Test Channel",
        created_by=admin_user.id
    )
    db_session.add(channel)

    # Create existing membership
    membership = ChannelMembership(
        channel_id=channel.id,
        user_id=regular_user.id
    )
    db_session.add_all([channel, membership])
    db_session.commit()

    response = admin_client.post(
        f"/api/admin/channels/{channel.id}/members",
        json={"user_id": str(regular_user.id)}
    )
    # Should either return 200 (already exists) or 400 (conflict)
    assert response.status_code in [200, 400]


def test_remove_channel_member(admin_client, db_session, admin_user, regular_user):
    """Test removing a user from a channel."""
    channel = Channel(
        id=uuid4(),
        name="Test Channel",
        created_by=admin_user.id
    )
    db_session.add(channel)

    membership = ChannelMembership(
        channel_id=channel.id,
        user_id=regular_user.id
    )
    db_session.add_all([channel, membership])
    db_session.commit()

    response = admin_client.delete(
        f"/api/admin/channels/{channel.id}/members/{regular_user.id}"
    )
    assert response.status_code == 200

    # Verify membership was deleted
    membership = db_session.query(ChannelMembership).filter(
        ChannelMembership.channel_id == channel.id,
        ChannelMembership.user_id == regular_user.id
    ).first()
    assert membership is None


def test_get_channel_details(admin_client, db_session, admin_user, regular_user):
    """Test getting detailed channel information."""
    channel = Channel(
        id=uuid4(),
        name="Test Channel",
        description="Test description",
        created_by=admin_user.id
    )
    db_session.add(channel)

    membership = ChannelMembership(
        channel_id=channel.id,
        user_id=regular_user.id
    )
    db_session.add_all([channel, membership])
    db_session.commit()

    response = admin_client.get(f"/api/admin/channels/{channel.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(channel.id)
    assert data["name"] == "Test Channel"
    assert "members" in data
    assert len(data["members"]) >= 1


# ============================================================================
# Audio Management Endpoints (GET /api/admin/audio)
# ============================================================================

def test_list_all_audio_as_admin(admin_client, db_session, admin_user):
    """Test listing all audio transcriptions as admin."""
    # Create users with unique emails to avoid conflicts
    user1 = User(id=uuid4(), email=f"user1-{uuid4().hex[:8]}@example.com", is_active=True)
    user2 = User(id=uuid4(), email=f"user2-{uuid4().hex[:8]}@example.com", is_active=True)
    db_session.add_all([user1, user2])
    db_session.flush()  # Flush to ensure users are inserted before transcriptions

    # Create transcriptions for different users
    for i, user in enumerate([user1, user2]):
        trans = Transcription(
            id=uuid4(),
            user_id=user.id,
            file_name=f"audio_{i}.m4a",
            file_path=f"/tmp/audio_{i}.m4a",
            status=TranscriptionStatus.COMPLETED
        )
        db_session.add(trans)
    db_session.commit()

    response = admin_client.get("/api/admin/audio")
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert len(data["items"]) >= 2


def test_assign_audio_to_channels(admin_client, db_session, admin_user, regular_user):
    """Test assigning audio to channels as admin."""
    # Create transcription
    trans = Transcription(
        id=uuid4(),
        user_id=regular_user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED
    )
    db_session.add(trans)
    db_session.commit()

    # Create channels with unique names - commit separately to avoid batch insert issues
    test_suffix = uuid4().hex[:8]
    channel1 = Channel(id=uuid4(), name=f"Assign-{test_suffix}-Channel-1", created_by=admin_user.id)
    db_session.add(channel1)
    db_session.commit()

    channel2 = Channel(id=uuid4(), name=f"Assign-{test_suffix}-Channel-2", created_by=admin_user.id)
    db_session.add(channel2)
    db_session.commit()

    response = admin_client.post(
        f"/api/admin/audio/{trans.id}/channels",
        json={"channel_ids": [str(channel1.id), str(channel2.id)]}
    )
    assert response.status_code == 200
    data = response.json()
    assert "channel_ids" in data
    assert len(data["channel_ids"]) == 2


def test_get_audio_channels_as_admin(admin_client, db_session, admin_user):
    """Test getting channels for audio as admin."""
    # Create transcription and channel
    trans = Transcription(
        id=uuid4(),
        user_id=admin_user.id,
        file_name="test.m4a",
        file_path="/tmp/test.m4a",
        status=TranscriptionStatus.COMPLETED
    )
    db_session.add(trans)

    test_suffix = uuid4().hex[:8]
    channel = Channel(id=uuid4(), name=f"GetAudio-{test_suffix}-Channel", created_by=admin_user.id)
    db_session.add(channel)

    # Create junction
    from app.models.channel import TranscriptionChannel
    tc = TranscriptionChannel(
        transcription_id=trans.id,
        channel_id=channel.id
    )
    db_session.add_all([trans, channel, tc])
    db_session.commit()

    response = admin_client.get(f"/api/admin/audio/{trans.id}/channels")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


# ============================================================================
# Authorization Tests (non-admin users should be denied)
# ============================================================================

def test_admin_endpoints_require_admin(test_client, db_session, regular_user):
    """Test that admin endpoints require admin privileges."""
    from app.core.supabase import get_current_user
    from app.api.deps import get_current_db_user, require_admin
    from app.main import app

    # Mock authentication as regular user
    async def mock_get_current_user():
        return {
            "id": str(regular_user.id),
            "email": regular_user.email,
            "email_confirmed_at": "2025-01-01T00:00:00Z"
        }

    async def mock_get_current_db_user():
        return regular_user

    # Override auth dependencies but NOT require_admin
    # This allows the real require_admin to run and check is_admin
    app.dependency_overrides[get_current_user] = mock_get_current_user
    app.dependency_overrides[get_current_db_user] = mock_get_current_db_user

    client = TestClient(app)

    # Try to access admin endpoint
    response = client.get("/api/admin/users")
    assert response.status_code == 403  # Forbidden

    app.dependency_overrides = {}


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

def test_create_channel_missing_name(admin_client):
    """Test creating channel without required name field."""
    response = admin_client.post("/api/admin/channels", json={"description": "No name"})
    assert response.status_code == 422  # Validation error


def test_add_channel_member_non_existent_user(admin_client, db_session, admin_user):
    """Test adding non-existent user to channel."""
    channel = Channel(
        id=uuid4(),
        name="Test Channel",
        created_by=admin_user.id
    )
    db_session.add(channel)
    db_session.commit()

    fake_user_id = uuid4()
    response = admin_client.post(
        f"/api/admin/channels/{channel.id}/members",
        json={"user_id": str(fake_user_id)}
    )
    assert response.status_code == 404  # User not found


def test_add_channel_member_non_existent_channel(admin_client, regular_user):
    """Test adding user to non-existent channel."""
    fake_channel_id = uuid4()
    response = admin_client.post(
        f"/api/admin/channels/{fake_channel_id}/members",
        json={"user_id": str(regular_user.id)}
    )
    assert response.status_code == 404  # Channel not found


def test_update_channel_duplicate_name(admin_client, db_session, admin_user):
    """Test updating channel to use existing channel name."""
    channel1 = Channel(id=uuid4(), name="Channel 1", created_by=admin_user.id)
    channel2 = Channel(id=uuid4(), name="Channel 2", created_by=admin_user.id)
    db_session.add_all([channel1, channel2])
    db_session.commit()

    # Try to rename channel2 to channel1's name
    response = admin_client.put(
        f"/api/admin/channels/{channel2.id}",
        json={"name": "Channel 1"}
    )
    assert response.status_code == 400  # Duplicate name


@pytest.mark.skip(reason="Pagination not implemented in API")
def test_list_users_pagination(admin_client, db_session):
    """Test pagination for user list."""
    # Create many users with unique emails to avoid conflicts
    test_suffix = uuid4().hex[:8]
    for i in range(25):
        user = User(
            id=uuid4(),
            email=f"pagination-{test_suffix}-user{i}@example.com",
            is_active=True,
            is_admin=False
        )
        db_session.add(user)
    db_session.commit()

    # Test first page - should return our test users
    response = admin_client.get("/api/admin/users?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    # Filter to only our test users (those with the unique suffix)
    our_users = [u for u in data if f"pagination-{test_suffix}" in u["email"]]
    assert len(our_users) == 10


@pytest.mark.skip(reason="Pagination not implemented in API")
def test_list_channels_pagination(admin_client, db_session, admin_user):
    """Test pagination for channel list."""
    # Create many channels with unique names to avoid conflicts
    test_suffix = uuid4().hex[:8]
    for i in range(15):
        channel = Channel(
            id=uuid4(),
            name=f"Pagination-{test_suffix}-Channel-{i}",
            created_by=admin_user.id
        )
        db_session.add(channel)
    db_session.commit()

    # Test pagination
    response = admin_client.get("/api/admin/channels?page=1&page_size=10")
    assert response.status_code == 200
    data = response.json()
    # Filter to only our test channels
    our_channels = [c for c in data if f"Pagination-{test_suffix}" in c["name"]]
    assert len(our_channels) == 10
