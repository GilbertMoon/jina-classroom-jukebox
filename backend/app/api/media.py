import hashlib
import os
from pathlib import Path
import tempfile
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from backend.app.auth_dependencies import AdminUserWithCsrf, DatabaseSession
from backend.app.config import get_max_media_size_bytes, get_media_root
from backend.app.models import ControlAuditLog, SongRequest, Track
from backend.app.models.entities import MediaStatus, RequestStatus
from backend.app.services.media import MediaValidationError, manual_upload_provider


router = APIRouter(prefix="/api/media", tags=["media"])
ALLOWED_EXTENSIONS = {".mp3", ".ogg", ".flac"}
CHUNK_SIZE = 1024 * 1024


class MediaUploadResponse(BaseModel):
    track_id: UUID
    status: MediaStatus
    original_filename: str
    size_bytes: int
    duration_seconds: int
    sha256: str


def safe_original_filename(filename: str | None) -> str:
    cleaned = (filename or "audio").replace("\\", "/").rsplit("/", 1)[-1]
    return cleaned[:255] or "audio"


@router.post("/upload", response_model=MediaUploadResponse)
async def upload_authorized_media(
    track_id: Annotated[UUID, Form()],
    rights_confirmed: Annotated[bool, Form()],
    rights_note: Annotated[str, Form(min_length=1, max_length=500)],
    file: Annotated[UploadFile, File()],
    user: AdminUserWithCsrf,
    db: DatabaseSession,
):
    if not rights_confirmed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="이용 권한을 확인해야 음원을 등록할 수 있습니다.",
        )
    cleaned_rights_note = rights_note.strip()
    if not cleaned_rights_note:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="이용 권한의 근거를 입력해 주세요.",
        )

    track = db.get(Track, track_id)
    if track is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="곡을 찾을 수 없습니다.")
    approved_request = db.scalar(
        select(SongRequest.id).where(
            SongRequest.track_id == track.id,
            SongRequest.status == RequestStatus.APPROVED,
        )
    )
    if approved_request is None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="승인된 신청곡에만 음원을 등록할 수 있습니다.",
        )
    if track.media_status == MediaStatus.READY or track.media_path:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="이미 음원이 등록된 곡입니다.",
        )

    original_filename = safe_original_filename(file.filename)
    extension = Path(original_filename).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="MP3, OGG 또는 FLAC 파일만 등록할 수 있습니다.",
        )

    media_root = get_media_root()
    media_root.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".upload-", suffix=extension, dir=media_root
    )
    temporary_path = Path(temporary_name)
    final_path = media_root / f"{track.id}{extension}"
    size_bytes = 0
    digest = hashlib.sha256()

    try:
        with os.fdopen(descriptor, "wb") as destination:
            while chunk := await file.read(CHUNK_SIZE):
                size_bytes += len(chunk)
                if size_bytes > get_max_media_size_bytes():
                    raise HTTPException(
                        status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                        detail="파일이 허용된 최대 크기를 초과했습니다.",
                    )
                digest.update(chunk)
                destination.write(chunk)
        if size_bytes == 0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="빈 파일은 등록할 수 없습니다.",
            )

        try:
            inspection = manual_upload_provider.inspect(temporary_path, extension)
        except MediaValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(exc)
            ) from exc

        sha256 = digest.hexdigest()
        duplicate = db.scalar(
            select(Track).where(Track.sha256 == sha256, Track.id != track.id)
        )
        if duplicate is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="같은 음원 파일이 다른 곡에 이미 등록되어 있습니다.",
            )

        os.replace(temporary_path, final_path)
        track.media_path = str(final_path)
        track.sha256 = sha256
        track.rights_status = "CONFIRMED"
        track.rights_note = cleaned_rights_note
        track.media_original_filename = original_filename
        track.media_content_type = file.content_type
        track.media_size_bytes = size_bytes
        track.duration_seconds = inspection.duration_seconds
        track.media_status = MediaStatus.READY
        db.add(
            ControlAuditLog(
                admin_id=user.id,
                action="media.upload",
                payload={
                    "track_id": str(track.id),
                    "filename": original_filename,
                    "size_bytes": size_bytes,
                    "sha256": sha256,
                },
            )
        )
        try:
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            final_path.unlink(missing_ok=True)
            raise

        return MediaUploadResponse(
            track_id=track.id,
            status=track.media_status,
            original_filename=original_filename,
            size_bytes=size_bytes,
            duration_seconds=inspection.duration_seconds,
            sha256=sha256,
        )
    finally:
        await file.close()
        temporary_path.unlink(missing_ok=True)
