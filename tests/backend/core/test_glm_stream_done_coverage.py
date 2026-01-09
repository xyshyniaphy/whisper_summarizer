"""
GLM Chat Stream [DONE] Path Coverage Test.

This test specifically targets lines 318-321 in glm.py which handle
the streaming completion [DONE] signal.
"""

import pytest
import json
from unittest.mock import MagicMock, patch
from app.core.glm import GLMClient


@pytest.mark.integration
class TestGLMStreamDonePath:
    """Test the [DONE] completion path in GLM streaming."""

    def test_chat_stream_with_done_signal_hits_lines_318_321(self) -> None:
        """
        Test that [DONE] signal properly executes lines 318-321.

        This targets glm.py lines 318-321:
        ```python
        response_time_ms = (time.time() - start_time) * 1000
        logger.info(f"[ChatStream] Stream complete ...")
        yield f"data: {json.dumps({'content': '', 'done': True, 'response_time_ms': response_time_ms})}\n\n"
        break
        ```

        Strategy: Mock httpx at module level since it's imported inside the function.
        """
        import httpx

        # Create a callable that returns our iterator when called
        # Note: The [DONE] line must be exactly "data: [DONE]" without trailing \n\n
        # because the code strips 'data: ' and compares to '[DONE]'
        lines_data = [
            b"data: {\"choices\":[{\"delta\":{\"content\":\"Hello\"}}]}\n\n",
            b"data: [DONE]"
        ]

        # Create mock stream response
        # Make iter_lines return the iterator directly by setting side_effect
        mock_stream_response = MagicMock()
        mock_stream_response.iter_lines = MagicMock(return_value=iter(lines_data))

        # Mock the stream() context manager
        mock_stream_cm = MagicMock()
        mock_stream_cm.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_cm.__exit__ = MagicMock(return_value=False)

        mock_httpx_client = MagicMock()
        mock_httpx_client.stream = MagicMock(return_value=mock_stream_cm)

        # Mock the Client() context manager
        mock_client_cm = MagicMock()
        mock_client_cm.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_client_cm.__exit__ = MagicMock(return_value=False)

        # Patch httpx.Client - when chat_stream imports httpx locally,
        # it will get the patched version
        with patch.object(httpx, "Client", return_value=mock_client_cm):
            client = GLMClient(api_key="test-key", base_url="https://test.com")

            # Call the function which will import httpx locally
            chunks = list(client.chat_stream(
                question="Test question",
                transcription_context="Test context"
            ))

            # Verify we got chunks including the final [DONE] signal
            assert len(chunks) > 0

            # Should have at least 2 chunks: content + done signal
            assert len(chunks) >= 2

            # The last chunk should be the done signal
            done_chunk = [c for c in chunks if '"done": true' in c or '"done":True' in c]
            assert len(done_chunk) > 0, "Should have at least one done chunk"
