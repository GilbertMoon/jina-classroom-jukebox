from contextlib import contextmanager
from dataclasses import dataclass
import os
from pathlib import Path
import time
from typing import Any, Callable, Iterable, Iterator

from mpd import MPDClient, MPDError

from backend.app.services.player import (
    PlaybackState,
    PlayerConfigurationError,
    PlayerConnectionError,
    Track,
)


@dataclass(frozen=True)
class MpdSettings:
    host: str
    port: int
    password: str | None
    timeout_seconds: float
    music_root: Path


class MpdPlayer:
    """MPD-backed player with the same interface as the development fake."""

    def __init__(
        self,
        settings: MpdSettings,
        client_factory: Callable[[], MPDClient] = MPDClient,
    ) -> None:
        self.settings = settings
        self.client_factory = client_factory
        self._muted = False
        self._volume_before_mute = 30

    @classmethod
    def from_env(cls) -> "MpdPlayer":
        music_root = Path(
            os.getenv("MPD_MUSIC_ROOT", os.getenv("MEDIA_ROOT", "media"))
        ).resolve()
        return cls(
            MpdSettings(
                host=os.getenv("MPD_HOST", "127.0.0.1"),
                port=int(os.getenv("MPD_PORT", "6600")),
                password=os.getenv("MPD_PASSWORD") or None,
                timeout_seconds=float(os.getenv("MPD_TIMEOUT_SECONDS", "5")),
                music_root=music_root,
            )
        )

    @contextmanager
    def _client(self) -> Iterator[MPDClient]:
        client = self.client_factory()
        client.timeout = self.settings.timeout_seconds
        client.idletimeout = None
        connected = False
        try:
            client.connect(self.settings.host, self.settings.port)
            connected = True
            if self.settings.password:
                client.password(self.settings.password)
            yield client
        except (MPDError, OSError, ConnectionError) as exc:
            raise PlayerConnectionError("MPD server is unavailable.") from exc
        finally:
            if connected:
                try:
                    client.close()
                except (MPDError, OSError):
                    pass
                try:
                    client.disconnect()
                except (MPDError, OSError):
                    pass

    def load_playlist(self, tracks: Iterable[Track]) -> None:
        loaded_tracks = tuple(tracks)
        if not loaded_tracks:
            raise PlayerConfigurationError("At least one track is required.")
        uris = [self._media_uri(track.media_path) for track in loaded_tracks]
        with self._client() as client:
            client.update()
            self._wait_for_database_update(client)
            client.clear()
            for uri in uris:
                client.add(uri)

    def status(self) -> dict[str, Any]:
        with self._client() as client:
            status = client.status()
            current = client.currentsong()
            playlist = client.playlistinfo()
        position = self._integer(status.get("song"), default=0)
        next_song = playlist[position + 1] if position + 1 < len(playlist) else {}
        return {
            "playback_state": self._state(status.get("state")),
            "current_track": self._track_info(current, status),
            "next_track": self._track_info(next_song, {}),
            "progress_seconds": self._integer(status.get("elapsed"), default=0),
            "volume": max(0, self._integer(status.get("volume"), default=0)),
            "muted": self._muted,
            "connection": "mpd",
            "backend": "mpd",
            "connected": True,
        }

    def play(self) -> dict[str, Any]:
        self._run_command("play")
        return self.status()

    def pause(self) -> dict[str, Any]:
        self._run_command("pause", 1)
        return self.status()

    def stop(self) -> dict[str, Any]:
        self._run_command("stop")
        return self.status()

    def next(self) -> dict[str, Any]:
        self._run_command("next")
        return self.status()

    def set_volume(self, volume: int) -> dict[str, Any]:
        self._run_command("setvol", volume)
        self._muted = volume == 0
        if volume > 0:
            self._volume_before_mute = volume
        return self.status()

    def set_muted(self, muted: bool) -> dict[str, Any]:
        if muted:
            current_volume = self.status()["volume"]
            if current_volume > 0:
                self._volume_before_mute = current_volume
            self._run_command("setvol", 0)
        else:
            self._run_command("setvol", self._volume_before_mute)
        self._muted = muted
        return self.status()

    def _run_command(self, command: str, *args: Any) -> None:
        with self._client() as client:
            getattr(client, command)(*args)

    def _media_uri(self, media_path: str | None) -> str:
        if not media_path:
            raise PlayerConfigurationError("A playlist track has no local media path.")
        path = Path(media_path).resolve()
        root = self.settings.music_root.resolve()
        try:
            return path.relative_to(root).as_posix()
        except ValueError as exc:
            raise PlayerConfigurationError(
                "A media file is outside MPD_MUSIC_ROOT."
            ) from exc

    def _wait_for_database_update(self, client: MPDClient) -> None:
        deadline = time.monotonic() + self.settings.timeout_seconds
        while "updating_db" in client.status():
            if time.monotonic() >= deadline:
                raise PlayerConnectionError("MPD database update timed out.")
            time.sleep(0.1)

    @staticmethod
    def _integer(value: Any, default: int) -> int:
        try:
            return int(float(value))
        except (TypeError, ValueError):
            return default

    @classmethod
    def _track_info(cls, song: dict[str, Any], status: dict[str, Any]) -> dict[str, Any]:
        file_name = song.get("file", "")
        duration = song.get("duration") or song.get("time") or status.get("duration")
        return {
            "id": song.get("id") or song.get("pos") or file_name,
            "title": song.get("title") or (Path(file_name).stem if file_name else "재생 중인 곡 없음"),
            "artist": song.get("artist") or "가수 미입력",
            "duration_seconds": cls._integer(duration, default=0),
            "media_path": file_name or None,
        }

    @staticmethod
    def _state(value: str | None) -> PlaybackState:
        return {
            "play": PlaybackState.PLAYING,
            "pause": PlaybackState.PAUSED,
            "stop": PlaybackState.STOPPED,
        }.get(value or "", PlaybackState.STOPPED)
