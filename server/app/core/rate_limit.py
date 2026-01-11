"""
Rate limiting utilities for shared endpoints.

Provides IP-based rate limiting to prevent abuse of public endpoints.
For production use, consider using Redis-backed rate limiting.
"""

import time
import logging
from collections import defaultdict
from typing import Dict, List

logger = logging.getLogger(__name__)

# Rate limiting configuration
_RATE_LIMIT_REQUESTS: int = 10  # requests per window
_RATE_LIMIT_WINDOW: int = 60  # seconds

# In-memory rate limit store (for production, use Redis)
# Format: {client_ip: [timestamp1, timestamp2, ...]}
_rate_limit_store: Dict[str, List[float]] = defaultdict(list)


def rate_limit_shared_chat(client_ip: str) -> bool:
    """
    Check if client IP is within rate limit for shared chat.

    Args:
        client_ip: Client IP address

    Returns:
        True if request is allowed, False if rate limited
    """
    now = time.time()

    # Clean old entries outside the time window
    _rate_limit_store[client_ip] = [
        timestamp for timestamp in _rate_limit_store[client_ip]
        if now - timestamp < _RATE_LIMIT_WINDOW
    ]

    # Check if limit exceeded
    if len(_rate_limit_store[client_ip]) >= _RATE_LIMIT_REQUESTS:
        logger.warning(
            f"[RateLimit] Rate limit exceeded for IP: {client_ip} "
            f"({len(_rate_limit_store[client_ip])} requests in {_RATE_LIMIT_WINDOW}s)"
        )
        return False

    # Add current request timestamp
    _rate_limit_store[client_ip].append(now)

    logger.debug(
        f"[RateLimit] Request allowed for IP: {client_ip} "
        f"({len(_rate_limit_store[client_ip])}/{_RATE_LIMIT_REQUESTS} requests)"
    )
    return True


def get_rate_limit_status(client_ip: str) -> dict:
    """
    Get current rate limit status for a client IP.

    Args:
        client_ip: Client IP address

    Returns:
        Dictionary with rate limit status
    """
    now = time.time()

    # Clean old entries first
    _rate_limit_store[client_ip] = [
        timestamp for timestamp in _rate_limit_store[client_ip]
        if now - timestamp < _RATE_LIMIT_WINDOW
    ]

    remaining = max(0, _RATE_LIMIT_REQUESTS - len(_rate_limit_store[client_ip]))
    reset_time = int(now + _RATE_LIMIT_WINDOW) if _rate_limit_store[client_ip] else int(now)

    return {
        "limit": _RATE_LIMIT_REQUESTS,
        "remaining": remaining,
        "reset": reset_time,
        "window": _RATE_LIMIT_WINDOW
    }


def clear_rate_limit(client_ip: str = None) -> None:
    """
    Clear rate limit data for a client or all clients.

    Args:
        client_ip: Client IP to clear, or None to clear all
    """
    if client_ip:
        _rate_limit_store.pop(client_ip, None)
        logger.info(f"[RateLimit] Cleared rate limit for IP: {client_ip}")
    else:
        _rate_limit_store.clear()
        logger.info("[RateLimit] Cleared all rate limits")
