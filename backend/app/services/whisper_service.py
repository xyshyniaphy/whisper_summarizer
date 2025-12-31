"""
Whisper.cpp 音声処理サービス
バックエンドからWhisper.cppバイナリを直接呼び出し
"""

import os
import subprocess
import tempfile
import re
import difflib
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Optional, Dict, List, Tuple
from threading import Event
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
        output_dir: Optional[str] = None,
        cancel_event: Optional[Event] = None,
        transcription_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        音声ファイルを文字起こし

        Args:
            audio_file_path: 音声ファイルのパス
            output_dir: 出力ディレクトリ (省略時は一時ディレクトリ)
            cancel_event: キャンセルシグナル (Event)
            transcription_id: 転写ID (PID追跡用)

        Returns:
            transcription: {
                "text": "全文",
                "segments": [タイムスタンプ付きセグメント],
                "language": "ja"
            }
        """
        # Check for cancellation immediately
        if cancel_event and cancel_event.is_set():
            logger.info("[CANCEL] Transcription cancelled before starting")
            raise Exception("Transcription cancelled")

        # Get audio duration first
        duration = self._get_audio_duration(audio_file_path)
        chunk_size_seconds = settings.CHUNK_SIZE_MINUTES * 60

        # Decide whether to use chunking
        use_chunking = (
            settings.ENABLE_CHUNKING and
            duration > chunk_size_seconds
        )

        if use_chunking:
            logger.info(f"Using chunked transcription for {duration}s audio (chunk size: {chunk_size_seconds}s)")
            return self.transcribe_with_chunking(audio_file_path, output_dir, cancel_event, transcription_id)
        else:
            logger.info(f"Using standard transcription for {duration}s audio")
            return self._transcribe_standard(audio_file_path, output_dir, cancel_event, transcription_id)
    
    def _transcribe_standard(
        self,
        audio_file_path: str,
        output_dir: Optional[str] = None,
        cancel_event: Optional[Event] = None,
        transcription_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Standard transcription without chunking (original implementation).

        Args:
            audio_file_path: 音声ファイルのパス
            output_dir: 出力ディレクトリ (省略時は一時ディレクトリ)
            cancel_event: キャンセルシグナル (Event)
            transcription_id: 転写ID (PID追跡用)

        Returns:
            transcription: 文字起こし結果
        """
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            logger.info("[CANCEL] Standard transcription cancelled before starting")
            raise Exception("Transcription cancelled")

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
        wav_path = self._convert_to_wav(audio_file_path, output_dir, timeout=min(timeout, 3600), cancel_event=cancel_event, transcription_id=transcription_id)

        try:
            # Check for cancellation before whisper
            if cancel_event and cancel_event.is_set():
                logger.info("[CANCEL] Standard transcription cancelled before whisper")
                raise Exception("Transcription cancelled")

            # Whisper.cppを実行
            result = self._run_whisper(wav_path, str(output_prefix), timeout, cancel_event, transcription_id)

            # 結果ファイルを解析
            transcription = self._parse_output(str(output_prefix))

            return transcription

        finally:
            # 一時ファイルをクリーンアップ
            if wav_path.exists():
                wav_path.unlink()
    
    def _convert_to_wav(
        self,
        input_path: str,
        output_dir: str,
        timeout: int = 300,
        cancel_event: Optional[Event] = None,
        transcription_id: Optional[str] = None
    ) -> Path:
        """
        音声ファイルをモノラル・16kHz WAVに変換

        Args:
            input_path: 入力ファイルパス
            output_dir: 出力ディレクトリ
            timeout: Conversion timeout in seconds (default: 300)
            cancel_event: キャンセルシグナル (Event)
            transcription_id: 転写ID (PID追跡用)

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

            # Use Popen for PID tracking and cancellation support
            process = subprocess.Popen(
                ffmpeg_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Track PID if transcription_id is provided
            if transcription_id:
                from app.services.transcription_processor import track_transcription_pid
                track_transcription_pid(transcription_id, process.pid)
                logger.info(f"[WHISPER] FFmpeg PID tracked: {process.pid} for transcription: {transcription_id}")

            try:
                stdout, stderr = process.communicate(timeout=timeout)

                if process.returncode != 0:
                    logger.error(f"FFmpeg failed with code {process.returncode}")
                    logger.error(f"FFmpeg STDERR:\n{stderr}")
                    raise subprocess.CalledProcessError(process.returncode, ffmpeg_cmd, stderr)

                logger.info(f"音声変換完了: {wav_path}")
                return wav_path

            except subprocess.TimeoutExpired:
                process.kill()
                raise Exception(f"FFmpeg conversion timeout after {timeout}s")

        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg変換エラー: {e.stderr}")
            raise Exception(f"音声変換エラー: {e.stderr}")
    
    def _run_whisper(
        self,
        wav_path: str,
        output_prefix: str,
        timeout: int = 600,
        cancel_event: Optional[Event] = None,
        transcription_id: Optional[str] = None
    ) -> subprocess.CompletedProcess:
        """
        Whisper.cppバイナリを実行

        Args:
            wav_path: WAVファイルパス
            output_prefix: 出力ファイルプレフィックス
            timeout: Transcription timeout in seconds (default: 600)
            cancel_event: キャンセルシグナル (Event)
            transcription_id: 転写ID (PID追跡用)

        Returns:
            result: subprocess実行結果
        """
        # Check for cancellation
        if cancel_event and cancel_event.is_set():
            logger.info("[CANCEL] Whisper cancelled before starting")
            raise Exception("Transcription cancelled")

        # Get file size for logging
        wav_size_mb = Path(wav_path).stat().st_size / (1024 * 1024)

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

        cmd_str = ' '.join(str(x) for x in whisper_cmd)

        # Prominent logging before execution
        logger("=" * 80)
        logger.info(f"[WHISPER START] Starting transcription")
        logger.info(f"[WHISPER] Input file: {wav_path} ({wav_size_mb:.2f} MB)")
        logger.info(f"[WHISPER] Output prefix: {output_prefix}")
        logger.info(f"[WHISPER] Model: {self.model}")
        logger.info(f"[WHISPER] Language: {self.language}")
        logger.info(f"[WHISPER] Threads: {self.threads}")
        logger.info(f"[WHISPER] Timeout: {timeout}s")
        logger.info(f"[WHISPER] Command: {cmd_str}")
        logger.info(f"[WHISPER] Transcription ID: {transcription_id}")
        logger("=" * 80)

        # Also print to stdout for immediate visibility
        print(f"\n{'='*80}", flush=True)
        print(f"[WHISPER] Starting transcription...", flush=True)
        print(f"[WHISPER] Input: {wav_path} ({wav_size_mb:.2f} MB)", flush=True)
        print(f"{'='*80}\n", flush=True)

        try:
            # Use Popen for PID tracking and cancellation support
            process = subprocess.Popen(
                whisper_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            # Track PID if transcription_id is provided
            if transcription_id:
                from app.services.transcription_processor import track_transcription_pid
                track_transcription_pid(transcription_id, process.pid)
                logger.info(f"[WHISPER] Whisper PID tracked: {process.pid} for transcription: {transcription_id}")

            try:
                stdout, stderr = process.communicate(timeout=timeout)

                # Create a CompletedProcess-like result
                class CompletedProcess:
                    def __init__(self, returncode, stdout, stderr):
                        self.returncode = returncode
                        self.stdout = stdout
                        self.stderr = stderr

                result = CompletedProcess(process.returncode, stdout, stderr)

                # Log completion status
                logger.info(f"[WHISPER] Process finished with return code: {result.returncode}")

                # Log stdout (whisper progress and results)
                if result.stdout:
                    logger.info(f"[WHISPER STDOUT]\n{result.stdout}")
                    # Also print progress to console
                    for line in result.stdout.split('\n'):
                        if line.strip():
                            print(f"[WHISPER] {line}", flush=True)

                # Log stderr (whisper warnings and errors)
                if result.stderr:
                    logger.info(f"[WHISPER STDERR]\n{result.stderr}")
                    # Also print to console
                    for line in result.stderr.split('\n'):
                        if line.strip():
                            print(f"[WHISPER] {line}", flush=True)

                # Check output files
                txt_file = Path(f"{output_prefix}.txt")
                srt_file = Path(f"{output_prefix}.srt")

                logger.info(f"[WHISPER] Output files check:")
                if txt_file.exists():
                    txt_size_kb = txt_file.stat().st_size / 1024
                    with open(txt_file, 'r') as f:
                        txt_preview = f.read(200)
                    logger.info(f"[WHISPER]   ✓ TXT: {txt_file.name} ({txt_size_kb:.2f} KB)")
                    logger.info(f"[WHISPER]   Preview: {txt_preview[:100]}...")
                else:
                    logger.warning(f"[WHISPER]   ✗ TXT not found: {txt_file}")

                if srt_file.exists():
                    srt_size_kb = srt_file.stat().st_size / 1024
                    logger.info(f"[WHISPER]   ✓ SRT: {srt_file.name} ({srt_size_kb:.2f} KB)")
                else:
                    logger.warning(f"[WHISPER]   ✗ SRT not found: {srt_file}")

                # Check if command succeeded
                if result.returncode != 0:
                    logger.error(f"[WHISPER ERROR] Command failed with exit code {result.returncode}")
                    logger.error(f"[WHISPER ERROR] Full stderr: {result.stderr}")
                    raise Exception(
                        f"Whisper transcription failed (exit code {result.returncode}): {result.stderr}"
                    )

                logger("=" * 80)
                logger.info(f"[WHISPER SUCCESS] Transcription completed successfully")
                logger("=" * 80)
                print(f"\n{'='*80}", flush=True)
                print(f"[WHISPER] Transcription completed successfully!", flush=True)
                print(f"{'='*80}\n", flush=True)

                return result

            except subprocess.TimeoutExpired:
                process.kill()
                logger.error(f"[WHISPER TIMEOUT] Process timed out after {timeout}s")
                print(f"\n[WHISPER ERROR] Transcription timed out after {timeout}s\n", flush=True)
                raise Exception(f"Whisper transcription timed out after {timeout} seconds")
        
        except Exception as e:
            logger.error(f"[WHISPER ERROR] Unexpected error: {type(e).__name__}: {e}")
            if hasattr(e, 'stderr') and e.stderr:
                logger.error(f"[WHISPER ERROR] stderr: {e.stderr}")
            print(f"\n[WHISPER ERROR] {type(e).__name__}: {e}\n", flush=True)
            raise
    
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

    # ========================================================================
    # Audio Chunking Methods (for faster transcription of long audio)
    # ========================================================================
    
    def transcribe_with_chunking(
        self,
        audio_file_path: str,
        output_dir: Optional[str] = None,
        cancel_event: Optional[Event] = None,
        transcription_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Transcribe audio using chunking strategy for faster processing.

        Splits audio into chunks, processes them in parallel, and merges results.

        Args:
            audio_file_path: 音声ファイルのパス
            output_dir: 出力ディレクトリ
            cancel_event: キャンセルシグナル (Event)
            transcription_id: 転写ID (PID追跡用)

        Returns:
            transcription: Merged transcription result
        """
        # Check for cancellation immediately
        if cancel_event and cancel_event.is_set():
            logger.info("[CANCEL][CHUNKING] Chunked transcription cancelled before starting")
            raise Exception("Transcription cancelled")

        logger.info(f"[CHUNKING] Starting chunked transcription for: {audio_file_path}")
        print(f"\n[CHUNKING] Starting chunked transcription...", flush=True)

        if output_dir is None:
            output_dir = tempfile.mkdtemp()

        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True, parents=True)

        # Convert to WAV first
        try:
            wav_path = self._convert_to_wav(audio_file_path, output_dir, cancel_event=cancel_event, transcription_id=transcription_id)
        except Exception as e:
            logger.error(f"[CHUNKING] Failed to convert to WAV: {e}")
            raise Exception(f"Audio conversion failed: {e}") from e

        try:
            # Check for cancellation after conversion
            if cancel_event and cancel_event.is_set():
                logger.info("[CANCEL][CHUNKING] Cancelled after conversion")
                raise Exception("Transcription cancelled")

            # Get audio duration
            duration = self._get_audio_duration(str(wav_path))

            logger.info(f"[CHUNKING] Audio duration: {duration}s ({duration/60:.1f} minutes)")
            print(f"[CHUNKING] Audio duration: {duration}s ({duration/60:.1f} minutes)", flush=True)

            # Split audio into chunks
            logger.info(f"[CHUNKING] Splitting audio into chunks...")
            print(f"[CHUNKING] Splitting audio into chunks...", flush=True)

            chunks_info = self._split_audio_into_chunks(
                str(wav_path),
                output_dir,
                duration
            )

            logger.info(f"[CHUNKING] Created {len(chunks_info)} chunks")
            print(f"[CHUNKING] Created {len(chunks_info)} chunks", flush=True)

            # Log chunk info
            for i, chunk in enumerate(chunks_info):
                logger.info(f"[CHUNKING]   Chunk {i}: {chunk['start_time']:.1f}s - {chunk['end_time']:.1f}s ({chunk['duration']:.1f}s)")

            # Transcribe chunks in parallel
            chunks_results = self._transcribe_chunks_parallel(chunks_info, output_dir, cancel_event, transcription_id)
            
            # Check for failed chunks
            failed_chunks = [i for i, r in enumerate(chunks_results) if "error" in r]
            if failed_chunks:
                logger.warning(f"[CHUNKING] Some chunks failed: {failed_chunks}")
                print(f"[CHUNKING] Warning: Chunks {failed_chunks} failed, will use partial results", flush=True)
            
            # Merge results
            logger.info(f"[CHUNKING] Merging results from {len(chunks_results)} chunks...")
            print(f"[CHUNKING] Merging results...", flush=True)
            
            merged = self._merge_chunk_results(chunks_results)
            
            # Log final result
            final_text_length = len(merged.get("text", ""))
            final_segment_count = len(merged.get("segments", []))
            
            logger.info(f"[CHUNKING] ✓ Merge complete: {final_text_length} chars, {final_segment_count} segments")
            print(f"[CHUNKING] ✓ Done: {final_text_length} characters transcribed", flush=True)
            
            return merged
            
        except Exception as e:
            logger.error(f"[CHUNKING] Transcription failed: {type(e).__name__}: {e}")
            print(f"[CHUNKING] ✗ Failed: {e}", flush=True)
            raise
        finally:
            # Cleanup converted wav
            if wav_path.exists():
                wav_path.unlink()
    
    def _split_audio_into_chunks(
        self,
        wav_path: str,
        output_dir: str,
        total_duration: int
    ) -> List[Dict[str, any]]:
        """
        Split audio into chunks, optionally using VAD for smart splitting.
        
        Args:
            wav_path: Input WAV file path
            output_dir: Output directory for chunks
            total_duration: Total audio duration in seconds
        
        Returns:
            List of chunk info dicts: [{
                "index": 0,
                "path": "/path/to/chunk_0.wav",
                "start_time": 0.0,
                "end_time": 600.0,
                "duration": 600.0
            }, ...]
        """
        chunk_size_seconds = settings.CHUNK_SIZE_MINUTES * 60
        overlap_seconds = settings.CHUNK_OVERLAP_SECONDS
        
        chunks_info = []
        current_time = 0
        chunk_index = 0
        
        if settings.USE_VAD_SPLIT:
            # Use VAD-based splitting
            silence_segments = self._detect_silence_segments(wav_path)
            split_points = self._calculate_split_points(
                total_duration,
                chunk_size_seconds,
                silence_segments
            )
            
            logger.info(f"VAD splitting: found {len(silence_segments)} silence regions, {len(split_points)} split points")
            
            # Create chunks based on calculated split points
            for i, split_point in enumerate(split_points):
                start_time = split_point["start"]
                end_time = split_point["end"]
                
                # Add overlap (except for first chunk)
                actual_start = max(0, start_time - overlap_seconds if i > 0 else 0)
                
                chunk_path = Path(output_dir) / f"chunk_{i:03d}.wav"
                self._extract_audio_segment(wav_path, str(chunk_path), actual_start, end_time)
                
                chunks_info.append({
                    "index": i,
                    "path": str(chunk_path),
                    "start_time": actual_start,
                    "end_time": end_time,
                    "duration": end_time - actual_start
                })
        else:
            # Simple fixed-length chunking
            while current_time < total_duration:
                end_time = min(current_time + chunk_size_seconds, total_duration)
                
                chunk_path = Path(output_dir) / f"chunk_{chunk_index:03d}.wav"
                self._extract_audio_segment(wav_path, str(chunk_path), current_time, end_time)
                
                chunks_info.append({
                    "index": chunk_index,
                    "path": str(chunk_path),
                    "start_time": current_time,
                    "end_time": end_time,
                    "duration": end_time - current_time
                })
                
                current_time = end_time
                chunk_index += 1
        
        logger.info(f"Created {len(chunks_info)} audio chunks")
        return chunks_info
    
    def _detect_silence_segments(self, wav_path: str) -> List[Tuple[float, float]]:
        """
        Detect silence segments in audio using FFmpeg silencedetect.
        
        Args:
            wav_path: Path to WAV file
        
        Returns:
            List of (start_time, end_time) tuples for silence segments
        """
        threshold = settings.VAD_SILENCE_THRESHOLD
        min_duration = settings.VAD_MIN_SILENCE_DURATION
        
        cmd = [
            "ffmpeg",
            "-i", wav_path,
            "-af", f"silencedetect=noise={threshold}dB:d={min_duration}",
            "-f", "null",
            "-"
        ]
        
        logger.info(f"Running VAD silence detection: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=300,
                check=False
            )
            
            # Parse silence timestamps from stderr
            silence_segments = []
            pattern = r'silence_start: ([\d.]+)|silence_end: ([\d.]+)'
            
            current_start = None
            for match in re.finditer(pattern, result.stderr):
                if match.group(1):  # silence_start
                    current_start = float(match.group(1))
                elif match.group(2) and current_start is not None:  # silence_end
                    silence_end = float(match.group(2))
                    silence_segments.append((current_start, silence_end))
                    current_start = None
            
            logger.info(f"Detected {len(silence_segments)} silence segments")
            return silence_segments
            
        except Exception as e:
            logger.warning(f"VAD detection failed: {e}, falling back to fixed splitting")
            return []
    
    def _calculate_split_points(
        self,
        total_duration: int,
        chunk_size: int,
        silence_segments: List[Tuple[float, float]]
    ) -> List[Dict[str, float]]:
        """
        Calculate optimal split points based on target chunk size and silence.
        
        Args:
            total_duration: Total audio duration
            chunk_size: Target chunk size in seconds
            silence_segments: List of (start, end) silence tuples
        
        Returns:
            List of {"start": float, "end": float} split points
        """
        split_points = []
        current_time = 0
        search_window = 60  # Search +/- 60 seconds for silence
        
        while current_time < total_duration:
            target_time = min(current_time + chunk_size, total_duration)
            
            # Find best silence point near target
            best_split = None
            best_distance = float('inf')
            
            for silence_start, silence_end in silence_segments:
                # Check if silence is within search window of target
                if abs(silence_start - target_time) <= search_window:
                    distance = abs(silence_start - target_time)
                    if distance < best_distance:
                        best_distance = distance
                        best_split = (silence_start, silence_end)
            
            if best_split:
                # Use silence midpoint for split
                split_time = (best_split[0] + best_split[1]) / 2
            else:
                # No silence found, use target time
                split_time = target_time
            
            split_points.append({
                "start": current_time,
                "end": split_time
            })
            
            current_time = split_time
        
        return split_points
    
    def _extract_audio_segment(
        self,
        input_path: str,
        output_path: str,
        start_time: float,
        end_time: float
    ) -> None:
        """
        Extract audio segment using FFmpeg.
        
        Args:
            input_path: Input file path
            output_path: Output file path
            start_time: Start time in seconds
            end_time: End time in seconds
        """
        duration = end_time - start_time
        
        cmd = [
            "ffmpeg",
            "-i", input_path,
            "-ss", str(start_time),
            "-t", str(duration),
            "-c", "copy",  # Copy without re-encoding for speed
            "-y",
            output_path
        ]
        
        try:
            subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                check=True
            )
            logger.debug(f"Extracted segment: {start_time}s - {end_time}s -> {output_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to extract segment: {e.stderr}")
            raise
    
    def _transcribe_chunks_parallel(
        self,
        chunks_info: List[Dict[str, any]],
        output_dir: str,
        cancel_event: Optional[Event] = None,
        transcription_id: Optional[str] = None
    ) -> List[Dict[str, any]]:
        """
        Transcribe multiple chunks in parallel using ThreadPoolExecutor.

        Args:
            chunks_info: List of chunk info dicts
            output_dir: Output directory
            cancel_event: キャンセルシグナル (Event)
            transcription_id: 転写ID (PID追跡用)

        Returns:
            List of transcription results (in chunk order)
        """
        max_workers = settings.MAX_CONCURRENT_CHUNKS
        total_chunks = len(chunks_info)

        results = [None] * total_chunks
        completed_count = 0
        failed_count = 0

        logger("=" * 80)
        logger.info(f"[PARALLEL TRANSCRIPTION] Starting {total_chunks} chunks with {max_workers} workers")
        print(f"\n{'='*80}", flush=True)
        print(f"[PARALLEL] Transcribing {total_chunks} chunks with {max_workers} workers...", flush=True)
        print(f"{'='*80}\n", flush=True)

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_chunk = {
                executor.submit(
                    self._transcribe_chunk,
                    chunk_info,
                    output_dir,
                    cancel_event,
                    transcription_id
                ): chunk_info for chunk_info in chunks_info
            }

            # Collect results as they complete
            for future in as_completed(future_to_chunk):
                chunk_info = future_to_chunk[future]
                chunk_index = chunk_info["index"]
                
                try:
                    result = future.result()
                    results[chunk_index] = result
                    completed_count += 1
                    
                    text_len = len(result.get('text', ''))
                    logger.info(f"[PARALLEL] Chunk {chunk_index}/{total_chunks} completed ({completed_count}/{total_chunks} done): {text_len} chars")
                    print(f"[PARALLEL] {completed_count}/{total_chunks} chunks completed (chunk {chunk_index} done)", flush=True)
                    
                except Exception as e:
                    failed_count += 1
                    logger.error(f"[PARALLEL] Chunk {chunk_index}/{total_chunks} FAILED: {e}")
                    print(f"[PARALLEL] Chunk {chunk_index} FAILED: {e}", flush=True)
                    
                    # Store error result
                    results[chunk_index] = {
                        "text": "",
                        "segments": [],
                        "language": self.language,
                        "error": str(e),
                        "chunk_index": chunk_index,
                        "chunk_start_time": chunk_info["start_time"],
                        "chunk_end_time": chunk_info["end_time"]
                    }
        
        logger("=" * 80)
        logger.info(f"[PARALLEL TRANSCRIPTION] Completed: {completed_count} succeeded, {failed_count} failed out of {total_chunks}")
        print(f"\n{'='*80}", flush=True)
        print(f"[PARALLEL] Done: {completed_count} succeeded, {failed_count} failed", flush=True)
        print(f"{'='*80}\n", flush=True)
        
        return results
    
    def _transcribe_chunk(
        self,
        chunk_info: Dict[str, any],
        output_dir: str,
        cancel_event: Optional[Event] = None,
        transcription_id: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Transcribe a single audio chunk.

        Args:
            chunk_info: Chunk info dict with path, start_time, etc.
            output_dir: Output directory
            cancel_event: キャンセルシグナル (Event)
            transcription_id: 転写ID (PID追跡用)

        Returns:
            Transcription result
        """
        # Check for cancellation before starting
        if cancel_event and cancel_event.is_set():
            logger.info(f"[CANCEL] Chunk {chunk_info['index']} cancelled before starting")
            return {"error": "Cancelled", "chunk_index": chunk_info["index"]}

        chunk_index = chunk_info["index"]
        chunk_path = chunk_info["path"]
        start_time = chunk_info["start_time"]

        logger.info(f"[CHUNK {chunk_index}] Starting transcription")
        logger.info(f"[CHUNK {chunk_index}]   Path: {chunk_path}")
        logger.info(f"[CHUNK {chunk_index}]   Start time: {start_time:.2f}s")
        logger.info(f"[CHUNK {chunk_index}]   Duration: {chunk_info['duration']:.2f}s")
        print(f"[CHUNK {chunk_index}] Transcribing... (start: {start_time:.1f}s)", flush=True)

        # Create output prefix for this chunk
        output_prefix = Path(output_dir) / f"chunk_{chunk_index:03d}"

        # Calculate timeout for this chunk
        chunk_duration = int(chunk_info["duration"])
        timeout = self._calculate_timeout(chunk_duration)

        try:
            # Run whisper on this chunk
            result = self._run_whisper(chunk_path, str(output_prefix), timeout, cancel_event, transcription_id)
            
            # Parse output
            transcription = self._parse_output(str(output_prefix))
            
            # Add offset to all segment timestamps
            if transcription["segments"]:
                for segment in transcription["segments"]:
                    segment["start"] = self._add_time_offset(segment["start"], start_time)
                    segment["end"] = self._add_time_offset(segment["end"], start_time)
            
            # Store chunk metadata for merging
            transcription["chunk_index"] = chunk_index
            transcription["chunk_start_time"] = start_time
            transcription["chunk_end_time"] = chunk_info["end_time"]
            
            text_length = len(transcription.get("text", ""))
            segment_count = len(transcription.get("segments", []))
            
            logger.info(f"[CHUNK {chunk_index}] ✓ Completed: {text_length} chars, {segment_count} segments")
            print(f"[CHUNK {chunk_index}] ✓ Done: {text_length} chars", flush=True)
            
            return transcription
            
        except Exception as e:
            logger.error(f"[CHUNK {chunk_index}] ✗ Failed: {type(e).__name__}: {e}")
            print(f"[CHUNK {chunk_index}] ✗ Failed: {e}", flush=True)
            # Re-raise with more context
            raise Exception(f"Chunk {chunk_index} transcription failed: {e}") from e
    
    def _add_time_offset(self, time_str: str, offset_seconds: float) -> str:
        """
        Add time offset to SRT timestamp string.
        
        Args:
            time_str: Timestamp in "HH:MM:SS,mmm" format
            offset_seconds: Offset to add in seconds
        
        Returns:
            New timestamp string with offset applied
        """
        # Parse SRT timestamp "00:01:23,456"
        match = re.match(r'(\d+):(\d+):(\d+),(\d+)', time_str)
        if not match:
            return time_str
        
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        milliseconds = int(match.group(4))
        
        total_ms = (hours * 3600000 + minutes * 60000 + seconds * 1000 + milliseconds)
        total_ms += int(offset_seconds * 1000)
        
        # Convert back
        total_ms = max(0, total_ms)
        new_hours = total_ms // 3600000
        total_ms %= 3600000
        new_minutes = total_ms // 60000
        total_ms %= 60000
        new_seconds = total_ms // 1000
        new_milliseconds = total_ms % 1000
        
        return f"{new_hours:02d}:{new_minutes:02d}:{new_seconds:02d},{new_milliseconds:03d}"
    
    def _merge_chunk_results(
        self,
        chunks_results: List[Dict[str, any]]
    ) -> Dict[str, any]:
        """
        Merge transcription results from multiple chunks.
        
        Uses LCS (Longest Common Subsequence) or timestamp-based strategy
        depending on MERGE_STRATEGY setting.
        
        Args:
            chunks_results: List of transcription results from chunks
        
        Returns:
            Merged transcription result
        """
        if not chunks_results:
            return {"text": "", "segments": [], "language": self.language}
        
        if len(chunks_results) == 1:
            return chunks_results[0]
        
        if settings.MERGE_STRATEGY == "lcs":
            return self._merge_with_lcs(chunks_results)
        else:
            return self._merge_with_timestamps(chunks_results)
    
    def _merge_with_timestamps(
        self,
        chunks_results: List[Dict[str, any]]
    ) -> Dict[str, any]:
        """
        Simple timestamp-based merging (may have duplicates at boundaries).
        
        Args:
            chunks_results: List of chunk transcriptions
        
        Returns:
            Merged transcription
        """
        overlap_seconds = settings.CHUNK_OVERLAP_SECONDS
        
        merged_text = []
        merged_segments = []
        
        for i, chunk in enumerate(chunks_results):
            if "error" in chunk:
                logger.warning(f"Skipping failed chunk {i}")
                continue
            
            # For text, add separator between chunks
            if merged_text and chunk.get("text"):
                merged_text.append(" ")
            if chunk.get("text"):
                merged_text.append(chunk["text"])
            
            # For segments, filter out overlap region (except first chunk)
            chunk_start = chunk.get("chunk_start_time", 0)
            for segment in chunk.get("segments", []):
                if i == 0:
                    # Keep all segments from first chunk
                    merged_segments.append(segment)
                else:
                    # For subsequent chunks, filter segments that start after overlap region
                    seg_start = self._parse_srt_time(segment["start"])
                    if seg_start >= (chunk_start + overlap_seconds):
                        merged_segments.append(segment)
        
        return {
            "text": "".join(merged_text).strip(),
            "segments": merged_segments,
            "language": self.language
        }
    
    def _merge_with_lcs(
        self,
        chunks_results: List[Dict[str, any]]
    ) -> Dict[str, any]:
        """
        Merge chunks using LCS (Longest Common Subsequence) for text alignment.
        
        This handles overlapping regions by finding matching text and deduplicating.
        
        Args:
            chunks_results: List of chunk transcriptions
        
        Returns:
            Merged transcription with deduplicated overlaps
        """
        overlap_seconds = settings.CHUNK_OVERLAP_SECONDS
        overlap_text_window = overlap_seconds + 5  # Extra buffer for text matching
        
        merged_text_parts = []
        merged_segments = []
        
        for i, chunk in enumerate(chunks_results):
            if "error" in chunk:
                logger.warning(f"Skipping failed chunk {i}")
                continue
            
            chunk_text = chunk.get("text", "")
            chunk_segments = chunk.get("segments", [])
            chunk_start = chunk.get("chunk_start_time", 0)
            
            if i == 0:
                # First chunk: use everything
                merged_text_parts.append(chunk_text)
                merged_segments.extend(chunk_segments)
            else:
                # Subsequent chunks: handle overlap
                previous_chunk = chunks_results[i - 1]
                prev_text = previous_chunk.get("text", "")
                
                # Extract overlap regions for text matching
                prev_overlap = self._extract_text_in_time_window(
                    previous_chunk,
                    chunk_start - overlap_text_window,
                    chunk_start + overlap_text_window
                )
                curr_overlap = self._extract_text_in_time_window(
                    chunk,
                    chunk_start,
                    chunk_start + overlap_text_window * 2
                )
                
                if prev_overlap and curr_overlap:
                    # Find LCS match
                    merged_text = self._merge_with_lcs_text(
                        prev_overlap,
                        curr_overlap,
                        merged_text_parts[-1] if merged_text_parts else "",
                        chunk_text
                    )
                    merged_text_parts.append(merged_text)
                else:
                    # No overlap detected, just append
                    if merged_text_parts:
                        merged_text_parts.append(" ")
                    merged_text_parts.append(chunk_text)
                
                # Filter segments to remove overlap duplicates
                for segment in chunk_segments:
                    seg_start = self._parse_srt_time(segment["start"])
                    # Only add segments that start after the overlap region
                    if seg_start >= (chunk_start + overlap_seconds / 2):
                        merged_segments.append(segment)
        
        return {
            "text": "".join(merged_text_parts).strip(),
            "segments": merged_segments,
            "language": self.language
        }
    
    def _extract_text_in_time_window(
        self,
        chunk_result: Dict[str, any],
        start_time: float,
        end_time: float
    ) -> str:
        """
        Extract text from segments within a time window.
        
        Args:
            chunk_result: Chunk transcription result
            start_time: Window start time in seconds
            end_time: Window end time in seconds
        
        Returns:
            Concatenated text from segments in the window
        """
        text_parts = []
        for segment in chunk_result.get("segments", []):
            seg_start = self._parse_srt_time(segment["start"])
            if start_time <= seg_start <= end_time:
                text_parts.append(segment["text"])
        return " ".join(text_parts)
    
    def _merge_with_lcs_text(
        self,
        prev_overlap: str,
        curr_overlap: str,
        prev_full: str,
        curr_full: str
    ) -> str:
        """
        Merge text using LCS to find and remove overlapping content.
        
        Args:
            prev_overlap: Text from previous chunk's overlap region
            curr_overlap: Text from current chunk's overlap region
            prev_full: Full text from previous chunk
            curr_full: Full text from current chunk
        
        Returns:
            Merged text with duplicates removed
        """
        # Use difflib to find longest matching sequence
        matcher = difflib.SequenceMatcher(None, prev_overlap, curr_overlap)
        match = matcher.find_longest_match(0, len(prev_overlap), 0, len(curr_overlap))
        
        if match.size > 20:  # Only use LCS if we have a meaningful match
            # Found significant overlap
            # Find where the match starts in curr_overlap
            match_start_in_curr = match.b
            
            # Skip the matched portion in curr_full
            # Find the position of curr_overlap in curr_full
            overlap_pos = curr_full.lower().find(curr_overlap[:match_start_in_curr + match.size].lower())
            
            if overlap_pos > 0:
                # Return curr_full starting after the matched overlap
                return " " + curr_full[overlap_pos + match.size:].lstrip()
        
        # No meaningful match found, return full current text
        return " " + curr_full
    
    def _parse_srt_time(self, time_str: str) -> float:
        """
        Parse SRT timestamp string to seconds.
        
        Args:
            time_str: Timestamp in "HH:MM:SS,mmm" format
        
        Returns:
            Time in seconds (float)
        """
        match = re.match(r'(\d+):(\d+):(\d+),(\d+)', time_str)
        if not match:
            return 0.0
        
        hours = int(match.group(1))
        minutes = int(match.group(2))
        seconds = int(match.group(3))
        milliseconds = int(match.group(4))
        
        return hours * 3600 + minutes * 60 + seconds + milliseconds / 1000
whisper_service = WhisperService()
