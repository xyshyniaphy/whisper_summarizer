"""
Admin API Missing Coverage Tests

Test for admin.py line 110 - user not found error.

Note: Line 122 (last admin protection) is logically unreachable due to:
1. Own-admin check (line 102) prevents self-modification
2. require_admin dependency prevents non-admins from accessing endpoint
3. Cannot create scenario where admin tries to demote the only other admin
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.user import User
from app.core.supabase import get_current_user
from app.main import app


@pytest.fixture
def admin_user_for_tests(db_session: Session) -> User:
    """Create an admin user for tests."""
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
    return user


@pytest.fixture
def admin_client(admin_user_for_tests: User) -> TestClient:
    """Authenticated admin client for tests."""
    async def override_auth():
        return {
            "id": str(admin_user_for_tests.id),
            "email": admin_user_for_tests.email,
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"is_admin": True, "is_active": True}
        }

    # Override get_current_user (not get_current_active_user)
    from app.core.supabase import get_current_user
    app.dependency_overrides[get_current_user] = override_auth

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.mark.integration
class TestAdminMissingCoverage:
    """Test admin API missing coverage lines."""

    def test_update_user_nonexistent_after_own_check_hits_line_110(
        self,
        admin_client: TestClient,
        db_session: Session
    ) -> None:
        """
        Test updating a non-existent user after own-admin check passes.

        This targets admin.py line 110 (user not found error).

        Flow:
        1. Admin tries to modify a different user (not self)
        2. That user doesn't exist
        3. Should hit line 110 (user not found error)
        """
        # Create a fake non-existent user ID
        fake_user_id = str(uuid.uuid4())

        # Make sure this user doesn't exist
        db_session.query(User).filter(User.id == fake_user_id).delete()
        db_session.commit()

        # Try to update this non-existent user using the correct endpoint
        response = admin_client.put(
            f"/api/admin/users/{fake_user_id}/admin",
            json={"is_admin": False}
        )

        # Should return 404 (user not found)
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "not found" in detail.lower() or "未找到" in detail
