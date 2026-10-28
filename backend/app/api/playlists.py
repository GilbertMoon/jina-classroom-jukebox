from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import func, select, update
from sqlalchemy.orm import selectinload

from backend.app.auth_dependencies import (
    AdminUserWithCsrf,
    CurrentUser,
    DatabaseSession,
)
from backend.app.models import ControlAuditLog, Playlist, PlaylistItem, Track
from backend.app.models.entities import MediaStatus


router = APIRouter(prefix="/api/playlists", tags=["playlists"])


class CreatePlaylist(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("플레이리스트 이름을 입력해 주세요.")
        return cleaned


class UpdatePlaylistItems(BaseModel):
    track_ids: list[UUID] = Field(max_length=200)


class PlaylistTrackResponse(BaseModel):
    id: UUID
    position: int
    title: str
    artist_or_channel: str | None
    duration_seconds: int | None


class PlaylistResponse(BaseModel):
    id: UUID
    name: str
    description: str | None
    is_active: bool
    items: list[PlaylistTrackResponse]


def response_from_playlist(playlist: Playlist) -> PlaylistResponse:
    ordered_items = sorted(playlist.items, key=lambda item: item.position)
    return PlaylistResponse(
        id=playlist.id,
        name=playlist.name,
        description=playlist.description,
        is_active=playlist.is_active,
        items=[
            PlaylistTrackResponse(
                id=item.track.id,
                position=item.position,
                title=item.track.title,
                artist_or_channel=item.track.artist_or_channel,
                duration_seconds=item.track.duration_seconds,
            )
            for item in ordered_items
        ],
    )


def playlist_query():
    return select(Playlist).options(
        selectinload(Playlist.items).selectinload(PlaylistItem.track)
    )


@router.get("", response_model=list[PlaylistResponse])
async def list_playlists(user: CurrentUser, db: DatabaseSession):
    playlists = db.scalars(
        playlist_query().order_by(Playlist.is_active.desc(), Playlist.created_at.desc())
    ).all()
    return [response_from_playlist(playlist) for playlist in playlists]


@router.post("", response_model=PlaylistResponse, status_code=status.HTTP_201_CREATED)
async def create_playlist(
    payload: CreatePlaylist,
    user: AdminUserWithCsrf,
    db: DatabaseSession,
):
    duplicate = db.scalar(
        select(Playlist).where(func.lower(Playlist.name) == payload.name.lower())
    )
    if duplicate is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="같은 이름의 플레이리스트가 이미 있습니다.",
        )
    playlist = Playlist(
        name=payload.name,
        description=(payload.description or "").strip() or None,
        created_by=user.id,
        items=[],
    )
    db.add(playlist)
    db.flush()
    db.add(
        ControlAuditLog(
            admin_id=user.id,
            action="playlist.create",
            payload={"playlist_id": str(playlist.id), "name": playlist.name},
        )
    )
    db.commit()
    return response_from_playlist(playlist)


@router.put("/{playlist_id}/items", response_model=PlaylistResponse)
async def replace_playlist_items(
    playlist_id: UUID,
    payload: UpdatePlaylistItems,
    user: AdminUserWithCsrf,
    db: DatabaseSession,
):
    playlist = db.scalar(playlist_query().where(Playlist.id == playlist_id))
    if playlist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="플레이리스트를 찾을 수 없습니다.",
        )
    if len(payload.track_ids) != len(set(payload.track_ids)):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="같은 곡을 한 플레이리스트에 중복 편성할 수 없습니다.",
        )

    tracks = db.scalars(select(Track).where(Track.id.in_(payload.track_ids))).all()
    tracks_by_id = {track.id: track for track in tracks}
    if len(tracks_by_id) != len(payload.track_ids):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="선택한 곡 중 찾을 수 없는 곡이 있습니다.",
        )
    if any(track.media_status != MediaStatus.READY for track in tracks):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="재생 준비가 끝난 곡만 편성할 수 있습니다.",
        )

    playlist.items.clear()
    db.flush()
    playlist.items.extend(
        PlaylistItem(track=tracks_by_id[track_id], position=index)
        for index, track_id in enumerate(payload.track_ids, start=1)
    )
    db.add(
        ControlAuditLog(
            admin_id=user.id,
            action="playlist.items.update",
            payload={
                "playlist_id": str(playlist.id),
                "track_ids": [str(track_id) for track_id in payload.track_ids],
            },
        )
    )
    db.commit()
    return response_from_playlist(playlist)


@router.post("/{playlist_id}/activate", response_model=PlaylistResponse)
async def activate_playlist(
    playlist_id: UUID,
    user: AdminUserWithCsrf,
    db: DatabaseSession,
):
    playlist = db.scalar(playlist_query().where(Playlist.id == playlist_id))
    if playlist is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="플레이리스트를 찾을 수 없습니다.",
        )
    if not playlist.items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="곡이 없는 플레이리스트는 활성화할 수 없습니다.",
        )

    db.execute(update(Playlist).values(is_active=False))
    playlist.is_active = True
    db.add(
        ControlAuditLog(
            admin_id=user.id,
            action="playlist.activate",
            payload={"playlist_id": str(playlist.id)},
        )
    )
    db.commit()
    return response_from_playlist(playlist)
