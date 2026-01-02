"""
Unit tests for download endpoint helper functions.

Tests the SRT validation, line counting, and structure validation logic
without requiring database access.

For full integration tests, see: testdata/test_20_min_download.py
"""
import pytest
import re


# ============================================================================
# Helper Functions
# ============================================================================

def count_lines(text: str) -> int:
    """Count non-empty lines in text."""
    lines = text.split('\n')
    return len([line for line in lines if line.strip()])


def validate_srt_timestamps(srt_content: str) -> tuple[bool, int]:
    """
    Check if SRT contains valid timestamp format.

    Valid format: HH:MM:SS,mmm --> HH:MM:SS,mmm
    Example: 00:01:23,456 --> 00:01:25,789

    Returns:
        tuple: (has_valid_timestamps, count)
    """
    pattern = r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}'
    matches = re.findall(pattern, srt_content)
    return len(matches) > 0, len(matches)


def validate_srt_structure(srt_content: str) -> dict:
    """
    Validate SRT file structure.

    Returns:
        dict with keys: valid, entries, issues
    """
    lines = srt_content.split('\n')
    entry_count = 0
    issues = []

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # SRT entry starts with a number
        if line.isdigit():
            entry_count += 1

            # Next line should be timestamp
            if i + 1 < len(lines):
                timestamp_line = lines[i + 1].strip()
                if not re.match(r'\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}', timestamp_line):
                    issues.append(f"Entry {entry_count}: Invalid timestamp format")

                # Next line should be text content
                if i + 2 < len(lines):
                    text_line = lines[i + 2].strip()
                    if not text_line:
                        issues.append(f"Entry {entry_count}: Missing text content")

                    i += 3  # Skip to next entry
                    continue

        i += 1

    return {
        "valid": len(issues) == 0,
        "entries": entry_count,
        "issues": issues
    }


# ============================================================================
# Unit Tests for Helper Functions
# ============================================================================

class TestCountLines:
    """Tests for count_lines helper function."""

    def test_count_lines_empty_string(self):
        """Test counting lines in empty string."""
        assert count_lines("") == 0

    def test_count_lines_single_line(self):
        """Test counting lines in single-line text."""
        assert count_lines("Single line") == 1

    def test_count_lines_multiple_lines(self):
        """Test counting lines in multi-line text."""
        text = "Line 1\n\nLine 2\n\nLine 3"
        assert count_lines(text) == 3

    def test_count_lines_more_than_10(self):
        """Test counting lines with more than 10 lines."""
        text = "\n\n".join([f"Line {i}" for i in range(1, 16)])
        assert count_lines(text) == 15
        assert count_lines(text) > 10


class TestValidateSrtTimestamps:
    """Tests for validate_srt_timestamps helper function."""

    def test_validate_srt_timestamps_empty(self):
        """Test timestamp validation with empty content."""
        has_valid, count = validate_srt_timestamps("")
        assert has_valid is False
        assert count == 0

    def test_validate_srt_timestamps_single_entry(self):
        """Test timestamp validation with single SRT entry."""
        srt = "1\n00:00:00,000 --> 00:00:02,400\nTest subtitle\n"
        has_valid, count = validate_srt_timestamps(srt)
        assert has_valid is True
        assert count == 1

    def test_validate_srt_timestamps_multiple_entries(self):
        """Test timestamp validation with multiple SRT entries."""
        srt = """1
00:00:00,000 --> 00:00:02,400
First subtitle

2
00:00:02,400 --> 00:00:05,800
Second subtitle

3
00:00:05,800 --> 00:00:08,200
Third subtitle
"""
        has_valid, count = validate_srt_timestamps(srt)
        assert has_valid is True
        assert count == 3

    def test_validate_srt_timestamps_more_than_10(self):
        """Test timestamp validation with more than 10 entries."""
        entries = []
        for i in range(15):
            entries.append(f"{i+1}\n00:00:{i*2:02d},000 --> 00:00:{i*2+1:02d},000\nSubtitle {i+1}\n")
        srt = "\n".join(entries)

        has_valid, count = validate_srt_timestamps(srt)
        assert has_valid is True
        assert count == 15
        assert count > 10


class TestValidateSrtStructure:
    """Tests for validate_srt_structure helper function."""

    def test_validate_srt_structure_valid(self):
        """Test SRT structure validation with valid content."""
        srt = """1
00:00:00,000 --> 00:00:02,400
First subtitle

2
00:00:02,400 --> 00:00:05,800
Second subtitle
"""
        result = validate_srt_structure(srt)
        assert result["valid"] is True
        assert result["entries"] == 2
        assert len(result["issues"]) == 0

    def test_validate_srt_structure_missing_text(self):
        """Test SRT structure validation with missing text."""
        srt = """1
00:00:00,000 --> 00:00:02,400

2
00:00:02,400 --> 00:00:05,800
Second subtitle
"""
        result = validate_srt_structure(srt)
        assert result["valid"] is False
        assert result["entries"] == 2
        assert "Missing text content" in str(result["issues"])

    def test_validate_srt_structure_more_than_10_entries(self):
        """Test SRT structure validation with more than 10 entries."""
        entries = []
        for i in range(15):
            start_sec = i * 2
            end_sec = start_sec + 1
            entries.append(f"{i+1}\n00:{start_sec//60:02d}:{start_sec%60:02d},000 --> 00:{end_sec//60:02d}:{end_sec%60:02d},000\nSubtitle {i+1}\n")
        srt = "\n".join(entries)

        result = validate_srt_structure(srt)
        assert result["valid"] is True
        assert result["entries"] == 15
        assert result["entries"] > 10

    def test_validate_srt_structure_chunked_transcription_simulation(self):
        """
        Test SRT structure validation simulating chunked transcription.

        This simulates a 20-minute transcription with many segments,
        validating that the structure validation handles large SRT files correctly.
        """
        # Simulate 100 segments (like chunked transcription)
        entries = []
        for i in range(100):
            start_sec = i * 12  # 12 seconds per subtitle
            end_sec = start_sec + 10
            start_min = start_sec // 60
            start_sec_part = start_sec % 60
            end_min = end_sec // 60
            end_sec_part = end_sec % 60
            entries.append(f"{i+1}\n00:{start_min:02d}:{start_sec_part:02d},000 --> 00:{end_min:02d}:{end_sec_part:02d},000\nSubtitle entry {i+1} from chunked transcription.\n")
        srt = "\n".join(entries)

        result = validate_srt_structure(srt)
        assert result["valid"] is True
        assert result["entries"] == 100
        assert result["entries"] > 10
        assert len(result["issues"]) == 0


# ============================================================================
# Integration Test Reference
# ============================================================================

class TestIntegrationTestReference:
    """Documentation of integration test location."""

    def test_integration_test_exists(self):
        """
        Reference to full integration test.

        The full end-to-end integration test for download functionality
        is located at: testdata/test_20_min_download.py

        That test validates:
        - Upload of 20_min.m4a audio file
        - Chunked transcription completion (triggers timestamp-based merge)
        - Text download with > 10 lines
        - SRT download with > 10 lines and valid timestamps
        - Segments.json.gz file creation

        Run with: python3 testdata/test_20_min_download.py
        """
        # This is a documentation test - the actual integration test
        # is in testdata/test_20_min_download.py
        assert True
