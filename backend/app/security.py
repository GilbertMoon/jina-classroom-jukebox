import secrets

from pwdlib import PasswordHash


password_hash = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hash.hash("not-a-real-user-password")


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, stored_hash: str | None) -> bool:
    """Verify every attempt, including unknown users, to reduce timing leaks."""
    return password_hash.verify(password, stored_hash or DUMMY_PASSWORD_HASH)


def new_csrf_token() -> str:
    return secrets.token_urlsafe(32)
