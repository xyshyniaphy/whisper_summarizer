"""
Pytest設定とフィクスチャ定義

テスト用のSupabaseモック、FastAPI TestClient、
その他共通フィクスチャを提供する。
"""

import os
from typing import Generator
import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock

# 環境変数をテスト用に設定（既に設定されている場合は上書きしない）
# 統合テストでは実際の.envファイルの値を使用する
os.environ.setdefault("SUPABASE_URL", "http://test-supabase-url.com")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/test_db")
os.environ.setdefault("GLM_API_KEY", "test-glm-api-key")
os.environ.setdefault("GLM_API_ENDPOINT", "http://test-glm-endpoint.com")
os.environ.setdefault("GLM_MODEL", "test-model")
os.environ.setdefault("GEMINI_API_KEY", "test-gemini-api-key")
os.environ.setdefault("GEMINI_API_ENDPOINT", "")  # 空文字列で公式SDKを使用
os.environ.setdefault("GEMINI_MODEL", "gemini-2.0-flash-exp")
os.environ.setdefault("REVIEW_LANGUAGE", "zh")


@pytest.fixture
def test_client() -> Generator[TestClient, None, None]:
  """
  FastAPI TestClientフィクスチャ
  
  Returns:
    TestClient: テスト用クライアント
  """
  from app.main import app
  
  with TestClient(app) as client:
    yield client


@pytest.fixture
def mock_supabase_client() -> MagicMock:
  """
  Supabaseクライアントモック
  
  Returns:
    MagicMock: モックされたSupabaseクライアント
  """
  mock_client = MagicMock()
  
  # auth.sign_upメソッドのモック
  mock_client.auth.sign_up = AsyncMock(return_value={
    "user": {
      "id": "test-user-id",
      "email": "test@example.com"
    },
    "session": {
      "access_token": "test-access-token",
      "refresh_token": "test-refresh-token"
    }
  })
  
  # auth.sign_in_with_passwordメソッドのモック
  mock_client.auth.sign_in_with_password = AsyncMock(return_value={
    "user": {
      "id": "test-user-id",
      "email": "test@example.com"
    },
    "session": {
      "access_token": "test-access-token",
      "refresh_token": "test-refresh-token"
    }
  })
  
  # auth.get_userメソッドのモック
  mock_client.auth.get_user = AsyncMock(return_value={
    "user": {
      "id": "test-user-id",
      "email": "test@example.com"
    }
  })
  
  return mock_client


@pytest.fixture
def sample_audio_file() -> bytes:
  """
  テスト用音声ファイルデータ
  
  Returns:
    bytes: 音声ファイルバイナリデータ
  """
  # 小さなWAVファイルヘッダー (44バイト)
  return b'RIFF' + b'\x00' * 40


@pytest.fixture
def sample_transcription_response() -> dict:
  """
  テスト用文字起こし結果
  
  Returns:
    dict: 文字起こし結果のサンプルデータ
  """
  return {
    "id": "test-transcription-id",
    "audio_id": "test-audio-id",
    "user_id": "test-user-id",
    "text": "これはテストの文字起こし結果です。",
    "language": "ja",
    "duration": 10.5,
    "created_at": "2025-12-30T08:00:00Z"
  }
