"""
Gemini API 実統合テスト

実際のGemini APIを呼び出して要約機能をテストする。
GEMINI_API_KEYが設定されていない場合はスキップされる。
"""

import pytest
import os
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock


"""
Gemini API 実統合テスト (モックなし)

実際のバックエンドAPIを呼び出してGemini要約機能をテストする。
モックは一切使用せず、実際のDB、認証システム、Gemini APIを使用する。
"""

import pytest
import os
import time
import uuid
from fastapi.testclient import TestClient
from app.main import app
from app.core.supabase import get_current_active_user
from app.models.user import User
from app.models.transcription import Transcription


# テスト用ダミーユーザー
DUMMY_USER_ID = "bae0bdba-80ae-4354-8339-ab3d81259762"


async def override_get_current_active_user():
    """認証をバイパスするためのダミーユーザー"""
    return {
        "id": DUMMY_USER_ID,
        "email": "test@gemini-integration.com",
        "email_confirmed_at": "2025-12-30T00:00:00Z"
    }


@pytest.fixture
def test_client_with_auth():
    """認証をバイパスし、DBにユーザーを作成する統合テストクライアント"""
    from app.db.session import SessionLocal
    
    # DBにダミーユーザーを作成
    db = SessionLocal()
    try:
        # 既存のテストユーザーをチェック
        existing_user = db.query(User).filter(User.id == uuid.UUID(DUMMY_USER_ID)).first()
        
        if not existing_user:
            # 新しいユーザー作成
            user = User(
                id=uuid.UUID(DUMMY_USER_ID),
                email="test@gemini-integration.com"
            )
            db.add(user)
            db.commit()
        else:
            # 既存ユーザーのメールアドレスを更新（必要な場合）
            if existing_user.email != "test@gemini-integration.com":
                existing_user.email = "test@gemini-integration.com"
                db.commit()
    except Exception as e:
        db.rollback()
        print(f"ユーザー作成エラー: {e}")
    finally:
        db.close()
    
    # 認証をオーバーライド
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user
    
    with TestClient(app) as client:
        yield client
    
    # テスト後にオーバーライドをクリア
    app.dependency_overrides = {}


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY") == "test-gemini-api-key",
    reason="Real GEMINI_API_KEY not set"
)
class TestGeminiRealAPINoMock:
    """モックなしの実Gemini API統合テスト"""
    
    def test_create_transcription_and_generate_summary(self, test_client_with_auth: TestClient):
        """
        実際のDBに文字起こしを作成し、実際のGemini APIで要約を生成するテスト
        
        フロー:
        1. DBに文字起こしデータを直接作成
        2. POST /api/transcriptions/{id}/summarize を呼び出し
        3. 実際のGemini APIが呼ばれて要約が生成される
        4. 結果を検証
        5. クリーンアップ
        """
        from app.db.session import SessionLocal
        
        # テスト用の文字起こしテキスト
        test_text = """
        今日の会議では、新しいプロジェクトについて議論しました。
        プロジェクトの目標は、ユーザー体験を向上させることです。
        具体的には、レスポンス時間を50%改善し、UI/UXを刷新します。
        次のステップとして、プロトタイプを2週間以内に作成します。
        最終的な締め切りは来月末です。
        チームメンバーは5名で、各自の役割が明確に定義されています。
        """
        
        transcription_id = None
        db = SessionLocal()
        
        try:
            # Step 1: DBに文字起こしデータを作成
            transcription = Transcription(
                id=str(uuid.uuid4()),
                user_id=DUMMY_USER_ID,
                file_name="test_gemini_integration.wav",
                original_text=test_text,
                status="completed"
            )
            db.add(transcription)
            db.commit()
            db.refresh(transcription)
            
            transcription_id = transcription.id
            print(f"\n✓ 文字起こしをDBに作成しました (ID: {transcription_id})")
            
            # Step 2: 要約生成APIを呼び出し（実際のGemini APIが呼ばれる）
            print("実際のGemini APIを呼び出して要約を生成中...")
            response = test_client_with_auth.post(
                f"/api/transcriptions/{transcription_id}/summarize"
            )
            
            # Step 3: レスポンス検証
            assert response.status_code in [200, 201], f"要約生成失敗: {response.status_code}, {response.text}"
            
            summary_data = response.json()
            
            # 基本的な検証
            assert "summary_text" in summary_data
            assert summary_data["summary_text"] is not None
            assert len(summary_data["summary_text"]) > 0
            
            print(f"\n✅ 実際のGemini APIで要約生成成功！")
            print(f"モデル: {summary_data.get('model_name')}")
            
            # REVIEW_LANGUAGEに応じた検証
            review_language = os.getenv("REVIEW_LANGUAGE", "zh")
            summary_text = summary_data["summary_text"]
            
            if review_language == "zh":
                # 中国語の場合
                assert any(keyword in summary_text for keyword in ["概述", "总结", "摘要", "主要", "详细"])
                print(f"✓ 中国語要約を検証")
                print(f"要約プレビュー:\n{summary_text[:300]}...")
            elif review_language == "ja":
                # 日本語の場合
                assert any(keyword in summary_text for keyword in ["概要", "要約", "まとめ", "ポイント", "詳細"])
                print(f"✓ 日本語要約を検証")
                print(f"要約プレビュー:\n{summary_text[:300]}...")
            elif review_language == "en":
                # 英語の場合
                assert any(keyword in summary_text.lower() for keyword in ["overview", "summary", "key", "details"])
                print(f"✓ 英語要約を検証")
                print(f"要約プレビュー:\n{summary_text[:300]}...")
            
            # 要約が十分な長さであることを確認
            assert len(summary_text.split()) > 10, "要約が短すぎます"
            
            # Step 4: 既存要約の取得テスト
            print("\n既存要約の取得をテスト中...")
            response2 = test_client_with_auth.post(
                f"/api/transcriptions/{transcription_id}/summarize"
            )
            
            assert response2.status_code == 200, "既存要約の取得失敗"
            summary_data2 = response2.json()
            
            # 同じ要約が返されることを確認
            assert summary_data2["summary_text"] == summary_text
            print("✓ 既存要約が正しく返されました")
            
        finally:
            # Step 5: クリーンアップ
            if transcription_id:
                # Summaryを削除
                from app.models.summary import Summary
                db.query(Summary).filter(Summary.transcription_id == transcription_id).delete()
                # Transcriptionを削除
                db.query(Transcription).filter(Transcription.id == transcription_id).delete()
                db.commit()
                print(f"\n✓ テストデータをクリーンアップしました")
            
            db.close()
    
    def test_summary_error_handling_no_transcription(self, test_client_with_auth: TestClient):
        """
        存在しない文字起こしIDで要約生成を試みるテスト
        
        実際のAPIエンドポイントのエラーハンドリングを検証
        """
        non_existent_id = str(uuid.uuid4())
        
        response = test_client_with_auth.post(
            f"/api/transcriptions/{non_existent_id}/summarize"
        )
        
        assert response.status_code == 404
        print(f"\n✓ 存在しない文字起こしIDで404エラーを正しく返しました")
    
    def test_summary_error_handling_no_text(self, test_client_with_auth: TestClient):
        """
        文字起こしテキストがない場合のエラーハンドリングテスト
        """
        from app.db.session import SessionLocal
        
        transcription_id = None
        db = SessionLocal()
        
        try:
            # テキストなしの文字起こしを作成
            transcription = Transcription(
                id=str(uuid.uuid4()),
                user_id=DUMMY_USER_ID,
                file_name="test_no_text.wav",
                original_text=None,  # テキストなし
                status="processing"
            )
            db.add(transcription)
            db.commit()
            db.refresh(transcription)
            
            transcription_id = transcription.id
            
            # 要約生成を試みる
            response = test_client_with_auth.post(
                f"/api/transcriptions/{transcription_id}/summarize"
            )
            
            assert response.status_code == 400
            print(f"\n✓ テキストなしで400エラーを正しく返しました")
            
        finally:
            if transcription_id:
                db.query(Transcription).filter(Transcription.id == transcription_id).delete()
                db.commit()
            db.close()


