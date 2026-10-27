import secrets
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.models import User
from backend.app.models.entities import UserRole


DatabaseSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DatabaseSession) -> User:
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")

    try:
        parsed_user_id = UUID(user_id)
    except (TypeError, ValueError):
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")

    user = db.get(User, parsed_user_id)
    if user is None or not user.is_active:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="로그인이 필요합니다.")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다.")
    return user


AdminUser = Annotated[User, Depends(require_admin)]


def require_user_csrf(
    request: Request,
    user: CurrentUser,
    x_csrf_token: Annotated[str | None, Header()] = None,
) -> User:
    expected_token = request.session.get("csrf_token")
    if not expected_token or not x_csrf_token or not secrets.compare_digest(
        expected_token, x_csrf_token
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF 검증에 실패했습니다.")
    return user


UserWithCsrf = Annotated[User, Depends(require_user_csrf)]


def require_admin_csrf(user: UserWithCsrf) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="관리자 권한이 필요합니다.")
    return user


AdminUserWithCsrf = Annotated[User, Depends(require_admin_csrf)]
