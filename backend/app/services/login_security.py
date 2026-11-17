import math
import os
import time
from collections import deque
from threading import Lock

from fastapi import Request


class LoginAttemptLimiter:
    """Limit repeated login failures without storing submitted passwords."""

    def __init__(self) -> None:
        self._failures: dict[str, deque[float]] = {}
        self._lock = Lock()

    @property
    def max_attempts(self) -> int:
        return max(1, int(os.getenv("LOGIN_MAX_ATTEMPTS", "5")))

    @property
    def window_seconds(self) -> int:
        return max(1, int(os.getenv("LOGIN_WINDOW_SECONDS", "300")))

    @property
    def max_tracked_keys(self) -> int:
        return max(1, int(os.getenv("LOGIN_MAX_TRACKED_KEYS", "10000")))

    @property
    def tracked_key_count(self) -> int:
        with self._lock:
            return len(self._failures)

    def key(self, request: Request, email: str) -> str:
        client_host = request.client.host if request.client else "unknown"
        return f"{client_host}:{email.strip().lower()}"

    def _remove_expired(self, failures: deque[float], now: float) -> None:
        cutoff = now - self.window_seconds
        while failures and failures[0] <= cutoff:
            failures.popleft()

    def _prune_expired(self, now: float) -> None:
        for key, failures in list(self._failures.items()):
            self._remove_expired(failures, now)
            if not failures:
                self._failures.pop(key, None)

    def retry_after(self, key: str) -> int | None:
        now = time.monotonic()
        with self._lock:
            self._prune_expired(now)
            failures = self._failures.get(key)
            if failures is None:
                return None
            if len(failures) < self.max_attempts:
                return None
            return max(1, math.ceil(self.window_seconds - (now - failures[0])))

    def record_failure(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            self._prune_expired(now)
            failures = self._failures.get(key)
            if failures is None:
                if len(self._failures) >= self.max_tracked_keys:
                    self._failures.pop(next(iter(self._failures)))
                failures = deque()
                self._failures[key] = failures
            failures.append(now)

    def record_success(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset(self) -> None:
        """Clear in-memory state for isolated tests."""
        with self._lock:
            self._failures.clear()


login_attempt_limiter = LoginAttemptLimiter()
