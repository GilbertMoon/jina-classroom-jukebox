from fastapi import FastAPI


app = FastAPI(
    title="Jina Classroom Jukebox",
    description="AX2 classroom jukebox API",
    version="0.1.0",
)


@app.get("/", tags=["service"])
async def read_root() -> dict[str, str]:
    """Return a friendly message for people opening the server in a browser."""
    return {"message": "Jina Classroom Jukebox is running."}


@app.get("/health/live", tags=["health"])
async def health_live() -> dict[str, str]:
    """Report whether the web application process is alive."""
    return {"status": "ok"}
