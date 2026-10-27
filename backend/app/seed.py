from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models import Track, User
from backend.app.models.entities import MediaStatus, UserRole


def seed_demo_data(session: Session) -> None:
    """Create a small, repeatable development dataset."""
    admin = session.scalar(select(User).where(User.email == "admin@jukebox.local"))
    if admin is None:
        session.add(
            User(
                name="Demo Admin",
                email="admin@jukebox.local",
                role=UserRole.ADMIN,
            )
        )

    track = session.scalar(
        select(Track).where(Track.youtube_video_id == "demo-track")
    )
    if track is None:
        session.add(
            Track(
                youtube_video_id="demo-track",
                title="Authorized Test Track",
                artist_or_channel="AX2 Studio",
                duration_seconds=30,
                media_status=MediaStatus.NOT_AVAILABLE,
                rights_status="DEMO_METADATA_ONLY",
            )
        )

    session.commit()
