"""
Audio Segmentation Service

Splits audio into fixed-duration chunks (10-30s) for SRT generation.
Uses VAD-detected silence as ideal split points for natural boundaries.
"""

import logging
from typing import List, Dict
from dataclasses import dataclass

import pydub
from pydub import AudioSegment
from pydub.silence import detect_nonsilent

logger = logging.getLogger(__name__)


@dataclass
class AudioChunk:
    """Represents a fixed-duration audio segment"""
    start_ms: int
    end_ms: int
    start_s: float
    end_s: float

    def to_dict(self) -> Dict:
        return {
            "start": self.start_ms,
            "end": self.end_ms,
            "start_s": self.start_s,
            "end_s": self.end_s
        }


class AudioSegmenter:
    """
    Splits audio into fixed-duration chunks using VAD-detected silence.

    Target duration: 20 seconds (configurable)
    Min duration: 10 seconds
    Max duration: 30 seconds
    """

    def __init__(
        self,
        target_duration_seconds: int = 20,
        min_duration_seconds: int = 10,
        max_duration_seconds: int = 30,
        silence_threshold: int = -40,  # dB
        min_silence_duration: float = 0.5,  # seconds
    ):
        if min_duration_seconds >= target_duration_seconds:
            raise ValueError(
                f"min_duration_seconds ({min_duration_seconds}) must be less than target_duration_seconds ({target_duration_seconds})"
            )
        if target_duration_seconds >= max_duration_seconds:
            raise ValueError(
                f"target_duration_seconds ({target_duration_seconds}) must be less than max_duration_seconds ({max_duration_seconds})"
            )

        self.target_duration = target_duration_seconds * 1000  # Convert to ms
        self.min_duration = min_duration_seconds * 1000
        self.max_duration = max_duration_seconds * 1000
        self.silence_threshold = silence_threshold
        self.min_silence_duration_ms = int(min_silence_duration * 1000)

    def segment(self, audio_path: str) -> List[Dict]:
        """
        Split audio file into fixed-duration chunks.

        Args:
            audio_path: Path to audio file

        Returns:
            List of AudioChunk dictionaries with start/end timestamps
        """
        logger.info(f"Loading audio: {audio_path}")
        audio = AudioSegment.from_file(audio_path)

        # Get total duration
        total_duration = len(audio)

        # If audio is shorter than min duration, return single chunk
        if total_duration <= self.min_duration:
            logger.info(f"Audio ({total_duration}ms) shorter than min duration, returning single chunk")
            return [AudioChunk(0, total_duration, 0.0, total_duration / 1000.0).to_dict()]

        # Detect nonsilent ranges (speech segments)
        logger.info("Detecting speech segments...")
        nonsilent_ranges = detect_nonsilent(
            audio,
            min_silence_len=self.min_silence_duration_ms,
            silence_thresh=self.silence_threshold,
            seek_step=100  # 100ms steps for efficiency
        )

        # If no speech detected, fall back to fixed chunks
        if not nonsilent_ranges:
            logger.warning("No speech detected, using fixed chunks")
            return self._create_fixed_chunks(total_duration)

        # Find optimal split points at silence
        split_points = self._find_split_points(nonsilent_ranges, total_duration)

        # Create chunks from split points
        chunks = self._create_chunks_from_splits(split_points, total_duration)

        logger.info(f"Created {len(chunks)} chunks from {total_duration}ms audio")
        return chunks

    def _find_split_points(self, nonsilent_ranges: List[tuple], total_duration: int) -> List[int]:
        """
        Find optimal split points using silence between speech segments.

        Args:
            nonsilent_ranges: List of (start_ms, end_ms) tuples
            total_duration: Total audio duration in ms

        Returns:
            List of split point timestamps in milliseconds
        """
        split_points = [0]  # Always start at 0
        current_position = 0

        for i, (start, end) in enumerate(nonsilent_ranges):
            # Check if we've exceeded target duration since last split
            time_since_last_split = start - current_position

            if time_since_last_split >= self.target_duration:
                # Find silence between this and previous speech segment
                if i > 0:
                    prev_end = nonsilent_ranges[i-1][1]
                    gap = start - prev_end

                    # If there's a silence gap, split in the middle
                    if gap >= self.min_silence_duration_ms:
                        split_point = prev_end + (gap // 2)
                        split_points.append(split_point)
                        current_position = split_point

        # Ensure we don't exceed max duration
        # Check if last chunk would be too long
        if split_points:
            time_since_last_split = total_duration - split_points[-1]
            if time_since_last_split > self.max_duration:
                # Force intermediate splits at equal intervals
                base_position = split_points[-1]
                num_forced_splits = int(time_since_last_split / self.target_duration)
                interval = time_since_last_split / (num_forced_splits + 1)
                for i in range(1, num_forced_splits + 1):
                    split_point = base_position + int(i * interval)
                    split_points.append(split_point)

        split_points.append(total_duration)  # Always end at total duration
        return sorted(list(set(split_points)))  # Remove duplicates and sort

    def _create_chunks_from_splits(self, split_points: List[int], total_duration: int) -> List[Dict]:
        """Create AudioChunk objects from split points"""
        chunks = []
        for i in range(len(split_points) - 1):
            start = split_points[i]
            end = split_points[i + 1]
            duration = end - start

            # Skip very small chunks at the end
            if duration < 1000:  # Less than 1 second
                # Merge with previous chunk
                if chunks:
                    chunks[-1]["end"] = end
                    chunks[-1]["end_s"] = end / 1000.0
                continue

            chunks.append(AudioChunk(
                start_ms=start,
                end_ms=end,
                start_s=start / 1000.0,
                end_s=end / 1000.0
            ).to_dict())

        return chunks

    def _create_fixed_chunks(self, total_duration: int) -> List[Dict]:
        """Fallback: create fixed chunks when VAD fails"""
        chunks = []
        current = 0
        chunk_num = 0

        while current < total_duration:
            end = min(current + self.target_duration, total_duration)
            duration = end - current

            # Last chunk might be short, that's okay
            if duration < 1000 and chunks:
                # Merge with previous
                chunks[-1]["end"] = total_duration
                chunks[-1]["end_s"] = total_duration / 1000.0
                break

            chunks.append(AudioChunk(
                start_ms=current,
                end_ms=end,
                start_s=current / 1000.0,
                end_s=end / 1000.0
            ).to_dict())

            current = end
            chunk_num += 1

        return chunks
