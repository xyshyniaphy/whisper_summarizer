"""
Pytest configuration and shared fixtures for backend tests.
"""
import os
import sys
import tempfile
from pathlib import Path
from typing import Generator
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from app.core.config import settings
from app.db.base_class import Base
from app.main import app


# ============================================================================
# Database Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def db_engine():
    """Create a test database engine."""
    # Use in-memory SQLite for faster tests
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False}
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(db_engine) -> Generator[Session, None, None]:
    """Create a test database session."""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=db_engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


# ============================================================================
# FastAPI Test Client Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Create a FastAPI test client with database dependency override."""
    from app.api.deps import get_db

    def _get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = _get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
def authenticated_client(client: TestClient) -> Generator[TestClient, None, None]:
    """Create a test client with mocked authentication."""
    from app.core.supabase import get_current_active_user
    from datetime import datetime

    # Mock authenticated user - Return UUID object directly, not string
    test_user_id = uuid4()
    mock_user = {
        "id": test_user_id,  # UUID object (SQLAlchemy needs it), converted to string in users.py
        "email": "test@example.com",
        "user_metadata": {"role": "user", "full_name": "Test User"},
        "email_confirmed_at": datetime.utcnow(),
        "created_at": datetime.utcnow(),
        "phone": None,
        "last_sign_in_at": None,
        "updated_at": datetime.utcnow(),
        "app_metadata": {},
    }

    def _get_current_user():
        return mock_user

    app.dependency_overrides[get_current_active_user] = _get_current_user
    yield client
    app.dependency_overrides.clear()


# ============================================================================
# Model Mock Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def mock_transcription():
    """Create a mock Transcription object."""
    class MockTranscription:
        def __init__(self):
            self.id = uuid4()
            self.user_id = uuid4()
            self.file_name = "test_audio.mp3"
            self.file_path = "/tmp/uploads/test_audio.mp3"
            self.storage_path = None
            self.text = "This is a test transcription.\\n\\nIt has multiple paragraphs."
            self.language = "en"
            self.duration_seconds = 300.0
            self.stage = "completed"
            self.error_message = None
            self.retry_count = 0
            self.completed_at = None
            self.pptx_status = "not-started"
            self.pptx_error_message = None
            self.created_at = None
            self.updated_at = None
            self.summaries = []

    return MockTranscription()


@pytest.fixture(scope="function")
def mock_transcription_with_summary():
    """Create a mock Transcription object with summary."""
    class MockSummary:
        def __init__(self):
            self.summary_text = "This is a test summary.\\n\\nIt has key points."

    class MockTranscription:
        def __init__(self):
            self.id = uuid4()
            self.user_id = uuid4()
            self.file_name = "test_audio.mp3"
            self.file_path = "/tmp/uploads/test_audio.mp3"
            self.storage_path = None
            self.text = "This is a test transcription.\\n\\nIt has multiple paragraphs."
            self.language = "en"
            self.duration_seconds = 300.0
            self.stage = "completed"
            self.error_message = None
            self.retry_count = 0
            self.completed_at = None
            self.pptx_status = "not-started"
            self.pptx_error_message = None
            self.created_at = None
            self.updated_at = None
            self.summaries = [MockSummary()]

    return MockTranscription()


@pytest.fixture(scope="function")
def mock_long_transcription():
    """Create a mock Transcription with very long content."""
    # Create content that spans multiple slides
    long_text = "\\n\\n".join([
        f"This is paragraph {i} with some content to test chunking."
        for i in range(100)
    ])

    class MockTranscription:
        def __init__(self):
            self.id = uuid4()
            self.user_id = uuid4()
            self.file_name = "long_audio.mp3"
            self.file_path = "/tmp/uploads/long_audio.mp3"
            self.storage_path = None
            self.text = long_text
            self.language = "en"
            self.duration_seconds = 3600.0
            self.stage = "completed"
            self.error_message = None
            self.retry_count = 0
            self.completed_at = None
            self.pptx_status = "not-started"
            self.pptx_error_message = None
            self.created_at = None
            self.updated_at = None
            self.summaries = []

    return MockTranscription()


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def temp_output_dir() -> Generator[Path, None, None]:
    """Create a temporary output directory for tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ============================================================================
# Marp Service Fixtures
# ============================================================================

@pytest.fixture(scope="function")
def marp_service(temp_output_dir: Path):
    """Create a MarpService instance with temporary output directory."""
    from app.services.marp_service import MarpService
    return MarpService(output_dir=temp_output_dir)


@pytest.fixture(scope="function")
def marp_service_with_real_path():
    """Create a MarpService instance with real output path (for integration tests)."""
    from app.services.marp_service import get_marp_service
    service = get_marp_service()
    # Ensure output directory exists
    service.output_dir.mkdir(parents=True, exist_ok=True)
    return service


# ============================================================================
# Utility Functions
# ============================================================================

def assert_valid_markdown(markdown: str) -> None:
    """Assert that markdown string has valid Marp frontmatter."""
    assert markdown.startswith("---")
    assert "marp: true" in markdown
    assert "---" in markdown[3:]  # Second frontmatter delimiter


def count_slides(markdown: str) -> int:
    """Count the number of slides in Marp markdown."""
    # Slide separators are "---" that are not in the frontmatter
    lines = markdown.split("\\n")
    in_frontmatter = False
    frontmatter_end = False
    count = 1  # Always at least one slide
    for line in lines:
        stripped = line.strip()
        if stripped == "---":
            if not in_frontmatter and not frontmatter_end:
                in_frontmatter = True
            elif in_frontmatter:
                frontmatter_end = True
                in_frontmatter = False
            else:
                count += 1
    return count
