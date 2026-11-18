from uuid import UUID

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from backend.app.auth_dependencies import CurrentUser, DatabaseSession, UserWithCsrf
from backend.app.models import User
from backend.app.models.entities import UserRole
from backend.app.security import hash_password, new_csrf_token, verify_password
from backend.app.services.login_security import login_attempt_limiter


router = APIRouter(prefix="/api/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=256)


class RegisterRequest(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=256)


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: str


def user_response(user: User) -> UserResponse:
    return UserResponse(id=user.id, name=user.name, email=user.email, role=user.role)


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(credentials: RegisterRequest, db: DatabaseSession):
    email = str(credentials.email).lower()
    if db.scalar(select(User.id).where(func.lower(User.email) == email)) is not None:
        raise HTTPException(status_code=409, detail="이미 등록된 이메일입니다.")

    user = User(
        name=credentials.name.strip(),
        email=email,
        password_hash=hash_password(credentials.password),
        role=UserRole.STUDENT,
        is_active=False,
    )
    db.add(user)
    db.commit()
    return {"message": "가입 신청이 완료되었습니다. 관리자 승인 후 로그인할 수 있습니다."}


@router.post("/login")
async def login(request: Request, credentials: LoginRequest, db: DatabaseSession):
    attempt_key = login_attempt_limiter.key(request, credentials.email)
    retry_after = login_attempt_limiter.retry_after(attempt_key)
    if retry_after is not None:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="로그인 시도가 너무 많습니다. 잠시 후 다시 시도해 주세요.",
            headers={"Retry-After": str(retry_after)},
        )

    user = db.scalar(
        select(User).where(func.lower(User.email) == credentials.email.strip().lower())
    )
    if user is None:
        verify_password(credentials.password, None)
    if user is None or not user.is_active or not verify_password(
        credentials.password, user.password_hash
    ):
        login_attempt_limiter.record_failure(attempt_key)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="이메일 또는 비밀번호가 올바르지 않습니다.",
        )

    login_attempt_limiter.record_success(attempt_key)
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
