import asyncio

from httpx import ASGITransport, AsyncClient
import pytest

from backend.app.api.player import player
from backend.app.main import app


async def get(path: str):
    """Call the FastAPI app in memory without opening a network port."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


async def request(method: str, path: str, json: dict | None = None):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.request(method, path, json=json)


@pytest.fixture(autouse=True)
def reset_fake_player() -> None:
    player.reset()


def test_read_root() -> None:
    response = asyncio.run(get("/"))

    assert response.status_code == 200
    assert response.json() == {"message": "Jina Classroom Jukebox is running."}


def test_health_live() -> None:
    response = asyncio.run(get("/health/live"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_admin_dashboard() -> None:
    response = asyncio.run(get("/admin"))

    assert response.status_code == 200
    assert "Jina Jukebox" in response.text
    assert "모의 관리자 플레이어" in response.text


def test_player_controls() -> None:
    initial = asyncio.run(get("/api/player/status")).json()
    playing = asyncio.run(
        request("POST", "/api/player/control", {"action": "play"})
    ).json()
    next_track = asyncio.run(
        request("POST", "/api/player/control", {"action": "next"})
    ).json()
    paused = asyncio.run(
        request("POST", "/api/player/control", {"action": "pause"})
    ).json()

    assert initial["playback_state"] == "stopped"
    assert playing["playback_state"] == "playing"
    assert next_track["current_track"]["id"] != initial["current_track"]["id"]
    assert paused["playback_state"] == "paused"


def test_volume_and_mute_controls() -> None:
    volume_response = asyncio.run(
        request("PUT", "/api/player/volume", {"volume": 42})
    )
    mute_response = asyncio.run(request("PUT", "/api/player/mute", {"muted": True}))

    assert volume_response.status_code == 200
    assert volume_response.json()["volume"] == 42
    assert mute_response.json()["muted"] is True


@pytest.mark.parametrize("volume", [-1, 101])
def test_invalid_volume_is_rejected(volume: int) -> None:
    response = asyncio.run(request("PUT", "/api/player/volume", {"volume": volume}))

    assert response.status_code == 422
