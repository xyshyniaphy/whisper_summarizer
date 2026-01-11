"""
Pytest Configuration for Remote Production Testing

This module provides fixtures and utilities for testing the production
server via SSH + docker exec (localhost auth bypass).
"""

import subprocess
import json
import os
import pytest
from typing import Any, Dict, List, Optional
from dataclasses import dataclass


# =============================================================================
# Configuration
# =============================================================================

REMOTE_SERVER = os.getenv("REMOTE_DEBUG_SERVER", "root@192.3.249.169")
REMOTE_CONTAINER = os.getenv("REMOTE_DEBUG_CONTAINER", "whisper_server_prd")


# =============================================================================
# Remote Execution Client
# =============================================================================

@dataclass
class RemoteResponse:
    """Response from remote Python execution."""
    status: int
    data: Any
    error: Optional[str] = None

    @property
    def is_success(self) -> bool:
        return self.status == 200

    @property
    def json(self) -> dict:
        if isinstance(self.data, dict):
            return self.data
        elif isinstance(self.data, str):
            try:
                return json.loads(self.data)
            except json.JSONDecodeError:
                return {"raw": self.data}
        return {}


class RemoteProductionClient:
    """
    Client for executing Python commands in the production container
    via SSH + docker exec.

    Requests from localhost (127.0.0.1) bypass authentication,
    allowing us to test the production API without OAuth tokens.
    """

    def __init__(self, server: str = REMOTE_SERVER, container: str = REMOTE_CONTAINER):
        self.server = server
        self.container = container

    def _execute_python(self, code: str) -> RemoteResponse:
        """
        Execute Python code in the remote container.

        Args:
            code: Python code to execute

        Returns:
            RemoteResponse with status, data, and error
        """
        # Escape single quotes for shell
        escaped_code = code.replace("'", "'\\''")

        cmd = [
            "ssh", self.server,
            f"docker exec {self.container} python -c '{escaped_code}'"
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                shell=False
            )

            if result.returncode != 0:
                return RemoteResponse(
                    status=-1,
                    data=None,
                    error=result.stderr.strip()
                )

            # Try to parse JSON response
            try:
                data = json.loads(result.stdout.strip())
                return RemoteResponse(status=200, data=data)
            except json.JSONDecodeError:
                # Return raw output if not JSON
                return RemoteResponse(
                    status=200,
                    data=result.stdout.strip()
                )

        except subprocess.TimeoutExpired:
            return RemoteResponse(
                status=-2,
                data=None,
                error="Request timeout after 30s"
            )
        except Exception as e:
            return RemoteResponse(
                status=-3,
                data=None,
                error=str(e)
            )

    def get(self, endpoint: str) -> RemoteResponse:
        """
        Send GET request to production API (localhost auth bypass).

        Args:
            endpoint: API endpoint (e.g., "/api/transcriptions")

        Returns:
            RemoteResponse with parsed JSON data
        """
        code = f"""import urllib.request, json, urllib.error
req = urllib.request.Request('http://localhost:8000{endpoint}')
try:
    with urllib.request.urlopen(req, timeout=60) as response:
        print(response.status)
        print(response.read().decode())
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode() if hasattr(e, 'read') else '{{\"detail\": \"Not Found\"}}')
except Exception as e:
    print(f"ERROR: {{e}}")
"""
        response = self._execute_python(code)

        # Parse status from output
        if isinstance(response.data, str):
            lines = response.data.strip().split('\n')
            if len(lines) >= 2:
                try:
                    status = int(lines[0])
                    body = '\n'.join(lines[1:])
                    try:
                        data = json.loads(body)
                        return RemoteResponse(status=status, data=data)
                    except json.JSONDecodeError:
                        return RemoteResponse(status=status, data=body)
                except ValueError:
                    pass

        return response

    def get_session(self) -> dict:
        """Get session.json content from production container."""
        cmd = [
            "ssh", self.server,
            f"docker exec {self.container} cat /app/session.json"
        ]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            try:
                return json.loads(result.stdout)
            except json.JSONDecodeError:
                pass
        return {}

    def health(self) -> bool:
        """Check if production server is healthy."""
        response = self.get("/health")
        return response.is_success

    def post(self, endpoint: str, data: dict = None) -> RemoteResponse:
        """
        Send POST request to production API.

        Args:
            endpoint: API endpoint
            data: Request body (will be JSON encoded)

        Returns:
            RemoteResponse with parsed JSON data
        """
        json_data = json.dumps(data) if data else "{}"
        code = f"""import urllib.request, json, sys, urllib.error
req = urllib.request.Request('http://localhost:8000{endpoint}', method='POST')
req.add_header('Content-Type', 'application/json')
req.data = json.dumps({json_data}).encode()
try:
    with urllib.request.urlopen(req, timeout=60) as response:
        print(response.status)
        print(response.read().decode())
except urllib.error.HTTPError as e:
    print(e.code)
    print(e.read().decode() if hasattr(e, 'read') else '{{\"detail\": \"Not Found\"}}')
except Exception as e:
    print(f"ERROR: {{e}}", file=sys.stderr)
        """
        response = self._execute_python(code)

        # Parse status from output
        if isinstance(response.data, str):
            lines = response.data.strip().split('\n')
            if len(lines) >= 2:
                try:
                    status = int(lines[0])
                    body = '\n'.join(lines[1:])
                    try:
                        data = json.loads(body)
                        return RemoteResponse(status=status, data=data)
                    except json.JSONDecodeError:
                        return RemoteResponse(status=status, data=body)
                except ValueError:
                    pass

        return response

    def stream_chat(self, transcription_id: str, message: str) -> RemoteResponse:
        """
        Send chat message and get streaming response.

        Args:
            transcription_id: Transcription UUID
            message: Chat message content

        Returns:
            RemoteResponse with streaming data chunks
        """
        return self.post(f"/api/transcriptions/{transcription_id}/chat/stream",
                        data={"content": message})

    def download_file(self, endpoint: str) -> RemoteResponse:
        """
        Download a file from production API.

        Args:
            endpoint: Download endpoint (e.g., "/api/transcriptions/{id}/download-docx")

        Returns:
            RemoteResponse with file content
        """
        code = f"""import urllib.request, urllib.error
req = urllib.request.Request('http://localhost:8000{endpoint}')
try:
    with urllib.request.urlopen(req, timeout=60) as response:
        print(response.status)
        print(response.headers.get('Content-Type', ''))
        print(response.read().decode('latin-1'))
except urllib.error.HTTPError as e:
    print(e.code)
    print('')
    print(e.read().decode('latin-1') if hasattr(e, 'read') else '')
except Exception as e:
    print(f"ERROR: {{e}}")
        """
        response = self._execute_python(code)

        # Parse status, content-type, and body from output
        if isinstance(response.data, str):
            lines = response.data.strip().split('\n')
            if len(lines) >= 3:
                try:
                    status = int(lines[0])
                    content_type = lines[1]
                    body = '\n'.join(lines[2:])
                    # Store content_type as metadata
                    response.status = status
                    response.data = body
                    return response
                except ValueError:
                    pass

        return response


