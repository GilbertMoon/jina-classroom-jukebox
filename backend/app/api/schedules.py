from datetime import time
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.auth_dependencies import (
    AdminUserWithCsrf,
    CurrentUser,
    DatabaseSession,
)
from backend.app.models import (
    ControlAuditLog,
    PlaybackEvent,
    Playlist,
    PlaylistItem,
    Schedule,
)


router = APIRouter(prefix="/api/schedules", tags=["schedules"])


class CreateSchedule(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    weekdays: list[int] = Field(min_length=1, max_length=7)
    start_time: time
    end_time: time
    timezone: str = Field(default="Asia/Seoul", max_length=50)
    playlist_id: UUID
    volume: int = Field(default=30, ge=0, le=100)
    is_enabled: bool = True

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("스케줄 이름을 입력해 주세요.")
        return cleaned

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int]) -> list[int]:
        if any(day < 0 or day > 6 for day in value):
            raise ValueError("요일은 월요일 0부터 일요일 6 사이여야 합니다.")
        if len(value) != len(set(value)):
            raise ValueError("같은 요일을 중복 선택할 수 없습니다.")
        return sorted(value)


class UpdateSchedule(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    weekdays: list[int] | None = Field(default=None, min_length=1, max_length=7)
    start_time: time | None = None
    end_time: time | None = None
    playlist_id: UUID | None = None
    volume: int | None = Field(default=None, ge=0, le=100)
    is_enabled: bool | None = None

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("스케줄 이름을 입력해 주세요.")
        return cleaned

    @field_validator("weekdays")
    @classmethod
    def validate_weekdays(cls, value: list[int] | None) -> list[int] | None:
        if value is None:
            return None
        if any(day < 0 or day > 6 for day in value) or len(value) != len(set(value)):
            raise ValueError("요일 선택이 올바르지 않습니다.")
        return sorted(value)


class ScheduleResponse(BaseModel):
    id: UUID
    name: str
    weekdays: list[int]
    start_time: time
    end_time: time
    timezone: str
    playlist_id: UUID
    playlist_name: str
    volume: int
    is_enabled: bool


def response_from_schedule(schedule: Schedule) -> ScheduleResponse:
    return ScheduleResponse(
        id=schedule.id,
        name=schedule.name,
        weekdays=schedule.weekdays,
        start_time=schedule.start_time,
        end_time=schedule.end_time,
        timezone=schedule.timezone,
        playlist_id=schedule.playlist_id,
        playlist_name=schedule.playlist.name,
        volume=schedule.volume,
        is_enabled=schedule.is_enabled,
    )


def validate_times(start_time: time, end_time: time, timezone_name: str) -> None:
    if start_time.tzinfo is not None or end_time.tzinfo is not None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="시작·종료 시간에는 시간대 정보를 포함하지 마세요.",
        )
    if start_time >= end_time:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="종료 시간은 시작 시간보다 늦어야 합니다. 자정을 넘기는 스케줄은 아직 지원하지 않습니다.",
        )
    if timezone_name != "Asia/Seoul":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="현재는 Asia/Seoul 시간대만 지원합니다.",
        )
    try:
        ZoneInfo(timezone_name)
    except ZoneInfoNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="알 수 없는 시간대입니다.",
        ) from exc


def ensure_active_playlist(db: DatabaseSession, playlist_id: UUID) -> Playlist:
    playlist = db.scalar(
        select(Playlist)
        .options(selectinload(Playlist.items))
        .where(Playlist.id == playlist_id)
    )
    if playlist is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="플레이리스트를 찾을 수 없습니다.")
    if not playlist.is_active or not playlist.items:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="곡이 있고 활성화된 플레이리스트만 스케줄에 사용할 수 있습니다.",
        )
    return playlist


