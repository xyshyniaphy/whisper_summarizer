"""
NotebookLM Guideline Download API Endpoint Tests

Tests for the NotebookLM guideline download functionality.
Validates guideline generation, storage, and download behavior.
"""

import pytest
import uuid
import gzip
from pathlib import Path
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.db.session import SessionLocal
from uuid import UUID


# Test user ID matching the conftest fixture (using a known UUID pattern)
TEST_USER_ID = "123e4567-e89b-42d3-a456-426614174000"
TEST_USER_ID_UUID = UUID(TEST_USER_ID)


@pytest.mark.integration
class TestNotebookLMAPI:
    """NotebookLM guideline download API integration tests"""

    # Temp directory for tests - matches the storage service directory
    TEST_TRANSCRIPTIONS_DIR = Path("/tmp/test_transcribes_api")

    @pytest.fixture(autouse=True)
    def setup_storage_directory(self):
        """Override storage service directory for all tests in this class."""
        import app.services.storage_service as storage_module
        import shutil

        # Save original directory
        original_dir = storage_module.TRANSCRIPTIONS_DIR
        # Override with test directory
        storage_module.TRANSCRIPTIONS_DIR = self.TEST_TRANSCRIPTIONS_DIR
        self.TEST_TRANSCRIPTIONS_DIR.mkdir(parents=True, exist_ok=True)

        yield

        # Cleanup
        if self.TEST_TRANSCRIPTIONS_DIR.exists():
            shutil.rmtree(self.TEST_TRANSCRIPTIONS_DIR, ignore_errors=True)
        # Restore original directory
        storage_module.TRANSCRIPTIONS_DIR = original_dir

    def setup_transcription_with_guideline(
        self, db_session, user_id: str, guideline_text: str
    ) -> str:
        """
        Create test transcription data with NotebookLM guideline file.

        Args:
            db_session: Database session
            user_id: User ID for the transcription
            guideline_text: Content of the guideline to create

        Returns:
            str: The transcription ID
        """
        trans_id = str(uuid.uuid4())
        trans_id_uuid = UUID(trans_id)
        user_id_uuid = UUID(user_id) if isinstance(user_id, str) else user_id

        # Create transcription in DB - use stage instead of status
        transcription = Transcription(
            id=trans_id_uuid,
            user_id=user_id_uuid,
            file_name=f"test_notebooklm_{trans_id}.wav",
            storage_path=f"{trans_id}.txt.gz",
            stage="completed"
        )
        db_session.add(transcription)
        db_session.commit()
        db_session.refresh(transcription)

        # Create guideline file
        guideline_path = self.TEST_TRANSCRIPTIONS_DIR / f"{trans_id}.notebooklm.txt.gz"
        guideline_bytes = guideline_text.encode('utf-8')
        compressed_bytes = gzip.compress(guideline_bytes, compresslevel=6)
        guideline_path.write_bytes(compressed_bytes)

        return trans_id

    def teardown_transcription_with_guideline(self, db_session, trans_id: str):
        """Cleanup test data including guideline file."""
        # Delete from DB - convert string to UUID for query
        trans_id_uuid = UUID(trans_id) if isinstance(trans_id, str) else trans_id
        try:
            # Check if table exists and record exists before deleting
            from sqlalchemy import inspect
            if inspect(db_session.connection()).has_table(Transcription.__tablename__):
                result = db_session.query(Transcription).filter(Transcription.id == trans_id_uuid).first()
                if result:
                    db_session.delete(result)
                    db_session.commit()
        except Exception as e:
            # Log but don't fail the test if cleanup fails
            print(f"Warning: Cleanup failed for {trans_id}: {e}")

        # Delete guideline file
        guideline_path = self.TEST_TRANSCRIPTIONS_DIR / f"{trans_id}.notebooklm.txt.gz"
        if guideline_path.exists():
            guideline_path.unlink()

    def test_download_notebooklm_guideline_success(
        self, real_auth_client: TestClient, db_session, real_auth_user: dict
    ) -> None:
        """Successful NotebookLM guideline download test."""
        guideline_text = """**角色设定：**
你是一位资深的佛学内容整理专家及演示文稿架构师。

## 概述
本讲座讨论了佛学修行的核心要点。

## 主要要点
- 戒定慧三学
- 空性智慧
- 慈悲观修

## 详细信息
讲座中详细讲解了如何通过禅修实践来体悟空性。
"""

        trans_id = self.setup_transcription_with_guideline(db_session, real_auth_user["id"], guideline_text)
        try:
            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download-notebooklm")
            assert response.status_code == 200
            assert "text/plain" in response.headers["content-type"]
            assert f"test_notebooklm_{trans_id}-notebooklm.txt" in response.headers["content-disposition"]
            assert len(response.content) > 0

            # Verify content is text
            content = response.content.decode('utf-8')
            assert "角色设定" in content or "概述" in content
            assert "佛学" in content

        finally:
            self.teardown_transcription_with_guideline(db_session, trans_id)

    def test_download_notebooklm_guideline_chinese_full(
        self, real_auth_client: TestClient, db_session, real_auth_user: dict
    ) -> None:
        """Full Chinese guideline content test."""
        guideline_text = """# 演示文稿大纲

## 幻灯片 1：概述
本讲座探讨了金刚经的核心思想。

## 幻灯片 2：主要要点
- 一切有为法，如梦幻泡影
- 应无所住，而生其心
- 凡所有相，皆是虚妄

## 幻灯片 3：详细解释
详细讲解了金刚经中关于空性的智慧。
"""

        trans_id = self.setup_transcription_with_guideline(db_session, real_auth_user["id"], guideline_text)
        try:
            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download-notebooklm")
            assert response.status_code == 200

            content = response.content.decode('utf-8')
            assert "幻灯片 1" in content
            assert "概述" in content
            assert "金刚经" in content

        finally:
            self.teardown_transcription_with_guideline(db_session, trans_id)

    def test_download_notebooklm_guideline_invalid_uuid(
        self, real_auth_client: TestClient, db_session
    ) -> None:
        """422 test for invalid UUID format."""
        response = real_auth_client.get("/api/transcriptions/invalid-uuid/download-notebooklm")
        assert response.status_code == 422

    def test_download_notebooklm_guideline_content_disposition(
        self, real_auth_client: TestClient, db_session, real_auth_user: dict
    ) -> None:
        """Test Content-Disposition header format."""
        guideline_text = "Test guideline for content disposition check."

        trans_id = self.setup_transcription_with_guideline(db_session, real_auth_user["id"], guideline_text)
        try:
            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download-notebooklm")

            if response.status_code == 200:
                content_disposition = response.headers.get("content-disposition", "")
                assert "attachment" in content_disposition
                assert "notebooklm.txt" in content_disposition

        finally:
            self.teardown_transcription_with_guideline(db_session, trans_id)

    def test_download_notebooklm_guideline_long_content(
        self, real_auth_client: TestClient, db_session, real_auth_user: dict
    ) -> None:
        """Test with long guideline content (10+ slides)."""
        # Generate content for 12 slides
        slides = []
        for i in range(1, 13):
            slides.append(f"""
## 幻灯片 {i}：幻灯片标题 {i}

本页主要讨论以下要点：
- 要点一：关于主题 {i} 的详细说明
- 要点二：深入探讨相关内容
- 要点三：实际应用指导
- 要点四：注意事项说明
""")

        guideline_text = f"""# 佛学讲座演示文稿大纲

{"".join(slides)}
"""

        trans_id = self.setup_transcription_with_guideline(db_session, real_auth_user["id"], guideline_text)
        try:
            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download-notebooklm")
            assert response.status_code == 200

            content = response.content.decode('utf-8')
            assert "幻灯片 1" in content
            assert "幻灯片 12" in content
            assert len(content) > 1000  # Should be substantial content

        finally:
            self.teardown_transcription_with_guideline(db_session, trans_id)


