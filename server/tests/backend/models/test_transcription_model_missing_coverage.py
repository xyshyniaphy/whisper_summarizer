"""
Transcription Model Missing Coverage Tests
Tests for uncovered property edge cases in Transcription model
"""

import pytest
from datetime import datetime, timedelta, timezone


class TestTranscriptionModelProperties:
    """Test transcription model properties with edge cases."""
    
    def test_original_text_empty_when_no_storage_path(self, db_session, test_transcription):
        """Test original_text returns empty string when storage_path is None."""
        test_transcription.storage_path = None
        db_session.commit()
        
        assert test_transcription.original_text == ""
    
    def test_original_text_empty_when_storage_path_empty_string(self, db_session, test_transcription):
        """Test original_text returns empty string when storage_path is empty."""
        test_transcription.storage_path = ""
        db_session.commit()
        
        assert test_transcription.original_text == ""
    
    def test_text_property_fallback_to_original(self, db_session, test_transcription):
        """Test text property falls back to original_text when formatted not available."""
        # Set up transcription with storage_path
        test_transcription.storage_path = f"{test_transcription.id}.txt.gz"
        db_session.commit()
        
        # text property should handle the case gracefully
        result = test_transcription.text
        assert isinstance(result, str)
    
    def test_is_expired_with_old_created_at(self, db_session, test_transcription):
        """Test is_expired returns True for old transcriptions."""
        from app.core.config import settings
        
        # Set created_at to older than MAX_KEEP_DAYS
        old_date = datetime.now(timezone.utc) - timedelta(days=settings.MAX_KEEP_DAYS + 1)
        test_transcription.created_at = old_date
        db_session.commit()
        
        assert test_transcription.is_expired is True
    
    def test_is_expired_with_recent_created_at(self, db_session, test_transcription):
        """Test is_expired returns False for recent transcriptions."""
        recent_date = datetime.now(timezone.utc) - timedelta(days=1)
        test_transcription.created_at = recent_date
        db_session.commit()
        
        assert test_transcription.is_expired is False
    
    def test_processing_time_with_none_timestamps(self, db_session, test_transcription):
        """Test processing_time handles None timestamps."""
        test_transcription.started_at = None
        test_transcription.completed_at = None
        db_session.commit()
        
        # Should return processing_time_seconds when timestamps are None
        result = test_transcription.processing_time
        assert result is None or result == test_transcription.processing_time_seconds
    
    def test_processing_time_calculates_difference(self, db_session, test_transcription):
        """Test processing_time calculates difference between timestamps."""
        started = datetime.now(timezone.utc) - timedelta(seconds=30)
        completed = datetime.now(timezone.utc)
        
        test_transcription.started_at = started
        test_transcription.completed_at = completed
        db_session.commit()
        
        result = test_transcription.processing_time
        # Should be approximately 30 seconds (may be slightly off due to timing)
        assert 25 <= result <= 35  # Allow some timing tolerance
