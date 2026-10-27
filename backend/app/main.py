from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from backend.app.api.health import router as health_router
from backend.app.api.player import router as player_router


APP_DIR = Path(__file__).resolve().parent


app = FastAPI(
    title="Jina Classroom Jukebox",
    description="AX2 classroom jukebox API",
    version="0.1.0",
)
app.include_router(health_router)
app.include_router(player_router)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")

templates = Jinja2Templates(directory=APP_DIR / "templates")


@app.get("/", tags=["service"])
async def read_root() -> dict[str, str]:
    """Return a friendly message for people opening the server in a browser."""
    return {"message": "Jina Classroom Jukebox is running."}


@app.get("/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    """Report whether the web application process is alive."""
    return {"status": "ok"}


@app.get("/admin", response_class=HTMLResponse, tags=["admin"])
async def admin_dashboard(request: Request) -> HTMLResponse:
    """Render the practice administrator dashboard."""
    return templates.TemplateResponse(request, "admin/dashboard.html")
