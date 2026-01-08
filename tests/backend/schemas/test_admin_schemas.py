"""
Admin Schema Validation Tests

Tests Pydantic schemas for admin-related request/response validation.
"""

import pytest
from pydantic import ValidationError
from uuid import UUID
from app.schemas.admin import (
    UserResponse,
    UserActivateRequest,
    UserAdminToggleRequest,
    ChannelCreate,
    ChannelUpdate,
    ChannelResponse,
    ChannelDetailResponse,
    ChannelMemberResponse,
    UserWithChannelsResponse,
    ChannelAssignmentRequest,
    TranscriptionChannelAssignmentRequest,
    TranscriptionChannelsResponse,
    AdminTranscriptionResponse,
    AdminTranscriptionListResponse,
)


class TestUserSchemas:
    """Test user-related admin schemas"""

    def test_user_response_valid(self):
        """Valid UserResponse"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "is_active": True,
            "is_admin": False,
            "created_at": "2024-01-01T00:00:00Z"
        }
        response = UserResponse(**data)
        assert response.email == "user@example.com"
        assert response.is_active is True
        assert isinstance(response.id, UUID)

    def test_user_response_invalid_email(self):
        """Invalid UserResponse with bad email"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "not-an-email",
            "is_active": True,
            "is_admin": False,
            "created_at": "2024-01-01T00:00:00Z"
        }
        with pytest.raises(ValidationError):
            UserResponse(**data)

    def test_user_activate_request_valid(self):
        """Valid UserActivateRequest"""
        data = {"is_active": True}
        request = UserActivateRequest(**data)
        assert request.is_active is True

    def test_user_admin_toggle_request_valid(self):
        """Valid UserAdminToggleRequest"""
        data = {"is_admin": True}
        request = UserAdminToggleRequest(**data)
        assert request.is_admin is True


