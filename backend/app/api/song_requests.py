from datetime import datetime
from enum import StrEnum
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.auth_dependencies import (
    AdminUser,
    AdminUserWithCsrf,
    DatabaseSession,
    StudentUser,
    StudentUserWithCsrf,
)
from backend.app.models import ControlAuditLog, SongRequest, Track
from backend.app.models.entities import MediaStatus, RequestStatus, utc_now
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


class RequesterSummary(BaseModel):
    name: str
    email: str
    status: RequestStatus


class AdminSongRequestResponse(SongRequestResponse):
    track_id: UUID
    media_status: MediaStatus
    media_original_filename: str | None
    requester_name: str
    requester_email: str
    request_count: int
    requesters: list[RequesterSummary]
    reviewed_at: datetime | None


class ReviewDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ReviewSongRequest(BaseModel):
    decision: ReviewDecision
    reject_reason: str | None = Field(default=None, max_length=500)


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


def admin_response_from_model(
    song_request: SongRequest,
    grouped_requests: list[SongRequest] | None = None,
) -> AdminSongRequestResponse:
    basic = response_from_model(song_request)
    group = grouped_requests or [song_request]
    return AdminSongRequestResponse(
        **basic.model_dump(),
        track_id=song_request.track.id,
        media_status=song_request.track.media_status,
        media_original_filename=song_request.track.media_original_filename,
        requester_name=song_request.requester.name,
        requester_email=song_request.requester.email,
        request_count=len(group),
        requesters=[
            RequesterSummary(
                name=item.requester.name,
                email=item.requester.email,
                status=item.status,
            )
            for item in group
        ],
        reviewed_at=song_request.reviewed_at,
    )


def create_or_resubmit_request(
    db, user_id: UUID, track: Track, comment: str | None = None
) -> SongRequest:
    existing = db.scalar(
        select(SongRequest).where(
            SongRequest.user_id == user_id,
            SongRequest.track_id == track.id,
        )
    )
    if existing is not None and existing.status != RequestStatus.REJECTED:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="승인 대기 중이거나 이미 승인된 YouTube 영상입니다.",
        )
    cleaned_comment = (comment or "").strip() or None
    if existing is not None:
        existing.status = RequestStatus.PENDING
        existing.comment = cleaned_comment
        existing.reject_reason = None
        existing.reviewed_by = None
        existing.reviewed_at = None
        existing.created_at = utc_now()
        return existing
    song_request = SongRequest(
        user_id=user_id,
        track_id=track.id,
        comment=cleaned_comment,
    )
    db.add(song_request)
    return song_request


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

    song_request = create_or_resubmit_request(
        db, user.id, track, payload.comment
    )
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


@router.delete("/{request_id}", status_code=status.HTTP_204_NO_CONTENT)
async def cancel_song_request(
    request_id: UUID, user: StudentUserWithCsrf, db: DatabaseSession
):
    song_request = db.scalar(
        select(SongRequest).where(
            SongRequest.id == request_id,
            SongRequest.user_id == user.id,
        )
    )
    if song_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="신청곡을 찾을 수 없습니다.")
    if song_request.status != RequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="승인 대기 중인 신청곡만 취소할 수 있습니다.",
        )
    db.delete(song_request)
    db.commit()


@router.get("", response_model=list[AdminSongRequestResponse])
async def list_all_song_requests(user: AdminUser, db: DatabaseSession):
    requests = db.scalars(
        select(SongRequest)
        .options(
            selectinload(SongRequest.track),
            selectinload(SongRequest.requester),
        )
        .order_by(SongRequest.created_at.desc())
    ).all()
    grouped: dict[UUID, list[SongRequest]] = {}
    for item in requests:
        grouped.setdefault(item.track_id, []).append(item)

    responses = []
    for group in grouped.values():
        representative = next(
            (item for item in group if item.status == RequestStatus.PENDING),
            group[0],
        )
        responses.append(admin_response_from_model(representative, group))
    return responses


@router.post("/{request_id}/review", response_model=AdminSongRequestResponse)
async def review_song_request(
    request_id: UUID,
    payload: ReviewSongRequest,
    user: AdminUserWithCsrf,
    db: DatabaseSession,
):
    song_request = db.scalar(
        select(SongRequest)
        .options(
            selectinload(SongRequest.track),
            selectinload(SongRequest.requester),
        )
        .where(SongRequest.id == request_id)
        .with_for_update()
    )
    if song_request is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="신청곡을 찾을 수 없습니다.")
    pending_requests = list(
        db.scalars(
            select(SongRequest)
            .options(
                selectinload(SongRequest.track),
                selectinload(SongRequest.requester),
            )
            .where(
                SongRequest.track_id == song_request.track_id,
                SongRequest.status == RequestStatus.PENDING,
            )
            .with_for_update()
        )
    )
    if not pending_requests:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 검토가 끝난 신청곡입니다.",
        )

    reject_reason = (payload.reject_reason or "").strip()
    if payload.decision == ReviewDecision.REJECT and not reject_reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="반려할 때는 사유를 입력해 주세요.",
        )

    reviewed_at = utc_now()
    for pending_request in pending_requests:
        if payload.decision == ReviewDecision.APPROVE:
            pending_request.status = RequestStatus.APPROVED
            pending_request.reject_reason = None
            pending_request.track.media_status = MediaStatus.PENDING_ACQUISITION
        else:
            pending_request.status = RequestStatus.REJECTED
            pending_request.reject_reason = reject_reason
        pending_request.reviewed_by = user.id
        pending_request.reviewed_at = reviewed_at

    db.add(
        ControlAuditLog(
            admin_id=user.id,
            action=f"request.{payload.decision.value.lower()}",
            payload={
                "request_id": str(pending_requests[0].id),
                "request_ids": [str(item.id) for item in pending_requests],
                "track_id": str(song_request.track_id),
                "reject_reason": reject_reason or None,
            },
        )
    )
    db.commit()
    for pending_request in pending_requests:
        db.refresh(pending_request)
    return admin_response_from_model(pending_requests[0], pending_requests)
