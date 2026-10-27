from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from backend.app.auth_dependencies import CurrentUser, DatabaseSession, UserWithCsrf
from backend.app.models import User
from backend.app.security import new_csrf_token, verify_password


router = APIRouter(prefix="/api/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: str


def user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, name=user.name, email=user.email, role=user.role)


@router.post("/login")
async def login(request: Request, credentials: LoginRequest, db: DatabaseSession):
    user = db.scalar(
        select(User).where(func.lower(User.email) == credentials.email.strip().lower())
    )
    if user is None:
        verify_password(credentials.password, None)
    if user is None or not user.is_active or not verify_password(
        credentials.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    csrf_token = new_csrf_token()
    request.session.clear()
    request.session.update({"user_id": str(user.id), "csrf_token": csrf_token})
    return {"user": user_response(user), "csrf_token": csrf_token}


@router.get("/me", response_model=UserResponse)
async def read_me(user: CurrentUser):
    return user_response(user)


@router.post("/logout")
async def logout(request: Request, user: UserWithCsrf):
    request.session.clear()
    return {"status": "logged_out"}
