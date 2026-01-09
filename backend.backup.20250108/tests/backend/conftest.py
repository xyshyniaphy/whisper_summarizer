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


# ============================================================================
# Database Initialization
# ============================================================================

@pytest.fixture(scope="session", autouse=True)
def init_test_database():
    """
    Initialize database tables for tests.
    This runs once at the beginning of the test session.
    """
    from app.db.base_class import Base
    from app.db.session import engine

    # Create all tables
    Base.metadata.create_all(bind=engine)
    yield
    # Optional: drop tables after tests (commented out to keep data for inspection)
    # Base.metadata.drop_all(bind=engine)


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
def real_auth_user() -> dict:
    """
    実テスト用のユーザー情報フィクスチャ
    """
    import uuid
    uid = uuid.uuid4()
    return {
        "id": str(uid),
        "email": f"test-real-{str(uid)[:8]}@example.com",
        "raw_uuid": uid
    }


@pytest.fixture
def real_auth_client(real_auth_user: dict) -> Generator[TestClient, None, None]:
    """
    実DBと認証バイパスを使用したTestClient
    
    DBにテストユーザーを作成し、認証をそのユーザーでバイパスする。
    テスト終了後にユーザーと関連データを削除する。
    """
    from app.main import app
    from app.core.supabase import get_current_active_user
    from app.db.session import SessionLocal
    from app.models.user import User
    from app.models.transcription import Transcription
    from app.models.summary import Summary

    async def override_auth():
        return {
            "id": real_auth_user["id"],
            "email": real_auth_user["email"],
            "email_confirmed_at": "2025-01-01T00:00:00Z"
        }

    # ユーザー作成
    db = SessionLocal()
    try:
        user = User(id=real_auth_user["raw_uuid"], email=real_auth_user["email"])
        db.add(user)
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()

    app.dependency_overrides[get_current_active_user] = override_auth

    with TestClient(app) as client:
        yield client

    # クリーンアップ
    app.dependency_overrides = {}
    db = SessionLocal()
    try:
        # 関連データの削除
        db.query(Summary).filter(Summary.transcription_id.in_(
            db.query(Transcription.id).filter(Transcription.user_id == real_auth_user["id"])
        )).delete(synchronize_session=False)
        db.query(Transcription).filter(Transcription.user_id == real_auth_user["id"]).delete(synchronize_session=False)
        db.query(User).filter(User.id == real_auth_user["raw_uuid"]).delete()
        db.commit()
    except Exception:
        db.rollback()
    finally:
        db.close()


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
    テスト用音声ファイルデータ（有効な1秒間の無音WAVファイル）
    
    Returns:
        bytes: 音声ファイルバイナリデータ
    """
    import wave
    import io
    
    with io.BytesIO() as buffer:
        with wave.open(buffer, 'wb') as wav_file:
            # モノラル, 16bit, 16kHz
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(16000)
            # 1秒分の無音データ (16000フレーム * 2バイト)
            wav_file.writeframes(b'\x00' * 32000)
        return buffer.getvalue()


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


@pytest.fixture
def db_session() -> Generator:
  """
  テスト用データベースセッション

  Returns:
    Session: SQLAlchemy セッション
  """
  from app.db.session import SessionLocal

  db = SessionLocal()
  try:
    yield db
  finally:
    db.close()
