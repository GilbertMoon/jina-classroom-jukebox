import asyncio
from collections.abc import Generator

from httpx import ASGITransport, AsyncClient
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.app.api import health
from backend.app.api.player import player
from backend.app.database import get_db
from backend.app.main import app
from backend.app.models import Base, ControlAuditLog, User
from backend.app.models.entities import UserRole
from backend.app.security import hash_password


@pytest.fixture(autouse=True)
def isolated_database() -> Generator[None, None, None]:
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, expire_on_commit=False)
    Base.metadata.create_all(engine)

    with testing_session() as session:
        session.add_all(
            [
                User(
                    name="Admin",
                    email="admin@example.com",
                    role=UserRole.ADMIN,
                    password_hash=hash_password("admin-password"),
                ),
                User(
                    name="Student",
                    email="student@example.com",
                    role=UserRole.STUDENT,
                    password_hash=hash_password("student-password"),
                ),
            ]
        )
        session.commit()

    def override_get_db():
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    app.state.testing_session = testing_session
    player.reset()
    yield
    app.dependency_overrides.clear()
    del app.state.testing_session
    Base.metadata.drop_all(engine)
    engine.dispose()


def run(coroutine):
    return asyncio.run(coroutine)


async def get(path: str):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def login(client: AsyncClient, email: str, password: str) -> str:
    response = await client.post(
        "/api/auth/login", json={"email": email, "password": password}
    )
    assert response.status_code == 200
    return response.json()["csrf_token"]


def test_read_root() -> None:
    response = run(get("/"))
    assert response.status_code == 200


def test_health_live() -> None:
    response = run(get("/health/live"))
    assert response.status_code == 200


def test_health_ready_when_database_is_available(monkeypatch) -> None:
    monkeypatch.setattr(health, "engine", create_engine("sqlite+pysqlite:///:memory:"))
    assert run(get("/health/ready")).status_code == 200


def test_health_ready_when_database_is_unavailable(monkeypatch) -> None:
    class UnavailableEngine:
        def connect(self):
            raise OperationalError("SELECT 1", {}, Exception("offline"))

    monkeypatch.setattr(health, "engine", UnavailableEngine())
    assert run(get("/health/ready")).status_code == 503


def test_login_page_is_public() -> None:
    response = run(get("/login"))
    assert response.status_code == 200
    assert "Jina Jukebox 로그인" in response.text


def test_invalid_login_uses_generic_error() -> None:
    async def scenario():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/auth/login",
                json={"email": "missing@example.com", "password": "wrong-password"},
            )

    response = run(scenario())
    assert response.status_code == 401
    assert response.json()["detail"] == "이메일 또는 비밀번호가 올바르지 않습니다."


def test_admin_can_login_open_dashboard_and_logout() -> None:
    async def scenario():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            csrf_token = await login(client, "admin@example.com", "admin-password")
            me = await client.get("/api/auth/me")
            dashboard = await client.get("/admin")
            logout = await client.post(
                "/api/auth/logout", headers={"X-CSRF-Token": csrf_token}
            )
            after_logout = await client.get("/api/auth/me")
            return me, dashboard, logout, after_logout

    me, dashboard, logout, after_logout = run(scenario())
    assert me.json()["role"] == "ADMIN"
    assert dashboard.status_code == 200
    assert logout.status_code == 200
    assert after_logout.status_code == 401


def test_anonymous_user_cannot_read_player_status() -> None:
    assert run(get("/api/player/status")).status_code == 401


def test_student_can_read_status_but_cannot_control_player() -> None:
    async def scenario():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            csrf_token = await login(client, "student@example.com", "student-password")
            current_status = await client.get("/api/player/status")
            control = await client.post(
                "/api/player/control",
                json={"action": "play"},
                headers={"X-CSRF-Token": csrf_token},
            )
            return current_status, control

    current_status, control = run(scenario())
    assert current_status.status_code == 200
    assert control.status_code == 403


def test_admin_control_requires_csrf_and_creates_audit_log() -> None:
    async def scenario():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            csrf_token = await login(client, "admin@example.com", "admin-password")
            without_csrf = await client.post(
                "/api/player/control", json={"action": "play"}
            )
            with_csrf = await client.post(
                "/api/player/control",
                json={"action": "play"},
                headers={"X-CSRF-Token": csrf_token},
            )
            return without_csrf, with_csrf

    without_csrf, with_csrf = run(scenario())
    assert without_csrf.status_code == 403
    assert with_csrf.status_code == 200

    with app.state.testing_session() as session:
        audit_log = session.scalar(select(ControlAuditLog))
        assert audit_log is not None
        assert audit_log.action == "player.play"


@pytest.mark.parametrize("volume", [-1, 101])
def test_invalid_volume_is_rejected(volume: int) -> None:
    async def scenario():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            csrf_token = await login(client, "admin@example.com", "admin-password")
            return await client.put(
                "/api/player/volume",
                json={"volume": volume},
                headers={"X-CSRF-Token": csrf_token},
            )

    assert run(scenario()).status_code == 422
