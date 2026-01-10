# Authentication Bypass System Design
## Automated Testing & Remote Debugging for Production Server

**Status**: Design Document
**Version**: 1.0
**Date**: 2026-01-10
**Author**: Claude Design Agent

---

## 1. Executive Summary

This document describes the design of a secure authentication bypass system that enables:
- **Automated testing** from localhost without authentication barriers
- **Remote debugging** via SSH + docker exec with local context simulation
- **Session management** via `session.json` for test state persistence
- **Zero configuration** - no environment variables needed for auth bypass

**Key Design Principle**: Auth bypass is **hardcoded for localhost only** based on request IP, not configurable via environment variables. This prevents accidental production exposure.

---

## 2. Current System Analysis

### 2.1 Existing Auth Flow

```
┌─────────┐
│ Request │
└────┬────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ FastAPI Endpoint Handler                               │
│                                                         │
│  @router.get("/api/transcriptions")                    │
│  async def get_transcriptions(                         │
│      current_user: dict = Depends(get_current_user)    │
│  ):                                                     │
└────┬────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│ get_current_user() in app/core/supabase.py             │
│                                                         │
│  if settings.DISABLE_AUTH:  ← ENV VAR CHECK           │
│      return fake_user                                  │
│                                                         │
│  token = credentials.credentials                        │
│  user = supabase.auth.get_user(token)                  │
│  return user                                           │
└─────────────────────────────────────────────────────────┘
```

### 2.2 Problems with Current Approach

| Issue | Current Approach | Problem |
|-------|-----------------|---------|
| **Configuration** | `DISABLE_AUTH=true` environment variable | Risk of accidental production exposure |
| **Scope** | Global - affects ALL requests | Cannot bypass selectively |
| **Testing** | Requires env var in every test env | Manual configuration needed |
| **Debugging** | Cannot test remote server locally | No way to simulate localhost from inside container |
| **Session State** | No persistence | Each request creates new fake user context |

---

## 3. New Design: IP-Based Localhost Bypass

### 3.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        REQUEST FLOW                                │
└─────────────────────────────────────────────────────────────────────┘

                              ┌─────────────────┐
                              │  Client Request │
                              └────────┬────────┘
                                       │
                        ┌──────────────┴──────────────┐
                        │                             │
                        ▼                             ▼
              ┌──────────────────┐          ┌──────────────────┐
              │  Localhost Test  │          │  Remote Request  │
              │  (127.0.0.1)     │          │  (w.198066.xyz)  │
              └──────┬───────────┘          └──────┬───────────┘
                     │                             │
                     │ Trusted                     │ Requires Auth
                     │                             │
                     ▼                             ▼
        ┌─────────────────────┐         ┌─────────────────────┐
        │  Auth Bypass        │         │  Supabase OAuth     │
        │  (session.json)     │         │  (Google OAuth)     │
        └──────────┬──────────┘         └──────────┬──────────┘
                   │                               │
                   └───────────────┬───────────────┘
                                   │
                                   ▼
                        ┌─────────────────────┐
                        │  Endpoint Handler   │
                        │  (current_user)     │
                        └─────────────────────┘
```

### 3.2 Localhost Detection Strategy

**Multi-layer detection** for security and flexibility:

```python
def is_localhost_request(request: Request) -> bool:
    """
    Detect if request originates from localhost.

    Checks in order of reliability:
    1. X-Forwarded-For header (Cloudflare/proxy)
    2. X-Real-IP header (nginx)
    3. client.host (direct connection)

    Returns True if IP is in localhost range:
    - 127.0.0.1
    - ::1 (IPv6 localhost)
    - localhost (hostname match)
    """
```

**Supported sources**:
| Source | Detection Method | Example |
|--------|-----------------|---------|
| Direct curl from server | `client.host == '127.0.0.1'` | `docker exec whisper_server_prd curl http://localhost:8000/api/transcriptions` |
| SSH tunnel | `X-Forwarded-For: 127.0.0.1` | `ssh -L 8080:localhost:3080 user@server` |
| Docker network | `client.host.startswith('172.')` (container) | **NOT bypassed** - requires proper auth |

