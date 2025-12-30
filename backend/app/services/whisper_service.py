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
WHISPER_LANGUAGE = os.getenv("WHISPER_LANGUAGE", "ja")
WHISPER_THREADS = os.getenv("WHISPER_THREADS", "4")


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
    
    async def transcribe(
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
        
        # 音声ファイルをモノラル・16kHzに変換
        wav_path = self._convert_to_wav(audio_file_path, output_dir)
        
        try:
            # Whisper.cppを実行
            result = await self._run_whisper(wav_path, str(output_prefix))
            
            # 結果ファイルを解析
            transcription = self._parse_output(str(output_prefix))
            
            return transcription
        
        finally:
            # 一時ファイルをクリーンアップ
            if wav_path.exists():
                wav_path.unlink()
    
    def _convert_to_wav(self, input_path: str, output_dir: str) -> Path:
        """
        音声ファイルをモノラル・16kHz WAVに変換
        
        Args:
            input_path: 入力ファイルパス
            output_dir: 出力ディレクトリ
        
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
        
        try:
            result = subprocess.run(
                ffmpeg_cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=True
            )
            logger.info(f"音声変換完了: {wav_path}")
            return wav_path
        
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg変換エラー: {e.stderr}")
            raise Exception(f"音声変換エラー: {e.stderr}")
    
    async def _run_whisper(self, wav_path: str, output_prefix: str) -> subprocess.CompletedProcess:
        """
        Whisper.cppバイナリを実行
        
        Args:
            wav_path: WAVファイルパス
            output_prefix: 出力ファイルプレフィックス
        
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
        
        try:
            result = subprocess.run(
                whisper_cmd,
                capture_output=True,
                text=True,
                timeout=600,
                check=True
            )
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
