"""
Pytest fixtures for server backend tests.

Provides test client, database session, and test data fixtures.
"""

import os
import tempfile
from typing import Generator
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

# Set test environment before imports
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/whisper_summarizer")
os.environ.setdefault("RUNNER_API_KEY", "test-runner-api-key")

from app.db.base_class import Base
from app.db.session import engine as app_engine
from app.models.transcription import Transcription, TranscriptionStatus
from app.models.user import User
from app.main import app


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def init_test_database():
    """
    Initialize database tables for tests.
    Drops and recreates all tables once per session to ensure fresh schema.
    """
    # Drop all tables first to ensure fresh schema
    Base.metadata.drop_all(bind=app_engine)
    # Create all tables with current schema
    Base.metadata.create_all(bind=app_engine)

    yield

    # Clean up after all tests
    Base.metadata.drop_all(bind=app_engine)


@pytest.fixture(scope="function", autouse=True)
def clean_test_database():
    """
    Clean up data between tests to ensure isolation.
    """
    # Clean up any existing data from previous test runs
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app_engine)
    cleanup_session = SessionLocal()

    try:
        # Delete all data in reverse dependency order
        from app.models.transcription import Transcription
        from app.models.channel import ChannelMembership, TranscriptionChannel, Channel
        from app.models.user import User
        from app.models.chat_message import ChatMessage
        from app.models.summary import Summary

        cleanup_session.query(TranscriptionChannel).delete()
        cleanup_session.query(ChatMessage).delete()
        cleanup_session.query(Summary).delete()
        cleanup_session.query(Transcription).delete()
        cleanup_session.query(ChannelMembership).delete()
        cleanup_session.query(Channel).delete()
        cleanup_session.query(User).delete()
        cleanup_session.commit()
    finally:
        cleanup_session.close()

    yield

    # Clean up after each test to prevent data leakage
    cleanup_session = SessionLocal()
    try:
        # Delete all data in reverse dependency order
        cleanup_session.query(TranscriptionChannel).delete()
        cleanup_session.query(ChatMessage).delete()
        cleanup_session.query(Summary).delete()
        cleanup_session.query(Transcription).delete()
        cleanup_session.query(ChannelMembership).delete()
        cleanup_session.query(Channel).delete()
        cleanup_session.query(User).delete()
        cleanup_session.commit()
    finally:
        cleanup_session.close()


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """
    Create a new database session for each test.

    Note: This fixture commits data so it's visible to test_client requests.
    Data is cleaned up by the function-scoped clean_test_database fixture.

    Yields:
        Session: Database session
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app_engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        # Close the session (don't rollback - test_client needs to see committed data)
        session.close()


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================

@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient without authentication.

    Yields:
        TestClient: Unauthenticated test client
    """
    with TestClient(app) as client:
        yield client


