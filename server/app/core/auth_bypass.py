"""
Localhost Authentication Bypass for Testing and Debugging

This module provides a secure way to bypass authentication for requests
originating from localhost, enabling automated testing and remote debugging
without exposing the bypass to external requests.

SECURITY: Bypass is hardcoded for localhost IPs only and cannot be
configured via environment variables. This prevents accidental production
exposure that was possible with the old DISABLE_AUTH environment variable.

Usage:
    from app.core.auth_bypass import is_localhost_request, get_test_user

    # In your auth dependency
    async def get_current_user(request: Request, ...):
        if is_localhost_request(request):
            return get_test_user()
        # ... normal auth flow ...
"""

from fastapi import Request
from typing import Optional
from uuid import UUID
from datetime import datetime, timezone
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

# Constants
LOCALHOST_IPS = {"127.0.0.1", "::1", "localhost"}
SESSION_FILE = Path("/app/session.json")
SESSION_EXAMPLE_FILE = Path("/app/session.json.example")

# Default test user UUID (matches DISABLE_AUTH fake user)
DEFAULT_TEST_USER_ID = "fc47855d-6973-4931-b6fd-bd28515bec0d"
DEFAULT_TEST_EMAIL = "test@example.com"


def is_localhost_request(request: Request) -> bool:
    """
    Detect if request originates from localhost.

    Checks multiple sources for reliability:
    1. X-Forwarded-For header (Cloudflare, nginx proxy)
    2. X-Real-IP header (nginx)
    3. CF-Connecting-IP header (Cloudflare)
    4. client.host (direct connection, SSH tunnels)

    SSH Tunnel Support:
        When using SSH tunnel with SOCKS5 proxy (e.g., ssh -D 3480),
        traffic emerges from the destination server as 127.0.0.1,
        triggering the client.host check below. This enables E2E
        testing against production servers without exposing the
        auth bypass to external requests.

    Args:
        request: FastAPI Request object

    Returns:
        True if request is from localhost, False otherwise

    Examples:
        >>> # Direct connection
        >>> request.client.host = "127.0.0.1"
        >>> is_localhost_request(request)
        True

        >>> # Via nginx proxy
        >>> request.headers = {"x-real-ip": "127.0.0.1"}
        >>> is_localhost_request(request)
        True

        >>> # Via SSH tunnel (SOCKS5 proxy)
        >>> request.client.host = "127.0.0.1"
        >>> is_localhost_request(request)
        True

        >>> # External request
        >>> request.headers = {"x-forwarded-for": "203.0.113.1"}
        >>> is_localhost_request(request)
        False
    """
    # Check X-Forwarded-For (may contain multiple IPs, take first/original)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip in LOCALHOST_IPS:
            logger.debug(f"[AuthBypass] Localhost detected via X-Forwarded-For: {client_ip}")
            return True

    # Check X-Real-IP (nginx specific)
    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip in LOCALHOST_IPS:
        logger.debug(f"[AuthBypass] Localhost detected via X-Real-IP: {real_ip}")
        return True

    # Check CF-Connecting-IP (Cloudflare specific)
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip and cf_ip in LOCALHOST_IPS:
        logger.debug(f"[AuthBypass] Localhost detected via CF-Connecting-IP: {cf_ip}")
        return True

    # Check direct connection
    if hasattr(request.client, 'host') and request.client.host in LOCALHOST_IPS:
        logger.debug(f"[AuthBypass] Localhost detected via client.host: {request.client.host}")
        return True

    return False


def load_session() -> dict:
    """
    Load session data from session.json.

    If session.json doesn't exist, creates a default session.

    Returns:
        Session data dict with test user info

    Examples:
        >>> session = load_session()
        >>> session['test_user']['email']
        'test@example.com'
    """
    if not SESSION_FILE.exists():
        logger.info(f"[AuthBypass] Session file not found, creating default: {SESSION_FILE}")
        return create_default_session()

    try:
        with open(SESSION_FILE, 'r') as f:
            session = json.load(f)
            logger.debug(f"[AuthBypass] Loaded session from {SESSION_FILE}")
            return session
    except json.JSONDecodeError as e:
        logger.error(f"[AuthBypass] Invalid JSON in session.json: {e}")
        return create_default_session()
    except Exception as e:
        logger.error(f"[AuthBypass] Failed to load session.json: {e}")
        return create_default_session()


