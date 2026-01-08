"""
Transcription Schema Validation Tests

Tests Pydantic schemas for transcription-related request/response validation.
"""

import pytest
from pydantic import ValidationError
from datetime import datetime, timedelta
from uuid import UUID
from app.schemas.transcription import (
    PaginatedResponse,
    SummaryBase,
    Summary,
    TranscriptionBase,
    TranscriptionCreate,
    TranscriptionUpdate,
    TranscriptionInDBBase,
    Transcription,
)


class TestSummarySchemas:
    """Test summary-related schemas"""

    def test_summary_base_valid(self):
        """Valid SummaryBase"""
        data = {
            "summary_text": "This is a test summary",
            "model_name": "GLM-4.5-Air"
        }
        summary = SummaryBase(**data)
        assert summary.summary_text == "This is a test summary"
        assert summary.model_name == "GLM-4.5-Air"

    def test_summary_base_optional_model(self):
        """Valid SummaryBase without model name"""
        data = {"summary_text": "This is a test summary"}
        summary = SummaryBase(**data)
        assert summary.summary_text == "This is a test summary"
        assert summary.model_name is None

    def test_summary_valid(self):
        """Valid Summary with all fields"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "550e8400-e29b-41d4-a716-446655440001",
            "summary_text": "Test summary",
            "model_name": "GLM-4.5-Air",
            "created_at": "2024-01-01T00:00:00Z"
        }
        summary = Summary(**data)
        assert isinstance(summary.id, UUID)
        assert isinstance(summary.transcription_id, UUID)
        assert summary.summary_text == "Test summary"


class TestTranscriptionSchemas:
    """Test transcription schemas"""

    def test_transcription_base_valid(self):
        """Valid TranscriptionBase"""
        data = {
            "file_name": "test.mp3",
            "language": "en",
            "duration_seconds": 120.5
        }
        base = TranscriptionBase(**data)
        assert base.file_name == "test.mp3"
        assert base.language == "en"

    def test_transcription_base_defaults(self):
        """Valid TranscriptionBase with defaults"""
        data = {"file_name": "test.mp3"}
        base = TranscriptionBase(**data)
        assert base.file_name == "test.mp3"
        assert base.status == "processing"  # Legacy default
        assert base.stage == "uploading"  # Current default
        assert base.language is None

    def test_transcription_create_valid(self):
        """Valid TranscriptionCreate"""
        data = {
            "file_name": "test.mp3",
            "language": "zh",
            "duration_seconds": 300.0
        }
        create = TranscriptionCreate(**data)
        assert create.file_name == "test.mp3"
        assert create.language == "zh"

    def test_transcription_update_valid(self):
        """Valid TranscriptionUpdate"""
        data = {
            "file_name": "updated.mp3",
            "stage": "completed",
            "error_message": None
        }
        update = TranscriptionUpdate(**data)
        assert update.file_name == "updated.mp3"
        assert update.stage == "completed"
        assert update.error_message is None

    def test_transcription_update_all_optional(self):
        """Valid TranscriptionUpdate with only required fields"""
        data = {"file_name": "test.mp3"}
        update = TranscriptionUpdate(**data)
        assert update.file_name == "test.mp3"
        # Optional fields default to None
        assert update.stage is None
        assert update.error_message is None

    def test_transcription_in_db_base_valid(self):
        """Valid TranscriptionInDBBase"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "file_name": "test.mp3",
            "stage": "completed",
            "language": "en",
            "duration_seconds": 120.5,
            "error_message": None,
            "retry_count": 0,
            "pptx_status": "not-started",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:05:00Z"
        }
        in_db = TranscriptionInDBBase(**data)
        assert isinstance(in_db.id, UUID)
        assert in_db.stage == "completed"

    def test_transcription_response_valid(self):
        """Valid Transcription response"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "file_name": "test.mp3",
            "stage": "completed",
            "language": "en",
            "duration_seconds": 120.5,
            "error_message": None,
            "retry_count": 0,
            "pptx_status": "ready",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:05:00Z",
            "text": "This is the transcription text",
            "summaries": []
        }
        response = Transcription(**data)
        assert response.text == "This is the transcription text"
        assert response.summaries == []

    def test_transcription_with_summaries(self):
        """Valid Transcription with summaries"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "file_name": "test.mp3",
            "stage": "completed",
            "language": "en",
            "duration_seconds": 120.5,
            "error_message": None,
            "retry_count": 0,
            "pptx_status": "ready",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:05:00Z",
            "text": "Test transcription",
            "summaries": [
                {
                    "id": "650e8400-e29b-41d4-a716-446655440001",
                    "transcription_id": "550e8400-e29b-41d4-a716-446655440000",
                    "summary_text": "Test summary",
                    "created_at": "2024-01-01T00:06:00Z"
                }
            ]
        }
        response = Transcription(**data)
        assert len(response.summaries) == 1
        assert response.summaries[0].summary_text == "Test summary"

    def test_transcription_time_remaining(self):
        """Valid Transcription with time_remaining"""
        td = timedelta(hours=24)
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "file_name": "test.mp3",
            "stage": "completed",
            "language": "en",
            "duration_seconds": 120.5,
            "error_message": None,
            "retry_count": 0,
            "pptx_status": "ready",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:05:00Z",
            "text": "Test",
            "summaries": [],
            "time_remaining": td
        }
        response = Transcription(**data)
        # time_remaining is serialized to total seconds
        assert response.model_dump()["time_remaining"] == 86400.0  # 24 hours in seconds


