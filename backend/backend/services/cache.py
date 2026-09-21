import asyncio
import time
from dataclasses import dataclass
from typing import Any, Protocol, TypeVar

T = TypeVar("T")


class CacheService(Protocol):
    async def get(self, key: str) -> Any | None: ...

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None: ...

    async def delete(self, key: str) -> None: ...

    def stats(self) -> dict[str, int]: ...


@dataclass
class CacheEntry[T]:
    value: T
    expires_at: float


class MemoryTTLCache:
    """Small process-local cache with the same interface a Redis cache can use."""

    def __init__(self) -> None:
        self._items: dict[str, CacheEntry[Any]] = {}
        self._lock = asyncio.Lock()
        self._hits = 0
        self._misses = 0

    async def get(self, key: str) -> Any | None:
        async with self._lock:
            entry = self._items.get(key)
            if entry is None or entry.expires_at <= time.monotonic():
                self._misses += 1
                self._items.pop(key, None)
                return None
            self._hits += 1
            return entry.value

    async def set(self, key: str, value: Any, ttl_seconds: int) -> None:
        async with self._lock:
            self._items[key] = CacheEntry(
                value=value,
                expires_at=time.monotonic() + ttl_seconds,
            )

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._items.pop(key, None)

    def stats(self) -> dict[str, int]:
        return {"hits": self._hits, "misses": self._misses}


cache_service = MemoryTTLCache()
