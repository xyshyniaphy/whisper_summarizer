"""
Main App Lifespan Exception Handler Tests

Test for main.py lines 24-25, 33-34 - lifespan exception handlers.
"""

import pytest
import logging
from unittest.mock import patch, MagicMock


@pytest.mark.integration
class TestMainLifespanExceptionHandlers:
    """Test main.py lifespan exception handlers."""

    def test_start_scheduler_exception_is_logged(self):
        """
        Test lifespan handles start_scheduler exception (lines 24-25).
        """
        # Patch at the import location (main.py imports from app.tasks)
        with patch('app.main.start_scheduler') as mock_start:
            with patch('app.main.stop_scheduler') as mock_stop:
                mock_start.side_effect = RuntimeError("Scheduler failed to start")
                
                with patch('app.main.logger') as mock_logger:
                    from app.main import lifespan
                    from fastapi import FastAPI
                    
                    app = FastAPI(lifespan=lifespan)
                    
                    # Add a simple route for testing
                    @app.get("/test")
                    async def test_route():
                        return {"status": "ok"}
                    
                    from fastapi.testclient import TestClient
                    with TestClient(app) as client:
                        response = client.get("/test")
                        
                    # Verify error was logged
                    mock_logger.error.assert_called()
                    error_call_str = str(mock_logger.error.call_args)
                    assert "Failed to start scheduler" in error_call_str or "Scheduler failed to start" in error_call_str

    def test_stop_scheduler_exception_is_logged(self):
        """
        Test lifespan handles stop_scheduler exception (lines 33-34).
        """
        with patch('app.main.start_scheduler') as mock_start:
            with patch('app.main.stop_scheduler') as mock_stop:
                mock_stop.side_effect = RuntimeError("Scheduler failed to stop")
                
                with patch('app.main.logger') as mock_logger:
                    from app.main import lifespan
                    from fastapi import FastAPI
                    
                    app = FastAPI(lifespan=lifespan)
                    
                    @app.get("/test")
                    async def test_route():
                        return {"status": "ok"}
                    
                    from fastapi.testclient import TestClient
                    with TestClient(app) as client:
                        response = client.get("/test")
                    
                    # After TestClient exits, shutdown runs
                    mock_logger.error.assert_called()
                    error_calls = [str(call) for call in mock_logger.error.call_args_list]
                    assert any("Error stopping scheduler" in call or "Scheduler failed to stop" in call for call in error_calls)

    def test_lifespan_normal_operation(self):
        """
        Test lifespan works normally when no exceptions occur.
        """
        with patch('app.main.start_scheduler') as mock_start:
            with patch('app.main.stop_scheduler') as mock_stop:
                with patch('app.main.logger') as mock_logger:
                    from app.main import lifespan
                    from fastapi import FastAPI
                    from fastapi.testclient import TestClient
                    
                    app = FastAPI(lifespan=lifespan)
                    
                    @app.get("/test")
                    async def test_route():
                        return {"status": "ok"}
                    
                    with TestClient(app) as client:
                        response = client.get("/test")
                        assert response.status_code == 200
                    
                    # Verify both were called
                    mock_start.assert_called_once()
                    mock_stop.assert_called_once()
                    
                    # Verify success messages were logged
                    info_calls = [str(call) for call in mock_logger.info.call_args_list]
                    assert any("started successfully" in call.lower() for call in info_calls)
                    assert any("stopped successfully" in call.lower() for call in info_calls)