@pytest.mark.integration
class TestNotebookLMGuidelineStorageService:
    """Test the storage service methods for NotebookLM guidelines."""

    @pytest.fixture
    def storage_service(self):
        """Create storage service instance for testing."""
        from app.services.storage_service import StorageService
        # Use temp directory for tests
        original_dir = Path("/app/data/transcribes")
        temp_dir = Path("/tmp/test_storage_notebooklm")
        temp_dir.mkdir(parents=True, exist_ok=True)

        # Temporarily override the directory
        import app.services.storage_service as storage_module
        storage_module.TRANSCRIPTIONS_DIR = temp_dir

        service = StorageService()
        yield service

        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
        storage_module.TRANSCRIPTIONS_DIR = original_dir

    def test_save_and_load_guideline(self, storage_service):
        """Test saving and loading a guideline."""
        trans_id = str(uuid.uuid4())
        guideline_text = "Test guideline content for storage testing."

        # Save
        storage_path = storage_service.save_notebooklm_guideline(trans_id, guideline_text)
        assert storage_path == f"{trans_id}.notebooklm.txt.gz"

        # Check exists
        assert storage_service.notebooklm_guideline_exists(trans_id)

        # Load
        loaded_text = storage_service.get_notebooklm_guideline(trans_id)
        assert loaded_text == guideline_text

        # Cleanup
        storage_service.delete_notebooklm_guideline(trans_id)
        assert not storage_service.notebooklm_guideline_exists(trans_id)

    def test_guideline_not_exists(self, storage_service):
        """Test checking for non-existent guideline."""
        fake_id = str(uuid.uuid4())
        assert not storage_service.notebooklm_guideline_exists(fake_id)

    def test_delete_nonexistent_guideline(self, storage_service):
        """Test deleting non-existent guideline returns False."""
        fake_id = str(uuid.uuid4())
        result = storage_service.delete_notebooklm_guideline(fake_id)
        assert result is False

    def test_guideline_compression(self, storage_service):
        """Test that guidelines are properly compressed."""
        trans_id = str(uuid.uuid4())
        # Create content that should compress well
        guideline_text = "Test guideline content. " * 100  # Repeated text

        storage_path = storage_service.save_notebooklm_guideline(trans_id, guideline_text)

        # Check that file exists and is compressed
        from app.services.storage_service import TRANSCRIPTIONS_DIR
        file_path = TRANSCRIPTIONS_DIR / storage_path
        assert file_path.exists()

        # Compressed file should be smaller than original
        compressed_size = file_path.stat().st_size
        original_size = len(guideline_text.encode('utf-8'))
        assert compressed_size < original_size

        # Cleanup
        storage_service.delete_notebooklm_guideline(trans_id)