# =============================================================================
# Pytest Fixtures
# =============================================================================

@pytest.fixture(scope="session")
def prod_client():
    """Remote production client fixture (session-scoped)."""
    client = RemoteProductionClient()

    # Verify connection before proceeding
    if not client.health():
        pytest.fail("Cannot connect to production server or health check failed")

    return client


@pytest.fixture(scope="session")
def prod_session(prod_client):
    """Get production session.json content."""
    return prod_client.get_session()


@pytest.fixture
def test_user_id(prod_session):
    """Get test user ID from session."""
    return prod_session.get("test_user", {}).get("id")


@pytest.fixture
def test_user_email(prod_session):
    """Get test user email from session."""
    return prod_session.get("test_user", {}).get("email")


# =============================================================================
# Test Helpers
# =============================================================================

class Assertions:
    """Custom assertions for production testing."""

    @staticmethod
    def assert_success(response: RemoteResponse):
        """Assert response is successful."""
        assert response.is_success, f"Request failed: {response.error}"

    @staticmethod
    def assert_status(response: RemoteResponse, expected_status: int):
        """Assert response has expected status."""
        assert response.status == expected_status, \
            f"Expected status {expected_status}, got {response.status}"

    @staticmethod
    def assert_has_key(response: RemoteResponse, key: str):
        """Assert response JSON has specific key."""
        Assertions.assert_success(response)
        assert key in response.json, f"Response missing key: {key}"

    @staticmethod
    def assert_auth_bypassed(response: RemoteResponse):
        """Assert request used auth bypass (localhost)."""
        # If auth bypass worked, we got 200 without OAuth token
        Assertions.assert_success(response)


@pytest.fixture
def assertions():
    """Assertions fixture."""
    return Assertions


@pytest.fixture(scope="session")
def prod_transcription_with_summary(prod_client: RemoteProductionClient):
    """Get a transcription ID that has a summary (for DOCX download tests)."""
    response = prod_client.get("/api/transcriptions?page_size=50")
    if not response.is_success:
        pytest.skip("Cannot get transcriptions list")

    transcriptions = response.json.get("data", [])
    for t in transcriptions:
        # Check if this transcription has summaries
        detail_response = prod_client.get(f"/api/transcriptions/{t['id']}")
        if detail_response.is_success:
            detail = detail_response.json
            if detail.get("summaries") and len(detail["summaries"]) > 0:
                return t["id"]

    pytest.skip("No transcription with summary found")


@pytest.fixture(scope="session")
def prod_any_transcription_id(prod_client: RemoteProductionClient):
    """Get any valid transcription ID for testing."""
    response = prod_client.get("/api/transcriptions?page_size=10")
    if not response.is_success:
        pytest.skip("Cannot get transcriptions list")

    transcriptions = response.json.get("data", [])
    if not transcriptions:
        pytest.skip("No transcriptions found")

    return transcriptions[0]["id"]
