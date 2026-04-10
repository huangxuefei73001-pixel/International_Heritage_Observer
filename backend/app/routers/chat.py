from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.deps import get_db_session, get_settings
from app.models import Conversation, Message, User
from app.schemas import AskRequest, AskResponse
from app.services.query_service import answer_from_library

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    x_debug_user: str | None = Header(default=None, alias="X-Debug-User"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db_session),
) -> AskResponse:
    if not x_debug_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing X-Debug-User")

    library_path = Path(settings.library_path)
    if not library_path.exists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Library not available")

    with db.begin():
        user = db.execute(select(User).where(User.email == x_debug_user)).scalars().first()
        if user is None:
            user = User(email=x_debug_user, role="user")
            db.add(user)
            db.flush()

        if payload.conversation_id is None:
            conversation = Conversation(user_id=user.id, title=payload.question[:255])
            db.add(conversation)
            db.flush()
        else:
            conversation = db.execute(
                select(Conversation)
                .where(Conversation.id == payload.conversation_id)
                .where(Conversation.user_id == user.id)
            ).scalars().first()
            if conversation is None:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conversation not found")

        db.add(
            Message(
                conversation_id=conversation.id,
                role="user",
                content=payload.question,
            )
        )
    try:
        result = answer_from_library(payload.question, library_path)
    except Exception as exc:  # pragma: no cover - controlled failure path
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={
                "detail": "Answer generation failed",
                "conversation_id": conversation.id,
            },
        ) from exc

    with db.begin():
        conversation = db.execute(
            select(Conversation)
            .where(Conversation.id == conversation.id)
            .where(Conversation.user_id == user.id)
        ).scalars().first()
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Conversation not found")

        conversation.updated_at = datetime.utcnow()
        db.add(
            Message(
                conversation_id=conversation.id,
                role="assistant",
                content=result["answer"],
                sources_json=json.dumps(result["sources"], ensure_ascii=False),
            )
        )
        db.flush()

    return AskResponse(
        conversation_id=conversation.id,
        answer=result["answer"],
        sources=result["sources"],
        messages_saved=2,
    )
