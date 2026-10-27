from dataclasses import asdict, dataclass
from enum import StrEnum
from typing import Any


class PlaybackState(StrEnum):
    STOPPED = "stopped"
    PLAYING = "playing"
    PAUSED = "paused"


@dataclass(frozen=True)
class Track:
    id: int
    title: str
    artist: str
    duration_seconds: int


class FakePlayer:
    """An in-memory player used before the Ubuntu MPD server is connected."""

    def __init__(self) -> None:
        self._playlist = (
            Track(1, "Morning Compile", "AX2 Studio", 198),
            Track(2, "Campus Loop", "Jina Lab", 224),
            Track(3, "After Class", "Code & Chords", 187),
        )
        self.reset()

    def reset(self) -> None:
        self._state = PlaybackState.STOPPED
        self._current_index = 0
        self._volume = 30
        self._muted = False
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
