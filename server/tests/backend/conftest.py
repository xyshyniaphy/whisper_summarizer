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
    Creates all tables once at the beginning of the test session.
    """
    # Create all tables
    Base.metadata.create_all(bind=app_engine)
    yield
    # Optional: clean up after tests
    # Base.metadata.drop_all(bind=app_engine)


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """
    Create a new database session for each test.

    Yields:
        Session: Database session
    """
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=app_engine)
    session = TestingSessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Rollback to clean up test data
        session.rollback()


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
    # Override authentication to return a valid runner token
    async def override_runner_auth():
        return "test-runner-api-key"

    # For runner API, we just need to pass the Bearer token
    with TestClient(app) as client:
        # Set default authorization header for runner API calls
        client.headers["Authorization"] = "Bearer test-runner-api-key"
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
    user = User(
        id=str(uuid4()),
        email="test@example.com",
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
