"""
ダウンロードAPI エンドポイントテスト

文字起こし結果（TXT, SRT）のダウンロード機能を検証する。
実DBと実ファイル操作を行う統合テスト。
"""

import pytest
import uuid
import os
from pathlib import Path
from fastapi.testclient import TestClient
from app.models.transcription import Transcription
from app.db.session import SessionLocal

# テキスト出力ディレクトリ（Docker内パス）
OUTPUT_DIR = Path("/app/data/output")

@pytest.mark.integration
class TestDownloadAPI:
    """ダウンロードAPI統合テスト"""

    def setup_transcription_with_file(self, user_id: str, format: str = "txt") -> str:
        """テスト用の文字起こしデータと物理ファイルを作成するヘルパー"""
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        
        try:
            # DBデータ作成
            transcription = Transcription(
                id=trans_id,
                user_id=user_id,
                file_name=f"test_download_{trans_id}.wav",
                original_text="This is test content.",
                status="completed"
            )
            db.add(transcription)
            db.commit()
            
            # 物理ファイル作成
            if not OUTPUT_DIR.exists():
                OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
                
            file_path = OUTPUT_DIR / f"{trans_id}.{format}"
            with open(file_path, "w") as f:
                f.write("This is test content content.")
                
            return trans_id
        finally:
            db.close()

    def teardown_transcription(self, trans_id: str):
        """テストデータのクリーンアップ"""
        db = SessionLocal()
        try:
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
        finally:
            db.close()
            
        # ファイル削除
        for ext in ["txt", "srt"]:
            file_path = OUTPUT_DIR / f"{trans_id}.{ext}"
            if file_path.exists():
                file_path.unlink()

    def test_download_txt_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """TXTファイルのダウンロード成功テスト"""
        trans_id = self.setup_transcription_with_file(real_auth_user["id"], "txt")
        try:
            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download?format=txt")
            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/plain")
            assert f"test_download_{trans_id}.txt" in response.headers["content-disposition"]
        finally:
            self.teardown_transcription(trans_id)

    def test_download_srt_success(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """SRTファイルのダウンロード成功テスト"""
        trans_id = self.setup_transcription_with_file(real_auth_user["id"], "srt")
        try:
            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download?format=srt")
            assert response.status_code == 200
            # SRTもtext/plainとして返される実装になっているか確認
            assert "text/plain" in response.headers["content-type"]
            assert f"test_download_{trans_id}.srt" in response.headers["content-disposition"]
        finally:
            self.teardown_transcription(trans_id)

    def test_download_not_found_db(self, real_auth_client: TestClient) -> None:
        """存在しないID（DBなし）での404テスト"""
        non_existent = str(uuid.uuid4())
        response = real_auth_client.get(f"/api/transcriptions/{non_existent}/download")
        assert response.status_code == 404
        assert "文字起こしが見つかりません" in response.json()["detail"]

    def test_download_not_found_file(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """DBにはあるがファイルがない場合の404テスト"""
        # ファイルを作成せずにDBデータのみ作成（ヘルパーを少し改変するか、手動で作る）
        db = SessionLocal()
        trans_id = str(uuid.uuid4())
        try:
            transcription = Transcription(
                id=trans_id,
                user_id=real_auth_user["id"],
                file_name="test_no_file.wav",
                status="completed"
            )
            db.add(transcription)
            db.commit()
            
            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download")
            assert response.status_code == 404
            assert "ファイルが見つかりません" in response.json()["detail"]
            
        finally:
            db.query(Transcription).filter(Transcription.id == trans_id).delete()
            db.commit()
            db.close()

    def test_download_invalid_format(self, real_auth_client: TestClient, real_auth_user: dict) -> None:
        """無効なフォーマット指定での422エラーテスト"""
        # FastAPIのQuery validationにより422になるはず
        trans_id = self.setup_transcription_with_file(real_auth_user["id"], "txt")
        try:
            response = real_auth_client.get(f"/api/transcriptions/{trans_id}/download?format=exe")
            assert response.status_code == 422
        finally:
            self.teardown_transcription(trans_id)
