from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter
from pydantic import BaseModel, Field

from backend.app.services.player import FakePlayer


router = APIRouter(prefix="/api/player", tags=["player"])
player = FakePlayer()


class PlayerAction(StrEnum):
    PLAY = "play"
    PAUSE = "pause"
    STOP = "stop"
    NEXT = "next"


class ControlRequest(BaseModel):
    action: PlayerAction


class VolumeRequest(BaseModel):
    volume: Annotated[int, Field(ge=0, le=100)]


class MuteRequest(BaseModel):
    muted: bool


@router.get("/status")
async def read_status():
    return player.status()


@router.post("/control")
async def control_player(request: ControlRequest):
    actions = {
        PlayerAction.PLAY: player.play,
        PlayerAction.PAUSE: player.pause,
        PlayerAction.STOP: player.stop,
        PlayerAction.NEXT: player.next,
    }
    return actions[request.action]()


@router.put("/volume")
async def update_volume(request: VolumeRequest):
    return player.set_volume(request.volume)


@router.put("/mute")
async def update_mute(request: MuteRequest):
    return player.set_muted(request.muted)
