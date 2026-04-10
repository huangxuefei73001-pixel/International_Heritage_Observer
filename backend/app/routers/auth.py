from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.auth import build_login_code, verify_login_code
from app.config import Settings
from app.deps import get_db_session, get_settings
from app.email import send_login_code_email
from app.models import LoginCode, User

router = APIRouter(prefix="/auth", tags=["auth"])


class SendLoginCodeRequest(BaseModel):
    email: str


class VerifyLoginCodeRequest(BaseModel):
    email: str
    code: str


class VerifyLoginCodeResponse(BaseModel):
    email: str
    role: str
    verified: bool


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
                expires_at=datetime.utcnow() + timedelta(minutes=10),
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
                .where(LoginCode.expires_at > datetime.utcnow())
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
            .values(used_at=datetime.utcnow())
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
