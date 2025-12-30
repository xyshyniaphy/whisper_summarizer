"""
Whisper サービステスト

WhisperServiceクラスの音声処理ロジックを検証する。
"""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import subprocess
from app.services.whisper_service import WhisperService


class TestWhisperService:
  """Whisperサービステストクラス"""
  
  @pytest.fixture
  def whisper_service(self) -> WhisperService:
    """
    WhisperServiceインスタンスフィクスチャ
    
    Returns:
      WhisperService: テスト用サービスインスタンス
    """
    # ファイル存在チェックをモック
    with patch("os.path.exists", return_value=True):
      return WhisperService()
  
  
  def test_init_success(self, whisper_service: WhisperService) -> None:
    """
    WhisperServiceが正常に初期化されるテスト
    
    Args:
      whisper_service: WhisperServiceインスタンス
    """
    assert whisper_service.binary == "/usr/local/bin/whisper-cli"
    assert whisper_service.model == "/usr/local/share/whisper-models/ggml-large-v3-turbo.bin"
    assert whisper_service.language in ["ja", "zh", "en"]
  
  
  def test_init_missing_binary(self) -> None:
    """
    バイナリが見つからない場合にエラーが発生するテスト
    """
    with patch("os.path.exists", side_effect=[False, True]):
      with pytest.raises(FileNotFoundError, match="Whisper.cppバイナリが見つかりません"):
        WhisperService()
  
  
  def test_convert_to_wav_success(self, whisper_service: WhisperService, tmp_path: Path) -> None:
    """
    音声ファイルがWAVに正常に変換されるテスト
    
    Args:
      whisper_service: WhisperServiceインスタンス
      tmp_path: Pytestの一時ディレクトリ
    """
    input_file = tmp_path / "test.m4a"
    input_file.touch()
    
    mock_result = MagicMock()
    mock_result.returncode = 0
    
    with patch("subprocess.run", return_value=mock_result):
      wav_path = whisper_service._convert_to_wav(str(input_file), str(tmp_path))
      
      assert wav_path.name == "test_converted.wav"
      assert str(tmp_path) in str(wav_path)
  
  
  def test_convert_to_wav_ffmpeg_error(self, whisper_service: WhisperService, tmp_path: Path) -> None:
    """
    FFmpeg変換エラーが正しく処理されるテスト
    
    Args:
      whisper_service: WhisperServiceインスタンス
      tmp_path: Pytestの一時ディレクトリ
    """
    input_file = tmp_path / "test.m4a"
    input_file.touch()
    
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stderr = "FFmpeg error"
    mock_result.check_returncode.side_effect = subprocess.CalledProcessError(1, "ffmpeg", stderr="FFmpeg error")
    
    with patch("subprocess.run", return_value=mock_result):
      with pytest.raises(Exception, match="音声変換エラー"):
        whisper_service._convert_to_wav(str(input_file), str(tmp_path))
  
  
  def test_run_whisper_success(self, whisper_service: WhisperService, tmp_path: Path) -> None:
    """
    Whisper.cppが正常に実行されるテスト
    
    Args:
      whisper_service: WhisperServiceインスタンス
      tmp_path: Pytestの一時ディレクトリ
    """
    wav_file = tmp_path / "test.wav"
    wav_file.touch()
    output_prefix = tmp_path / "output"
    
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Whisper output"
    mock_result.stderr = ""
    
    with patch("subprocess.run", return_value=mock_result):
      result = whisper_service._run_whisper(str(wav_file), str(output_prefix))
      
      assert result.returncode == 0
  
  
  def test_parse_srt_success(self, whisper_service: WhisperService, tmp_path: Path) -> None:
    """
    SRTファイルが正常に解析されるテスト
    
    Args:
      whisper_service: WhisperServiceインスタンス
      tmp_path: Pytestの一時ディレクトリ
    """
    srt_content = """1
00:00:00,000 --> 00:00:05,000
これはテストです。

2
00:00:05,000 --> 00:00:10,000
二番目のセグメントです。
"""
    
    srt_file = tmp_path / "test.srt"
    srt_file.write_text(srt_content, encoding="utf-8")
    
    segments = whisper_service._parse_srt(srt_file)
    
    assert len(segments) == 2
    assert segments[0]["start"] == "00:00:00,000"
    assert segments[0]["end"] == "00:00:05,000"
    assert segments[0]["text"] == "これはテストです。"
    assert segments[1]["start"] == "00:00:05,000"
    assert segments[1]["end"] == "00:00:10,000"
    assert segments[1]["text"] == "二番目のセグメントです。"
  
  
  def test_parse_output_success(self, whisper_service: WhisperService, tmp_path: Path) -> None:
    """
    出力ファイルが正常に解析されるテスト
    
    Args:
      whisper_service: WhisperServiceインスタンス
      tmp_path: Pytestの一時ディレクトリ
    """
    output_prefix = tmp_path / "output"
    
    # テキストファイル作成
    txt_file = Path(f"{output_prefix}.txt")
    txt_file.write_text("これは全文テキストです。", encoding="utf-8")
    
    # SRTファイル作成
    srt_content = """1
00:00:00,000 --> 00:00:05,000
これは全文テキストです。
"""
    srt_file = Path(f"{output_prefix}.srt")
    srt_file.write_text(srt_content, encoding="utf-8")
    
    result = whisper_service._parse_output(str(output_prefix))
    
    assert result["text"] == "これは全文テキストです。"
    assert result["language"] in ["ja", "zh", "en"]
    assert len(result["segments"]) == 1
    assert result["segments"][0]["text"] == "これは全文テキストです。"
