"""
FastAPI メインアプリケーション
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app import models  # Ensure models are registered
from app.api import auth, audio, transcriptions, users
from app.tasks import start_scheduler, stop_scheduler
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Whisper Summarizer API",
    description="音声文字起こし・要約システムのバックエンドAPI",
    version="1.0.0"
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
app.include_router(auth.router, prefix="/api/auth", tags=["認証"])
app.include_router(users.router, prefix="/api/users", tags=["ユーザー"])
app.include_router(audio.router, prefix="/api/audio", tags=["音声"])
app.include_router(transcriptions.router, prefix="/api/transcriptions", tags=["文字起こし"])


@app.get("/")
async def root():
    """ルートエンドポイント"""
    return {
        "message": "Whisper Summarizer API",
        "version": "1.0.0",
        "docs": "/docs"
    }


@app.get("/health")
async def health_check():
    """ヘルスチェックエンドポイント"""
    return {
        "status": "healthy",
        "service": "whisper-summarizer-backend"
    }


@app.on_event("startup")
async def startup_event():
    """Initialize scheduled tasks on startup."""
    try:
        start_scheduler()
        logger.info("Application started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup scheduler on shutdown."""
    try:
        stop_scheduler()
        logger.info("Application shutdown complete")
    except Exception as e:
        logger.error(f"Error during shutdown: {e}", exc_info=True)
