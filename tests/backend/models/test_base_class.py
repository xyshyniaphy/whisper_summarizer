"""Base class tablename generation test."""

import pytest


class TestBaseClassTablename:
    """Test Base class __tablename__ generation."""

    def test_existing_models_have_correct_tablenames(self):
        """Test that existing models have correct tablename values."""
        from app.models.transcription import Transcription
        from app.models.user import User
        from app.models.channel import Channel

        # Test that models inherit from Base and have correct tablename
        assert Transcription.__tablename__ == "transcriptions"
        assert User.__tablename__ == "users"
        assert Channel.__tablename__ == "channels"