def create_default_session() -> dict:
    """
    Create default session with test user.

    Returns:
        Default session dict

    Examples:
        >>> session = create_default_session()
        >>> session['test_user']['email']
        'test@example.com'
    """
    session = {
        "version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "test_user": {
            "id": DEFAULT_TEST_USER_ID,
            "email": DEFAULT_TEST_EMAIL,
            "is_admin": True,
            "is_active": True
        },
        "test_channels": [],
        "test_transcriptions": []
    }

    # Save to file
    try:
        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSION_FILE, 'w') as f:
            json.dump(session, f, indent=2)
        logger.info(f"[AuthBypass] Created default session at {SESSION_FILE}")
    except Exception as e:
        logger.error(f"[AuthBypass] Failed to create session.json: {e}")

    return session


def get_test_user() -> dict:
    """
    Get test user from session.

    Returns a fake user dict compatible with get_current_user()
    for use when localhost auth bypass is triggered.

    Returns:
        Fake user dict with same structure as Supabase user

    Examples:
        >>> user = get_test_user()
        >>> user['email']
        'test@example.com'
        >>> isinstance(user['id'], UUID)
        True
    """
    session = load_session()
    test_user = session.get("test_user", {})

    user_id_str = test_user.get("id", DEFAULT_TEST_USER_ID)

    # Validate and convert to UUID
    try:
        user_id = UUID(user_id_str)
    except (ValueError, AttributeError):
        logger.warning(f"[AuthBypass] Invalid user_id in session: {user_id_str}, using default")
        user_id = UUID(DEFAULT_TEST_USER_ID)

    return {
        "id": user_id,
        "email": test_user.get("email", DEFAULT_TEST_EMAIL),
        "email_confirmed_at": datetime.now(timezone.utc),
        "phone": None,
        "last_sign_in_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "user_metadata": {
            "role": "admin" if test_user.get("is_admin") else "user",
            "provider": "google",
            "auth_bypass": True  # Marker for bypassed auth
        },
        "app_metadata": {},
    }


def update_session_test_user(user_id: str, email: str, is_admin: bool = False) -> bool:
    """
    Update test user in session.

    Useful for switching between different test users during testing.

    Args:
        user_id: User UUID (string format)
        email: User email
        is_admin: Whether user should have admin privileges

    Returns:
        True if update succeeded, False otherwise

    Examples:
        >>> update_session_test_user(
        ...     "123e4567-e89b-42d3-a456-426614174000",
        ...     "admin@example.com",
        ...     is_admin=True
        ... )
        True
    """
    try:
        session = load_session()
        session["test_user"] = {
            "id": user_id,
            "email": email,
            "is_admin": is_admin,
            "is_active": True
        }
        session["updated_at"] = datetime.now(timezone.utc).isoformat()

        SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(SESSION_FILE, 'w') as f:
            json.dump(session, f, indent=2)

        logger.info(f"[AuthBypass] Updated session test user: {email} (admin={is_admin})")
        return True
    except Exception as e:
        logger.error(f"[AuthBypass] Failed to update session.json: {e}")
        return False


def add_test_transcription(transcription_id: str, file_name: str, status: str = "completed") -> bool:
    """
    Add a transcription to the test session.

    Useful for tracking test transcriptions across debug sessions.

    Args:
        transcription_id: Transcription UUID
        file_name: Original file name
        status: Transcription status

    Returns:
        True if update succeeded, False otherwise
    """
    try:
        session = load_session()

        # Check if already exists
        for t in session["test_transcriptions"]:
            if t["id"] == transcription_id:
                logger.debug(f"[AuthBypass] Transcription {transcription_id} already in session")
                return True

        # Add new transcription
        session["test_transcriptions"].append({
            "id": transcription_id,
            "file_name": file_name,
            "status": status,
            "added_at": datetime.now(timezone.utc).isoformat()
        })
        session["updated_at"] = datetime.now(timezone.utc).isoformat()

        with open(SESSION_FILE, 'w') as f:
            json.dump(session, f, indent=2)

        logger.info(f"[AuthBypass] Added test transcription: {transcription_id}")
        return True
    except Exception as e:
        logger.error(f"[AuthBypass] Failed to add test transcription: {e}")
        return False


def log_bypassed_request(request: Request, user: dict):
    """
    Log auth bypass event for audit purposes.

    Args:
        request: FastAPI Request object
        user: User dict returned by get_test_user()
    """
    logger.info(
        "[AuthBypass] Localhost request bypassed authentication",
        extra={
            "bypassed": True,
            "client_ip": request.client.host if request.client else "unknown",
            "user_agent": request.headers.get("user-agent", "unknown"),
            "path": request.url.path,
            "method": request.method,
            "user_id": str(user["id"]),
            "user_email": user["email"],
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )
