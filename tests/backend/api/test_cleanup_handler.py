"""
DOCX Cleanup Exception Handler Tests

Test for transcriptions.py lines 616-621 - cleanup exception handler.
"""

import pytest
import uuid
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, PropertyMock


@pytest.mark.asyncio
class TestDOCXCleanupExceptionHandlers:
    """Test DOCX cleanup exception handlers."""

    @patch('tempfile.mkdtemp')
    @patch('tempfile.mktemp')
    @patch('docx.Document')
    @patch('shutil.rmtree')
    async def test_cleanup_function_exception_handler_logs_warning(
        self, mock_rmtree, mock_document_class, mock_mktemp, mock_mkdtemp
    ):
        """
        Test that cleanup function logs warning when shutil.rmtree fails.

        This targets transcriptions.py lines 620-621:
        ```python
        except Exception as e:
            logger.warning(f"Failed to cleanup temp directory: {e}")
        ```
        """
        from app.api.transcriptions import download_summary_docx
        from app.models.transcription import Transcription
        from app.models.summary import Summary

        mock_mkdtemp.return_value = "/tmp/test_docx"
        mock_mktemp.return_value = "/tmp/test_docx/file.docx"

        mock_db = MagicMock()
        mock_transcription = MagicMock()
        mock_transcription.id = uuid.uuid4()
        mock_transcription.file_name = "test_cleanup.wav"

        mock_summary = MagicMock()
        mock_summary.summary_text = "Test content for cleanup"

        mock_transcription.summaries = [mock_summary]
        mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
        mock_user = {"id": str(uuid.uuid4())}

        mock_doc = MagicMock()
        mock_document_class.return_value = mock_doc

        # Track the cleanup function that was added
        cleanup_function = None

        def capture_cleanup(func):
            nonlocal cleanup_function
            cleanup_function = func
            return func

        mock_background_tasks = MagicMock()
        mock_background_tasks.add_task.side_effect = capture_cleanup

        with patch('app.api.transcriptions.FileResponse') as mock_file_response:
            mock_file_response.return_value = MagicMock()

            # Call the endpoint
            await download_summary_docx(str(uuid.uuid4()), mock_background_tasks, mock_db, mock_user)

        # Verify cleanup function was captured
        assert cleanup_function is not None

        # Now manually execute the cleanup function with rmtree raising exception
        with patch('app.api.transcriptions.logger') as mock_logger:
            with patch('shutil.rmtree') as mock_rmtree_actual:
                mock_rmtree_actual.side_effect = PermissionError("Permission denied")

                # Execute the cleanup function
                cleanup_function()

                # Verify warning was logged
                mock_logger.warning.assert_called_once()
                warning_call = str(mock_logger.warning.call_args)
                assert "Failed to cleanup temp directory" in warning_call

    @patch('tempfile.mkdtemp')
    @patch('tempfile.mktemp')
    @patch('docx.Document')
    async def test_cleanup_function_success_logs_debug(
        self, mock_document_class, mock_mktemp, mock_mkdtemp
    ):
        """
        Test that cleanup function logs debug message on success.

        This targets transcriptions.py lines 618-619:
        ```python
        shutil.rmtree(temp_dir, ignore_errors=True)
        logger.debug(f"Cleaned up temp directory: {temp_dir}")
        ```
        """
        from app.api.transcriptions import download_summary_docx
        from app.models.transcription import Transcription
        from app.models.summary import Summary

        # Create real temp directory for cleanup
        temp_dir_real = tempfile.mkdtemp(prefix="test_cleanup_")

        try:
            mock_mktemp.return_value = temp_dir_real + "/file.docx"
            mock_mkdtemp.return_value = temp_dir_real

            mock_db = MagicMock()
            mock_transcription = MagicMock()
            mock_transcription.id = uuid.uuid4()
            mock_transcription.file_name = "test_cleanup_success.wav"

            mock_summary = MagicMock()
            mock_summary.summary_text = "Test content"

            mock_transcription.summaries = [mock_summary]
            mock_db.query.return_value.filter.return_value.first.return_value = mock_transcription
            mock_user = {"id": str(uuid.uuid4())}

            mock_doc = MagicMock()
            mock_document_class.return_value = mock_doc

            # Track the cleanup function
            cleanup_function = None

            def capture_cleanup(func):
                nonlocal cleanup_function
                cleanup_function = func
                return func

            mock_background_tasks = MagicMock()
            mock_background_tasks.add_task.side_effect = capture_cleanup

            with patch('app.api.transcriptions.FileResponse') as mock_file_response:
                mock_file_response.return_value = MagicMock()

                # Call the endpoint
                await download_summary_docx(str(uuid.uuid4()), mock_background_tasks, mock_db, mock_user)

            assert cleanup_function is not None

            # Execute the cleanup function and verify it works
            with patch('app.api.transcriptions.logger') as mock_logger:
                cleanup_function()

                # Verify debug message was logged
                mock_logger.debug.assert_called_once()
                debug_call = str(mock_logger.debug.call_args)
                assert "Cleaned up temp directory" in debug_call

        finally:
            # Cleanup real temp directory if it still exists
            if Path(temp_dir_real).exists():
                shutil.rmtree(temp_dir_real, ignore_errors=True)
