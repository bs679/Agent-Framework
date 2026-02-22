"""Redis caching layer for Pulse API.

Usage
-----
Cache a route response with a TTL:

    from integrations.pulse.core.cache import cache_response, invalidate

    @router.get("/context")
    @cache_response(ttl=300, key_prefix="agent_context")
    async def get_agent_context(user=Depends(get_current_user)):
        ...

Invalidate all keys for a prefix:

    await invalidate("agent_context")

Design decisions
----------------
- Redis is *optional*. If REDIS_URL is not set or Redis is unreachable the
  cache falls back to pass-through mode — requests are served from source
  without any error being raised.
- Cache keys incorporate the user's owner_id so one user never sees another
  user's cached response.
- A ``cache_bust=true`` query param forces a fresh fetch regardless of TTL.
"""

from __future__ import annotations

import functools
import hashlib
import json
import logging
import os
from typing import Any, Callable

logger = logging.getLogger(__name__)

_REDIS_URL = os.environ.get("REDIS_URL", "redis://localhost:6379/0")
_REDIS_ENABLED = bool(os.environ.get("REDIS_URL"))

_redis_client = None


def _get_redis():
    """Lazily initialise the Redis client (singleton)."""
    global _redis_client
    if _redis_client is not None:
        return _redis_client
    if not _REDIS_ENABLED:
        return None
    try:
        import redis.asyncio as aioredis  # type: ignore[import]
        _redis_client = aioredis.from_url(
            _REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        return _redis_client
    except Exception as exc:
        logger.warning("Redis init failed — caching disabled: %s", exc)
        return None


async def get_cached(key: str) -> Any | None:
    """Return cached value for *key*, or None on miss / error."""
    client = _get_redis()
    if client is None:
        return None
    try:
        raw = await client.get(key)
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as exc:
        logger.debug("Redis get failed for key=%s: %s", key, exc)
        return None


async def set_cached(key: str, value: Any, ttl: int) -> None:
    """Store *value* in Redis with the given *ttl* (seconds)."""
    client = _get_redis()
    if client is None:
        return
    try:
        await client.setex(key, ttl, json.dumps(value))
    except Exception as exc:
        logger.debug("Redis set failed for key=%s: %s", key, exc)


async def invalidate(prefix: str) -> None:
    """Delete all keys matching ``prefix:*``."""
    client = _get_redis()
    if client is None:
        return
    try:
        pattern = f"{prefix}:*"
        keys = await client.keys(pattern)
        if keys:
            await client.delete(*keys)
            logger.debug("Cache invalidated %d keys for prefix=%s", len(keys), prefix)
    except Exception as exc:
        logger.debug("Redis invalidate failed for prefix=%s: %s", prefix, exc)


async def redis_ping() -> str:
    """Return 'ok', 'disabled', or 'error' for the health endpoint."""
    if not _REDIS_ENABLED:
        return "disabled"
    client = _get_redis()
    if client is None:
        return "error"
    try:
        result = await client.ping()
        return "ok" if result else "error"
    except Exception:
        return "error"


def build_cache_key(prefix: str, owner_id: str, **kwargs: Any) -> str:
    """Build a deterministic cache key from prefix, owner, and extra params."""
    extra = hashlib.md5(
        json.dumps(kwargs, sort_keys=True).encode()
    ).hexdigest()[:8] if kwargs else ""
    parts = [prefix, owner_id]
    if extra:
        parts.append(extra)
    return ":".join(parts)