def ensure_no_overlap(
    db: DatabaseSession,
    weekdays: list[int],
    start_time: time,
    end_time: time,
    is_enabled: bool,
    exclude_id: UUID | None = None,
) -> None:
    if not is_enabled:
        return
    schedules = db.scalars(select(Schedule).where(Schedule.is_enabled.is_(True))).all()
    for existing in schedules:
        if existing.id == exclude_id:
            continue
        shares_day = bool(set(weekdays) & set(existing.weekdays))
        overlaps_time = start_time < existing.end_time and end_time > existing.start_time
        if shares_day and overlaps_time:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"'{existing.name}' 스케줄과 시간이 겹칩니다.",
            )


def schedule_query():
    return select(Schedule).options(selectinload(Schedule.playlist))


@router.get("", response_model=list[ScheduleResponse])
async def list_schedules(user: CurrentUser, db: DatabaseSession):
    schedules = db.scalars(
        schedule_query().order_by(Schedule.start_time, Schedule.name)
    ).all()
    return [response_from_schedule(item) for item in schedules]


@router.post("", response_model=ScheduleResponse, status_code=status.HTTP_201_CREATED)
async def create_schedule(
    payload: CreateSchedule,
    user: AdminUserWithCsrf,
    db: DatabaseSession,
):
    validate_times(payload.start_time, payload.end_time, payload.timezone)
    playlist = ensure_active_playlist(db, payload.playlist_id)
    ensure_no_overlap(
        db, payload.weekdays, payload.start_time, payload.end_time, payload.is_enabled
    )
    schedule = Schedule(**payload.model_dump())
    schedule.playlist = playlist
    db.add(schedule)
    db.flush()
    db.add(
        ControlAuditLog(
            admin_id=user.id,
            action="schedule.create",
            payload={"schedule_id": str(schedule.id), "name": schedule.name},
        )
    )
    db.commit()
    return response_from_schedule(schedule)


@router.patch("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: UUID,
    payload: UpdateSchedule,
    user: AdminUserWithCsrf,
    db: DatabaseSession,
):
    schedule = db.scalar(schedule_query().where(Schedule.id == schedule_id))
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="스케줄을 찾을 수 없습니다.")
    changes = payload.model_dump(exclude_unset=True)
    values = {
        "weekdays": changes.get("weekdays", schedule.weekdays),
        "start_time": changes.get("start_time", schedule.start_time),
        "end_time": changes.get("end_time", schedule.end_time),
        "is_enabled": changes.get("is_enabled", schedule.is_enabled),
        "playlist_id": changes.get("playlist_id", schedule.playlist_id),
    }
    validate_times(values["start_time"], values["end_time"], schedule.timezone)
    if values["is_enabled"]:
        playlist = ensure_active_playlist(db, values["playlist_id"])
    else:
        playlist = db.scalar(
            select(Playlist)
            .options(selectinload(Playlist.items))
            .where(Playlist.id == values["playlist_id"])
        )
        if playlist is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="플레이리스트를 찾을 수 없습니다.",
            )
    ensure_no_overlap(
        db,
        values["weekdays"],
        values["start_time"],
        values["end_time"],
        values["is_enabled"],
        exclude_id=schedule.id,
    )
    for field, value in changes.items():
        setattr(schedule, field, value)
    schedule.playlist = playlist
    db.add(
        ControlAuditLog(
            admin_id=user.id,
            action="schedule.update",
            payload={"schedule_id": str(schedule.id), "changes": sorted(changes)},
        )
    )
    db.commit()
    return response_from_schedule(schedule)


@router.delete("/{schedule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_schedule(
    schedule_id: UUID,
    user: AdminUserWithCsrf,
    db: DatabaseSession,
) -> Response:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="스케줄을 찾을 수 없습니다.")
    has_history = db.scalar(
        select(PlaybackEvent.id).where(PlaybackEvent.schedule_id == schedule.id)
    )
    if has_history is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="재생 기록이 있는 스케줄은 삭제하지 말고 비활성화해 주세요.",
        )
    db.add(
        ControlAuditLog(
            admin_id=user.id,
            action="schedule.delete",
            payload={"schedule_id": str(schedule.id), "name": schedule.name},
        )
    )
    db.delete(schedule)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
