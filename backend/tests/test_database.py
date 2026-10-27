from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, func, inspect, select
from sqlalchemy.orm import Session

from backend.app.models import Base, Track, User
from backend.app.models.entities import MediaStatus, UserRole
from backend.app.seed import seed_demo_data


EXPECTED_TABLES = {
    "alembic_version",
    "control_audit_logs",
    "playback_events",
    "playlist_items",
    "playlists",
    "schedules",
    "requests",
    "system_settings",
    "tracks",
    "users",
}


def test_models_can_be_saved_and_loaded() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        session.add(
            User(name="Jina", email="jina@example.com", role=UserRole.ADMIN)
        )
        session.add(
            Track(title="Test Track", media_status=MediaStatus.NOT_AVAILABLE)
        )
        session.commit()

    with Session(engine) as session:
        assert session.scalar(select(User).where(User.email == "jina@example.com"))
        assert session.scalar(select(Track).where(Track.title == "Test Track"))


def test_demo_seed_is_repeatable() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as session:
        seed_demo_data(session)
        seed_demo_data(session)

        assert session.scalar(select(func.count()).select_from(User)) == 2
        assert session.scalar(select(func.count()).select_from(Track)) == 1


def test_initial_migration_upgrades_and_downgrades(
    tmp_path: Path, monkeypatch
) -> None:
    database_path = tmp_path / "migration-test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite+pysqlite:///{database_path.as_posix()}")
    config = Config("alembic.ini")

    command.upgrade(config, "head")
    engine = create_engine(f"sqlite+pysqlite:///{database_path.as_posix()}")
    assert set(inspect(engine).get_table_names()) == EXPECTED_TABLES

    command.downgrade(config, "base")
    assert inspect(engine).get_table_names() == ["alembic_version"]
