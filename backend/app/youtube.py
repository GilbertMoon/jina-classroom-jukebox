import re
from urllib.parse import parse_qs, urlparse


VIDEO_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]{11}$")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}


def extract_youtube_video_id(value: str) -> str | None:
    """Return a normalized YouTube video ID from a supported public URL."""
    try:
        parsed = urlparse(value.strip())
    except ValueError:
        return None

    if parsed.scheme not in {"http", "https"}:
        return None

    host = (parsed.hostname or "").lower()
    candidate: str | None = None
    if host in YOUTUBE_HOSTS and parsed.path == "/watch":
        candidate = parse_qs(parsed.query).get("v", [None])[0]
    elif host == "youtu.be":
        candidate = parsed.path.removeprefix("/").split("/", 1)[0]
    elif host in YOUTUBE_HOSTS:
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) == 2 and parts[0] in {"shorts", "embed"}:
            candidate = parts[1]

    return candidate if candidate and VIDEO_ID_PATTERN.fullmatch(candidate) else None


def canonical_youtube_url(video_id: str) -> str:
    return f"https://www.youtube.com/watch?v={video_id}"
