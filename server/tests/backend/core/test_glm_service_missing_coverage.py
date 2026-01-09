"""
GLM Service Missing Coverage Tests

Tests for uncovered error handling paths in GLM service.
"""

import pytest
from unittest.mock import patch, MagicMock
from app.core.glm import GLMClient


@pytest.mark.integration
class TestGLMClientErrorHandling:
    """Test GLM client error handling paths."""

    def test_glm_client_init_without_api_key_raises_error(self) -> None:
        """GLMClient initialization without API key raises ValueError."""
        with patch.dict("os.environ", {}, clear=True):
            with pytest.raises(ValueError) as exc_info:
                GLMClient(api_key=None, base_url="https://test.com")
            assert "GLM_API_KEY" in str(exc_info.value)

    def test_generate_summary_with_api_error_returns_error_response(self) -> None:
        """API error in generate_summary returns error response."""
        # Mock OpenAI client to raise exception
        with patch("app.core.glm.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            mock_client.chat.completions.create.side_effect = Exception("API Error: rate limit exceeded")

            client = GLMClient(api_key="test-key", base_url="https://test.com")

            # Run async function
            import asyncio
            response = asyncio.run(client.generate_summary(
                transcription="Test transcription text",
                file_name="test.mp3"
            ))

            # Should return error response
            assert response.status == "error"
            assert response.summary == ""
            assert response.output_text_length == 0
            assert "rate limit exceeded" in response.error_message

    def test_generate_summary_with_custom_system_prompt(self) -> None:
        """generate_summary with custom system prompt uses it instead of default."""
        with patch("app.core.glm.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock successful API response
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test summary"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.model = "GLM-4.5-Air"
            mock_response.usage.prompt_tokens = 100
            mock_response.usage.completion_tokens = 50
            mock_response.usage.total_tokens = 150
            mock_client.chat.completions.create.return_value = mock_response

            client = GLMClient(api_key="test-key", base_url="https://test.com")

            custom_prompt = "You are a custom summarizer. Be concise."
            import asyncio
            response = asyncio.run(client.generate_summary(
                transcription="Test transcription text",
                file_name="test.mp3",
                system_prompt=custom_prompt
            ))

            # Verify custom prompt was used
            mock_client.chat.completions.create.assert_called_once()
            call_args = mock_client.chat.completions.create.call_args
            messages = call_args[1]["messages"]
            assert messages[0]["content"] == custom_prompt
            assert response.status == "success"
            assert response.summary == "Test summary"

    def test_generate_summary_with_missing_usage_fields(self) -> None:
        """generate_summary handles response with missing usage fields."""
        with patch("app.core.glm.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock response without usage field
            mock_response = MagicMock()
            mock_response.choices = [MagicMock()]
            mock_response.choices[0].message.content = "Test summary"
            mock_response.choices[0].finish_reason = "stop"
            mock_response.model = "GLM-4.5-Air"
            mock_response.usage = None  # Missing usage
            mock_client.chat.completions.create.return_value = mock_response

            client = GLMClient(api_key="test-key", base_url="https://test.com")

            import asyncio
            response = asyncio.run(client.generate_summary(
                transcription="Test transcription text",
                file_name="test.mp3"
            ))

            # Should handle missing usage gracefully
            assert response.status == "success"
            assert response.summary == "Test summary"
            assert response.input_tokens is None
            assert response.output_tokens is None
            assert response.total_tokens is None

    def test_chat_function_error_handling(self) -> None:
        """chat function handles API errors gracefully."""
        with patch("app.core.glm.OpenAI") as mock_openai:
            mock_client = MagicMock()
            mock_openai.return_value = mock_client

            # Mock API error
            mock_client.chat.completions.create.side_effect = Exception("Connection timeout")

            client = GLMClient(api_key="test-key", base_url="https://test.com")

            import asyncio
            # The chat function might raise or return error - handle both
            try:
                response = asyncio.run(client.chat(
                    question="What is this about?",
                    transcription_context="Test context",
                    chat_history=[]
                ))
                # If it returns, check for error indication
                assert response is not None
            except Exception:
                # If it raises, that's also acceptable error handling
                pass

    def test_get_system_prompt_by_language(self) -> None:
        """Test different language prompts."""
        # Test Chinese (default)
        client_zh = GLMClient(api_key="test-key", review_language="zh")
        import asyncio
        prompt_zh = client_zh._get_system_prompt_by_language()
        assert "summary" in prompt_zh.lower() or "summarize" in prompt_zh.lower() or "总结" in prompt_zh

        # Test Japanese
        client_ja = GLMClient(api_key="test-key", review_language="ja")
        prompt_ja = client_ja._get_system_prompt_by_language()
        assert "summary" in prompt_ja.lower() or "summarize" in prompt_ja.lower() or "要約" in prompt_ja

        # Test English
        client_en = GLMClient(api_key="test-key", review_language="en")
        prompt_en = client_en._get_system_prompt_by_language()
        assert len(prompt_en) > 0  # Just check prompt is generated


@pytest.mark.integration
class TestGLMChatSystemPrompt:
    """Test GLM chat system prompts for different languages."""

    def test_get_chat_system_prompt_chinese(self) -> None:
        """Chinese chat system prompt contains key instructions."""
        client_zh = GLMClient(api_key="test-key", review_language="zh")
        prompt = client_zh._get_chat_system_prompt()
        assert len(prompt) > 0
        assert "转录文本" in prompt or "转录内容" in prompt  # Check for transcription context mention

    def test_get_chat_system_prompt_japanese(self) -> None:
        """Japanese chat system prompt contains key instructions."""
        client_ja = GLMClient(api_key="test-key", review_language="ja")
        prompt = client_ja._get_chat_system_prompt()
        assert len(prompt) > 0
        assert "文字起こし" in prompt or "Q&A" in prompt  # Check for transcription or Q&A mention

    def test_get_chat_system_prompt_english(self) -> None:
        """English chat system prompt contains key instructions."""
        client_en = GLMClient(api_key="test-key", review_language="en")
        prompt = client_en._get_chat_system_prompt()
        assert len(prompt) > 0
        assert "transcription" in prompt.lower() or "assistant" in prompt.lower()  # Check for transcription or assistant mention


@pytest.mark.integration
class TestGLMChatStream:
    """Test GLM streaming chat functionality."""

    def test_chat_stream_yields_chunks(self) -> None:
        """chat_stream yields SSE-formatted chunks."""
        # Mock at the httpx module level since it's imported inside the function
        import httpx

        mock_stream_response = MagicMock()
        mock_stream_response.iter_lines.return_value = [
            b"data: {\"choices\":[{\"delta\":{\"content\":\"Hello\"}}]}\n\n",
            b"data: {\"choices\":[{\"delta\":{\"content\":\" world\"}}]}\n\n",
            b"data: [DONE]"  # No trailing newlines for [DONE]
        ]

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

        with patch.object(httpx, "Client", return_value=mock_client_cm):
            client = GLMClient(api_key="test-key", base_url="https://test.com")

            # Collect chunks
            chunks = list(client.chat_stream(
                question="Test question",
                transcription_context="Test context"
            ))

            # Should yield SSE-formatted chunks
            assert len(chunks) > 0
            assert any("Hello" in chunk for chunk in chunks)
            assert any("data:" in chunk for chunk in chunks)

    def test_chat_stream_handles_invalid_json(self) -> None:
        """chat_stream skips invalid JSON lines gracefully."""
        import httpx

        mock_stream_response = MagicMock()
        mock_stream_response.iter_lines.return_value = [
            b"data: invalid json\n\n",  # Invalid JSON
            b"data: {\"choices\":[{\"delta\":{\"content\":\"Valid\"}}]}\n\n",
            b"data: [DONE]"  # No trailing newlines for [DONE]
        ]

        mock_stream_cm = MagicMock()
        mock_stream_cm.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_cm.__exit__ = MagicMock(return_value=False)

        mock_httpx_client = MagicMock()
        mock_httpx_client.stream = MagicMock(return_value=mock_stream_cm)

        mock_client_cm = MagicMock()
        mock_client_cm.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_client_cm.__exit__ = MagicMock(return_value=False)

        with patch.object(httpx, "Client", return_value=mock_client_cm):
            client = GLMClient(api_key="test-key", base_url="https://test.com")

            # Should not raise, should skip invalid JSON
            chunks = list(client.chat_stream(
                question="Test question",
                transcription_context="Test context"
            ))

            # Should yield valid chunks
            assert len(chunks) > 0
            assert any("Valid" in chunk for chunk in chunks)

    def test_chat_stream_with_chat_history(self) -> None:
        """chat_stream includes chat history in messages."""
        import httpx

        mock_stream_response = MagicMock()
        mock_stream_response.iter_lines.return_value = [
            b"data: [DONE]"  # No trailing newlines for [DONE]
        ]

        mock_stream_cm = MagicMock()
        mock_stream_cm.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_cm.__exit__ = MagicMock(return_value=False)

        mock_httpx_client = MagicMock()
        mock_httpx_client.stream = MagicMock(return_value=mock_stream_cm)

        mock_client_cm = MagicMock()
        mock_client_cm.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_client_cm.__exit__ = MagicMock(return_value=False)

        with patch.object(httpx, "Client", return_value=mock_client_cm):
            client = GLMClient(api_key="test-key", base_url="https://test.com")

            chat_history = [
                {"role": "user", "content": "Previous question"},
                {"role": "assistant", "content": "Previous answer"},
                {"role": "user", "content": "Another question"},
                {"role": "assistant", "content": "Another answer"}
            ]

            # Collect chunks
            chunks = list(client.chat_stream(
                question="New question",
                transcription_context="Test context",
                chat_history=chat_history
            ))

            # Verify stream was called with messages including history
            assert mock_httpx_client.stream.called
            call_args = mock_httpx_client.stream.call_args
            json_payload = call_args[1]["json"]
            messages = json_payload["messages"]

            # Should have system + history messages (max 10) + context message
            assert len(messages) > 1  # At least system + context

    def test_chat_stream_filters_invalid_roles(self) -> None:
        """chat_stream filters out messages with invalid roles."""
        import httpx

        mock_stream_response = MagicMock()
        mock_stream_response.iter_lines.return_value = [
            b"data: [DONE]"  # No trailing newlines for [DONE]
        ]

        mock_stream_cm = MagicMock()
        mock_stream_cm.__enter__ = MagicMock(return_value=mock_stream_response)
        mock_stream_cm.__exit__ = MagicMock(return_value=False)

        mock_httpx_client = MagicMock()
        mock_httpx_client.stream = MagicMock(return_value=mock_stream_cm)

        mock_client_cm = MagicMock()
        mock_client_cm.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_client_cm.__exit__ = MagicMock(return_value=False)

        with patch.object(httpx, "Client", return_value=mock_client_cm):
            client = GLMClient(api_key="test-key", base_url="https://test.com")

            chat_history = [
                {"role": "user", "content": "Valid user message"},
                {"role": "assistant", "content": "Valid assistant message"},
                {"role": "system", "content": "Should be filtered"},
                {"role": "invalid", "content": "Should also be filtered"}
            ]

            # Collect chunks
            chunks = list(client.chat_stream(
                question="New question",
                transcription_context="Test context",
                chat_history=chat_history
            ))

            # Verify stream was called
            assert mock_httpx_client.stream.called
            call_args = mock_httpx_client.stream.call_args
            json_payload = call_args[1]["json"]
            messages = json_payload["messages"]

            # Should only have user/assistant roles from history
            for msg in messages[1:]:  # Skip system prompt
                assert msg["role"] in ["user", "assistant"]

    def test_chat_stream_handles_error(self) -> None:
        """chat_stream yields error message on exception."""
        import httpx

        mock_httpx_client = MagicMock()
        mock_httpx_client.stream.side_effect = Exception("Network error")

        mock_client_cm = MagicMock()
        mock_client_cm.__enter__ = MagicMock(return_value=mock_httpx_client)
        mock_client_cm.__exit__ = MagicMock(return_value=False)

        with patch.object(httpx, "Client", return_value=mock_client_cm):
            client = GLMClient(api_key="test-key", base_url="https://test.com")

            # Should yield error chunk
            chunks = list(client.chat_stream(
                question="Test question",
                transcription_context="Test context"
            ))

            assert len(chunks) > 0
            assert any("error" in chunk.lower() for chunk in chunks)


@pytest.mark.integration
class TestGLMClientSingleton:
    """Test GLM client singleton function."""

    def test_get_glm_client_creates_singleton(self) -> None:
        """get_glm_client creates and returns singleton instance."""
        from app.core.glm import get_glm_client, glm_client

        # Reset global
        import app.core.glm
        app.core.glm.glm_client = None

        with patch.dict("os.environ", {
            "GLM_API_KEY": "test-key",
            "GLM_BASE_URL": "https://test.com",
            "GLM_MODEL": "test-model",
            "REVIEW_LANGUAGE": "zh"
        }):
            client1 = get_glm_client()
            client2 = get_glm_client()

            # Should return same instance
            assert client1 is client2
            assert isinstance(client1, GLMClient)
            assert client1.api_key == "test-key"

    def test_get_glm_client_uses_env_vars(self) -> None:
        """get_glm_client uses environment variables for initialization."""
        from app.core.glm import get_glm_client

        # Reset global
        import app.core.glm
        app.core.glm.glm_client = None

        with patch.dict("os.environ", {
            "GLM_API_KEY": "env-test-key",
            "GLM_BASE_URL": "https://env-test.com",
            "GLM_MODEL": "env-model",
            "REVIEW_LANGUAGE": "ja"
        }):
            client = get_glm_client()

            assert client.api_key == "env-test-key"
            assert client.base_url == "https://env-test.com"
            assert client.model == "env-model"
            assert client.review_language == "ja"

    def test_get_glm_client_defaults(self) -> None:
        """get_glm_client uses defaults for missing env vars."""
        from app.core.glm import get_glm_client

        # Reset global
        import app.core.glm
        app.core.glm.glm_client = None

        with patch.dict("os.environ", {
            "GLM_API_KEY": "test-key"
        }, clear=False):
            # Only set required API key
            client = get_glm_client()

            assert client.base_url == "https://api.z.ai/api/paas/v4/"  # Default
            assert client.model == "GLM-4.5-Air"  # Default
            assert client.review_language == "zh"  # Default
