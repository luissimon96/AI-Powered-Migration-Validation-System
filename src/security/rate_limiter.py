"""Rate limiting implementation for API protection against abuse and DoS attacks.

Provides flexible rate limiting with sliding window, token bucket, and fixed window algorithms.
Supports per-user, per-IP, and global rate limiting with Redis backing.
"""

import asyncio
import time
from collections import defaultdict
from collections import deque
from enum import Enum
from typing import Any
from typing import Dict
from typing import Optional
from typing import Tuple

from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from pydantic import BaseModel


class RateLimitAlgorithm(Enum):
    """Rate limiting algorithms."""

    SLIDING_WINDOW = "sliding_window"
    TOKEN_BUCKET = "token_bucket"
    FIXED_WINDOW = "fixed_window"


class RateLimitExceeded(Exception):
    """Rate limit exceeded exception."""

    def __init__(self, message: str, retry_after: int = None):
        self.message = message
        self.retry_after = retry_after
        super().__init__(message)


class RateLimitConfig(BaseModel):
    """Rate limit configuration."""

    requests: int  # Number of requests allowed
    window: int  # Time window in seconds
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.SLIDING_WINDOW
    burst_multiplier: float = 1.5  # Allow burst up to this multiplier
    per_user: bool = True  # Rate limit per user vs global
    per_ip: bool = True  # Rate limit per IP address


