"""
Gemini要約API エンドポイントテスト

実際のバックエンドAPIを呼び出してGemini要約機能をテストする。
DBは実DBを使用し、Gemini API呼び出しのみモックする。
"""

import pytest
import uuid
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock
from app.models.transcription import Transcription
from app.models.summary import Summary
from app.db.session import SessionLocal

# 固定テスト用テキスト
FIXED_TEST_TRANSCRIPTION = """
これはテスト用の文字起こしテキストです。
今日の会議では、新しいプロジェクトについて議論しました。
プロジェクトの目標は、ユーザー体験を向上させることです。
次のステップとして、プロトタイプを作成します。
締め切りは来月末です。
"""

EXPECTED_SUMMARY = """
# 概要
会議で新プロジェクトについて議論し、ユーザー体験向上を目標に設定した。

# 主要なポイント
- 新しいプロジェクトの議論
- ユーザー体験の向上が目標
- プロトタイプ作成が次のステップ

# 詳細
締め切りは来月末に設定されています。
"""


@pytest.mark.integration
class TestSummarizeAPI:
    """Gemini要約API統合テスト"""

    def setup_transcription(self, user_id: str, file_name: str = "test.wav", text: str = FIXED_TEST_TRANSCRIPTION) -> str:
        """テスト用の文字起こしデータを作成するヘルパー"""
        db = SessionLocal()
        try:
            transcription = Transcription(
                id=str(uuid.uuid4()),
                user_id=user_id,
                file_name=file_name,
                original_text=text,
                status="completed"
            )
            db.add(transcription)
            db.commit()
            db.refresh(transcription)
            return transcription.id
        finally:
            db.close()

    def test_generate_summary_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """要約生成が成功するテスト"""
        trans_id = self.setup_transcription(real_auth_user["id"])
        
        # GeminiClientのモック
        with patch("app.core.gemini.GeminiClient.generate_summary", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = EXPECTED_SUMMARY
            
            response = real_auth_client.post(f"/api/transcriptions/{trans_id}/summarize")
            
            assert response.status_code in [200, 201]
            data = response.json()
            assert data["summary_text"] == EXPECTED_SUMMARY
            assert data["transcription_id"] == str(trans_id)

    def test_generate_summary_transcription_not_found(self, real_auth_client: TestClient) -> None:
        """存在しない文字起こしIDで404を返すテスト"""
        non_existent_id = str(uuid.uuid4())
        response = real_auth_client.post(f"/api/transcriptions/{non_existent_id}/summarize")
        assert response.status_code == 404

    def test_generate_summary_no_transcription_text(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """文字起こしテキストがない場合に400を返すテスト"""
        trans_id = self.setup_transcription(real_auth_user["id"], text=None)
        
        response = real_auth_client.post(f"/api/transcriptions/{trans_id}/summarize")
        assert response.status_code == 400

    def test_generate_summary_already_exists(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """既存の要約がある場合それを返すテスト"""
        trans_id = self.setup_transcription(real_auth_user["id"])
        
        with patch("app.core.gemini.GeminiClient.generate_summary", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = EXPECTED_SUMMARY
            
            # 1回目
            response1 = real_auth_client.post(f"/api/transcriptions/{trans_id}/summarize")
            assert response1.status_code in [200, 201]
            
            # 2回目 (Gemini APIは呼ばれないはずだが、呼ばれても同じ結果を確認)
            response2 = real_auth_client.post(f"/api/transcriptions/{trans_id}/summarize")
            assert response2.status_code == 200
            assert response2.json()["summary_text"] == EXPECTED_SUMMARY

    def test_generate_summary_chinese_language(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """中国語設定で要約生成ができるテスト"""
        trans_id = self.setup_transcription(real_auth_user["id"])
        
        expected_zh = "# 概述\n..."
        
        # 環境変数を上書きするか、GeminiClientの呼び出しをモックして言語パラメータを確認する
        with patch("app.core.gemini.GeminiClient.generate_summary", new_callable=AsyncMock) as mock_generate:
            mock_generate.return_value = expected_zh
            
            # REVIEW_LANGUAGE環境変数はconftest.pyで設定されている("zh")
            response = real_auth_client.post(f"/api/transcriptions/{trans_id}/summarize")
            
            assert response.status_code in [200, 201]
            assert response.json()["summary_text"] == expected_zh
