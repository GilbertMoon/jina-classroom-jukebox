from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.api.song_requests import (
    SongRequestResponse,
    create_or_resubmit_request,
    response_from_model,
)
from backend.app.auth_dependencies import DatabaseSession, StudentUser, StudentUserWithCsrf
from backend.app.models import Track, WishListItem
from backend.app.youtube import canonical_youtube_url, extract_youtube_video_id


router = APIRouter(prefix="/api/wishlist", tags=["wish list"])


class CreateWishListItem(BaseModel):
    youtube_url: str = Field(min_length=1, max_length=2048)
    title: str = Field(min_length=1, max_length=300)
    artist_or_channel: str | None = Field(default=None, max_length=300)

    @field_validator("title")
    @classmethod
    def title_must_not_be_blank(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("곡 제목을 입력해 주세요.")
        return cleaned


class WishListItemResponse(BaseModel):
    id: UUID
    youtube_url: str
    youtube_video_id: str
    title: str
    artist_or_channel: str | None
    created_at: datetime


def response_from_wish(item: WishListItem) -> WishListItemResponse:
    return WishListItemResponse(
        id=item.id,
        youtube_url=item.track.source_url or "",
        youtube_video_id=item.track.youtube_video_id or "",
        title=item.track.title,
        artist_or_channel=item.track.artist_or_channel,
        created_at=item.created_at,
    )


@router.post("", response_model=WishListItemResponse, status_code=status.HTTP_201_CREATED)
async def create_wish_list_item(
    payload: CreateWishListItem, user: StudentUserWithCsrf, db: DatabaseSession
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
        select(WishListItem).where(
            WishListItem.user_id == user.id,
            WishListItem.track_id == track.id,
        )
    )
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="이미 Wish List에 담긴 영상입니다.")
    item = WishListItem(user_id=user.id, track_id=track.id)
    db.add(item)
    db.commit()
    db.refresh(item)
    item.track = track
    return response_from_wish(item)


@router.get("/me", response_model=list[WishListItemResponse])
async def list_my_wish_list(user: StudentUser, db: DatabaseSession):
    items = db.scalars(
        select(WishListItem)
        .options(selectinload(WishListItem.track))
        .where(WishListItem.user_id == user.id)
        .order_by(WishListItem.created_at.desc())
    ).all()
    return [response_from_wish(item) for item in items]


def owned_wish_item(db, item_id: UUID, user_id: UUID) -> WishListItem:
    item = db.scalar(
        select(WishListItem)
        .options(selectinload(WishListItem.track))
        .where(WishListItem.id == item_id, WishListItem.user_id == user_id)
    )
    if item is None:
        raise HTTPException(status_code=404, detail="Wish List 항목을 찾을 수 없습니다.")
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_wish_list_item(
    item_id: UUID, user: StudentUserWithCsrf, db: DatabaseSession
):
    item = owned_wish_item(db, item_id, user.id)
    db.delete(item)
    db.commit()


@router.post("/{item_id}/request", response_model=SongRequestResponse)
async def convert_wish_to_request(
    item_id: UUID, user: StudentUserWithCsrf, db: DatabaseSession
):
    item = owned_wish_item(db, item_id, user.id)
    track = item.track
    song_request = create_or_resubmit_request(db, user.id, track)
    db.delete(item)
    db.commit()
    db.refresh(song_request)
    song_request.track = track
    return response_from_model(song_request)
