from __future__ import annotations

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.deps import get_db_session, get_settings
from app.models import Conversation, User
from app.services.sync_service import refresh_library

router = APIRouter(prefix="/admin", tags=["admin"])


def _require_admin_user(
    x_debug_user: str | None,
    db: Session,
) -> User:
    if not x_debug_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing X-Debug-User")

    user = db.execute(select(User).where(User.email == x_debug_user)).scalars().first()
    if user is None or user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return user


@router.get("/conversations")
def list_conversations(
    x_debug_user: str | None = Header(default=None, alias="X-Debug-User"),
    db: Session = Depends(get_db_session),
) -> list[dict]:
    _require_admin_user(x_debug_user, db)

    rows = db.execute(
        select(Conversation, User.email)
        .join(User, User.id == Conversation.user_id)
        .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
    ).all()

    return [
        {
            "conversation_id": conversation.id,
            "title": conversation.title,
            "user_email": user_email,
            "created_at": conversation.created_at,
            "updated_at": conversation.updated_at,
        }
        for conversation, user_email in rows
    ]


@router.post("/refresh-library")
def refresh_library_endpoint(
    x_debug_user: str | None = Header(default=None, alias="X-Debug-User"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db_session),
) -> dict:
    _require_admin_user(x_debug_user, db)
    return refresh_library(settings)
