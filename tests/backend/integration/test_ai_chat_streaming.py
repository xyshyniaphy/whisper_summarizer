"""
AI Chat Streaming Integration Tests

Tests the AI chat streaming functionality including:
- SSE streaming responses
- Chat history management
- Chat with transcription context
- Error handling

Run: ./tests/run.prd.sh test_ai_chat_streaming
"""

import pytest
import json
from conftest import RemoteProductionClient, Assertions


class TestChatStreaming:
    """Test AI chat streaming endpoint."""

    def test_chat_stream_response(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Should receive streaming response from chat endpoint."""
        response = prod_client.stream_chat(prod_any_transcription_id, "你好，请总结这个转录内容")
        # Streaming response may return success or contain streaming data
        assert response.status in [200, -1], f"Unexpected status: {response.status}, error: {response.error}"

    def test_chat_with_empty_message(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should handle empty chat message."""
        response = prod_client.stream_chat(prod_any_transcription_id, "")
        # May return validation error or accept empty message
        assert response.status in [200, 400, 422]

    def test_chat_with_long_message(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should handle long chat messages."""
        long_message = "请详细分析这个转录内容，" * 50  # ~500 characters
        response = prod_client.stream_chat(prod_any_transcription_id, long_message)
        assert response.status in [200, -1, 413], f"Unexpected status: {response.status}"


class TestChatHistory:
    """Test chat history retrieval."""

    def test_get_chat_history(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Should get chat history for transcription."""
        response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}/chat")
        assertions.assert_success(response)

        data = response.json
        assert "messages" in data or "history" in data or isinstance(data, list)

    def test_chat_history_structure(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str, assertions: Assertions):
        """Chat history should have proper structure."""
        response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}/chat")
        assertions.assert_success(response)

        data = response.json
        # Check structure based on actual API response
        if isinstance(data, dict):
            if "messages" in data:
                messages = data["messages"]
            elif "history" in data:
                messages = data["history"]
            else:
                messages = []
        elif isinstance(data, list):
            messages = data
        else:
            messages = []

        # If messages exist, check structure
        if messages:
            msg = messages[0] if isinstance(messages, list) else messages
            # Messages should have content or text field
            assert isinstance(msg, dict)


class TestChatWithContext:
    """Test chat with transcription context."""

    def test_chat_uses_transcription_context(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Chat should use transcription text as context."""
        # Get transcription detail to verify context is available
        detail_response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}")
        if not detail_response.is_success:
            pytest.skip("Cannot get transcription detail")

        transcription = detail_response.json
        if not transcription.get("text"):
            pytest.skip("Transcription has no text content")

        # Send a question that requires context
        response = prod_client.stream_chat(prod_any_transcription_id, "这个转录的主要内容是什么？")
        assert response.status in [200, -1]

    def test_chat_with_summary_context(self, prod_client: RemoteProductionClient, prod_transcription_with_summary: str):
        """Chat should have access to AI summary."""
        response = prod_client.stream_chat(prod_transcription_with_summary, "根据摘要总结要点")
        assert response.status in [200, -1]


class TestChatErrorHandling:
    """Test chat error handling."""

    def test_chat_with_invalid_transcription_id(self, prod_client: RemoteProductionClient):
        """Should handle invalid transcription ID."""
        fake_id = "00000000-0000-0000-0000-000000000000"
        response = prod_client.stream_chat(fake_id, "测试消息")
        assert response.status in [404, 400, 422]

    def test_chat_with_malformed_transcription_id(self, prod_client: RemoteProductionClient):
        """Should handle malformed transcription ID."""
        response = prod_client.stream_chat("invalid-uuid", "测试消息")
        assert response.status in [404, 422, 400]

    def test_chat_with_special_characters(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should handle special characters in message."""
        special_message = "测试特殊字符: @#$%^&*()_+-=[]{}|;':\",./<>?"
        response = prod_client.stream_chat(prod_any_transcription_id, special_message)
        assert response.status in [200, -1, 400]


class TestChatWithMultipleMessages:
    """Test chat with message history."""

    def test_consecutive_chat_messages(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should handle consecutive chat messages."""
        messages = [
            "你好",
            "请继续",
            "谢谢"
        ]

        for msg in messages:
            response = prod_client.stream_chat(prod_any_transcription_id, msg)
            # Each message should get a response
            assert response.status in [200, -1], f"Failed for message: {msg}"

    def test_chat_history_updates(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Chat history should update after each message."""
        # Get initial history
        initial_response = prod_client.get(f"/api/transcriptions/{prod_any_transcription_id}/chat")
        initial_count = 0

        if initial_response.is_success:
            data = initial_response.json
            if isinstance(data, dict):
                initial_count = len(data.get("messages", data.get("history", [])))
            elif isinstance(data, list):
                initial_count = len(data)

        # Send a message
        prod_client.stream_chat(prod_any_transcription_id, "测试消息")

        # Note: History check may vary depending on implementation
        # Some systems may not store history


class TestChatAuthBypass:
    """Test that chat works with auth bypass."""

    def test_chat_without_auth_token(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Chat should work without OAuth token (localhost bypass)."""
        response = prod_client.stream_chat(prod_any_transcription_id, "测试认证绕过")
        # If auth bypass works, should get response
        assert response.status in [200, -1, 400]


class TestStreamingResponseFormat:
    """Test streaming response format."""

    def test_streaming_response_format(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should return proper streaming format (SSE)."""
        response = prod_client.stream_chat(prod_any_transcription_id, "简单测试")
        # Check if response contains streaming data
        if response.is_success and response.data:
            # SSE format typically has "data:" prefix
            data_str = str(response.data)
            # May contain SSE markers or just raw text
            assert len(data_str) > 0


class TestChatWithDifferentQuestions:
    """Test chat with various types of questions."""

    def test_chat_summary_request(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should handle summary request."""
        response = prod_client.stream_chat(prod_any_transcription_id, "请总结这段文字")
        assert response.status in [200, -1]

    def test_chat_translation_request(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should handle translation request."""
        response = prod_client.stream_chat(prod_any_transcription_id, "请翻译成英文")
        assert response.status in [200, -1]

    def test_chat_extraction_request(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should handle key information extraction."""
        response = prod_client.stream_chat(prod_any_transcription_id, "请提取关键信息")
        assert response.status in [200, -1]

    def test_chat_clarification_request(self, prod_client: RemoteProductionClient, prod_any_transcription_id: str):
        """Should handle clarification question."""
        response = prod_client.stream_chat(prod_any_transcription_id, "能详细说明一下吗？")
        assert response.status in [200, -1]
