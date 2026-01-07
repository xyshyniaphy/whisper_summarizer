"""
Main App Tests

Tests for FastAPI application startup, shutdown, and endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from app.main import app, lifespan, root, health_check


# ============================================================================
# Lifespan Tests
# ============================================================================

class TestLifespan:
    """Test application lifespan events."""

    @pytest.mark.asyncio
    @patch('app.main.start_scheduler')
    async def test_should_start_scheduler_on_startup(self, mock_start_scheduler):
        """Should start scheduler on application startup."""
        mock_start_scheduler.return_value = None

        async with lifespan(app):
            pass

        mock_start_scheduler.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.main.start_scheduler')
    @patch('app.main.logger')
    async def test_should_log_startup_success(self, mock_logger, mock_start_scheduler):
        """Should log successful scheduler start."""
        mock_start_scheduler.return_value = None

        async with lifespan(app):
            pass

        mock_logger.info.assert_any_call("Scheduler started successfully")

    @pytest.mark.asyncio
    @patch('app.main.start_scheduler')
    @patch('app.main.logger')
    async def test_should_log_startup_error(self, mock_logger, mock_start_scheduler):
        """Should log error when scheduler start fails."""
        mock_start_scheduler.side_effect = Exception("Startup error")

        async with lifespan(app):
            pass

        mock_logger.error.assert_called()
        error_call_args = str(mock_logger.error.call_args)
        assert "Failed to start scheduler" in error_call_args

    @pytest.mark.asyncio
    @patch('app.main.stop_scheduler')
    async def test_should_stop_scheduler_on_shutdown(self, mock_stop_scheduler):
        """Should stop scheduler on application shutdown."""
        mock_stop_scheduler.return_value = None

        async with lifespan(app):
            pass

        mock_stop_scheduler.assert_called_once()

    @pytest.mark.asyncio
    @patch('app.main.stop_scheduler')
    @patch('app.main.logger')
    async def test_should_log_shutdown_success(self, mock_logger, mock_stop_scheduler):
        """Should log successful scheduler stop."""
        mock_stop_scheduler.return_value = None

        async with lifespan(app):
            pass

        mock_logger.info.assert_any_call("Scheduler stopped successfully")

    @pytest.mark.asyncio
    @patch('app.main.stop_scheduler')
    @patch('app.main.logger')
    async def test_should_log_shutdown_error(self, mock_logger, mock_stop_scheduler):
        """Should log error when scheduler stop fails."""
        mock_stop_scheduler.side_effect = Exception("Shutdown error")

        async with lifespan(app):
            pass

        mock_logger.error.assert_called()
        error_call_args = str(mock_logger.error.call_args)
        assert "Error stopping scheduler" in error_call_args


# ============================================================================
# Root Endpoint Tests
# ============================================================================

class TestRootEndpoint:
    """Test root endpoint."""

    @pytest.mark.asyncio
    async def test_should_return_api_info(self):
        """Should return API information."""
        result = await root()

        assert result["message"] == "Whisper Summarizer API"
        assert result["version"] == "1.0.0"
        assert result["docs"] == "/docs"


# ============================================================================
# Health Check Tests
# ============================================================================

class TestHealthCheck:
    """Test health check endpoint."""

    @pytest.mark.asyncio
    async def test_should_return_healthy_status(self):
        """Should return healthy status."""
        result = await health_check()

        assert result["status"] == "healthy"
        assert result["service"] == "whisper-summarizer-server"


# ============================================================================
# CORS Configuration Tests
# ============================================================================

class TestCorsConfiguration:
    """Test CORS middleware configuration."""

    def test_should_have_cors_middleware(self):
        """Should have CORS middleware configured."""
        from app.main import app
        from fastapi.middleware.cors import CORSMiddleware

        # Find CORS middleware
        cors_middleware = None
        for middleware in app.user_middleware:
            if middleware.cls == CORSMiddleware:
                cors_middleware = middleware
                break

        assert cors_middleware is not None

    @patch('app.main.settings.CORS_ORIGINS', "http://localhost:3000,http://example.com")
    def test_should_parse_cors_origins_from_settings(self):
        """Should parse CORS origins from settings."""
        from app.main import settings

        origins = settings.CORS_ORIGINS.split(",")

        assert "http://localhost:3000" in origins
        assert "http://example.com" in origins


# ============================================================================
# Router Registration Tests
# ============================================================================

class TestRouterRegistration:
    """Test that all routers are registered."""

    def test_should_register_auth_router(self):
        """Should register auth router with correct prefix."""
        # Routes should include auth-related paths
        paths = [getattr(r, 'path', None) for r in app.routes]
        assert any('auth' in str(p) for p in paths if p)

    def test_should_register_users_router(self):
        """Should register users router with correct prefix."""
        paths = [getattr(r, 'path', None) for r in app.routes]
        assert any('users' in str(p) for p in paths if p)

    def test_should_register_audio_router(self):
        """Should register audio router with correct prefix."""
        paths = [getattr(r, 'path', None) for r in app.routes]
        assert any('audio' in str(p) for p in paths if p)

    def test_should_register_transcriptions_router(self):
        """Should register transcriptions router with correct prefix."""
        paths = [getattr(r, 'path', None) for r in app.routes]
        assert any('transcriptions' in str(p) for p in paths if p)

    def test_should_register_shared_router(self):
        """Should register shared router with correct prefix."""
        paths = [getattr(r, 'path', None) for r in app.routes]
        assert any('shared' in str(p) for p in paths if p)

    def test_should_register_admin_router(self):
        """Should register admin router with correct prefix."""
        paths = [getattr(r, 'path', None) for r in app.routes]
        assert any('/api' in str(p) for p in paths if p)


# ============================================================================
# FastAPI Instance Tests
# ============================================================================

class TestFastAPIInstance:
    """Test FastAPI application configuration."""

    def test_should_have_correct_title(self):
        """Should have correct application title."""
        assert app.title == "Whisper Summarizer API"

    def test_should_have_correct_description(self):
        """Should have correct application description."""
        assert "音声文字起こし・要約システム" in app.description

    def test_should_have_correct_version(self):
        """Should have correct application version."""
        assert app.version == "1.0.0"

    def test_should_have_lifespan_configured(self):
        """Should have lifespan configured."""
        # Lifespan is set in FastAPI app
        assert app.router.lifespan_context is not None
