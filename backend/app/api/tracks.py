from uuid import UUID

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select

from backend.app.auth_dependencies import CurrentUser, DatabaseSession
from backend.app.models import Track
from backend.app.models.entities import MediaStatus


router = APIRouter(prefix="/api/tracks", tags=["tracks"])


class ReadyTrackResponse(BaseModel):
    id: UUID
    title: str
    artist_or_channel: str | None
    duration_seconds: int | None
    media_status: MediaStatus


@router.get("", response_model=list[ReadyTrackResponse])
async def list_ready_tracks(user: CurrentUser, db: DatabaseSession):
    tracks = db.scalars(
        select(Track)
        .where(Track.media_status == MediaStatus.READY)
        .order_by(Track.title, Track.created_at)
    ).all()
    return [
        ReadyTrackResponse(
            id=track.id,
            title=track.title,
            artist_or_channel=track.artist_or_channel,
            duration_seconds=track.duration_seconds,
            media_status=track.media_status,
        )
        for track in tracks
    ]
