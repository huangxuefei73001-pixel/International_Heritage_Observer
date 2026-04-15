from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.deps import get_db_session, get_settings
from app.models import Conversation, Message, User
from app.schemas import AskRequest, AskResponse, ConversationDetail, ConversationMessage, ConversationSummary
from app.services.query_service import answer_from_library

router = APIRouter(prefix="/chat", tags=["chat"])


def _require_user(
    x_debug_user: str | None,
    db: Session,
) -> User:
    if not x_debug_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing X-Debug-User")

    user = db.execute(select(User).where(User.email == x_debug_user)).scalars().first()
    if user is None:
        user = User(email=x_debug_user, role="user")
        db.add(user)
        db.flush()
    return user


def _serialize_timestamp(value: datetime) -> str:
    return value.isoformat()


def _parse_sources(value: str | None) -> list[dict]:
    if not value:
        return []
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


@router.get("/conversations", response_model=list[ConversationSummary])
def list_conversations(
    x_debug_user: str | None = Header(default=None, alias="X-Debug-User"),
    db: Session = Depends(get_db_session),
) -> list[ConversationSummary]:
    with db.begin():
        user = _require_user(x_debug_user, db)
        conversations = (
            db.execute(
                select(Conversation)
                .where(Conversation.user_id == user.id)
                .order_by(Conversation.updated_at.desc(), Conversation.id.desc())
            )
            .scalars()
            .all()
        )

    return [
        ConversationSummary(
            conversation_id=conversation.id,
            title=conversation.title,
            created_at=_serialize_timestamp(conversation.created_at),
            updated_at=_serialize_timestamp(conversation.updated_at),
        )
        for conversation in conversations
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
def get_conversation_detail(
    conversation_id: int,
    x_debug_user: str | None = Header(default=None, alias="X-Debug-User"),
    db: Session = Depends(get_db_session),
) -> ConversationDetail:
    with db.begin():
        user = _require_user(x_debug_user, db)
        conversation = (
            db.execute(
                select(Conversation)
                .where(Conversation.id == conversation_id)
                .where(Conversation.user_id == user.id)
            )
            .scalars()
            .first()
        )
        if conversation is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Conversation not found")

        messages = (
            db.execute(
                select(Message)
                .where(Message.conversation_id == conversation.id)
                .order_by(Message.id.asc())
            )
            .scalars()
            .all()
        )

    return ConversationDetail(
        conversation_id=conversation.id,
        title=conversation.title,
        created_at=_serialize_timestamp(conversation.created_at),
        updated_at=_serialize_timestamp(conversation.updated_at),
        messages=[
            ConversationMessage(
                id=message.id,
                role=message.role,
                content=message.content,
                created_at=_serialize_timestamp(message.created_at),
                sources=_parse_sources(message.sources_json),
            )
            for message in messages
        ],
    )


@router.post("/ask", response_model=AskResponse)
def ask(
    payload: AskRequest,
    x_debug_user: str | None = Header(default=None, alias="X-Debug-User"),
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db_session),
) -> AskResponse:
    library_path = Path(settings.library_path)
    if not library_path.exists():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Library not available")

    with db.begin():
        user = _require_user(x_debug_user, db)

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

        conversation.updated_at = datetime.now(timezone.utc)
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
