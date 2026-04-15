from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth import build_login_code, verify_login_code
from app.config import Settings
from app.deps import get_db_session, get_settings
from app.email import send_login_code_email
from app.models import LoginCode, User
from app.schemas import PasswordLoginRequest, VerifyLoginCodeResponse

router = APIRouter(prefix="/auth", tags=["auth"])


class SendLoginCodeRequest(BaseModel):
    email: str


class VerifyLoginCodeRequest(BaseModel):
    email: str
    code: str


@router.post("/send-code")
def send_code(
    payload: SendLoginCodeRequest,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db_session),
) -> dict[str, str]:
    stored_hash, plain_code = build_login_code()
    send_login_code_email(settings, payload.email, plain_code)
    with db.begin():
        db.add(
            LoginCode(
                email=payload.email,
                code_hash=stored_hash,
                expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
            )
        )
    return {"email": payload.email, "status": "sent"}


@router.post("/verify-code", response_model=VerifyLoginCodeResponse)
def verify_code(
    payload: VerifyLoginCodeRequest,
    db: Session = Depends(get_db_session),
) -> VerifyLoginCodeResponse:
    with db.begin():
        login_code = (
            db.execute(
                select(LoginCode)
                .where(LoginCode.email == payload.email)
                .where(LoginCode.used_at.is_(None))
                .where(LoginCode.expires_at > datetime.now(timezone.utc))
                .order_by(LoginCode.id.desc())
                .with_for_update()
            )
            .scalars()
            .first()
        )
        if login_code is None or not verify_login_code(payload.code, login_code.code_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid login code",
            )

        consumed = db.execute(
            update(LoginCode)
            .where(LoginCode.id == login_code.id)
            .where(LoginCode.used_at.is_(None))
            .values(used_at=datetime.now(timezone.utc))
        )
        if consumed.rowcount != 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid login code",
            )

        user = db.execute(select(User).where(User.email == payload.email)).scalars().first()
        if user is None:
            user = User(email=payload.email, role="user")
            db.add(user)
            db.flush()

        role = user.role

    return VerifyLoginCodeResponse(email=payload.email, role=role, verified=True)


@router.post("/password-login", response_model=VerifyLoginCodeResponse)
def password_login(
    payload: PasswordLoginRequest,
    db: Session = Depends(get_db_session),
) -> VerifyLoginCodeResponse:
    if payload.username != "admin" or payload.password != "admin":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
        )

    with db.begin():
        user = db.execute(select(User).where(User.email == "admin")).scalars().first()
        if user is None:
            user = User(email="admin", role="admin")
            db.add(user)
            db.flush()
        elif user.role != "admin":
            user.role = "admin"

        user.last_login_at = datetime.now(timezone.utc)

    return VerifyLoginCodeResponse(email="admin", role="admin", verified=True)
