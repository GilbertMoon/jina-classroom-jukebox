from dataclasses import asdict, dataclass
from enum import StrEnum
import os
from typing import Any, Iterable, Protocol


class PlaybackState(StrEnum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass(frozen=True)
class Track:
    id: Any
    title: str
    artist: str
    duration_seconds: int
    media_path: str | None = None


class PlayerError(RuntimeError):
    """Base error for player backends that cannot complete a command."""


class PlayerConnectionError(PlayerError):
    """Raised when the configured player service is unavailable."""


class PlayerConfigurationError(PlayerError):
    """Raised when player paths or settings are unsafe or invalid."""


class PlayerBackend(Protocol):
    def load_playlist(self, tracks: Iterable[Track]) -> None: ...
    def status(self) -> dict[str, Any]: ...
    def play(self) -> dict[str, Any]: ...
    def pause(self) -> dict[str, Any]: ...
    def stop(self) -> dict[str, Any]: ...
    def next(self) -> dict[str, Any]: ...
    def set_volume(self, volume: int) -> dict[str, Any]: ...
    def set_muted(self, muted: bool) -> dict[str, Any]: ...


class FakePlayer:
    """An in-memory player used before the Ubuntu MPD server is connected."""

    def __init__(self) -> None:
        self._demo_playlist = (
            Track(1, "Morning Compile", "AX2 Studio", 198),
            Track(2, "Campus Loop", "Jina Lab", 224),
            Track(3, "After Class", "Code & Chords", 187),
        )
        self.reset()

    def reset(self) -> None:
        self._playlist = self._demo_playlist
        self._state = PlaybackState.STOPPED
        self._current_index = 0
        self._volume = 30
        self._muted = False
        self._progress_seconds = 0

    def load_playlist(self, tracks: Iterable[Track]) -> None:
        loaded_tracks = tuple(tracks)
        if not loaded_tracks:
            raise ValueError("At least one track is required.")
        self._playlist = loaded_tracks
        self._current_index = 0
        self._progress_seconds = 0

    def status(self) -> dict[str, Any]:
        current_track = self._playlist[self._current_index]
        next_track = self._playlist[(self._current_index + 1) % len(self._playlist)]
        return {
            "playback_state": self._state,
            "current_track": asdict(current_track),
            "next_track": asdict(next_track),
            "progress_seconds": self._progress_seconds,
            "volume": self._volume,
            "muted": self._muted,
            "connection": "demo",
            "backend": "fake",
            "connected": True,
        }

    def play(self) -> dict[str, Any]:
        self._state = PlaybackState.PLAYING
        return self.status()

    def pause(self) -> dict[str, Any]:
        if self._state == PlaybackState.PLAYING:
            self._state = PlaybackState.PAUSED
        return self.status()

    def stop(self) -> dict[str, Any]:
        self._state = PlaybackState.STOPPED
        self._progress_seconds = 0
        return self.status()

    def next(self) -> dict[str, Any]:
        self._current_index = (self._current_index + 1) % len(self._playlist)
        self._progress_seconds = 0
        return self.status()

    def set_volume(self, volume: int) -> dict[str, Any]:
        self._volume = volume
        if volume > 0:
            self._muted = False
        return self.status()

    def set_muted(self, muted: bool) -> dict[str, Any]:
        self._muted = muted
        return self.status()


class PlayerManager:
    """Stable facade that lets the app switch between fake and MPD backends."""

    def __init__(self) -> None:
        self.use_fake()

    @property
    def backend_name(self) -> str:
        return self._backend_name

    def use_fake(self) -> None:
        self._backend: PlayerBackend = FakePlayer()
        self._backend_name = "fake"

    def use_backend(self, backend: PlayerBackend, name: str) -> None:
        self._backend = backend
        self._backend_name = name

    def configure_from_env(self) -> None:
        backend_name = os.getenv("PLAYER_BACKEND", "fake").strip().lower()
        if backend_name == "fake":
            self.use_fake()
            return
        if backend_name == "mpd":
            from backend.app.services.mpd_player import MpdPlayer

            self.use_backend(MpdPlayer.from_env(), "mpd")
            return
        raise PlayerConfigurationError(
            "PLAYER_BACKEND must be either 'fake' or 'mpd'."
        )

    def reset(self) -> None:
        reset = getattr(self._backend, "reset", None)
        if reset is not None:
            reset()

    def load_playlist(self, tracks: Iterable[Track]) -> None:
        self._backend.load_playlist(tracks)

    def status(self) -> dict[str, Any]:
        return self._backend.status()

    def play(self) -> dict[str, Any]:
        return self._backend.play()

    def pause(self) -> dict[str, Any]:
        return self._backend.pause()

    def stop(self) -> dict[str, Any]:
        return self._backend.stop()

    def next(self) -> dict[str, Any]:
        return self._backend.next()

    def set_volume(self, volume: int) -> dict[str, Any]:
        return self._backend.set_volume(volume)

    def set_muted(self, muted: bool) -> dict[str, Any]:
        return self._backend.set_muted(muted)


player = PlayerManager()
