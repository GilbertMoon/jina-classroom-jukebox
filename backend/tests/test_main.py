import asyncio

from httpx import ASGITransport, AsyncClient

from backend.app.main import app


async def get(path: str):
    """Call the FastAPI app in memory without opening a network port."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.get(path)


def test_read_root() -> None:
    response = asyncio.run(get("/"))

    assert response.status_code == 200
    assert response.json() == {"message": "Jina Classroom Jukebox is running."}


def test_health_live() -> None:
    response = asyncio.run(get("/health/live"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