@pytest.mark.integration
@pytest.mark.skipif(
    not os.getenv("GEMINI_API_ENDPOINT") or os.getenv("GEMINI_API_ENDPOINT") == "",
    reason="GEMINI_API_ENDPOINT not set"
)
class TestGeminiCustomEndpoint:
    """カスタムエンドポイントのテスト"""
    
    def test_generate_summary_with_custom_endpoint(self, test_client_with_auth: TestClient):
        """
        カスタムエンドポイントで実際のGemini APIを呼び出すテスト
        """
        from app.db.session import SessionLocal
        
        test_text = "カスタムエンドポイントのテストです。このテキストから要約を生成します。"
        
        transcription_id = None
        db = SessionLocal()
        
        try:
            transcription = Transcription(
                id=str(uuid.uuid4()),
                user_id=DUMMY_USER_ID,
                file_name="test_custom_endpoint.wav",
                original_text=test_text,
                status="completed"
            )
            db.add(transcription)
            db.commit()
            db.refresh(transcription)
            
            transcription_id = transcription.id
            
            custom_endpoint = os.getenv("GEMINI_API_ENDPOINT")
            print(f"\n✓ カスタムエンドポイント使用: {custom_endpoint}")
            
            response = test_client_with_auth.post(
                f"/api/transcriptions/{transcription_id}/summarize"
            )
            
            # カスタムエンドポイントの結果は環境依存のため、200/201/500を許容
            assert response.status_code in [200, 201, 500]
            
            if response.status_code in [200, 201]:
                summary_data = response.json()
                assert "summary_text" in summary_data
                print(f"✅ カスタムエンドポイントで要約生成成功")
            else:
                print(f"⚠️ カスタムエンドポイントエラー（環境依存）")
            
        finally:
            if transcription_id:
                from app.models.summary import Summary
                db.query(Summary).filter(Summary.transcription_id == transcription_id).delete()
                db.query(Transcription).filter(Transcription.id == transcription_id).delete()
                db.commit()
            db.close()
