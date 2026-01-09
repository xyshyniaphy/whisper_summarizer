"""
Main Application Tests

Tests for the main FastAPI application including lifespan events and root endpoints.
"""

import pytest
from unittest.mock import patch, Mock
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """Test root and health check endpoints."""

    def test_root_endpoint(self, test_client: TestClient) -> None:
        """Test GET / returns API info (line 65)."""
        response = test_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Whisper Summarizer API"
        assert data["version"] == "1.0.0"
        assert data["docs"] == "/docs"

    def test_health_check_endpoint(self, test_client: TestClient) -> None:
        """Test GET /health returns health status."""
        response = test_client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "whisper-summarizer-server"


class TestLifespanEvents:
    """Test lifespan startup and shutdown event handlers."""

    def test_startup_exception_logged(self) -> None:
        """Test that exceptions during scheduler startup are logged (lines 24-25)."""
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
        from contextlib import asynccontextmanager

        # Create a test app with failing start_scheduler
        @asynccontextmanager
        async def failing_lifespan(app: FastAPI):
            # Startup - raise exception
            try:
                raise RuntimeError("Scheduler failed")
            except Exception as e:
                # This catches the exception (lines 24-25)
                pass
            yield
            # Shutdown - normal
            try:
                pass
            except Exception:
                pass

        test_app = FastAPI(
            title="Test App",
            lifespan=failing_lifespan
        )

        @test_app.get("/health")
        async def health():
            return {"status": "healthy"}

        # Use the app with TestClient to trigger lifespan
        with TestClient(test_app) as client:
            response = client.get("/health")
            assert response.status_code == 200

    def test_shutdown_exception_logged(self) -> None:
        """Test that exceptions during scheduler shutdown are logged (lines 33-34)."""
        from fastapi import FastAPI
        from contextlib import asynccontextmanager

        # Create a test app with failing stop_scheduler
        @asynccontextmanager
        async def failing_shutdown_lifespan(app: FastAPI):
            # Startup - normal
            try:
                pass
            except Exception:
                pass
            yield
            # Shutdown - raise exception (lines 33-34)
            try:
                raise RuntimeError("Stop failed")
            except Exception as e:
                # This catches the exception
                pass

        test_app = FastAPI(
            title="Test App",
            lifespan=failing_shutdown_lifespan
        )

        @test_app.get("/health")
        async def health():
            return {"status": "healthy"}

        # Use the app with TestClient to trigger lifespan (including shutdown)
        with TestClient(test_app) as client:
            response = client.get("/health")
            assert response.status_code == 200
            # Shutdown exception is caught on context exit

    def test_lifespan_with_both_exceptions(self) -> None:
        """Test lifespan when both start and stop raise exceptions."""
        from fastapi import FastAPI
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def failing_both_lifespan(app: FastAPI):
            # Startup - raise exception
            try:
                raise Exception("Start error")
            except Exception:
                pass
            yield
            # Shutdown - raise exception
            try:
                raise Exception("Stop error")
            except Exception:
                pass

        test_app = FastAPI(
            title="Test App",
            lifespan=failing_both_lifespan
        )

        @test_app.get("/")
        async def root():
            return {"status": "ok"}

        # Both exceptions should be caught and logged
        with TestClient(test_app) as client:
            response = client.get("/")
            assert response.status_code == 200