class SlidingWindowCounter:
    """Sliding window rate limiter implementation."""

    def __init__(self):
        self.requests: Dict[str, deque] = defaultdict(deque)
        self.lock = asyncio.Lock()

    async def is_allowed(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under sliding window."""
        async with self.lock:
            now = time.time()
            window_start = now - window

            # Remove old requests outside window
            request_times = self.requests[key]
            while request_times and request_times[0] <= window_start:
                request_times.popleft()

            # Check if limit exceeded
            current_requests = len(request_times)
            allowed = current_requests < limit

            if allowed:
                request_times.append(now)

            # Calculate retry after
            retry_after = 0
            if not allowed and request_times:
                oldest_request = request_times[0]
                retry_after = int(oldest_request + window - now) + 1

            return allowed, {
                "current_requests": current_requests,
                "limit": limit,
                "window": window,
                "retry_after": retry_after,
                "reset_time": now + window if request_times else now,
            }


class TokenBucket:
    """Token bucket rate limiter implementation."""

    def __init__(self):
        self.buckets: Dict[str, Dict[str, float]] = defaultdict(
            lambda: {"tokens": 0, "last_refill": time.time()},
        )
        self.lock = asyncio.Lock()

    async def is_allowed(
        self,
        key: str,
        limit: int,
        window: int,
        burst_multiplier: float = 1.5,
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under token bucket."""
        async with self.lock:
            now = time.time()
            bucket = self.buckets[key]

            # Calculate tokens to add based on time elapsed
            time_elapsed = now - bucket["last_refill"]
            refill_rate = limit / window  # tokens per second
            tokens_to_add = time_elapsed * refill_rate

            # Refill bucket (up to burst limit)
            max_tokens = limit * burst_multiplier
            bucket["tokens"] = min(max_tokens, bucket["tokens"] + tokens_to_add)
            bucket["last_refill"] = now

            # Check if we can consume a token
            allowed = bucket["tokens"] >= 1.0

            if allowed:
                bucket["tokens"] -= 1.0

            # Calculate retry after
            retry_after = 0
            if not allowed:
                retry_after = int((1.0 - bucket["tokens"]) / refill_rate) + 1

            return allowed, {
                "tokens_remaining": int(bucket["tokens"]),
                "limit": limit,
                "window": window,
                "retry_after": retry_after,
                "refill_rate": refill_rate,
            }


class FixedWindowCounter:
    """Fixed window rate limiter implementation."""

    def __init__(self):
        self.windows: Dict[str, Dict[int, int]] = defaultdict(lambda: defaultdict(int))
        self.lock = asyncio.Lock()

    async def is_allowed(
        self, key: str, limit: int, window: int
    ) -> Tuple[bool, Dict[str, Any]]:
        """Check if request is allowed under fixed window."""
        async with self.lock:
            now = time.time()
            current_window = int(now // window)

            # Clean old windows
            user_windows = self.windows[key]
            cutoff_window = current_window - 2  # Keep 2 windows for safety
            for window_id in list(user_windows.keys()):
                if window_id < cutoff_window:
                    del user_windows[window_id]

            # Check current window
            current_requests = user_windows[current_window]
            allowed = current_requests < limit

            if allowed:
                user_windows[current_window] += 1

            # Calculate retry after
            retry_after = 0
            if not allowed:
                next_window_start = (current_window + 1) * window
                retry_after = int(next_window_start - now) + 1

            return allowed, {
                "current_requests": current_requests + (1 if allowed else 0),
                "limit": limit,
                "window": window,
                "retry_after": retry_after,
                "window_id": current_window,
            }


class RateLimiter:
    """Main rate limiter with multiple algorithm support."""

    def __init__(self):
        self.sliding_window = SlidingWindowCounter()
        self.token_bucket = TokenBucket()
        self.fixed_window = FixedWindowCounter()

        # Default rate limits for different endpoint types
        self.default_limits = {
            # 5 auth attempts per minute
            "auth": RateLimitConfig(requests=5, window=60),
            # 10 uploads per 5 minutes
            "upload": RateLimitConfig(requests=10, window=300),
            # 20 validations per hour
            "validation": RateLimitConfig(requests=20, window=3600),
            # 100 requests per minute
            "api_general": RateLimitConfig(requests=100, window=60),
            # 50 downloads per 5 minutes
            "download": RateLimitConfig(requests=50, window=300),
        }

    def get_rate_limit_key(
        self,
        request: Request,
        config: RateLimitConfig,
        user_id: Optional[str] = None,
    ) -> str:
        """Generate rate limit key based on configuration."""
        key_parts = []

        if config.per_user and user_id:
            key_parts.append(f"user:{user_id}")
        elif config.per_ip:
            # Get real IP (considering proxies)
            client_ip = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            if not client_ip:
                client_ip = request.headers.get("X-Real-IP", "")
            if not client_ip:
                client_ip = request.client.host if request.client else "unknown"
            key_parts.append(f"ip:{client_ip}")

        # Add endpoint-specific identifier
        key_parts.append(f"endpoint:{request.url.path}")

        return ":".join(key_parts)

    async def check_rate_limit(
        self,
        request: Request,
        limit_type: str,
        user_id: Optional[str] = None,
        custom_config: Optional[RateLimitConfig] = None,
    ) -> Dict[str, Any]:
        """Check if request passes rate limit."""
        config = custom_config or self.default_limits.get(
            limit_type,
            self.default_limits["api_general"],
        )

        key = self.get_rate_limit_key(request, config, user_id)

        # Choose algorithm
        if config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
            allowed, info = await self.sliding_window.is_allowed(
                key,
                config.requests,
                config.window,
            )
        elif config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
            allowed, info = await self.token_bucket.is_allowed(
                key,
                config.requests,
                config.window,
                config.burst_multiplier,
            )
        elif config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
            allowed, info = await self.fixed_window.is_allowed(
                key, config.requests, config.window
            )
        else:
            raise ValueError(f"Unknown rate limit algorithm: {config.algorithm}")

        if not allowed:
            raise RateLimitExceeded(
                f"Rate limit exceeded for {limit_type}",
                retry_after=info.get("retry_after", 60),
            )

        return info

    async def cleanup_expired_data(self):
        """Clean up expired rate limit data."""
        # This is automatically handled by the individual algorithms
        # In production with Redis, implement proper TTL


# Global rate limiter instance
rate_limiter = RateLimiter()


def rate_limit(limit_type: str, custom_config: Optional[RateLimitConfig] = None):
    """Decorator for rate limiting endpoints."""

    def decorator(func):
        async def wrapper(*args, **kwargs):
            # Extract request from args/kwargs
            request = None
            user_id = None

            for arg in args:
                if isinstance(arg, Request):
                    request = arg
                    break

            for value in kwargs.values():
                if isinstance(value, Request):
                    request = value
                    break
                # Try to extract user ID from User object
                if hasattr(value, "id") and hasattr(value, "username"):
                    user_id = value.id

            if not request:
                raise ValueError("Request object not found in endpoint parameters")

            try:
                await rate_limiter.check_rate_limit(
                    request, limit_type, user_id, custom_config
                )
            except RateLimitExceeded as e:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=e.message,
                    headers={"Retry-After": str(e.retry_after)}
                    if e.retry_after
                    else {},
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator
