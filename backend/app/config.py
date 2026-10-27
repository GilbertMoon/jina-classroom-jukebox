import os

from dotenv import load_dotenv


load_dotenv()


DEFAULT_DATABASE_URL = (
    "postgresql+psycopg://jukebox:jukebox@localhost:5432/jukebox"
)


def get_database_url() -> str:
    """Read the database address at runtime so tests can safely override it."""
    return os.getenv("DATABASE_URL", DEFAULT_DATABASE_URL)
