"""
Gemini API Response Schemas
Schemas for Gemini API responses including debug information
"""

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class GeminiResponse(BaseModel):
    """Complete response from Gemini API with debug information"""
    summary: str  # Generated summary text
    model_name: str  # Model used
    prompt: str  # System prompt used
    input_text_length: int  # Character count of input
    output_text_length: int  # Character count of output

    # Token usage (if available)
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

    # Performance
    response_time_ms: float  # Response time in milliseconds
    temperature: float

    # Status
    status: str = "success"
    error_message: Optional[str] = None

    # Raw response for debugging (optional)
    raw_response: Optional[dict] = None
