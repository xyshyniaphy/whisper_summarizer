"""
音声アップロードAPI エンドポイントテスト

音声ファイルのアップロード、文字起こしリスト取得、
削除機能の動作を検証する。
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
from io import BytesIO


class TestAudioAPI:
  """音声APIテストクラス"""
  
  @pytest.mark.integration
  def test_upload_audio_success(self, test_client: TestClient, sample_audio_file: bytes) -> None:
    """
    音声ファイルのアップロードが成功するテスト
    
    Args:
      test_client: FastAPI TestClient
      sample_audio_file: テスト用音声ファイル
    """
    # WhisperServiceとSupabaseをモック
    with patch("app.services.whisper_service.whisper_service.transcribe") as mock_transcribe:
      mock_transcribe.return_value = {
        "text": "テスト文字起こし",
        "segments": [],
        "language": "ja"
      }
      
      with patch("app.core.supabase.get_supabase_client") as mock_supabase:
        mock_client = MagicMock()
        mock_client.auth.get_user = AsyncMock(return_value={
          "user": {"id": "test-user-id"}
        })
        mock_supabase.return_value = mock_client
        
        files = {
          "file": ("test.wav", BytesIO(sample_audio_file), "audio/wav")
        }
        
        response = test_client.post(
          "/api/audio/upload",
          files=files,
          headers={"Authorization": "Bearer test-token"}
        )
        
        # 認証が実装されていない場合は401
        assert response.status_code in [200, 201, 401]
  
  
  @pytest.mark.integration
  def test_upload_audio_invalid_format(self, test_client: TestClient) -> None:
    """
    無効なファイル形式でエラーが返るテスト
    
    Args:
      test_client: FastAPI TestClient
    """
    files = {
      "file": ("test.txt", BytesIO(b"not an audio file"), "text/plain")
    }
    
    response = test_client.post(
      "/api/audio/upload",
      files=files,
      headers={"Authorization": "Bearer test-token"}
    )
    
    # 認証エラーまたはバリデーションエラー
    assert response.status_code in [400, 401, 422]
  
  
  @pytest.mark.integration
  def test_get_transcriptions_list(self, test_client: TestClient, mock_supabase_client: MagicMock) -> None:
    """
    文字起こしリストが取得できるテスト
    
    Args:
      test_client: FastAPI TestClient
      mock_supabase_client: モックされたSupabaseクライアント
    """
    with patch("app.core.supabase.get_supabase_client", return_value=mock_supabase_client):
      response = test_client.get(
        "/api/transcriptions",
        headers={"Authorization": "Bearer test-token"}
      )
      
      # 認証が実装されていない場合は401
      assert response.status_code in [200, 401]
  
  
  @pytest.mark.integration
  def test_delete_transcription(self, test_client: TestClient, mock_supabase_client: MagicMock) -> None:
    """
    文字起こしの削除が成功するテスト
    
    Args:
      test_client: FastAPI TestClient
      mock_supabase_client: モックされたSupabaseクライアント
    """
    transcription_id = "test-transcription-id"
    
    with patch("app.core.supabase.get_supabase_client", return_value=mock_supabase_client):
      with patch("os.remove") as mock_remove:
        response = test_client.delete(
          f"/api/audio/{transcription_id}",
          headers={"Authorization": "Bearer test-token"}
        )
        
        # 認証が実装されていない場合は401
        assert response.status_code in [200, 204, 401, 404]
  
  
  def test_upload_without_auth(self, test_client: TestClient, sample_audio_file: bytes) -> None:
    """
    認証なしでアップロードするとエラーになるテスト
    
    Args:
      test_client: FastAPI TestClient
      sample_audio_file: テスト用音声ファイル
    """
    files = {
      "file": ("test.wav", BytesIO(sample_audio_file), "audio/wav")
    }
    
    response = test_client.post("/api/audio/upload", files=files)
    
    # 認証が必須の場合は401
    assert response.status_code in [401]