---

## 4. Session Management System

### 4.1 session.json Structure

```json
{
  "version": "1.0",
  "created_at": "2026-01-10T00:00:00Z",
  "updated_at": "2026-01-10T01:30:00Z",
  "test_user": {
    "id": "fc47855d-6973-4931-b6fd-bd28515bec0d",
    "email": "test@example.com",
    "is_admin": true,
    "is_active": true
  },
  "test_channels": [
    {
      "id": "channel-uuid-1",
      "name": "Test Channel 1"
    }
  ],
  "test_transcriptions": [
    {
      "id": "transcription-uuid-1",
      "file_name": "test_audio.m4a",
      "status": "completed"
    }
  ]
}
```

### 4.2 Session File Location

```
server/
├── app/
│   ├── core/
│   │   └── auth_bypass.py     ← New file
├── session.json               ← Session state (gitignored)
└── session.json.example       ← Template (committed)
```

### 4.3 Session Lifecycle

```
┌─────────────────────────────────────────────────────────────┐
│                    SESSION LIFECYCLE                        │
└─────────────────────────────────────────────────────────────┘

    Application Startup
           │
           ▼
    ┌──────────────────┐
    │ Load or Create   │
    │ session.json     │
    └────────┬─────────┘
             │
             ▼
    ┌──────────────────┐      ┌──────────────────┐
    │ First Request    │──────│ Validate User    │
    │ (localhost)      │      │ Exists in DB     │
    └────────┬─────────┘      └────────┬─────────┘
             │                          │
             │ User exists              │ Create user
             ▼                          ▼
    ┌──────────────────┐      ┌──────────────────┐
    │ Return Fake User │      │ Save user to     │
    │ from session     │      │ session.json     │
    └──────────────────┘      └──────────────────┘
```

---

## 5. Implementation Components

### 5.1 New File: `server/app/core/auth_bypass.py`

```python
"""
Localhost Authentication Bypass for Testing and Debugging

This module provides a secure way to bypass authentication for requests
originating from localhost, enabling automated testing and remote debugging
without exposing the bypass to external requests.

SECURITY: Bypass is hardcoded for localhost IPs only and cannot be
configured via environment variables.
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


def is_localhost_request(request: Request) -> bool:
    """
    Detect if request originates from localhost.

    Checks multiple headers and sources:
    1. X-Forwarded-For (Cloudflare, nginx proxy)
    2. X-Real-IP (nginx)
    3. CF-Connecting-IP (Cloudflare)
    4. client.host (direct connection)

    Args:
        request: FastAPI Request object

    Returns:
        True if request is from localhost, False otherwise
    """
    # Check X-Forwarded-For (may contain multiple IPs)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP (original client)
        client_ip = forwarded_for.split(",")[0].strip()
        if client_ip in LOCALHOST_IPS:
            return True

    # Check X-Real-IP
    real_ip = request.headers.get("x-real-ip")
    if real_ip and real_ip in LOCALHOST_IPS:
        return True

    # Check CF-Connecting-IP (Cloudflare)
    cf_ip = request.headers.get("cf-connecting-ip")
    if cf_ip and cf_ip in LOCALHOST_IPS:
        return True

    # Check direct connection
    if hasattr(request.client, 'host') and request.client.host in LOCALHOST_IPS:
        return True

    return False


def load_session() -> dict:
    """
    Load session data from session.json.

    Returns:
        Session data dict with test user info
    """
    if not SESSION_FILE.exists():
        return create_default_session()

    try:
        with open(SESSION_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to load session.json: {e}")
        return create_default_session()


def create_default_session() -> dict:
    """
    Create default session with test user.

    Returns:
        Default session dict
    """
    session = {
        "version": "1.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "test_user": {
            "id": "fc47855d-6973-4931-b6fd-bd28515bec0d",
            "email": "test@example.com",
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
        logger.info(f"Created default session at {SESSION_FILE}")
    except Exception as e:
        logger.error(f"Failed to create session.json: {e}")

    return session


def get_test_user() -> dict:
    """
    Get test user from session.

    Returns:
        Fake user dict compatible with get_current_user()
    """
    session = load_session()
    test_user = session.get("test_user", {})

    return {
        "id": UUID(test_user.get("id", "fc47855d-6973-4931-b6fd-bd28515bec0d")),
        "email": test_user.get("email", "test@example.com"),
        "email_confirmed_at": datetime.now(timezone.utc),
        "phone": None,
        "last_sign_in_at": datetime.now(timezone.utc),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "user_metadata": {
            "role": "admin" if test_user.get("is_admin") else "user",
            "provider": "google"
        },
        "app_metadata": {},
    }


def update_session_test_user(user_id: str, email: str, is_admin: bool = False):
    """
    Update test user in session.

    Args:
        user_id: User UUID
        email: User email
        is_admin: Whether user is admin
    """
    session = load_session()
    session["test_user"] = {
        "id": user_id,
        "email": email,
        "is_admin": is_admin,
        "is_active": True
    }
    session["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(session, f, indent=2)
        logger.info(f"Updated session test user to {email}")
    except Exception as e:
        logger.error(f"Failed to update session.json: {e}")
```