@pytest.mark.integration
class TestNotebookLMServiceGeneration:
    """Test the NotebookLM service guideline generation."""

    def test_notebooklm_service_init(self):
        """Test NotebookLM service initialization."""
        from app.services.notebooklm_service import NotebookLMService, NOTEBOOKLM_SYSTEM_PROMPT

        service = NotebookLMService()
        assert service is not None
        assert service.model == "GLM-4.5-Air"
        assert len(NOTEBOOKLM_SYSTEM_PROMPT) > 0

    def test_notebooklm_prompt_contains_required_sections(self):
        """Test that the hardcoded prompt contains all required sections."""
        from app.services.notebooklm_service import NOTEBOOKLM_SYSTEM_PROMPT

        # Check for key sections
        assert "角色设定" in NOTEBOOKLM_SYSTEM_PROMPT
        assert "概述" in NOTEBOOKLM_SYSTEM_PROMPT
        assert "主要要点" in NOTEBOOKLM_SYSTEM_PROMPT
        assert "详细信息" in NOTEBOOKLM_SYSTEM_PROMPT
        assert "核心议题" in NOTEBOOKLM_SYSTEM_PROMPT
        assert "义理辨析" in NOTEBOOKLM_SYSTEM_PROMPT
        assert "修行建议" in NOTEBOOKLM_SYSTEM_PROMPT

    def test_notebooklm_singleton(self):
        """Test that get_notebooklm_service returns singleton."""
        from app.services.notebooklm_service import get_notebooklm_service

        service1 = get_notebooklm_service()
        service2 = get_notebooklm_service()
        assert service1 is service2

    def test_generate_guideline_with_short_text_fails(self):
        """Test that guideline generation fails with text that's too short."""
        from app.services.notebooklm_service import NotebookLMService

        service = NotebookLMService()

        with pytest.raises(ValueError, match="too short"):
            service.generate_guideline(
                transcription_text="Short text less than 50 characters.",
                file_name="test.wav"
            )

    def test_load_spec_prompt_returns_hardcoded_prompt(self):
        """Test that _load_spec_prompt returns the hardcoded prompt."""
        from app.services.notebooklm_service import NotebookLMService, NOTEBOOKLM_SYSTEM_PROMPT

        service = NotebookLMService()
        prompt = service._load_spec_prompt()

        assert prompt == NOTEBOOKLM_SYSTEM_PROMPT
        assert len(prompt) > 1000  # Should be substantial content
