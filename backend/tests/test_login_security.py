from backend.app.services import login_security
from backend.app.services.login_security import LoginAttemptLimiter


def test_unknown_lookup_does_not_create_memory_entry() -> None:
    limiter = LoginAttemptLimiter()
    assert limiter.retry_after("unknown") is None
    assert limiter.tracked_key_count == 0


def test_expired_entries_are_removed(monkeypatch) -> None:
    now = 100.0
    monkeypatch.setenv("LOGIN_WINDOW_SECONDS", "10")
    monkeypatch.setattr(login_security.time, "monotonic", lambda: now)
    limiter = LoginAttemptLimiter()
    limiter.record_failure("first")
    assert limiter.tracked_key_count == 1
    now = 111.0
    assert limiter.retry_after("another") is None
    assert limiter.tracked_key_count == 0


def test_tracked_keys_are_bounded(monkeypatch) -> None:
    monkeypatch.setenv("LOGIN_MAX_TRACKED_KEYS", "2")
    limiter = LoginAttemptLimiter()
    limiter.record_failure("first")
    limiter.record_failure("second")
    limiter.record_failure("third")
    assert limiter.tracked_key_count == 2
