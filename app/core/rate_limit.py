from __future__ import annotations

import time
from collections import deque
from dataclasses import dataclass
from threading import Lock
from typing import Deque, Dict, Tuple

from fastapi import Depends, HTTPException, Request, status


@dataclass
class _Bucket:
    hits: Deque[float]
    last_seen: float


class MemoryRateLimiter:
    """Very small in-process rate limiter.

    Notes:
    - Good enough for dev/single-process deployments.
    - For multi-worker / multi-replica production, use Redis-backed limiter.
    """

    def __init__(self, *, max_keys: int = 20_000) -> None:
        self._max_keys = max_keys
        self._lock = Lock()
        self._buckets: Dict[str, _Bucket] = {}

    def hit(self, key: str, *, limit: int, window_seconds: int) -> Tuple[bool, int]:
        now = time.monotonic()
        window_start = now - float(window_seconds)

        with self._lock:
            bucket = self._buckets.get(key)
            if bucket is None:
                bucket = _Bucket(hits=deque(), last_seen=now)
                self._buckets[key] = bucket

            bucket.last_seen = now
            hits = bucket.hits

            # Drop old hits.
            while hits and hits[0] <= window_start:
                hits.popleft()

            if len(hits) >= int(limit):
                retry_after = int(window_seconds - (now - hits[0])) + 1
                return False, max(1, retry_after)

            hits.append(now)

            # Very simple cleanup if map grows too large.
            if len(self._buckets) > self._max_keys:
                self._cleanup(now, ttl_seconds=window_seconds * 10)

            return True, 0

    def _cleanup(self, now: float, *, ttl_seconds: int) -> None:
        cutoff = now - float(ttl_seconds)
        to_del = [k for k, b in self._buckets.items() if b.last_seen < cutoff]
        for k in to_del:
            self._buckets.pop(k, None)


_limiter = MemoryRateLimiter()


def _client_ip(request: Request) -> str:
    # Respect proxies if configured to pass X-Forwarded-For
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    if request.client:
        return request.client.host
    return "unknown"


def rate_limit(scope: str, *, limit: int, window_seconds: int):
    """Dependency factory: apply simple rate limits to endpoints."""

    def _dep(request: Request) -> None:
        ip = _client_ip(request)
        key = f"{scope}:{ip}"
        ok, retry_after = _limiter.hit(key, limit=limit, window_seconds=window_seconds)
        if not ok:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests",
                headers={"Retry-After": str(retry_after)},
            )

    return Depends(_dep)


# Test helper

def _reset_for_tests() -> None:
    """Clear limiter state (used by tests)."""
    with _limiter._lock:  # type: ignore[attr-defined]
        _limiter._buckets.clear()  # type: ignore[attr-defined]
