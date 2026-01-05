"""
Pytest configuration for server tests.

Sets up test environment variables and shared fixtures.
"""

import os
import sys

# Add server directory to Python path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Set test environment variables
os.environ.setdefault("SUPABASE_URL", "http://test-supabase-url.com")
os.environ.setdefault("SUPABASE_ANON_KEY", "test-anon-key")
os.environ.setdefault("SUPABASE_SERVICE_ROLE_KEY", "test-service-role-key")
os.environ.setdefault("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/whisper_summarizer")
os.environ.setdefault("RUNNER_API_KEY", "test-runner-api-key")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("LOG_LEVEL", "DEBUG")
os.environ.setdefault("DISABLE_AUTH", "false")
