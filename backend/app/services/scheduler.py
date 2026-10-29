from datetime import datetime, timezone
import os
from uuid import UUID
from zoneinfo import ZoneInfo

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.database import SessionLocal
from backend.app.models import PlaybackEvent, Playlist, PlaylistItem, Schedule
from backend.app.services.player import Track as PlayerTrack
from backend.app.services.player import PlayerError, player


class ScheduleRunner:
    """Evaluate stored schedules and control the current player time slot."""

    def __init__(self) -> None:
        self.reset()

    def reset(self) -> None:
        self.current_schedule_id: UUID | None = None
        self.current_event_id: UUID | None = None

    def evaluate(self, now: datetime, db: Session) -> None:
        if now.tzinfo is None:
            raise ValueError("Schedule evaluation requires a timezone-aware datetime.")
        schedules = db.scalars(
            select(Schedule)
            .options(
                selectinload(Schedule.playlist)
                .selectinload(Playlist.items)
                .selectinload(PlaylistItem.track)
            )
            .where(Schedule.is_enabled.is_(True))
        ).all()
        active = next(
            (schedule for schedule in schedules if self._is_active(schedule, now)),
            None,
        )

        if active is not None and active.id != self.current_schedule_id:
            self._complete_current_event(now, db)
            ordered_items = sorted(active.playlist.items, key=lambda item: item.position)
            if not ordered_items:
                return
            try:
                player.load_playlist(
                    PlayerTrack(
                        id=str(item.track.id),
                        title=item.track.title,
                        artist=item.track.artist_or_channel or "가수 미입력",
                        duration_seconds=item.track.duration_seconds or 0,
                        media_path=item.track.media_path,
                    )
                    for item in ordered_items
                )
                player.set_volume(active.volume)
                player.play()
            except PlayerError as exc:
                failed_event = PlaybackEvent(
                    track_id=ordered_items[0].track.id,
                    schedule_id=active.id,
                    started_at=now.astimezone(timezone.utc),
                    ended_at=now.astimezone(timezone.utc),
                    result="FAILED",
                    error_code=type(exc).__name__,
                )
                db.add(failed_event)
                db.commit()
                self.current_schedule_id = active.id
                self.current_event_id = failed_event.id
                return
            event = PlaybackEvent(
                track_id=ordered_items[0].track.id,
                schedule_id=active.id,
                started_at=now.astimezone(timezone.utc),
                result="RUNNING",
            )
            db.add(event)
            db.commit()
            self.current_schedule_id = active.id
            self.current_event_id = event.id
        elif active is None and self.current_schedule_id is not None:
            try:
                player.stop()
                self._complete_current_event(now, db)
            except PlayerError as exc:
                self._complete_current_event(
                    now, db, result="FAILED", error_code=type(exc).__name__
                )
            self.reset()

    def _complete_current_event(
        self,
        now: datetime,
        db: Session,
        result: str = "COMPLETED",
        error_code: str | None = None,
    ) -> None:
        event = (
            db.get(PlaybackEvent, self.current_event_id)
            if self.current_event_id is not None
            else None
        )
        if event is not None and event.ended_at is None:
            event.ended_at = now.astimezone(timezone.utc)
            event.result = result
            event.error_code = error_code
            db.commit()

    @staticmethod
    def _is_active(schedule: Schedule, now: datetime) -> bool:
        local_now = now.astimezone(ZoneInfo(schedule.timezone))
        local_time = local_now.time().replace(tzinfo=None)
        return (
            schedule.playlist.is_active
            and bool(schedule.playlist.items)
            and local_now.weekday() in schedule.weekdays
            and schedule.start_time <= local_time < schedule.end_time
        )


schedule_runner = ScheduleRunner()
job_scheduler = AsyncIOScheduler(timezone=ZoneInfo("Asia/Seoul"))


def run_schedule_tick() -> None:
    with SessionLocal() as db:
        schedule_runner.evaluate(datetime.now(timezone.utc), db)


def start_schedule_service() -> None:
    if job_scheduler.running:
        return
    interval = max(5, int(os.getenv("SCHEDULER_INTERVAL_SECONDS", "30")))
    job_scheduler.add_job(
        run_schedule_tick,
        "interval",
        seconds=interval,
        id="jukebox-schedule-evaluator",
        replace_existing=True,
        coalesce=True,
        max_instances=1,
        next_run_time=datetime.now(timezone.utc),
    )
    job_scheduler.start()


def stop_schedule_service() -> None:
    if job_scheduler.running:
        job_scheduler.shutdown(wait=False)