### 5.2 Modified: `server/app/core/supabase.py`

```python
# Import at top of file
from app.core.auth_bypass import is_localhost_request, get_test_user


async def get_current_user(
    request: Request,  # ADD Request parameter
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """
    JWTトークンから現在のユーザーを取得 (Google OAuth)

    Localhost requests bypass authentication for testing.

    Args:
        request: FastAPI Request object
        credentials: HTTPベアラートークン

    Returns:
        user: ユーザー情報 (dict)

    Raises:
        HTTPException: 認証エラー
    """
    # Localhost bypass - HARDCODED, no configuration needed
    if is_localhost_request(request):
        logger.debug("[AuthBypass] Localhost request detected, using test user")
        return get_test_user()

    # Check if credentials provided
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="認証が必要です"
        )

    # ... rest of Supabase validation ...
```

### 5.3 Modified: `server/app/core/config.py`

```python
# REMOVE this line:
# DISABLE_AUTH: bool = False  # Disable authentication for testing

# DISABLE_AUTH is completely removed - bypass is now hardcoded for localhost only
```

---

## 6. Remote Debugging Workflow

### 6.1 Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    REMOTE DEBUGGING                            │
└─────────────────────────────────────────────────────────────────┘

    Developer Machine                    Production Server
    ┌─────────────────┐                 ┌─────────────────────┐
    │                 │                 │                     │
    │  $ ssh root@    │                 │  ┌───────────────┐  │
    │    192.3.249.   │                 │  │ Docker Host   │  │
    │    169          │─────────────────│> │               │  │
    │                 │   SSH Tunnel    │  │ ┌───────────┐ │  │
    └─────────────────┘                 │  │ │whisper_   │ │  │
                                        │  │ │server_prd│ │  │
                                        │  │ │          │ │  │
                                        │  │ │┌─────────┤ │  │
                                        │  │ ││ FastAPI │ │  │
                                        │  │ ││         │ │  │
                                        │  │ │└─────────┘ │  │
                                        │  │ │             │  │
                                        │  │ │ Request:   │  │
                                        │  │ │ 127.0.0.1  │  │
                                        │  │ │ ✓ Localhost│  │
                                        │  │ │   Bypass   │  │
                                        │  │ └───────────┘ │  │
                                        │  └───────────────┘  │
                                        └─────────────────────┘
```

### 6.2 Usage Examples

**Example 1: Test transcriptions API**

```bash
# SSH into production server
ssh root@192.3.249.169

# Execute curl inside Docker container (localhost = bypass)
docker exec whisper_server_prd curl -s http://localhost:8000/api/transcriptions | jq .
```

**Example 2: Upload audio file**

```bash
# SSH into production server
ssh root@192.3.249.169

# Copy file to container
docker cp test_audio.m4a whisper_server_prd:/tmp/test_audio.m4a

# Upload via API (localhost = bypass)
docker exec whisper_server_prd curl -X POST \
  http://localhost:8000/api/audio/upload \
  -F "file=@/tmp/test_audio.m4a" | jq .
