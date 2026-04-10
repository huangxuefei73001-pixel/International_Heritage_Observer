from __future__ import annotations

import json
import tempfile
from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.deps import get_db_session, get_settings
from app.main import app
from app.database import Base
from app.models import Conversation, Message, User
from app.services.query_service import answer_from_library


def test_answer_from_library_returns_structured_blocks():
    library_path = Path("tests/tmp/chat_articles.jsonl")
    library_path.parent.mkdir(parents=True, exist_ok=True)
    library_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "article_id": "1",
                        "title": "韩国召开第48届世界遗产大会联席工作会",
                        "published_at": "2026-03-20 11:25",
                        "channel": "国际遗产观察",
                        "category": "韩国",
                        "source_url": "https://mp.weixin.qq.com/s/example",
                        "local_source_path": "/tmp/a.docx",
                        "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["韩国", "世界遗产大会"],
                    },
                    ensure_ascii=False,
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    result = answer_from_library("最近韩国有什么世界遗产动态？", library_path)

    assert "answer" in result
    assert "sources" in result
    assert result["sources"][0]["title"] == "韩国召开第48届世界遗产大会联席工作会"
    assert result["sources"][0]["url"] == "https://mp.weixin.qq.com/s/example"
    assert result["sources"][0]["published_at"] == "2026-03-20 11:25"
    assert result["sources"][0]["category"] == "韩国"
    assert result["sources"][0]["evidence_type"] == "一般动态"


