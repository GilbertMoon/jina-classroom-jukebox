import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from backend.app.api.auth import router as auth_router
from backend.app.api.health import router as health_router
from backend.app.api.media import router as media_router
from backend.app.api.player import router as player_router
from backend.app.api.playlists import router as playlists_router
from backend.app.api.song_requests import router as song_requests_router
from backend.app.api.schedules import router as schedules_router
from backend.app.api.tracks import router as tracks_router
from backend.app.auth_dependencies import require_admin, require_student
from backend.app.models import User
from backend.app.services.scheduler import start_schedule_service, stop_schedule_service


APP_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler_enabled = os.getenv("SCHEDULER_ENABLED", "true").lower() == "true"
    if scheduler_enabled:
        start_schedule_service()
    yield
    if scheduler_enabled:
        stop_schedule_service()


app = FastAPI(
    title="Jina Classroom Jukebox",
    description="AX2 classroom jukebox API",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SESSION_SECRET", "development-only-change-me"),
    session_cookie="jukebox_session",
    max_age=60 * 60 * 8,
    same_site="lax",
    https_only=os.getenv("APP_ENV") == "production",
)
app.include_router(auth_router)
app.include_router(health_router)
app.include_router(media_router)
app.include_router(player_router)
app.include_router(playlists_router)
app.include_router(song_requests_router)
app.include_router(schedules_router)
app.include_router(tracks_router)
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
async def admin_dashboard(
    request: Request, user: User = Depends(require_admin)
) -> HTMLResponse:
    """Render the practice administrator dashboard."""
    return templates.TemplateResponse(
        request,
        "admin/dashboard.html",
        {"user": user, "csrf_token": request.session["csrf_token"]},
    )


@app.get("/login", response_class=HTMLResponse, tags=["authentication"])
async def login_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "login.html")


@app.get("/student", response_class=HTMLResponse, tags=["student"])
async def student_dashboard(
    request: Request, user: User = Depends(require_student)
) -> HTMLResponse:
    return templates.TemplateResponse(
        request,
        "student/dashboard.html",
        {"user": user, "csrf_token": request.session["csrf_token"]},
    )
