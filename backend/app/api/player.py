from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.auth_dependencies import (
    AdminUserWithCsrf,
    CurrentUser,
)
from backend.app.database import get_db
from backend.app.models import ControlAuditLog
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
async def read_status(user: CurrentUser):
    return player.status()


@router.post("/control")
async def control_player(
    request: ControlRequest,
    user: AdminUserWithCsrf,
    db: Session = Depends(get_db),
):
    actions = {
        PlayerAction.PLAY: player.play,
        PlayerAction.PAUSE: player.pause,
        PlayerAction.STOP: player.stop,
        PlayerAction.NEXT: player.next,
    }
    result = actions[request.action]()
    db.add(
        ControlAuditLog(
            admin_id=user.id,
            action=f"player.{request.action.value}",
            payload={"playback_state": result["playback_state"]},
        )
    )
    db.commit()
    return result


@router.put("/volume")
async def update_volume(
    request: VolumeRequest,
    user: AdminUserWithCsrf,
    db: Session = Depends(get_db),
):
    result = player.set_volume(request.volume)
    db.add(
        ControlAuditLog(
            admin_id=user.id,
            action="player.volume",
            payload={"volume": request.volume},
        )
    )
    db.commit()
    return result


@router.put("/mute")
async def update_mute(
    request: MuteRequest,
    user: AdminUserWithCsrf,
    db: Session = Depends(get_db),
):
    result = player.set_muted(request.muted)
    db.add(
        ControlAuditLog(
            admin_id=user.id,
            action="player.mute",
            payload={"muted": request.muted},
        )
    )
    db.commit()
    return result
