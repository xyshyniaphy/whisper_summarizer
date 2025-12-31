"""
Whisper.cpp 音声処理サービス
バックエンドからWhisper.cppバイナリを直接呼び出し
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional, Dict, List
import logging

logger = logging.getLogger(__name__)

# Whisper.cppバイナリのパス
WHISPER_BINARY = "/usr/local/bin/whisper-cli"
WHISPER_MODEL = "/usr/local/share/whisper-models/ggml-large-v3-turbo.bin"

# Import settings for language and threads configuration
from app.core.config import settings
WHISPER_LANGUAGE = settings.WHISPER_LANGUAGE
WHISPER_THREADS = str(settings.WHISPER_THREADS)


class WhisperService:
    """Whisper.cpp音声処理サービス"""
    
    def __init__(self):
        self.binary = WHISPER_BINARY
        self.model = WHISPER_MODEL
        self.language = WHISPER_LANGUAGE
        self.threads = WHISPER_THREADS
        
        # バイナリとモデルの存在確認
        if not os.path.exists(self.binary):
            raise FileNotFoundError(f"Whisper.cppバイナリが見つかりません: {self.binary}")
        if not os.path.exists(self.model):
            raise FileNotFoundError(f"Whisperモデルが見つかりません: {self.model}")

    def _get_audio_duration(self, audio_file_path: str) -> int:
        """
        Get audio duration in seconds using ffprobe.

        Args:
            audio_file_path: Path to audio file

        Returns:
            Duration in seconds (0 if unable to determine)
        """
        cmd = [
            "ffprobe",
            "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            audio_file_path
        ]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            duration = float(result.stdout.strip())
            logger.info(f"Audio duration: {duration:.2f} seconds ({duration/3600:.2f} hours)")
            return int(duration)
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, ValueError) as e:
            logger.warning(f"Failed to get audio duration: {e}, will use default timeout")
            return 0

    def _calculate_timeout(self, duration_seconds: int) -> int:
        """
        Calculate timeout based on audio duration.

        Whisper typically processes at 0.3x - 0.7x real-time speed depending on hardware.
        Using 2x multiplier provides safety margin for slower systems.

        Args:
            duration_seconds: Audio duration in seconds

        Returns:
            Timeout in seconds (minimum 300 for short files)
        """
        MINIMUM_TIMEOUT = 300  # 5 minutes for very short files
        MULTIPLIER = 2  # Safety multiplier

        if duration_seconds <= 0:
            return MINIMUM_TIMEOUT

        calculated_timeout = duration_seconds * MULTIPLIER + MINIMUM_TIMEOUT

        # Log for user visibility
        hours = duration_seconds / 3600
        timeout_hours = calculated_timeout / 3600
        logger.info(
            f"Timeout calculation: {hours:.2f}h audio → {timeout_hours:.2f}h timeout "
            f"({calculated_timeout}s)"
        )

        return calculated_timeout
    
    def transcribe(
        self,
        audio_file_path: str,
        output_dir: Optional[str] = None
    ) -> Dict[str, any]:
        """
        音声ファイルを文字起こし
        
        Args:
            audio_file_path: 音声ファイルのパス
            output_dir: 出力ディレクトリ (省略時は一時ディレクトリ)
        
        Returns:
            transcription: {
                "text": "全文",
                "segments": [タイムスタンプ付きセグメント],
                "language": "ja"
            }
        """
        # 出力ディレクトリの設定
        if output_dir is None:
            output_dir = tempfile.mkdtemp()
        
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)
        
        # 出力ファイル名 (拡張子なし)
        audio_filename = Path(audio_file_path).stem
        output_prefix = output_path / audio_filename
        
        # Get audio duration and calculate dynamic timeout
        duration = self._get_audio_duration(audio_file_path)
        timeout = self._calculate_timeout(duration)

        # 音声ファイルをモノラル・16kHzに変換
        wav_path = self._convert_to_wav(audio_file_path, output_dir, timeout=min(timeout, 3600))

        try:
            # Whisper.cppを実行
            result = self._run_whisper(wav_path, str(output_prefix), timeout)
            
            # 結果ファイルを解析
            transcription = self._parse_output(str(output_prefix))
            
            return transcription
        
        finally:
            # 一時ファイルをクリーンアップ
            if wav_path.exists():
                wav_path.unlink()
    
    def _convert_to_wav(self, input_path: str, output_dir: str, timeout: int = 300) -> Path:
        """
        音声ファイルをモノラル・16kHz WAVに変換

        Args:
            input_path: 入力ファイルパス
            output_dir: 出力ディレクトリ
            timeout: Conversion timeout in seconds (default: 300)

        Returns:
            wav_path: 変換後のWAVファイルパス
        """
        wav_filename = Path(input_path).stem + "_converted.wav"
        wav_path = Path(output_dir) / wav_filename
        
        ffmpeg_cmd = [
            "ffmpeg",
            "-i", input_path,
            "-ar", "16000",  # 16kHz
            "-ac", "1",      # モノラル
            "-c:a", "pcm_s16le",  # 16-bit PCM
            "-y",
            str(wav_path)
        ]
        
        print(f"DEBUG: Running ffmpeg command: {ffmpeg_cmd}", flush=True)

        
        try:
            logger.info(f"Converting audio: {input_path} -> {wav_path}")
            cmd_str = ' '.join(str(x) for x in ffmpeg_cmd)
            logger.info(f"Running FFmpeg command: {cmd_str}")
            
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg failed with code {result.returncode}")
                logger.error(f"FFmpeg STDERR:\n{result.stderr}")
                result.check_returncode()

            logger.info(f"音声変換完了: {wav_path}")
            return wav_path
        
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg変換エラー: {e.stderr}")
            raise Exception(f"音声変換エラー: {e.stderr}")
    
    def _run_whisper(self, wav_path: str, output_prefix: str, timeout: int = 600) -> subprocess.CompletedProcess:
        """
        Whisper.cppバイナリを実行

        Args:
            wav_path: WAVファイルパス
            output_prefix: 出力ファイルプレフィックス
            timeout: Transcription timeout in seconds (default: 600)

        Returns:
            result: subprocess実行結果
        """
        whisper_cmd = [
            self.binary,
            "-m", self.model,
            "-f", wav_path,
            "-l", self.language,
            "-t", self.threads,
            "-of", output_prefix,
            "-otxt",  # テキスト出力
            "-osrt",  # SRT出力 (タイムスタンプ)
        ]
        
        print(f"DEBUG: Running whisper command: {whisper_cmd}", flush=True)

        
        try:
            # Ensure all args are strings for logging
            cmd_str = ' '.join(str(x) for x in whisper_cmd)
            logger.info(f"Running Whisper command: {cmd_str}")
            result = subprocess.run(
                whisper_cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False  # Do not raise immediately to capture output
            )
            
            logger.info(f"Whisper finished with return code: {result.returncode}")
            if result.stdout:
                logger.info(f"Whisper STDOUT:\n{result.stdout}")
            if result.stderr:
                logger.warning(f"Whisper STDERR:\n{result.stderr}")
                
            result.check_returncode() # Now raise if failed
            
            logger.info(f"Whisper.cpp実行完了: {output_prefix}")
            return result
        
        except subprocess.CalledProcessError as e:
            logger.error(f"Whisper.cpp実行エラー: {e.stderr}")
            raise Exception(f"文字起こしエラー: {e.stderr}")
    
    def _parse_output(self, output_prefix: str) -> Dict[str, any]:
        """
        Whisper.cppの出力ファイルを解析
        
        Args:
            output_prefix: 出力ファイルプレフィックス
        
        Returns:
            transcription: 文字起こし結果
        """
        txt_file = Path(f"{output_prefix}.txt")
        srt_file = Path(f"{output_prefix}.srt")
        
        # テキスト全文を読み込み
        full_text = ""
        if txt_file.exists():
            with open(txt_file, "r", encoding="utf-8") as f:
                full_text = f.read().strip()
        
        # SRTファイルからタイムスタンプ付きセグメントを抽出
        segments = []
        if srt_file.exists():
            segments = self._parse_srt(srt_file)
        
        return {
            "text": full_text,
            "segments": segments,
            "language": self.language
        }
    
    def _parse_srt(self, srt_path: Path) -> List[Dict[str, str]]:
        """
        SRTファイルを解析してタイムスタンプ付きセグメントを抽出
        
        Args:
            srt_path: SRTファイルパス
        
        Returns:
            segments: [{"start": "00:00:00,000", "end": "00:00:05,000", "text": "..."}]
        """
        segments = []
        
        with open(srt_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        
        i = 0
        while i < len(lines):
            # インデックス行をスキップ
            if lines[i].strip().isdigit():
                i += 1
                
                # タイムスタンプ行
                if i < len(lines) and "-->" in lines[i]:
                    time_parts = lines[i].strip().split(" --> ")
                    start_time = time_parts[0]
                    end_time = time_parts[1]
                    i += 1
                    
                    # テキスト行
                    text_lines = []
                    while i < len(lines) and lines[i].strip():
                        text_lines.append(lines[i].strip())
                        i += 1
                    
                    segments.append({
                        "start": start_time,
                        "end": end_time,
                        "text": " ".join(text_lines)
                    })
            
            i += 1
        
        return segments


# シングルトンインスタンス
whisper_service = WhisperService()
