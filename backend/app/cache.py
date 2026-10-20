from copy import deepcopy
from threading import Lock
from time import monotonic


class TTLCache:
    """Thread-safe in-memory cache with automatic expiration."""

    def __init__(self, ttl_seconds: int = 300):
        self.ttl_seconds = ttl_seconds
        self._items = {}
        self._lock = Lock()

    def get(self, key: str):
        """Return a cached value, or None if missing or expired."""
        with self._lock:
            item = self._items.get(key)

            if item is None:
                return None

            expires_at, value = item

            if monotonic() >= expires_at:
                del self._items[key]
                return None

            return deepcopy(value)

    def set(self, key: str, value):
        """Cache a value for the configured TTL."""
        with self._lock:
            self._items[key] = (
                monotonic() + self.ttl_seconds,
                deepcopy(value),
            )

    def delete(self, key: str):
        """Remove a specific cache entry."""
        with self._lock:
            self._items.pop(key, None)

    def clear(self):
        """Remove all cached entries."""
        with self._lock:
            self._items.clear()


analysis_cache = TTLCache(ttl_seconds=300)