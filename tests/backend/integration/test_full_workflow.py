"""
音声アップロードから文字起こし、削除までの完全なワークフローを検証する統合テスト

このテストは実際のWhisper.cppを使用して文字起こしを実行します。
"""
import os
import time
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

# テストデータのパス
TEST_AUDIO_FILE = Path(__file__).parent.parent.parent.parent / "testdata" / "audio1074124412.conved_2min.m4a"

class TestFullWorkflow:
    """音声処理の完全なワークフローテスト"""
    
    @pytest.mark.skip(reason="Test audio file not available in test environment")
    @pytest.mark.integration
    @pytest.mark.slow
    def test_full_transcription_workflow(self, test_client: TestClient):
        """
        音声アップロード → 文字起こし → 結果検証 → 削除の完全なフロー
        
        1. テスト音声ファイルをアップロード
        2. 文字起こし完了を待機（最大5分）
        3. 文字起こし結果が10バイト以上であることを検証
        4. 文字起こしを削除
        """
        # テストファイルの存在確認
        assert TEST_AUDIO_FILE.exists(), f"テストファイルが見つかりません: {TEST_AUDIO_FILE}"
        
        # Step 1: 音声ファイルをアップロード
        with open(TEST_AUDIO_FILE, 'rb') as audio_file:
            files = {'file': ('test_audio.m4a', audio_file, 'audio/mp4')}
            response = test_client.post('/api/audio/upload', files=files)
        
        assert response.status_code == 201, f"アップロード失敗: {response.text}"
        upload_data = response.json()
        assert 'id' in upload_data, "idが返されていません"
        
        transcription_id = upload_data['id']
        print(f"\n✓ 音声ファイルをアップロードしました (ID: {transcription_id})")
        
        # Step 2: 文字起こし完了を待機
        max_wait_time = 300  # 最大5分
        poll_interval = 5    # 5秒ごとにポーリング
        elapsed_time = 0
        transcription_result = None
        
        print("文字起こし処理を待機中...")
        while elapsed_time < max_wait_time:
            # 文字起こしリストを取得
            response = test_client.get('/api/transcriptions')
            assert response.status_code == 200, f"リスト取得失敗: {response.text}"
            
            transcriptions = response.json()
            # 該当する文字起こしを検索
            for trans in transcriptions:
                if trans['id'] == transcription_id:
                    transcription_result = trans
                    break
            
            # 完了チェック
            if transcription_result and transcription_result.get('status') == 'completed':
                print(f"✓ 文字起こしが完了しました ({elapsed_time}秒経過)")
                break
            
            # 失敗チェック
            if transcription_result and transcription_result.get('status') == 'failed':
                pytest.fail(f"文字起こしが失敗しました: {transcription_result.get('error_message', '不明なエラー')}")
            
            time.sleep(poll_interval)
            elapsed_time += poll_interval
            
            if elapsed_time % 30 == 0:  # 30秒ごとに進捗を表示
                status = transcription_result.get('status', 'unknown') if transcription_result else 'not found'
                print(f"  {elapsed_time}秒経過... (ステータス: {status})")
        
        # タイムアウトチェック
        assert transcription_result is not None, "文字起こし結果が見つかりません"
        assert transcription_result.get('status') == 'completed', \
            f"文字起こしがタイムアウトしました ({elapsed_time}秒経過、ステータス: {transcription_result.get('status')})"
        
        # Step 3: 文字起こし結果の検証
        # レスポンスの内容をデバッグ出力
        print(f"\nレスポンス内容: {transcription_result}")
        
        # 正しいフィールド名を使用（original_textまたはtextなど）
        transcribed_text = (
            transcription_result.get('transcribed_text') or 
            transcription_result.get('original_text') or 
            transcription_result.get('text') or 
            ''
        )
        assert transcribed_text, f"文字起こしテキストが空です。レスポンス: {transcription_result}"
        
        text_length = len(transcribed_text.encode('utf-8'))
        assert text_length > 10, f"文字起こし結果が短すぎます: {text_length}バイト"
        
        print(f"✓ 文字起こし結果を検証しました ({text_length}バイト)")
        print(f"  テキストプレビュー: {transcribed_text[:100]}...")
        
        # Step 4: 文字起こしを削除
        response = test_client.delete(f'/api/transcriptions/{transcription_id}')
        assert response.status_code == 204, f"削除失敗: {response.text}"
        
        print(f"✓ 文字起こしを削除しました (ID: {transcription_id})")
        
        # 削除確認
        response = test_client.get('/api/transcriptions')
        assert response.status_code == 200
        transcriptions = response.json()
        
        # 削除された文字起こしが存在しないことを確認
        for trans in transcriptions:
            assert trans['id'] != transcription_id, "削除したはずの文字起こしがまだ存在します"
        
        print("✓ 削除を確認しました")
        print("\n=== テスト完了 ===")