class TestChannelSchemas:
    """Test channel-related admin schemas"""

    def test_channel_create_valid(self):
        """Valid ChannelCreate"""
        data = {
            "name": "New Channel",
            "description": "A new channel"
        }
        channel = ChannelCreate(**data)
        assert channel.name == "New Channel"
        assert channel.description == "A new channel"

    def test_channel_create_name_only(self):
        """Valid ChannelCreate with name only"""
        data = {"name": "New Channel"}
        channel = ChannelCreate(**data)
        assert channel.name == "New Channel"
        assert channel.description is None

    def test_channel_update_valid(self):
        """Valid ChannelUpdate"""
        data = {
            "name": "Updated Channel",
            "description": "Updated description"
        }
        channel = ChannelUpdate(**data)
        assert channel.name == "Updated Channel"

    def test_channel_update_all_optional(self):
        """Valid ChannelUpdate with no fields"""
        data = {}
        channel = ChannelUpdate(**data)
        assert channel.name is None
        assert channel.description is None

    def test_channel_response_valid(self):
        """Valid ChannelResponse"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Test Channel",
            "description": "A test channel",
            "created_by": "550e8400-e29b-41d4-a716-446655440001",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "member_count": 5
        }
        response = ChannelResponse(**data)
        assert response.name == "Test Channel"
        assert response.member_count == 5

    def test_channel_detail_response_valid(self):
        """Valid ChannelDetailResponse with members"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "name": "Test Channel",
            "description": "A test channel",
            "created_by": "550e8400-e29b-41d4-a716-446655440001",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "member_count": 2,
            "members": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440002",
                    "email": "user1@example.com",
                    "is_active": True,
                    "is_admin": False,
                    "created_at": "2024-01-01T00:00:00Z"
                },
                {
                    "id": "650e8400-e29b-41d4-a716-446655440003",
                    "email": "user2@example.com",
                    "is_active": True,
                    "is_admin": False,
                    "created_at": "2024-01-01T00:00:00Z"
                }
            ]
        }
        response = ChannelDetailResponse(**data)
        assert len(response.members) == 2
        assert response.members[0].email == "user1@example.com"

    def test_channel_member_response_valid(self):
        """Valid ChannelMemberResponse"""
        data = {
            "channel_id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "550e8400-e29b-41d4-a716-446655440001",
            "assigned_at": "2024-01-01T00:00:00Z",
            "assigned_by": "550e8400-e29b-41d4-a716-446655440002"
        }
        response = ChannelMemberResponse(**data)
        assert isinstance(response.channel_id, UUID)
        assert response.assigned_by is not None

    def test_user_with_channels_response_valid(self):
        """Valid UserWithChannelsResponse"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "email": "user@example.com",
            "is_active": True,
            "is_admin": False,
            "created_at": "2024-01-01T00:00:00Z",
            "channels": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "name": "Channel 1",
                    "description": "First channel",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                }
            ]
        }
        response = UserWithChannelsResponse(**data)
        assert len(response.channels) == 1


class TestChannelAssignmentSchemas:
    """Test channel assignment schemas"""

    def test_channel_assignment_request_valid(self):
        """Valid ChannelAssignmentRequest"""
        data = {
            "user_id": "550e8400-e29b-41d4-a716-446655440000"
        }
        request = ChannelAssignmentRequest(**data)
        assert isinstance(request.user_id, UUID)

    def test_channel_assignment_request_invalid_uuid(self):
        """Invalid ChannelAssignmentRequest with bad UUID"""
        data = {"user_id": "not-a-uuid"}
        with pytest.raises(ValidationError):
            ChannelAssignmentRequest(**data)

    def test_transcription_channel_assignment_request_valid(self):
        """Valid TranscriptionChannelAssignmentRequest"""
        data = {
            "channel_ids": [
                "550e8400-e29b-41d4-a716-446655440000",
                "650e8400-e29b-41d4-a716-446655440001"
            ]
        }
        request = TranscriptionChannelAssignmentRequest(**data)
        assert len(request.channel_ids) == 2

    def test_transcription_channel_assignment_request_empty(self):
        """Valid TranscriptionChannelAssignmentRequest with empty list"""
        data = {"channel_ids": []}
        request = TranscriptionChannelAssignmentRequest(**data)
        assert request.channel_ids == []

    def test_transcription_channel_assignment_request_invalid_uuid(self):
        """Invalid TranscriptionChannelAssignmentRequest with bad UUID"""
        data = {"channel_ids": ["not-a-uuid"]}
        with pytest.raises(ValidationError):
            TranscriptionChannelAssignmentRequest(**data)

    def test_transcription_channels_response_valid(self):
        """Valid TranscriptionChannelsResponse"""
        data = {
            "transcription_id": "550e8400-e29b-41d4-a716-446655440000",
            "channels": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440001",
                    "name": "Channel 1",
                    "description": "First channel",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:00:00Z"
                }
            ]
        }
        response = TranscriptionChannelsResponse(**data)
        assert len(response.channels) == 1


class TestAdminTranscriptionSchemas:
    """Test admin transcription schemas"""

    def test_admin_transcription_response_valid(self):
        """Valid AdminTranscriptionResponse"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "user_id": "550e8400-e29b-41d4-a716-446655440001",
            "file_name": "test.mp3",
            "language": "en",
            "duration_seconds": 120.5,
            "stage": "completed",
            "error_message": None,
            "pptx_status": "not-started",
            "created_at": "2024-01-01T00:00:00Z",
            "completed_at": "2024-01-01T00:05:00Z",
            "channels": []
        }
        response = AdminTranscriptionResponse(**data)
        assert response.file_name == "test.mp3"
        assert response.stage == "completed"

    def test_admin_transcription_list_response_valid(self):
        """Valid AdminTranscriptionListResponse"""
        data = {
            "total": 5,
            "items": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "user_id": "550e8400-e29b-41d4-a716-446655440001",
                    "file_name": "test.mp3",
                    "language": "en",
                    "duration_seconds": 120.5,
                    "stage": "completed",
                    "error_message": None,
                    "pptx_status": "ready",
                    "created_at": "2024-01-01T00:00:00Z",
                    "completed_at": "2024-01-01T00:05:00Z",
                    "channels": []
                }
            ]
        }
        response = AdminTranscriptionListResponse(**data)
        assert response.total == 5
        assert len(response.items) == 1


class TestSchemaEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_unicode_in_channel_name(self):
        """Test channel names with unicode characters"""
        data = {
            "name": "チャンネル名",
            "description": "日本語の説明"
        }
        channel = ChannelCreate(**data)
        assert channel.name == "チャンネル名"

    def test_email_validation_edge_cases(self):
        """Test email validation with edge cases"""
        valid_emails = [
            "user@example.com",
            "user.name@example.com",
            "user+tag@example.co.uk",
            "123@example.com"
        ]

        for email in valid_emails:
            data = {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": email,
                "is_active": True,
                "is_admin": False,
                "created_at": "2024-01-01T00:00:00Z"
            }
            response = UserResponse(**data)
            assert response.email == email

    def test_empty_channel_description(self):
        """Test channel with empty description"""
        data = {
            "name": "Test Channel",
            "description": ""
        }
        channel = ChannelCreate(**data)
        assert channel.description == ""

    def test_long_channel_name(self):
        """Test channel with very long name"""
        long_name = "a" * 250
        data = {"name": long_name}
        channel = ChannelCreate(**data)
        assert len(channel.name) == 250

    def test_multiple_channel_ids(self):
        """Test assignment with multiple channel IDs"""
        data = {
            "channel_ids": [
                "550e8400-e29b-41d4-a716-446655440000",
                "650e8400-e29b-41d4-a716-446655440001",
                "750e8400-e29b-41d4-a716-446655440002",
                "850e8400-e29b-41d4-a716-446655440003",
                "950e8400-e29b-41d4-a716-446655440004"
            ]
        }
        request = TranscriptionChannelAssignmentRequest(**data)
        assert len(request.channel_ids) == 5
