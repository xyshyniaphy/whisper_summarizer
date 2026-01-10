"""
Unit tests for auth_bypass module

Tests the localhost authentication bypass system used for
automated testing and remote debugging.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from fastapi import Request

from app.core.auth_bypass import (
    is_localhost_request,
    get_test_user,
    load_session,
    create_default_session,
    update_session_test_user,
    add_test_transcription,
    log_bypassed_request,
    LOCALHOST_IPS,
    SESSION_FILE
)


class TestLocalhostDetection:
    """Test localhost request detection"""

    def create_mock_request(self, client_host=None, headers=None):
        """Helper to create mock request"""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = client_host
        request.headers = headers or {}
        request.url = Mock()
        request.url.path = "/api/test"
        request.method = "GET"
        return request

    def test_direct_localhost_ipv4(self):
        """Test direct IPv4 localhost connection"""
        request = self.create_mock_request(client_host="127.0.0.1")
        assert is_localhost_request(request) is True

    def test_direct_localhost_ipv6(self):
        """Test direct IPv6 localhost connection"""
        request = self.create_mock_request(client_host="::1")
        assert is_localhost_request(request) is True

    def test_x_forwarded_for_localhost(self):
        """Test X-Forwarded-For with localhost"""
        request = self.create_mock_request(
            client_host="192.168.1.100",
            headers={"x-forwarded-for": "127.0.0.1"}
        )
        assert is_localhost_request(request) is True

    def test_x_forwarded_for_multiple_ips(self):
        """Test X-Forwarded-For with multiple IPs (should check first)"""
        request = self.create_mock_request(
            client_host="192.168.1.100",
            headers={"x-forwarded-for": "127.0.0.1, 10.0.0.1, 172.16.0.1"}
        )
        assert is_localhost_request(request) is True

    def test_x_real_ip_localhost(self):
        """Test X-Real-IP with localhost"""
        request = self.create_mock_request(
            client_host="192.168.1.100",
            headers={"x-real-ip": "127.0.0.1"}
        )
        assert is_localhost_request(request) is True

    def test_cf_connecting_ip_localhost(self):
        """Test CF-Connecting-IP with localhost"""
        request = self.create_mock_request(
            client_host="192.168.1.100",
            headers={"cf-connecting-ip": "127.0.0.1"}
        )
        assert is_localhost_request(request) is True

    def test_remote_ip_rejected(self):
        """Test that remote IPs are not bypassed"""
        request = self.create_mock_request(client_host="192.168.1.100")
        assert is_localhost_request(request) is False

    def test_external_ip_rejected(self):
        """Test that external requests are not bypassed"""
        request = self.create_mock_request(
            client_host="203.0.113.1",
            headers={"x-forwarded-for": "203.0.113.1"}
        )
        assert is_localhost_request(request) is False

    def test_docker_network_rejected(self):
        """Test that Docker network IPs are not bypassed"""
        # Docker bridge networks typically use 172.x.x.x
        request = self.create_mock_request(client_host="172.17.0.2")
        assert is_localhost_request(request) is False

    def test_no_client_host(self):
        """Test request without client.host attribute"""
        request = self.create_mock_request()
        delattr(request, 'client')
        assert is_localhost_request(request) is False


class TestSessionManagement:
    """Test session.json management"""

    @pytest.fixture
    def temp_session_file(self, tmp_path):
        """Create temporary session file for testing"""
        session_path = tmp_path / "session.json"
        with patch('app.core.auth_bypass.SESSION_FILE', session_path):
            yield session_path

    def test_create_default_session(self, temp_session_file):
        """Test default session creation"""
        with patch('app.core.auth_bypass.SESSION_FILE', temp_session_file):
            session = create_default_session()

            assert session["version"] == "1.0"
            assert "created_at" in session
            assert "test_user" in session
            assert session["test_user"]["email"] == "test@example.com"
            assert session["test_user"]["is_admin"] is True
            assert session["test_channels"] == []
            assert session["test_transcriptions"] == []

            # Verify file was created
            assert temp_session_file.exists()

    def test_load_existing_session(self, temp_session_file):
        """Test loading existing session"""
        test_session = {
            "version": "1.0",
            "created_at": "2026-01-10T00:00:00Z",
            "updated_at": "2026-01-10T00:00:00Z",
            "test_user": {
                "id": "custom-user-id",
                "email": "custom@example.com",
                "is_admin": False,
                "is_active": True
            },
            "test_channels": [],
            "test_transcriptions": []
        }

        temp_session_file.write_text(json.dumps(test_session))

        with patch('app.core.auth_bypass.SESSION_FILE', temp_session_file):
            session = load_session()
            assert session["test_user"]["email"] == "custom@example.com"
            assert session["test_user"]["is_admin"] is False

    def test_load_invalid_json_creates_default(self, temp_session_file):
        """Test that invalid JSON creates default session"""
        temp_session_file.write_text("invalid json {")

        with patch('app.core.auth_bypass.SESSION_FILE', temp_session_file):
            session = load_session()
            assert session["test_user"]["email"] == "test@example.com"

    def test_update_session_test_user(self, temp_session_file):
        """Test updating test user in session"""
        # Create initial session
        with patch('app.core.auth_bypass.SESSION_FILE', temp_session_file):
            create_default_session()

            # Update user
            result = update_session_test_user(
                user_id="new-user-id",
                email="newuser@example.com",
                is_admin=False
            )

            assert result is True

            # Verify update
            session = load_session()
            assert session["test_user"]["email"] == "newuser@example.com"
            assert session["test_user"]["is_admin"] is False


class TestGetTestUser:
    """Test get_test_user function"""

    def test_get_test_user_structure(self):
        """Test that get_test_user returns correct structure"""
        with patch('app.core.auth_bypass.load_session') as mock_load:
            mock_load.return_value = {
                "test_user": {
                    "id": "fc47855d-6973-4931-b6fd-bd28515bec0d",
                    "email": "test@example.com",
                    "is_admin": True,
                    "is_active": True
                }
            }

            user = get_test_user()

            # Check structure matches get_current_user() return value
            assert "id" in user
            assert "email" in user
            assert "email_confirmed_at" in user
            assert "user_metadata" in user
            assert "app_metadata" in user

            # Check values
            assert user["email"] == "test@example.com"
            assert user["user_metadata"]["role"] == "admin"
            assert user["user_metadata"]["auth_bypass"] is True

    def test_get_test_user_with_invalid_uuid(self):
        """Test that invalid UUID falls back to default"""
        with patch('app.core.auth_bypass.load_session') as mock_load:
            mock_load.return_value = {
                "test_user": {
                    "id": "invalid-uuid",
                    "email": "test@example.com",
                    "is_admin": True,
                    "is_active": True
                }
            }

            user = get_test_user()
            # Should use default UUID when invalid
            assert str(user["id"]) == "fc47855d-6973-4931-b6fd-bd28515bec0d"


class TestAddTestTranscription:
    """Test add_test_transcription function"""

    @pytest.fixture
    def temp_session_file(self, tmp_path):
        """Create temporary session file for testing"""
        session_path = tmp_path / "session.json"
        with patch('app.core.auth_bypass.SESSION_FILE', session_path):
            yield session_path

    def test_add_transcription(self, temp_session_file):
        """Test adding a transcription to session"""
        with patch('app.core.auth_bypass.SESSION_FILE', temp_session_file):
            create_default_session()

            result = add_test_transcription(
                transcription_id="trans-123",
                file_name="test.m4a",
                status="completed"
            )

            assert result is True

            session = load_session()
            assert len(session["test_transcriptions"]) == 1
            assert session["test_transcriptions"][0]["id"] == "trans-123"
            assert session["test_transcriptions"][0]["file_name"] == "test.m4a"

    def test_add_duplicate_transcription(self, temp_session_file):
        """Test that duplicate transcriptions are handled"""
        with patch('app.core.auth_bypass.SESSION_FILE', temp_session_file):
            create_default_session()

            # Add first time
            add_test_transcription("trans-123", "test.m4a")

            # Add again (should not duplicate)
            add_test_transcription("trans-123", "test.m4a")

            session = load_session()
            assert len(session["test_transcriptions"]) == 1


class TestLogBypassedRequest:
    """Test log_bypassed_request function"""

    def test_log_bypassed_request(self, caplog):
        """Test that bypassed requests are logged correctly"""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {"user-agent": "test-agent"}
        request.url = Mock()
        request.url.path = "/api/test"
        request.method = "GET"

        user = {
            "id": "test-user-id",
            "email": "test@example.com"
        }

        with caplog.at_level("INFO"):
            log_bypassed_request(request, user)

        # Check log contains expected info
        assert "bypassed authentication" in caplog.text.lower()


class TestIntegration:
    """Integration tests for auth bypass system"""

    def test_full_bypass_workflow(self, tmp_path):
        """Test complete workflow: detect bypass -> get user -> log"""
        # Create mock request
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "127.0.0.1"
        request.headers = {}
        request.url = Mock()
        request.url.path = "/api/transcriptions"
        request.method = "GET"

        with patch('app.core.auth_bypass.SESSION_FILE', tmp_path / "session.json"):
            # Step 1: Detect localhost
            assert is_localhost_request(request) is True

            # Step 2: Get test user
            user = get_test_user()
            assert user["email"] == "test@example.com"

            # Step 3: Log bypass
            with patch('app.core.auth_bypass.logger') as mock_logger:
                log_bypassed_request(request, user)
                assert mock_logger.info.called

    def test_external_request_workflow(self):
        """Test that external requests don't bypass"""
        request = Mock(spec=Request)
        request.client = Mock()
        request.client.host = "203.0.113.1"
        request.headers = {}
        request.url = Mock()
        request.url.path = "/api/transcriptions"
        request.method = "GET"

        # Should not bypass
        assert is_localhost_request(request) is False
