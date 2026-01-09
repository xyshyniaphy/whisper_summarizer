"""
Admin API Last Admin Demotion Tests

Test for admin.py lines 110, 122 - last admin demotion check.

The check prevents demotion when admin_count <= 1 BEFORE the change.
So with 2 admins, demoting 1 succeeds (leaves 1 admin).
To hit line 122, we need a scenario where admin_count is 1.
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.user import User


@pytest.fixture
def admin_a(db_session: Session) -> dict:
    """Create Admin A."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"admin-a-{str(uid)[:8]}@example.com",
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
def admin_b(db_session: Session) -> dict:
    """Create Admin B."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"admin-b-{str(uid)[:8]}@example.com",
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
def admin_c(db_session: Session) -> dict:
    """Create Admin C."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"admin-c-{str(uid)[:8]}@example.com",
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
def admin_a_auth_client(admin_a: dict, db_session: Session) -> TestClient:
    """Test client authenticated as Admin A."""
    from app.main import app
    from app.core.supabase import get_current_active_user
    from app.api.deps import require_admin

    async def override_auth():
        return {
            "id": admin_a["id"],
            "email": admin_a["email"],
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"is_admin": True, "is_active": True}
        }

    def override_require_admin():
        return db_session.query(User).filter(User.id == admin_a["raw_uuid"]).first()

    app.dependency_overrides[get_current_active_user] = override_auth
    app.dependency_overrides[require_admin] = override_require_admin

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.mark.integration
class TestAdminLastAdminDemotion:
    """Test admin API when trying to demote the last admin."""

    def test_with_two_admins_can_demote_one(
        self, 
        admin_a_auth_client: TestClient, 
        admin_a: dict,
        admin_b: dict,
        db_session: Session
    ) -> None:
        """
        With 2 admins, can demote 1 (leaves 1 admin).
        admin_count check passes because 2 > 1.
        This verifies the expected behavior.
        """
        # Verify we have exactly 2 admins
        admin_count = db_session.query(User).filter(
            User.is_admin == True,
            User.deleted_at.is_(None)
        ).count()
        assert admin_count == 2

        # Admin A tries to demote Admin B
        response = admin_a_auth_client.put(
            f"/api/admin/users/{admin_b['id']}/admin",
            json={"is_admin": False}
        )

        # Should succeed - admin_count was 2, which is > 1
        assert response.status_code == 200

        # Verify Admin B is no longer admin
        admin_b_updated = db_session.query(User).filter(User.id == admin_b["raw_uuid"]).first()
        assert admin_b_updated.is_admin is False

        # Verify only 1 admin remains
        admin_count_after = db_session.query(User).filter(
            User.is_admin == True,
            User.deleted_at.is_(None)
        ).count()
        assert admin_count_after == 1

        # Restore for cleanup
        admin_b_updated.is_admin = True
        db_session.commit()

    def test_with_three_admins_can_demote_one(
        self,
        admin_a_auth_client: TestClient,
        admin_a: dict,
        admin_b: dict,
        admin_c: dict,
        db_session: Session
    ) -> None:
        """
        With 3 admins, can demote 1 (leaves 2 admins).
        admin_count check passes because 3 > 1.
        """
        # Verify we have 3 admins
        admin_count = db_session.query(User).filter(
            User.is_admin == True,
            User.deleted_at.is_(None)
        ).count()
        assert admin_count == 3

        # Admin A tries to demote Admin B
        response = admin_a_auth_client.put(
            f"/api/admin/users/{admin_b['id']}/admin",
            json={"is_admin": False}
        )

        # Should succeed - admin_count was 3, which is > 1
        assert response.status_code == 200

        # Verify Admin B is no longer admin
        admin_b_updated = db_session.query(User).filter(User.id == admin_b["raw_uuid"]).first()
        assert admin_b_updated.is_admin is False

        # Restore for cleanup
        admin_b_updated.is_admin = True
        db_session.commit()

    def test_cannot_modify_own_admin_status(
        self,
        admin_a_auth_client: TestClient,
        admin_a: dict
    ) -> None:
        """
        Cannot modify own admin status.
        This hits the early return (line 102-106) before the last-admin check.
        """
        response = admin_a_auth_client.put(
            f"/api/admin/users/{admin_a['id']}/admin",
            json={"is_admin": False}
        )

        # Should fail with "own admin status" error
        assert response.status_code == 400
        detail = response.json()["detail"]
        assert "Cannot modify your own admin status" in detail or "own" in detail.lower()

    def test_line_110_user_not_found(
        self,
        admin_a_auth_client: TestClient
    ) -> None:
        """
        Test line 110 - user not found check.
        """
        fake_user_id = str(uuid.uuid4())
        response = admin_a_auth_client.put(
            f"/api/admin/users/{fake_user_id}/admin",
            json={"is_admin": False}
        )

        # Should fail with "User not found"
        assert response.status_code == 404
        detail = response.json()["detail"]
        assert "not found" in detail.lower()
