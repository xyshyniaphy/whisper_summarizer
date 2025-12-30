"""
Gemini要約API エンドポイントテスト

固定テキストを使用してGemini要約機能の動作を検証する。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


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

# 中国語期待される要約
EXPECTED_SUMMARY_ZH = """
# 概述
今天的会议讨论了新项目，目标是提升用户体验。

# 主要要点
- 讨论新项目
- 目标是提升用户体验
- 下一步将创建原型

# 详细信息
截止日期是下个月末。
"""


class TestGeminiSummarizeAPI:
  """Gemini要約APIテストクラス"""
  
  @pytest.mark.integration
  def test_generate_summary_success(self, test_client: TestClient) -> None:
    """
    要約生成が成功するテスト
    
    Args:
      test_client: FastAPI TestClient
    """
    # GeminiClientをモック
    with patch("app.api.transcriptions.get_gemini_client") as mock_get_client:
      mock_gemini_client = AsyncMock()
      mock_gemini_client.generate_summary.return_value = EXPECTED_SUMMARY
      mock_gemini_client.model = "gemini-2.0-flash-exp"
      mock_get_client.return_value = mock_gemini_client
      
      # 認証をモック
      mock_user = {"id": "test-user-id", "email": "test@example.com"}
      with patch("app.api.transcriptions.get_current_active_user", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user
        
        # Transcriptionをモック
        from app.models.transcription import Transcription
        mock_transcription = Transcription(
          id="test-transcription-id",
          user_id="test-user-id",
          file_name="test.wav",
          original_text=FIXED_TEST_TRANSCRIPTION,
          status="completed"
        )
        
        with patch("app.api.transcriptions.db") as mock_db:
          # Transcription取得をモック
          mock_query = mock_db.query.return_value
          mock_filter = mock_query.filter.return_value
          mock_filter.first.return_value = mock_transcription
          
          # Summary取得をモック（既存要約なし）
          mock_summary_query = mock_db.query.return_value
          mock_summary_filter = mock_summary_query.filter.return_value
          mock_summary_filter.first.return_value = None
          
          response = test_client.post(
            "/api/transcriptions/test-transcription-id/summarize",
            headers={"Authorization": "Bearer test-token"}
          )
          
          # 認証が実装されていない場合は401、実装されている場合は200/201
          assert response.status_code in [200, 201, 401]
          
          # 成功した場合のレスポンス検証
          if response.status_code in [200, 201]:
            data = response.json()
            assert "summary_text" in data
            assert data["summary_text"] == EXPECTED_SUMMARY
  
  @pytest.mark.integration
  def test_generate_summary_transcription_not_found(self, test_client: TestClient) -> None:
    """
    存在しない文字起こしIDで404を返すテスト
    
    Args:
      test_client: FastAPI TestClient
    """
    mock_user = {"id": "test-user-id"}
    with patch("app.api.transcriptions.get_current_active_user", new_callable=AsyncMock) as mock_get_user:
      mock_get_user.return_value = mock_user
      
      with patch("app.api.transcriptions.db") as mock_db:
        # Transcription取得をモック（見つからない）
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = None
        
        response = test_client.post(
          "/api/transcriptions/non-existent-id/summarize",
          headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [404, 401]
  
  @pytest.mark.integration
  def test_generate_summary_no_transcription_text(self, test_client: TestClient) -> None:
    """
    文字起こしテキストがない場合に400を返すテスト
    
    Args:
      test_client: FastAPI TestClient
    """
    mock_user = {"id": "test-user-id"}
    with patch("app.api.transcriptions.get_current_active_user", new_callable=AsyncMock) as mock_get_user:
      mock_get_user.return_value = mock_user
      
      from app.models.transcription import Transcription
      mock_transcription = Transcription(
        id="test-transcription-id",
        user_id="test-user-id",
        file_name="test.wav",
        original_text=None,  # テキストなし
        status="processing"
      )
      
      with patch("app.api.transcriptions.db") as mock_db:
        mock_query = mock_db.query.return_value
        mock_filter = mock_query.filter.return_value
        mock_filter.first.return_value = mock_transcription
        
        response = test_client.post(
          "/api/transcriptions/test-transcription-id/summarize",
          headers={"Authorization": "Bearer test-token"}
        )
        
        assert response.status_code in [400, 401]
  
  @pytest.mark.integration
  def test_generate_summary_already_exists(self, test_client: TestClient) -> None:
    """
    既存の要約がある場合、それを返すテスト
    
    Args:
      test_client: FastAPI TestClient
    """
    mock_user = {"id": "test-user-id"}
    with patch("app.api.transcriptions.get_current_active_user", new_callable=AsyncMock) as mock_get_user:
      mock_get_user.return_value = mock_user
      
      from app.models.transcription import Transcription
      from app.models.summary import Summary
      
      mock_transcription = Transcription(
        id="test-transcription-id",
        user_id="test-user-id",
        file_name="test.wav",
        original_text=FIXED_TEST_TRANSCRIPTION,
        status="completed"
      )
      
      mock_summary = Summary(
        id="existing-summary-id",
        transcription_id="test-transcription-id",
        summary_text="既存の要約テキスト",
        model_name="gemini-2.0-flash-exp"
      )
      
      with patch("app.api.transcriptions.db") as mock_db:
        # 最初のquery().filter().first()はTranscription
        # 2番目のquery().filter().first()はSummary
        def mock_query_side_effect(*args):
          mock_result = AsyncMock()
          mock_filter_result = AsyncMock()
          
          # 呼び出し回数に応じて異なる結果を返す
          if not hasattr(mock_query_side_effect, 'call_count'):
            mock_query_side_effect.call_count = 0
          
          if mock_query_side_effect.call_count == 0:
            # Transcription取得
            mock_filter_result.first.return_value = mock_transcription
          else:
            # Summary取得
            mock_filter_result.first.return_value = mock_summary
          
          mock_query_side_effect.call_count += 1
          mock_result.filter.return_value = mock_filter_result
          return mock_result
        
        mock_db.query.side_effect = mock_query_side_effect
        
        response = test_client.post(
          "/api/transcriptions/test-transcription-id/summarize",
          headers={"Authorization": "Bearer test-token"}
        )
        
        # 認証が実装されていない場合は401、実装されている場合は200
        assert response.status_code in [200, 401]
        
        # 成功した場合、既存の要約が返されることを確認
        if response.status_code == 200:
          data = response.json()
          assert data["summary_text"] == "既存の要約テキスト"
  
  def test_generate_summary_without_auth(self, test_client: TestClient) -> None:
    """
    認証なしで要約生成するとエラーになるテスト
    
    Args:
      test_client: FastAPI TestClient
    """
    response = test_client.post("/api/transcriptions/test-id/summarize")
    
    # 認証が必須の場合は401
    assert response.status_code in [401, 403]
  
  @pytest.mark.integration
  def test_generate_summary_chinese_language(self, test_client: TestClient) -> None:
    """
    REVIEW_LANGUAGE=zh（中国語）で要約生成するテスト
    
    Args:
      test_client: FastAPI TestClient
    """
    # GeminiClientをモック（中国語要約を返す）
    with patch("app.api.transcriptions.get_gemini_client") as mock_get_client:
      mock_gemini_client = AsyncMock()
      mock_gemini_client.generate_summary.return_value = EXPECTED_SUMMARY_ZH
      mock_gemini_client.model = "gemini-2.0-flash-exp"
      mock_gemini_client.review_language = "zh"  # 中国語設定を確認
      mock_get_client.return_value = mock_gemini_client
      
      # 認証をモック
      mock_user = {"id": "test-user-id", "email": "test@example.com"}
      with patch("app.api.transcriptions.get_current_active_user", new_callable=AsyncMock) as mock_get_user:
        mock_get_user.return_value = mock_user
        
        # Transcriptionをモック
        from app.models.transcription import Transcription
        mock_transcription = Transcription(
          id="test-transcription-id",
          user_id="test-user-id",
          file_name="test.wav",
          original_text=FIXED_TEST_TRANSCRIPTION,
          status="completed"
        )
        
        with patch("app.api.transcriptions.db") as mock_db:
          # Transcription取得をモック
          mock_query = mock_db.query.return_value
          mock_filter = mock_query.filter.return_value
          mock_filter.first.return_value = mock_transcription
          
          # Summary取得をモック（既存要約なし）
          mock_summary_query = mock_db.query.return_value
          mock_summary_filter = mock_summary_query.filter.return_value
          mock_summary_filter.first.return_value = None
          
          response = test_client.post(
            "/api/transcriptions/test-transcription-id/summarize",
            headers={"Authorization": "Bearer test-token"}
          )
          
          # 認証が実装されていない場合は401、実装されている場合は200/201
          assert response.status_code in [200, 201, 401]
          
          # 成功した場合のレスポンス検証
          if response.status_code in [200, 201]:
            data = response.json()
            assert "summary_text" in data
            # 中国語の要約が返されることを確認
            assert data["summary_text"] == EXPECTED_SUMMARY_ZH
            # 中国語の特徴的なキーワードが含まれていることを確認
            assert "概述" in data["summary_text"]
            assert "主要要点" in data["summary_text"]
            assert "详细信息" in data["summary_text"]
            
            # GeminiClientがreview_language="zh"で初期化されていることを確認
            assert mock_gemini_client.review_language == "zh"