class TestPaginatedResponse:
    """Test paginated response schema"""

    def test_paginated_response_valid(self):
        """Valid PaginatedResponse"""
        data = {
            "total": 100,
            "page": 1,
            "page_size": 10,
            "total_pages": 10,
            "data": [
                {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "file_name": "test.mp3",
                    "stage": "completed",
                    "created_at": "2024-01-01T00:00:00Z",
                    "updated_at": "2024-01-01T00:05:00Z",
                    "text": "",
                    "summaries": []
                }
            ]
        }
        response = PaginatedResponse[Transcription](**data)
        assert response.total == 100
        assert response.page == 1
        assert response.total_pages == 10
        assert len(response.data) == 1

    def test_paginated_response_empty(self):
        """Valid PaginatedResponse with empty data"""
        data = {
            "total": 0,
            "page": 1,
            "page_size": 10,
            "total_pages": 0,
            "data": []
        }
        response = PaginatedResponse[Transcription](**data)
        assert response.total == 0
        assert response.data == []


class TestTranscriptionSchemaEdgeCases:
    """Test edge cases and boundary conditions"""

    def test_various_stages(self):
        """Test all valid stage values"""
        valid_stages = ["uploading", "transcribing", "summarizing", "completed", "failed"]
        for stage in valid_stages:
            data = {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "test.mp3",
                "stage": stage,
                "language": None,
                "duration_seconds": None,
                "error_message": None,
                "retry_count": 0,
                "pptx_status": "not-started",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "text": "",
                "summaries": []
            }
            response = Transcription(**data)
            assert response.stage == stage

    def test_various_languages(self):
        """Test various language codes"""
        valid_languages = ["en", "zh", "ja", "es", "fr", "de", "ko"]
        for lang in valid_languages:
            data = {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "test.mp3",
                "stage": "completed",
                "language": lang,
                "duration_seconds": 120.5,
                "error_message": None,
                "retry_count": 0,
                "pptx_status": "ready",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "text": "Test",
                "summaries": []
            }
            response = Transcription(**data)
            assert response.language == lang

    def test_unicode_filename(self):
        """Test transcription with unicode filename"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "file_name": "テストファイル.mp3",
            "stage": "completed",
            "language": "ja",
            "duration_seconds": 120.5,
            "error_message": None,
            "retry_count": 0,
            "pptx_status": "ready",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "text": "テスト",
            "summaries": []
        }
        response = Transcription(**data)
        assert response.file_name == "テストファイル.mp3"

    def test_duration_boundaries(self):
        """Test duration seconds boundary values"""
        test_durations = [0.1, 1.0, 60.0, 3600.0, 86400.0]
        for duration in test_durations:
            data = {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "test.mp3",
                "stage": "completed",
                "language": "en",
                "duration_seconds": duration,
                "error_message": None,
                "retry_count": 0,
                "pptx_status": "ready",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "text": "Test",
                "summaries": []
            }
            response = Transcription(**data)
            assert response.duration_seconds == duration

    def test_retry_count_values(self):
        """Test various retry count values"""
        for retry_count in [0, 1, 2, 5, 10]:
            data = {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "test.mp3",
                "stage": "completed",
                "language": "en",
                "duration_seconds": 120.5,
                "error_message": None,
                "retry_count": retry_count,
                "pptx_status": "ready",
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "text": "Test",
                "summaries": []
            }
            response = Transcription(**data)
            assert response.retry_count == retry_count

    def test_pptx_status_values(self):
        """Test various PPTX status values"""
        pptx_statuses = ["not-started", "generating", "ready", "failed"]
        for pptx_status in pptx_statuses:
            data = {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "file_name": "test.mp3",
                "stage": "completed",
                "language": "en",
                "duration_seconds": 120.5,
                "error_message": None,
                "retry_count": 0,
                "pptx_status": pptx_status,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "text": "Test",
                "summaries": []
            }
            response = Transcription(**data)
            assert response.pptx_status == pptx_status

    def test_transcription_with_error(self):
        """Test failed transcription with error message"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "file_name": "test.mp3",
            "stage": "failed",
            "language": None,
            "duration_seconds": None,
            "error_message": "Audio file is corrupted",
            "retry_count": 1,
            "pptx_status": "not-started",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:00:00Z",
            "text": "",
            "summaries": []
        }
        response = Transcription(**data)
        assert response.stage == "failed"
        assert response.error_message == "Audio file is corrupted"

    def test_long_summary_text(self):
        """Test summary with very long text"""
        long_summary = "This is a summary. " * 100  # ~2000 characters
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "transcription_id": "650e8400-e29b-41d4-a716-446655440001",
            "summary_text": long_summary,
            "created_at": "2024-01-01T00:00:00Z"
        }
        summary = Summary(**data)
        assert len(summary.summary_text) == len(long_summary)

    def test_multiple_summaries(self):
        """Test transcription with multiple summaries"""
        data = {
            "id": "550e8400-e29b-41d4-a716-446655440000",
            "file_name": "test.mp3",
            "stage": "completed",
            "language": "en",
            "duration_seconds": 120.5,
            "error_message": None,
            "retry_count": 0,
            "pptx_status": "ready",
            "created_at": "2024-01-01T00:00:00Z",
            "updated_at": "2024-01-01T00:05:00Z",
            "text": "Test transcription",
            "summaries": [
                {
                    "id": f"650e8400-e29b-41d4-a716-44665544000{i}",
                    "transcription_id": "550e8400-e29b-41d4-a716-446655440000",
                    "summary_text": f"Summary {i}",
                    "created_at": "2024-01-01T00:00:00Z"
                }
                for i in range(5)
            ]
        }
        response = Transcription(**data)
        assert len(response.summaries) == 5

    def test_pagination_boundary_values(self):
        """Test pagination with boundary values"""
        # Test with maximum values
        data = {
            "total": 1000000,
            "page": 10000,
            "page_size": 1000,
            "total_pages": 1000,
            "data": []
        }
        response = PaginatedResponse[Transcription](**data)
        assert response.total == 1000000
        assert response.page == 10000
