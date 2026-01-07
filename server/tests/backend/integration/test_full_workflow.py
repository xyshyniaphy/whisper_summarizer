"""
音声アップロードから文字起こし、削除までの完全なワークフローを検証する統合テスト

このテストはアップロードから削除までの基本的なワークフローを検証します。
テスト環境ではフェイクの音声データを使用します。
"""
import os
import pytest
from pathlib import Path
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.supabase import get_current_active_user

from app.models.user import User

# 認証をバイパスするためのダミーユーザー (UUID4形式)
DUMMY_USER_ID = str(uuid.uuid4())

async def override_get_current_active_user():
    return {
        "id": DUMMY_USER_ID,
        "email": "test@integration.com",
        "email_confirmed_at": "2025-12-30T00:00:00Z"
    }

@pytest.fixture
def test_client():
    """統合テスト用に認証をバイパスし、且つDBにユーザーを用意するクライアント"""
    global DUMMY_USER_ID
    from app.db.session import SessionLocal

    # DBにダミーユーザーを作成 (外部キー制約のため)
    db = SessionLocal()
    try:
        # 既存のテストユーザーを一旦削除（Nil UUID等の不整合を排除するため）
        db.query(User).filter(User.email == "test@integration.com").delete()
        db.commit()

        # 新しいUUID4でユーザー作成
        user = User(
            id=uuid.UUID(DUMMY_USER_ID),
            email="test@integration.com"
        )
        db.add(user)
        db.commit()
    finally:
        db.close()

    app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    with TestClient(app) as client:
        yield client
    # テスト後にオーバーライドをクリア
    app.dependency_overrides = {}

# テストデータのパス（元のテストファイルへの参照を保持）
TEST_AUDIO_FILE = Path(__file__).parent.parent.parent.parent / "testdata" / "audio1074124412.conved_2min.m4a"

class TestFullWorkflow:
    """音声処理の完全なワークフローテスト"""

    @pytest.mark.integration
    def test_full_transcription_workflow(self, test_client: TestClient):
        """
        音声アップロード → データ取得 → 削除の完全なフロー

        Note: This test uses fake audio data for test environment.
        In production with runner, it would process real audio files.
        """
        # Use fake audio content instead of real file
        fake_audio = b"fake audio content for testing"
        files = {'file': ('test_audio.wav', fake_audio, 'audio/wav')}

        # Step 1: 音声ファイルをアップロード
        response = test_client.post('/api/audio/upload', files=files)

        assert response.status_code == 201, f"アップロード失敗: {response.text}"
        upload_data = response.json()
        assert 'id' in upload_data, "idが返されていません"

        transcription_id = upload_data['id']
        print(f"\n✓ 音声ファイルをアップロードしました (ID: {transcription_id})")

        # Step 2: アップロードされたデータを取得
        response = test_client.get(f'/api/transcriptions/{transcription_id}')
        assert response.status_code == 200, f"取得失敗: {response.text}"

        transcription_result = response.json()
        assert transcription_result['id'] == transcription_id
        print(f"✓ 文字起こしデータを取得しました (stage: {transcription_result.get('stage', 'unknown')})")

        # Step 3: 文字起こしを削除
        response = test_client.delete(f'/api/transcriptions/{transcription_id}')
        assert response.status_code in [200, 204], f"削除失敗: {response.text}"
        print(f"✓ 文字起こしを削除しました")

        # Step 4: 削除されたことを確認
        response = test_client.get(f'/api/transcriptions/{transcription_id}')
        assert response.status_code == 404, "削除後にまだデータが残っています"
        print(f"✓ 削除されたことを確認しました")

    @pytest.mark.integration
    @pytest.mark.skip(reason="Requires real audio file and runner processing")
    @pytest.mark.slow
    def test_full_transcription_workflow_with_real_audio(self, test_client: TestClient):
        """
        実際の音声ファイルを使用した完全なワークフローテスト
        （テスト環境ではスキップされます）
        """
        # テストファイルの存在確認
        if not TEST_AUDIO_FILE.exists():
            pytest.skip(f"テストファイルが見つかりません: {TEST_AUDIO_FILE}")

        # Step 1: 音声ファイルをアップロード
        with open(TEST_AUDIO_FILE, 'rb') as audio_file:
            files = {'file': ('test_audio.m4a', audio_file, 'audio/mp4')}
            response = test_client.post('/api/audio/upload', files=files)

        assert response.status_code == 201, f"アップロード失敗: {response.text}"
        upload_data = response.json()
        assert 'id' in upload_data, "idが返されていません"

        transcription_id = upload_data['id']
        print(f"\n✓ 音声ファイルをアップロードしました (ID: {transcription_id})")

        # Step 2: 文字起こし完了を待機... (実際の処理には時間がかかります)
        # This would require the runner to be running
        print("✓ テストスキップ: ランナー処理が必要です")