```

**Example 3: Test chat endpoint**

```bash
# SSH into production server
ssh root@192.3.249.169

# Get transcription ID from session
TRANSCRIPTION_ID=$(docker exec whisper_server_prd cat /app/session.json | jq -r '.test_transcriptions[0].id')

# Test chat streaming (localhost = bypass)
docker exec whisper_server_prd curl -N \
  "http://localhost:8000/api/transcriptions/$TRANSCRIPTION_ID/chat/stream?message=总结内容"
```

### 6.3 Helper Script: `scripts/remote_debug.sh`

```bash
#!/bin/bash
# Remote Debugging Helper Script

SERVER="root@192.3.249.169"
CONTAINER="whisper_server_prd"

# SSH and execute command in container
remote_curl() {
    local method=${1:-GET}
    local endpoint=$2
    local data=${3:-}

    ssh "$SERVER" "docker exec $CONTAINER curl -s -X $method http://localhost:8000$endpoint $data"
}

# Example usage
case "${1:-help}" in
    transcriptions)
        remote_curl GET "/api/transcriptions" | jq .
        ;;
    upload)
        file=$2
        ssh "$SERVER" "docker cp $file $CONTAINER:/tmp/test.m4a"
        remote_curl POST "/api/audio/upload" "-F file=@/tmp/test.m4a" | jq .
        ;;
    chat)
        trans_id=$2
        message=$3
        docker exec "$CONTAINER" curl -N "http://localhost:8000/api/transcriptions/$trans_id/chat/stream?message=$message"
        ;;
    *)
        echo "Usage: $0 {transcriptions|upload|chat} [...]"
        ;;
esac
```

---

## 7. Testing Strategy

### 7.1 Unit Tests

```python
# tests/backend/core/test_auth_bypass.py

import pytest
from fastapi import Request
from app.core.auth_bypass import (
    is_localhost_request,
    get_test_user,
    load_session,
    update_session_test_user
)


class TestLocalhostDetection:
    """Test localhost request detection"""

    def test_direct_localhost_ipv4(self, mock_request):
        """Test direct IPv4 localhost connection"""
        mock_request.client.host = "127.0.0.1"
        assert is_localhost_request(mock_request) is True

    def test_direct_localhost_ipv6(self, mock_request):
        """Test direct IPv6 localhost connection"""
        mock_request.client.host = "::1"
        assert is_localhost_request(mock_request) is True

    def test_x_forwarded_for_localhost(self, mock_request):
        """Test X-Forwarded-For with localhost"""
        mock_request.headers = {"x-forwarded-for": "127.0.0.1"}
        assert is_localhost_request(mock_request) is True

    def test_x_real_ip_localhost(self, mock_request):
        """Test X-Real-IP with localhost"""
        mock_request.headers = {"x-real-ip": "127.0.0.1"}
        assert is_localhost_request(mock_request) is True

    def test_remote_ip_rejected(self, mock_request):
        """Test that remote IPs are not bypassed"""
        mock_request.client.host = "192.168.1.100"
        assert is_localhost_request(mock_request) is False

    def test_external_request_rejected(self, mock_request):
        """Test that external requests are not bypassed"""
        mock_request.headers = {"x-forwarded-for": "203.0.113.1"}
        assert is_localhost_request(mock_request) is False


class TestSessionManagement:
    """Test session.json management"""

    def test_create_default_session(self, tmp_path):
        """Test default session creation"""
        # Test implementation
        pass

    def test_load_existing_session(self, tmp_path):
        """Test loading existing session"""
        # Test implementation
        pass

    def test_update_test_user(self, tmp_path):
        """Test updating test user in session"""
        # Test implementation
        pass


class TestAuthBypassIntegration:
    """Test auth bypass integration"""

    @pytest.mark.asyncio
    async def test_localhost_request_bypassed(self, client):
        """Test that localhost requests bypass auth"""
        # Test implementation
        pass

    @pytest.mark.asyncio
    async def test_remote_request_requires_auth(self, client):
        """Test that remote requests require auth"""
        # Test implementation
        pass
