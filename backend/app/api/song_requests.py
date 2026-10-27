from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.auth_dependencies import (
    DatabaseSession,
    StudentUser,
    StudentUserWithCsrf,
)
from backend.app.models import SongRequest, Track
from backend.app.models.entities import RequestStatus
from backend.app.youtube import canonical_youtube_url, extract_youtube_video_id


router = APIRouter(prefix="/api/requests", tags=["song requests"])


class CreateSongRequest(BaseModel):
    youtube_url: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=300)
    artist_or_channel: str | None = Field(default=None, max_length=300)
    comment: str | None = Field(default=None, max_length=500)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("곡 제목을 입력해 주세요.")
        return cleaned


class SongRequestResponse(BaseModel):
    id: UUID
    youtube_url: str
    youtube_video_id: str
    title: str
    artist_or_channel: str | None
    comment: str | None
    status: RequestStatus
    reject_reason: str | None
    created_at: datetime


def response_from_model(song_request: SongRequest) -> SongRequestResponse:
    track = song_request.track
    return SongRequestResponse(
        id=song_request.id,
        youtube_url=track.source_url or "",
        youtube_video_id=track.youtube_video_id or "",
        title=track.title,
        artist_or_channel=track.artist_or_channel,
        comment=song_request.comment,
        status=song_request.status,
        reject_reason=song_request.reject_reason,
        created_at=song_request.created_at,
    )


@router.post("", response_model=SongRequestResponse, status_code=status.HTTP_201_CREATED)
async def create_song_request(
    payload: CreateSongRequest,
    user: StudentUserWithCsrf,
    db: DatabaseSession,
):
    video_id = extract_youtube_video_id(payload.youtube_url)
    if video_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="올바른 YouTube 영상 주소를 입력해 주세요.",
        )

    track = db.scalar(select(Track).where(Track.youtube_video_id == video_id))
    if track is None:
        track = Track(
            youtube_video_id=video_id,
            source_url=canonical_youtube_url(video_id),
            title=payload.title,
            artist_or_channel=(payload.artist_or_channel or "").strip() or None,
        )
        db.add(track)
        db.flush()

    duplicate = db.scalar(
        select(SongRequest).where(
            SongRequest.user_id == user.id,
            SongRequest.track_id == track.id,
        )
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 신청한 YouTube 영상입니다.",
        )

    song_request = SongRequest(
        user_id=user.id,
        track_id=track.id,
        comment=(payload.comment or "").strip() or None,
    )
    db.add(song_request)
    db.commit()
    db.refresh(song_request)
    song_request.track = track
    return response_from_model(song_request)


@router.get("/me", response_model=list[SongRequestResponse])
async def list_my_song_requests(user: StudentUser, db: DatabaseSession):
    requests = db.scalars(
        select(SongRequest)
        .options(selectinload(SongRequest.track))
        .where(SongRequest.user_id == user.id)
        .order_by(SongRequest.created_at.desc())
    ).all()
    return [response_from_model(item) for item in requests]
