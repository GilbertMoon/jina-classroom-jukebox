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
from backend.app.models import Base, ControlAuditLog, SongRequest, Track, User
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
                User(
                    name="Another Student",
                    email="another@example.com",
                    role=UserRole.STUDENT,
                    password_hash=hash_password("another-password"),
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


def test_student_can_open_dashboard_create_and_list_own_request() -> None:
    async def scenario():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            csrf_token = await login(client, "student@example.com", "student-password")
            dashboard = await client.get("/student")
            created = await client.post(
                "/api/requests",
                headers={"X-CSRF-Token": csrf_token},
                json={
                    "youtube_url": "https://youtu.be/dQw4w9WgXcQ?t=4",
                    "title": "Test Song",
                    "artist_or_channel": "Test Channel",
                    "comment": "아침에 듣고 싶어요",
                },
            )
            own_requests = await client.get("/api/requests/me")
            return dashboard, created, own_requests

    dashboard, created, own_requests = run(scenario())
    assert dashboard.status_code == 200
    assert created.status_code == 201
    assert created.json()["youtube_url"] == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert created.json()["status"] == "PENDING"
    assert [item["title"] for item in own_requests.json()] == ["Test Song"]

    with app.state.testing_session() as session:
        assert len(session.scalars(select(Track)).all()) == 1
        assert len(session.scalars(select(SongRequest)).all()) == 1


@pytest.mark.parametrize(
    "youtube_url",
    [
        "not-a-url",
        "https://example.com/watch?v=dQw4w9WgXcQ",
        "https://youtube.com.evil.example/watch?v=dQw4w9WgXcQ",
        "https://www.youtube.com/watch?v=too-short",
    ],
)
def test_invalid_youtube_url_is_rejected(youtube_url: str) -> None:
    async def scenario():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            csrf_token = await login(client, "student@example.com", "student-password")
            return await client.post(
                "/api/requests",
                headers={"X-CSRF-Token": csrf_token},
                json={"youtube_url": youtube_url, "title": "Test Song"},
            )

    assert run(scenario()).status_code == 422


def test_duplicate_request_is_rejected_and_other_student_has_private_list() -> None:
    async def scenario():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as student:
            csrf_token = await login(student, "student@example.com", "student-password")
            payload = {
                "youtube_url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
                "title": "Test Song",
            }
            first = await student.post(
                "/api/requests", json=payload, headers={"X-CSRF-Token": csrf_token}
            )
            duplicate = await student.post(
                "/api/requests", json=payload, headers={"X-CSRF-Token": csrf_token}
            )

        async with AsyncClient(transport=transport, base_url="http://test") as other:
            await login(other, "another@example.com", "another-password")
            other_list = await other.get("/api/requests/me")
        return first, duplicate, other_list

    first, duplicate, other_list = run(scenario())
    assert first.status_code == 201
    assert duplicate.status_code == 409
    assert other_list.json() == []


def test_song_request_requires_student_role_and_csrf() -> None:
    async def scenario():
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as student:
            await login(student, "student@example.com", "student-password")
            no_csrf = await student.post(
                "/api/requests",
                json={
                    "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
                    "title": "Test Song",
                },
            )
        async with AsyncClient(transport=transport, base_url="http://test") as admin:
            admin_csrf = await login(admin, "admin@example.com", "admin-password")
            admin_request = await admin.post(
                "/api/requests",
                headers={"X-CSRF-Token": admin_csrf},
                json={
                    "youtube_url": "https://youtu.be/dQw4w9WgXcQ",
                    "title": "Test Song",
                },
            )
        return no_csrf, admin_request

    no_csrf, admin_request = run(scenario())
    assert no_csrf.status_code == 403
    assert admin_request.status_code == 403


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
