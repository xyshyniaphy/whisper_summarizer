"""
Chat API エンドポイントテスト

AIチャット機能（履歴取得、メッセージ送信、ストリーミング）を検証する。
"""

import pytest
import uuid
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.models.transcription import Transcription
from app.models.chat_message import ChatMessage
from app.db.session import SessionLocal


@pytest.mark.integration
class TestGetChatHistoryEndpoint:
    """チャット履歴取得エンドポイントのテスト"""

    def test_get_chat_history_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしで履歴取得するとエラーになるテスト"""
        response = test_client.get(f"/api/transcriptions/{uuid.uuid4()}/chat")
        assert response.status_code in [401, 403]

    def test_get_chat_history_transcription_not_found(self, real_auth_client: TestClient) -> None:
        """存在しない転写IDで404を返すテスト"""
        non_existent = str(uuid.uuid4())
        response = real_auth_client.get(f"/api/transcriptions/{non_existent}/chat")
        assert response.status_code == 404

    def test_get_chat_history_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """チャット履歴取得が成功するテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)

            # チャットメッセージを追加
            chat1 = ChatMessage(
                id=str(uuid.uuid4()),
                transcription_id=trans_id,
                user_id=real_auth_user["raw_uuid"],
                role="user",
                content="Test question"
            )
            chat2 = ChatMessage(
                id=str(uuid.uuid4()),
                transcription_id=trans_id,
                user_id=real_auth_user["raw_uuid"],
                role="assistant",
                content="Test answer"
            )
            db.add(chat1)
            db.add(chat2)
            db.commit()

            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/chat")
            assert response.status_code == 200
            data = response.json()
            assert "messages" in data
            assert len(data["messages"]) == 2
        finally:
            db.query(ChatMessage).filter(ChatMessage.transcription_id == trans_id).delete()
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()


@pytest.mark.integration
class TestSendChatMessageEndpoint:
    """チャットメッセージ送信エンドポイントのテスト"""

    def test_send_chat_message_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしで送信するとエラーになるテスト"""
        response = test_client.post(
            f"/api/transcriptions/{uuid.uuid4()}/chat",
            json={"content": "Test message"}
        )
        assert response.status_code in [401, 403]

    def test_send_chat_message_transcription_not_found(self, real_auth_client: TestClient) -> None:
        """存在しない転写IDで404を返すテスト"""
        non_existent = str(uuid.uuid4())
        response = real_auth_client.post(
            f"/api/transcriptions/{non_existent}/chat",
            json={"content": "Test message"}
        )
        assert response.status_code == 404

    def test_send_chat_message_empty_content(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """空のメッセージで400エラーを返すテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)
            db.commit()

            response = real_auth_client.post(
                f"/api/transcriptions/{trans_id}/chat",
                json={"content": ""}
            )
            assert response.status_code == 400
        finally:
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()

    def test_send_chat_message_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """メッセージ送信が成功するテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)
            db.commit()

            # GLM APIをモック
            with patch("app.core.glm.get_glm_client") as mock_get_client:
                mock_client = AsyncMock()
                # ジェネレータを作成
                async def mock_generator():
                    yield {"content": "Test", "done": False}
                    yield {"content": " response", "done": True}
                mock_client.chat_stream = AsyncMock(return_value=mock_generator())
                mock_get_client.return_value = mock_client

                response = real_auth_client.post(
                    f"/api/transcriptions/{trans_id}/chat",
                    json={"content": "Test question"}
                )

            # ストリーミングレスポンスなので200のはず
            assert response.status_code == 200
        finally:
            db.query(ChatMessage).filter(ChatMessage.transcription_id == trans_id).delete()
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()


@pytest.mark.integration
class TestStreamChatMessageEndpoint:
    """チャットストリーミングエンドポイントのテスト"""

    def test_stream_chat_requires_authentication(self, test_client: TestClient) -> None:
        """認証なしでストリーム要求するとエラーになるテスト"""
        response = test_client.post(
            f"/api/transcriptions/{uuid.uuid4()}/chat/stream",
            json={"content": "Test message"}
        )
        assert response.status_code in [401, 403]

    def test_stream_chat_transcription_not_found(self, real_auth_client: TestClient) -> None:
        """存在しない転写IDで404を返すテスト"""
        non_existent = str(uuid.uuid4())
        response = real_auth_client.post(
            f"/api/transcriptions/{non_existent}/chat/stream",
            json={"content": "Test message"}
        )
        assert response.status_code == 404

    def test_stream_chat_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """ストリーミングが成功するテスト"""
        # テスト用データ作成
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test.wav",
                storage_path=f"{trans_id}.txt.gz",
                stage="completed"
            )
            db.add(transcription)
            db.commit()

            # GLM APIをモック
            with patch("app.core.glm.get_glm_client") as mock_get_glm:
                mock_client = AsyncMock()
                # ジェネレータを作成
                async def mock_generator():
                    yield {"content": "Streaming", "done": False}
                    yield {"content": " response", "done": True}
                mock_client.chat_stream = mock_generator
                mock_get_glm.return_value = mock_client

                response = real_auth_client.post(
                    f"/api/transcriptions/{trans_id}/chat/stream",
                    json={"content": "Test question"}
                )

            # Server-Sent EventsのContent-Typeを確認
            assert response.status_code == 200
            assert "text/event-stream" in response.headers["content-type"]
        finally:
            db.query(ChatMessage).filter(ChatMessage.transcription_id == trans_id).delete()
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()
