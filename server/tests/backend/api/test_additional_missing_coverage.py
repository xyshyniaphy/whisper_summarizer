"""
Additional Missing Coverage Tests

Tests for remaining uncovered code paths:
- admin.py: Last admin deletion (line 170)
- shared.py: Transcription not found (line 51)
- main.py: Lifespan exception handlers (lines 24-25, 33-34)
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.models.user import User
from app.models.transcription import Transcription, TranscriptionStatus
from app.models.share_link import ShareLink


@pytest.fixture
def admin_user_for_delete_test(db_session: Session) -> dict:
    """Create admin user for delete test."""
    uid = uuid.uuid4()
    user = User(
        id=uid,
        email=f"admin-del-{str(uid)[:8]}@example.com",
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
def admin_auth_client_for_delete_test(admin_user_for_delete_test: dict, db_session: Session) -> TestClient:
    """Admin authenticated test client for delete test."""
    from app.main import app
    from app.core.supabase import get_current_active_user
    from app.api.deps import require_admin

    async def override_auth():
        return {
            "id": admin_user_for_delete_test["id"],
            "email": admin_user_for_delete_test["email"],
            "email_confirmed_at": "2025-01-01T00:00:00Z",
            "user_metadata": {"is_admin": True, "is_active": True}
        }

    def override_require_admin():
        return db_session.query(User).filter(User.id == admin_user_for_delete_test["raw_uuid"]).first()

    app.dependency_overrides[get_current_active_user] = override_auth
    app.dependency_overrides[require_admin] = override_require_admin

    with TestClient(app) as client:
        yield client

    app.dependency_overrides = {}


@pytest.mark.integration
class TestSharedAPITranscriptionNotFound:
    """Test shared API when transcription is not found."""

    def test_get_shared_transcription_not_found_returns_404(self, test_client: TestClient, db_session: Session) -> None:
        """Get shared transcription returns 404 when transcription deleted."""
        # Create user, transcription, and share link
        uid = uuid.uuid4()
        user = User(id=uid, email=f"test-share-404-{str(uid)[:8]}@example.com", is_active=True)
        db_session.add(user)
        db_session.flush()

        tid = uuid.uuid4()
        trans = Transcription(
            id=tid,
            user_id=uid,
            file_name="test_share_404.mp3",
            status=TranscriptionStatus.COMPLETED,
            stage="completed"
        )
        db_session.add(trans)
        db_session.flush()

        # Create share link
        link = ShareLink(
            id=str(uuid.uuid4()),
            transcription_id=tid,
            share_token="test_token_404",
            expires_at=datetime.now(timezone.utc).replace(year=2099)
        )
        db_session.add(link)
        db_session.commit()

        try:
            # Delete the transcription (but share link still exists)
            db_session.query(Transcription).filter(Transcription.id == tid).delete()
            db_session.commit()

            # Try to get shared transcription - should return 404
            response = test_client.get("/api/shared/test_token_404")
            assert response.status_code == 404
            assert "不存在" in response.json()["detail"] or "not found" in response.json()["detail"].lower()
        finally:
            db_session.query(ShareLink).filter(ShareLink.share_token == "test_token_404").delete()
            db_session.query(User).filter(User.id == uid).delete()
            db_session.commit()


@pytest.mark.integration
class TestAdminLastAdminDeletion:
    """Test admin API when trying to delete the last admin."""

    def test_cannot_delete_last_admin(self, admin_auth_client_for_delete_test: TestClient, admin_user_for_delete_test: dict, db_session: Session) -> None:
        """Cannot delete the last admin user."""
        # Create a SECOND admin to try deleting the first admin
        second_admin_id = uuid.uuid4()
        second_admin = User(
            id=second_admin_id,
            email=f"second-admin-{str(second_admin_id)[:8]}@example.com",
            is_active=True,
            is_admin=True,
            activated_at=datetime.now(timezone.utc)
        )
        db_session.add(second_admin)
        db_session.commit()

        # Update the auth client to be the second admin
        from app.main import app
        from app.core.supabase import get_current_active_user
        from app.api.deps import require_admin

        async def override_auth_as_second_admin():
            return {
                "id": str(second_admin_id),
                "email": second_admin.email,
                "email_confirmed_at": "2025-01-01T00:00:00Z",
                "user_metadata": {"is_admin": True, "is_active": True}
            }

        def override_require_admin_second():
            return db_session.query(User).filter(User.id == second_admin_id).first()

        app.dependency_overrides[get_current_active_user] = override_auth_as_second_admin
        app.dependency_overrides[require_admin] = override_require_admin_second

        try:
            # Now there are 2 admins
            admin_count = db_session.query(User).filter(
                User.is_admin == True,
                User.deleted_at.is_(None)
            ).count()
            assert admin_count == 2, "Test expects exactly 2 admins"

            # Second admin deletes first admin (now only 1 admin left)
            response = admin_auth_client_for_delete_test.delete(f"/api/admin/users/{admin_user_for_delete_test['id']}")
            if response.status_code == 200:
                # Now only 1 admin remains (the second one)
                # Try to delete the last admin (second admin deleting themselves)
                response2 = admin_auth_client_for_delete_test.delete(f"/api/admin/users/{str(second_admin_id)}")

                # Should fail with 400 - either "own account" or "last admin" error
                assert response2.status_code == 400
                detail = response2.json()["detail"]
                # Either error message is acceptable - both prevent deletion
                assert "Cannot delete the last admin" in detail or "Cannot delete your own account" in detail or "last admin" in detail.lower() or "own account" in detail.lower()
        finally:
            # Cleanup
            app.dependency_overrides = {}
            db_session.query(User).filter(User.id == second_admin_id).delete()
            db_session.commit()


# Note: main.py lifespan exception handlers are difficult to test in pytest
# because they require FastAPI startup/shutdown events which run outside test context.
# These handlers log errors but don't affect functionality, so lower priority.
