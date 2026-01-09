"""
Final Missing Coverage Tests

Tests for remaining achievable coverage lines.

Targets:
- admin.py line 158: Delete non-existent user

Note: glm.py lines 318-321 (stream completion) are in async streaming code
that requires complex mocking of HTTP client responses. The coverage would
be minimal improvement for the testing complexity required.
"""

import pytest
import uuid
from datetime import datetime, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User
from app.core.supabase import get_current_user
from app.main import app


@pytest.fixture
def admin_user_final(db_session: Session) -> User:
    """Create an admin user for final tests."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"admin-final-{str(uid)[:8]}@example.com",
        is_active=True,
        is_admin=True,
        activated_at=datetime.now(timezone.utc)
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def admin_client_final(admin_user_final: User) -> TestClient:
    """Authenticated admin client for final tests."""
    async def override_auth():
        return {
            "id": str(admin_user_final.id),
            "email": admin_user_final.email,
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"is_admin": True, "is_active": True}
        }

    app.dependency_overrides[get_current_user] = override_auth

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.mark.integration
class TestAdminDeleteNonExistentUser:
    """Test admin.py line 158 - delete non-existent user."""

    def test_delete_nonexistent_user_returns_404_hits_line_158(
        self,
        admin_client_final: TestClient,
        admin_user_final: User,
        db_session: Session
    ) -> None:
        """
        Test that deleting a non-existent user returns 404.

        This targets admin.py line 158:
        ```python
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
        ```

        Scenario:
        1. Admin tries to delete a different user (not self)
        2. That user doesn't exist
        3. Should hit line 158 (user not found error)

        This is different from the update test because:
        - Update endpoint: targets line 110
        - Delete endpoint: targets line 158
        """
        # Create a fake non-existent user ID
        fake_user_id = str(uuid.uuid4())

        # Make sure this user doesn't exist
        db_session.query(User).filter(User.id == fake_user_id).delete()
        db_session.commit()

        # Try to delete this non-existent user (admin is deleting a different user)
        response = admin_client_final.delete(f"/api/admin/users/{fake_user_id}")

        # Should return 404 (user not found) - line 158
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "not found" in detail.lower() or "未找到" in detail or "不存在" in detail
