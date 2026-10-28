from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from mutagen import MutagenError
from mutagen.flac import FLAC
from mutagen.mp3 import MP3
from mutagen.oggvorbis import OggVorbis


class MediaValidationError(ValueError):
    pass


@dataclass(frozen=True)
class MediaInspection:
    duration_seconds: int


class SourceProvider(Protocol):
    def inspect(self, path: Path, extension: str) -> MediaInspection: ...


class ManualUploadProvider:
    """Validate a locally uploaded audio file without downloading anything."""

    audio_types = {
        ".mp3": MP3,
        ".ogg": OggVorbis,
        ".flac": FLAC,
    }

    def inspect(self, path: Path, extension: str) -> MediaInspection:
        audio_type = self.audio_types.get(extension)
        if audio_type is None:
            raise MediaValidationError("MP3, OGG 또는 FLAC 파일만 등록할 수 있습니다.")
        try:
            audio = audio_type(path)
            duration = round(audio.info.length)
        except (MutagenError, OSError, ValueError) as exc:
            raise MediaValidationError(
                "파일이 손상되었거나 선택한 형식의 재생 가능한 음원이 아닙니다."
            ) from exc
        if duration <= 0:
            raise MediaValidationError("재생 시간이 없는 음원은 등록할 수 없습니다.")
        return MediaInspection(duration_seconds=duration)


manual_upload_provider = ManualUploadProvider()
