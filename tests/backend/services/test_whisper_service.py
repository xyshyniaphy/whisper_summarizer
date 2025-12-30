"""
Whisper サービステスト (実プロセス版 - モックなし)

WhisperServiceクラスの音声処理ロジックを検証する。
実際のFFmpegとWhisper.cppバイナリを使用する。
"""

import pytest
import os
from pathlib import Path
from app.services.whisper_service import WhisperService, whisper_service


class TestWhisperServiceReal:
    """Whisperサービス実動作テストクラス"""
  
    def test_init_success(self) -> None:
        """
        WhisperServiceが正常に初期化されるテスト
        実際のバイナリとモデルファイルの存在を確認する。
        """
        service = WhisperService()
        assert service.binary == "/usr/local/bin/whisper-cli"
        assert os.path.exists(service.binary)
        assert os.path.exists(service.model)
  
  
    def test_convert_to_wav_success(self, tmp_path: Path, sample_audio_file: bytes) -> None:
        """
        音声ファイルがWAVに正常に変換されるテスト (実FFmpeg使用)
        """
        # 入力ファイル作成（conftest.pyのsample_audio_fileを使用）
        input_file = tmp_path / "test_input.wav"
        with open(input_file, "wb") as f:
            f.write(sample_audio_file)
            
        # 変換実行
        # sample_audio_fileは既にWAVだが、_convert_to_wavを通すことで
        # ffmpegが正常に動作し、指定のフォーマット(16kHzモノラル)に再エンコード/コピーされることを確認
        wav_path = whisper_service._convert_to_wav(str(input_file), str(tmp_path))
        
        assert wav_path.exists()
        assert wav_path.name == "test_input_converted.wav"
        assert wav_path.stat().st_size > 0
  
  
    def test_run_whisper_success(self, tmp_path: Path, sample_audio_file: bytes) -> None:
        """
        Whisper.cppが正常に実行されるテスト (実Whisperバイナリ使用)
        """
        # 16kHzモノラルWAVを用意
        # sample_audio_fileはconftestで16kHzモノラルWAVとして生成されている
        wav_file = tmp_path / "test_for_whisper.wav"
        with open(wav_file, "wb") as f:
            f.write(sample_audio_file)
            
        output_prefix = tmp_path / "whisper_output"
        
        # 実行
        # 無音ファイルなので、出力テキストは空 ("") かもしれないが、
        # プロセスが正常終了し、ファイルが生成されることを確認する
        result = whisper_service._run_whisper(str(wav_file), str(output_prefix))
        
        assert result.returncode == 0
        
        # 出力ファイル確認 (-otxt, -osrtを指定しているため)
        txt_path = Path(f"{str(output_prefix)}.txt")
        srt_path = Path(f"{str(output_prefix)}.srt")
        
        assert txt_path.exists()
        assert srt_path.exists()
  
  
    def test_parse_srt_real_file(self, tmp_path: Path) -> None:
        """
        実際のファイル書き込みを伴うSRT解析テスト
        """
        srt_content = "1\n00:00:00,000 --> 00:00:05,000\nこれはテストです。\n\n"
        srt_file = tmp_path / "test_real.srt"
        with open(srt_file, "w", encoding="utf-8") as f:
            f.write(srt_content)
            
        segments = whisper_service._parse_srt(srt_file)
        
        assert len(segments) == 1
        assert segments[0]["text"] == "これはテストです。"