def test_chat_ask_endpoint_returns_structured_answer():
    library_path = Path("tests/tmp/chat_endpoint_articles.jsonl")
    library_path.parent.mkdir(parents=True, exist_ok=True)
    library_path.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "article_id": "1",
                        "title": "韩国召开第48届世界遗产大会联席工作会",
                        "published_at": "2026-03-20 11:25",
                        "channel": "国际遗产观察",
                        "category": "韩国",
                        "source_url": "https://mp.weixin.qq.com/s/example",
                        "local_source_path": "/tmp/a.docx",
                        "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                        "content_html_excerpt": "<p>x</p>",
                        "parse_status": "ok",
                        "tags_auto": ["韩国", "世界遗产大会"],
                    },
                    ensure_ascii=False,
                )
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    client, engine, _ = _build_chat_test_client(library_path)

    try:
        response = client.post(
            "/chat/ask",
            headers={"X-Debug-User": "user@example.com"},
            json={"question": "最近韩国有什么世界遗产动态？"},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    body = response.json()
    assert "answer" in body
    assert "sources" in body
    assert body["sources"][0]["url"] == "https://mp.weixin.qq.com/s/example"


def test_chat_ask_endpoint_returns_controlled_error_when_library_is_missing():
    missing_path = Path(tempfile.gettempdir()) / "does-not-exist-chat-library.jsonl"
    if missing_path.exists():
        missing_path.unlink()

    client, engine, _ = _build_chat_test_client(missing_path)

    try:
        response = client.post(
            "/chat/ask",
            headers={"X-Debug-User": "user@example.com"},
            json={"question": "最近韩国有什么世界遗产动态？"},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 400
    assert response.json()["detail"] == "Library not available"


def _build_chat_test_client(library_path: Path):
    database_url = f"sqlite:///{library_path.parent / 'chat.db'}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def override_get_settings():
        return Settings(
            database_url=database_url,
            session_secret="secret",
            openrouter_api_key="test-key",
            openrouter_model="openai/gpt-4.1-mini",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user",
            smtp_password="pass",
            smtp_sender="bot@example.com",
            library_path=str(library_path),
        )

    def override_get_db_session():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_settings] = override_get_settings
    app.dependency_overrides[get_db_session] = override_get_db_session
    client = TestClient(app, raise_server_exceptions=False)
    return client, engine, session_factory


def test_chat_ask_creates_conversation_and_messages(tmp_path):
    library_path = tmp_path / "chat_library.jsonl"
    library_path.write_text(
        json.dumps(
            {
                "article_id": "1",
                "title": "韩国召开第48届世界遗产大会联席工作会",
                "published_at": "2026-03-20 11:25",
                "channel": "国际遗产观察",
                "category": "韩国",
                "source_url": "https://mp.weixin.qq.com/s/example",
                "local_source_path": "/tmp/a.docx",
                "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                "content_html_excerpt": "<p>x</p>",
                "parse_status": "ok",
                "tags_auto": ["韩国", "世界遗产大会"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    client, engine, session_factory = _build_chat_test_client(library_path)

    try:
        response = client.post(
            "/chat/ask",
            headers={"X-Debug-User": "user@example.com"},
            json={"question": "最近韩国有什么世界遗产动态？", "conversation_id": None},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] is not None
    assert body["messages_saved"] == 2

    with session_factory() as db:
        conversation = db.execute(select(Conversation)).scalar_one()
        messages = db.execute(select(Message).order_by(Message.id)).scalars().all()
        user = db.execute(select(User).where(User.email == "user@example.com")).scalar_one()

    assert conversation.user_id == user.id
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert messages[1].sources_json is not None


def test_chat_ask_reuses_existing_conversation(tmp_path):
    library_path = tmp_path / "chat_library.jsonl"
    library_path.write_text(
        json.dumps(
            {
                "article_id": "1",
                "title": "韩国召开第48届世界遗产大会联席工作会",
                "published_at": "2026-03-20 11:25",
                "channel": "国际遗产观察",
                "category": "韩国",
                "source_url": "https://mp.weixin.qq.com/s/example",
                "local_source_path": "/tmp/a.docx",
                "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                "content_html_excerpt": "<p>x</p>",
                "parse_status": "ok",
                "tags_auto": ["韩国", "世界遗产大会"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    client, engine, session_factory = _build_chat_test_client(library_path)

    try:
        with session_factory() as db:
            user = User(email="user@example.com", role="user")
            db.add(user)
            db.flush()
            conversation = Conversation(user_id=user.id, title="Existing")
            db.add(conversation)
            db.flush()
            db.execute(
                Conversation.__table__.update()
                .where(Conversation.id == conversation.id)
                .values(updated_at=datetime(2024, 1, 1, 0, 0, 0))
            )
            conversation_id = conversation.id
            db.commit()

        response = client.post(
            "/chat/ask",
            headers={"X-Debug-User": "user@example.com"},
            json={"question": "最近韩国有什么世界遗产动态？", "conversation_id": conversation_id},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    assert response.json()["conversation_id"] == conversation_id
    assert response.json()["messages_saved"] == 2

    with session_factory() as db:
        conversation = db.execute(select(Conversation).where(Conversation.id == conversation_id)).scalar_one()
        messages = db.execute(
            select(Message).where(Message.conversation_id == conversation_id).order_by(Message.id)
        ).scalars().all()

    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "assistant"
    assert conversation.updated_at > datetime(2024, 1, 1, 0, 0, 0)


def test_chat_ask_rejects_other_users_conversation(tmp_path):
    library_path = tmp_path / "chat_library.jsonl"
    library_path.write_text(
        json.dumps(
            {
                "article_id": "1",
                "title": "韩国召开第48届世界遗产大会联席工作会",
                "published_at": "2026-03-20 11:25",
                "channel": "国际遗产观察",
                "category": "韩国",
                "source_url": "https://mp.weixin.qq.com/s/example",
                "local_source_path": "/tmp/a.docx",
                "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                "content_html_excerpt": "<p>x</p>",
                "parse_status": "ok",
                "tags_auto": ["韩国", "世界遗产大会"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    client, engine, session_factory = _build_chat_test_client(library_path)

    try:
        with session_factory() as db:
            owner = User(email="owner@example.com", role="user")
            intruder = User(email="intruder@example.com", role="user")
            db.add_all([owner, intruder])
            db.flush()
            conversation = Conversation(user_id=owner.id, title="Owner")
            db.add(conversation)
            db.flush()
            conversation_id = conversation.id
            db.commit()

        response = client.post(
            "/chat/ask",
            headers={"X-Debug-User": "intruder@example.com"},
            json={"question": "最近韩国有什么世界遗产动态？", "conversation_id": conversation_id},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 400
    assert response.json()["detail"] == "Conversation not found"


def test_chat_ask_keeps_user_message_when_answer_generation_fails(tmp_path, monkeypatch):
    library_path = tmp_path / "chat_library.jsonl"
    library_path.write_text(
        json.dumps(
            {
                "article_id": "1",
                "title": "韩国召开第48届世界遗产大会联席工作会",
                "published_at": "2026-03-20 11:25",
                "channel": "国际遗产观察",
                "category": "韩国",
                "source_url": "https://mp.weixin.qq.com/s/example",
                "local_source_path": "/tmp/a.docx",
                "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                "content_html_excerpt": "<p>x</p>",
                "parse_status": "ok",
                "tags_auto": ["韩国", "世界遗产大会"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    client, engine, session_factory = _build_chat_test_client(library_path)
    monkeypatch.setattr(
        "app.routers.chat.answer_from_library",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    try:
        response = client.post(
            "/chat/ask",
            headers={"X-Debug-User": "user@example.com"},
            json={"question": "最近韩国有什么世界遗产动态？", "conversation_id": None},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 502
    assert response.json()["detail"]["conversation_id"] is not None

    with session_factory() as db:
        conversations = db.execute(select(Conversation)).scalars().all()
        messages = db.execute(select(Message).order_by(Message.id)).scalars().all()

    assert len(conversations) == 1
    assert len(messages) == 1
    assert messages[0].role == "user"


def test_chat_ask_returns_controlled_error_when_user_header_missing(tmp_path):
    library_path = tmp_path / "chat_library.jsonl"
    library_path.write_text(
        json.dumps(
            {
                "article_id": "1",
                "title": "韩国召开第48届世界遗产大会联席工作会",
                "published_at": "2026-03-20 11:25",
                "channel": "国际遗产观察",
                "category": "韩国",
                "source_url": "https://mp.weixin.qq.com/s/example",
                "local_source_path": "/tmp/a.docx",
                "content_text": "韩国日前召开第48届世界遗产大会跨部门工作会。",
                "content_html_excerpt": "<p>x</p>",
                "parse_status": "ok",
                "tags_auto": ["韩国", "世界遗产大会"],
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    client, engine, _ = _build_chat_test_client(library_path)

    try:
        response = client.post("/chat/ask", json={"question": "最近韩国有什么世界遗产动态？", "conversation_id": None})
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing X-Debug-User"
