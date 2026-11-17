from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select

from backend.app.auth_dependencies import AdminUser, AdminUserWithCsrf, DatabaseSession
from backend.app.models import ControlAuditLog, User
from backend.app.models.entities import UserRole


router = APIRouter(prefix="/api/users", tags=["users"])


class PendingUserResponse(BaseModel):
    id: UUID
    name: str
    email: str


@router.get("/pending", response_model=list[PendingUserResponse])
async def pending_users(db: DatabaseSession, admin: AdminUser):
    return list(
        db.scalars(
            select(User)
            .where(User.role == UserRole.STUDENT, User.is_active.is_(False))
            .order_by(User.created_at)
        )
    )


@router.post("/{user_id}/approve", response_model=PendingUserResponse)
async def approve_user(user_id: UUID, db: DatabaseSession, admin: AdminUserWithCsrf):
    user = db.get(User, user_id)
    if user is None or user.role != UserRole.STUDENT:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="승인할 학생을 찾을 수 없습니다.")
    if user.is_active:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="이미 승인된 학생입니다.")
    user.is_active = True
    db.add(
        ControlAuditLog(
            admin_id=admin.id,
            action="USER_APPROVED",
            payload={"user_id": str(user.id), "email": user.email},
        )
    )
    db.commit()
    db.refresh(user)
    return user