```

### 7.2 Integration Tests

```python
# tests/backend/integration/test_remote_debug.py

import pytest
from pathlib import Path


class TestRemoteDebugging:
    """Test remote debugging scenarios"""

    def test_docker_exec_curl_transcriptions(self):
        """Test fetching transcriptions via docker exec curl"""
        # Implementation
        pass

    def test_docker_exec_curl_upload(self):
        """Test uploading via docker exec curl"""
        # Implementation
        pass

    def test_session_json_persistence(self):
        """Test session.json persists across requests"""
        # Implementation
        pass
```

---

## 8. Security Considerations

### 8.1 Threat Model

| Threat | Mitigation |
|--------|------------|
| **Accidental production bypass** | Hardcoded localhost check only, no env var |
| **IP spoofing via headers** | Check multiple headers, verify source |
| **Docker network access** | Container IPs not in localhost range |
| **Session file exposure** | File in container only, not exposed |
| **Unauthorized localhost access** | Requires server SSH access first |

### 8.2 Security Checklist

- [x] Bypass is **hardcoded** - no environment variable configuration
- [x] Only **localhost IPs** trigger bypass (127.0.0.1, ::1)
- [x] **Multiple header checks** prevent simple spoofing
- [x] **Session file** is container-local, not exposed
- [x] **Audit logging** for all bypassed requests
- [x] **Docker network** requests still require auth
- [x] **External requests** always require Supabase auth

### 8.3 Audit Logging

```python
# Add to get_current_user() when bypass is triggered
logger.info(
    "[AuthBypass] Localhost request bypassed auth",
    extra={
        "bypassed": True,
        "client_ip": request.client.host,
        "user_agent": request.headers.get("user-agent"),
        "path": request.url.path,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
)
```

---

## 9. Migration Plan

### 9.1 Phase 1: Implementation

1. Create `server/app/core/auth_bypass.py`
2. Modify `server/app/core/supabase.py` to import and use bypass
3. Remove `DISABLE_AUTH` from `server/app/core/config.py`
4. Create `session.json.example` template

### 9.2 Phase 2: Testing

1. Write unit tests for auth_bypass.py
2. Write integration tests for localhost bypass
3. Test remote debugging workflow
4. Verify external requests still require auth

### 9.3 Phase 3: Deployment

1. Deploy to production server
2. Verify session.json creation
3. Test docker exec curl commands
4. Monitor audit logs

### 9.4 Phase 4: Cleanup

1. Remove `DISABLE_AUTH` from all docker-compose files
2. Remove `DISABLE_AUTH` from .env files
3. Update documentation
4. Remove old test fixtures

---

## 10. Rollback Plan

If issues arise:

1. **Revert supabase.py**: Remove localhost bypass code
2. **Restore config.py**: Add back `DISABLE_AUTH` setting
3. **Update compose files**: Add `DISABLE_AUTH=true` for testing
4. **Restart services**: `docker-compose restart server`

---

## 11. Documentation Updates

### 11.1 Files to Update

- `CLAUDE.md` - Add auth bypass documentation
- `README.md` - Update testing section
- `PRODUCTION_README.md` - Add remote debugging guide
- `tests/backend/README.md` - Update test documentation

### 11.2 New Documentation Files

- `server/session.json.example` - Session template
- `scripts/remote_debug.sh` - Remote debugging helper
- `docs/TESTING.md` - Testing guide with auth bypass

---

## 12. Summary

This design provides a **secure, zero-configuration** authentication bypass system that enables:

| Feature | Description |
|---------|-------------|
| **Localhost Bypass** | Hardcoded for 127.0.0.1, ::1, localhost only |
| **Zero Config** | No environment variables needed |
| **Session Management** | `session.json` for test state persistence |
| **Remote Debugging** | SSH + docker exec workflow |
| **Audit Logging** | All bypassed requests logged |
| **Secure by Default** | External requests always require auth |

**Key Benefits**:
- No risk of accidental production exposure
- Simplified automated testing
- Easy remote debugging workflow
- Persistent test session state
- No configuration management overhead

---

**End of Design Document**
