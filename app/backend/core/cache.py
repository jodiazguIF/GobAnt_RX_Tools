import time
from typing import Callable, Any

class TTLCache:
    """Very small in-memory TTL cache."""

    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str, loader: Callable[[], Any]) -> Any:
        value, expires = self._store.get(key, (None, 0))
        now = time.time()
        if expires > now:
            return value
        value = loader()
        self._store[key] = (value, now + self.ttl)
        return value
