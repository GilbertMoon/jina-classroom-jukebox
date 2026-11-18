import pytest
from pydantic import ValidationError

from backend.app.api.auth import RegisterRequest


@pytest.mark.parametrize(
    "email",
    [
        "plain-address",
        "missing-domain@",
        "@missing-local.example",
        "two@@example.com",
        "spaces are@example.com",
        "student@example..com",
    ],
)
def test_registration_rejects_invalid_email_formats(email: str) -> None:
    with pytest.raises(ValidationError):
        RegisterRequest(name="Student", email=email, password="valid-password")


def test_registration_accepts_and_normalizes_valid_email() -> None:
    request = RegisterRequest(
        name="Student",
        email="Student@Example.COM",
        password="valid-password",
    )
    assert str(request.email) == "Student@example.com"
