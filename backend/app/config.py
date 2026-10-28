import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()


DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://jukebox:jukebox@localhost:5432/jukebox"
)


def get_database_url() -> str:
    """Read the database address at runtime so tests can safely override it."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)


def get_media_root() -> Path:
    """Return the private directory used for authorized local audio files."""
    return Path(os.getenv("MEDIA_ROOT", "media")).resolve()


def get_max_media_size_bytes() -> int:
    """Convert the upload limit from megabytes to bytes."""
    return int(os.getenv("MAX_MEDIA_SIZE_MB", "50")) * 1024 * 1024