@pytest.fixture
def auth_client() -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient with runner authentication.

    Uses valid RUNNER_API_KEY for authenticated requests.

    Yields:
        TestClient: Authenticated test client for runner API
    """
    # Get the actual RUNNER_API_KEY from environment
    import os
    runner_api_key = os.environ.get("RUNNER_API_KEY", "test-runner-api-key")

    # For runner API, we just need to pass the Bearer token
    with TestClient(app) as client:
        # Set default authorization header for runner API calls
        client.headers["Authorization"] = f"Bearer {runner_api_key}"
        yield client


@pytest.fixture
def user_auth_client() -> Generator[TestClient, None, None]:
    """
    FastAPI TestClient with user authentication.

    For testing user-facing endpoints like audio upload.

    Yields:
        TestClient: Authenticated test client for user API
    """
    from app.core.supabase import get_current_active_user
    from app.models.user import User

    test_user_id = str(uuid4())

    async def override_user_auth():
        return {
            "id": test_user_id,
            "email": f"test-{test_user_id[:8]}@example.com",
            "email_confirmed_at": "2025-01-01T00:00:00Z"
        }

    app.dependency_overrides[get_current_active_user] = override_user_auth

    with TestClient(app) as client:
        yield client

    # Clean up override
    app.dependency_overrides = {}


@pytest.fixture
def real_auth_user() -> dict:
    """
    実テスト用のユーザー情報フィクスチャ (for compatibility with root tests)
    """
    test_user_id = uuid4()
    return {
        "id": str(test_user_id),
        "email": f"test-real-{str(test_user_id)[:8]}@example.com",
        "raw_uuid": test_user_id
    }


@pytest.fixture
def real_auth_client(real_auth_user: dict) -> Generator[TestClient, None, None]:
    """
    実DBと認証バイパスを使用したTestClient (for compatibility with root tests)

    DBにテストユーザーを作成し、認証をそのユーザーでバイパスする。
    テスト終了後にユーザーと関連データを削除する。
    """
    from app.core.supabase import get_current_active_user
    from app.models.user import User
    from app.models.transcription import Transcription
    from app.models.summary import Summary

    async def override_auth():
        return {
            "id": real_auth_user["id"],
            "email": real_auth_user["email"],
            "email_confirmed_at": "2025-01-01T00:00:00Z"
        }

    # ユーザー作成
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app_engine)
    db = SessionLocal()
    try:
        user = User(id=real_auth_user["raw_uuid"], email=real_auth_user["email"])
        db.add(user)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

    app.dependency_overrides[get_current_active_user] = override_auth

    with TestClient(app) as client:
        yield client

    # クリーンアップ
    app.dependency_overrides = {}
    db = SessionLocal()
    try:
        # 関連データの削除
        db.query(Summary).filter(Summary.transcription_id.in_(
            db.query(Transcription.id).filter(Transcription.user_id == real_auth_user["raw_uuid"])
        )).delete(synchronize_session=False)
        db.query(Transcription).filter(Transcription.user_id == real_auth_user["raw_uuid"]).delete(synchronize_session=False)
        db.query(User).filter(User.id == real_auth_user["raw_uuid"]).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


# ============================================================================
# Test Data Fixtures
# ============================================================================

@pytest.fixture
def test_user(db_session: Session) -> User:
    """
    Create a test user in the database.

    Yields:
        User: Test user instance
    """
    user_id = str(uuid4())
    user = User(
        id=user_id,
        email=f"test-{user_id[:8]}@example.com",
        is_active=True,
        is_admin=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def test_transcription(db_session: Session, test_user: User) -> Transcription:
    """
    Create a test transcription in pending status.

    Yields:
        Transcription: Test transcription instance
    """
    # Create a temporary audio file
    temp_dir = Path(tempfile.gettempdir())
    temp_file = temp_dir / f"test_audio_{uuid4()}.mp3"
    temp_file.write_bytes(b"fake audio content")

    transcription = Transcription(
        id=uuid4(),
        file_name="test_audio.mp3",
        file_path=str(temp_file),
        status=TranscriptionStatus.PENDING,
        user_id=test_user.id
    )
    db_session.add(transcription)
    db_session.commit()
    db_session.refresh(transcription)

    yield transcription

    # Cleanup
    if temp_file.exists():
        temp_file.unlink()


@pytest.fixture
def test_processing_transcription(db_session: Session, test_user: User) -> Transcription:
    """
    Create a test transcription in processing status.

    Yields:
        Transcription: Test transcription in processing state
    """
    transcription = Transcription(
        id=uuid4(),
        file_name="processing_audio.mp3",
        status=TranscriptionStatus.PROCESSING,
        runner_id="test-runner-01",
        user_id=test_user.id
    )
    db_session.add(transcription)
    db_session.commit()
    db_session.refresh(transcription)

    return transcription


@pytest.fixture
def test_completed_transcription(db_session: Session, test_user: User) -> Transcription:
    """
    Create a test transcription in completed status.

    Yields:
        Transcription: Test transcription in completed state
    """
    transcription = Transcription(
        id=uuid4(),
        file_name="completed_audio.mp3",
        status=TranscriptionStatus.COMPLETED,
        user_id=test_user.id,
        stage="completed"
    )
    db_session.add(transcription)
    db_session.commit()
    db_session.refresh(transcription)

    return transcription


# ============================================================================
# Audio File Fixtures
# ============================================================================

@pytest.fixture
def test_audio_file() -> Path:
    """
    Create a temporary test audio file.

    Yields:
        Path: Path to temporary audio file
    """
    temp_dir = Path(tempfile.gettempdir())
    temp_file = temp_dir / f"test_audio_{uuid4()}.mp3"
    temp_file.write_bytes(b"fake audio content for testing")

    yield temp_file

    # Cleanup
    if temp_file.exists():
        temp_file.unlink()


@pytest.fixture
def test_audio_content() -> bytes:
    """
    Return fake audio content for uploads.

    Yields:
        bytes: Fake audio content
    """
    return b"fake audio content for testing"


@pytest.fixture
def sample_audio_file() -> bytes:
    """
    テスト用音声ファイルデータ（有効な1秒間の無音WAVファイル）- alias for test_audio_content

    Returns:
        bytes: Audio file binary data
    """
    return b"fake audio content for testing"
