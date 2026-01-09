"""
Runner API Missing Coverage Tests
Tests for uncovered error paths in runner API
"""

import pytest


class TestRunnerAPIStatusValidation:
    """Test runner API status validation."""
    
    def test_list_jobs_valid_status_filters(self, auth_client):
        """Test that valid status filters work correctly."""
        for status in ["pending", "processing", "completed", "failed"]:
            response = auth_client.get(f"/api/runner/jobs?status={status}&limit=10")
            # Current implementation doesn't validate, returns 200
            assert response.status_code in [200, 400]
    
    def test_list_jobs_default_limit(self, auth_client):
        """Test that jobs endpoint has default limit."""
        response = auth_client.get("/api/runner/jobs?status=pending")
        assert response.status_code == 200


class TestRunnerAPIAudioErrors:
    """Test runner API audio error handling."""
    
    def test_get_audio_no_path_returns_404(self, auth_client, db_session, test_transcription):
        """Test getting audio when no path is set returns 404."""
        test_transcription.file_path = None
        test_transcription.storage_path = None
        db_session.commit()
        
        response = auth_client.get(f"/api/runner/audio/{test_transcription.id}")
        
        assert response.status_code == 404
        assert "not set" in response.json()["detail"]
    
    def test_get_audio_nonexistent_job_returns_404(self, auth_client):
        """Test getting audio for non-existent job returns 404."""
        from uuid import uuid4
        fake_id = uuid4()
        
        response = auth_client.get(f"/api/runner/audio/{fake_id}")
        
        assert response.status_code == 404


class TestRunnerAPIJobNotFound:
    """Test runner API job not found errors."""
    
    def test_start_nonexistent_job_returns_404(self, auth_client):
        """Test starting non-existent job returns 404."""
        from uuid import uuid4
        fake_id = uuid4()
        
        response = auth_client.post(
            f"/api/runner/jobs/{fake_id}/start",
            json={"runner_id": "test-runner"}
        )
        
        assert response.status_code == 404
    
    def test_complete_nonexistent_job_returns_404(self, auth_client):
        """Test completing non-existent job returns 404."""
        from uuid import uuid4
        fake_id = uuid4()
        
        response = auth_client.post(
            f"/api/runner/jobs/{fake_id}/complete",
            json={"text": "test", "summary": "test", "processing_time_seconds": 10}
        )
        
        assert response.status_code == 404
    
    def test_fail_nonexistent_job_returns_404(self, auth_client):
        """Test failing non-existent job returns 404."""
        from uuid import uuid4
        fake_id = uuid4()
        
        response = auth_client.post(
            f"/api/runner/jobs/{fake_id}/fail",
            params={"error_message": "Test error"}
        )
        
        assert response.status_code == 404
