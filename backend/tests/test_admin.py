from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import Settings
from app.database import Base
from app.deps import get_db_session, get_settings
from app.main import app
from app.models import Conversation, Message, User


def _build_admin_test_client(library_path: Path):
    database_url = f"sqlite:///{library_path.parent / 'admin.db'}"
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
            incoming_source_dir="/Users/pauline/Desktop/国际遗产观察/3.26-国际观察mptext抓取/本次新增",
            sync_log_dir="data/sync_logs",
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


def test_admin_conversations_requires_admin_user(tmp_path):
    library_path = tmp_path / "library" / "articles.jsonl"
    library_path.parent.mkdir(parents=True, exist_ok=True)
    client, engine, session_factory = _build_admin_test_client(library_path)

    try:
        with session_factory() as db:
            db.add(User(email="user@example.com", role="user"))
            db.commit()

        response = client.get(
            "/admin/conversations",
            headers={"X-Debug-User": "user@example.com"},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 403
    assert response.json()["detail"] == "Admin access required"


def test_admin_conversations_returns_minimal_list_for_admin_user(tmp_path):
    library_path = tmp_path / "library" / "articles.jsonl"
    library_path.parent.mkdir(parents=True, exist_ok=True)
    client, engine, session_factory = _build_admin_test_client(library_path)

    try:
        with session_factory() as db:
            admin = User(email="admin@example.com", role="admin")
            user = User(email="user@example.com", role="user")
            db.add_all([admin, user])
            db.flush()

            older_conversation = Conversation(user_id=user.id, title="First thread")
            newer_conversation = Conversation(user_id=admin.id, title="Second thread")
            db.add_all([older_conversation, newer_conversation])
            db.flush()
            db.execute(
                Conversation.__table__.update()
                .where(Conversation.id == older_conversation.id)
                .values(updated_at=datetime(2024, 1, 1, 0, 0, 0))
            )
            db.execute(
                Conversation.__table__.update()
                .where(Conversation.id == newer_conversation.id)
                .values(updated_at=datetime(2024, 1, 2, 0, 0, 0))
            )
            db.commit()

        response = client.get(
            "/admin/conversations",
            headers={"X-Debug-User": "admin@example.com"},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["title"] == "Second thread"
    assert body[0]["user_email"] == "admin@example.com"
    assert set(body[0].keys()) == {"conversation_id", "title", "user_email", "created_at", "updated_at"}


def test_admin_refresh_library_returns_sync_summary(tmp_path, monkeypatch):
    library_path = tmp_path / "library" / "articles.jsonl"
    library_path.parent.mkdir(parents=True, exist_ok=True)
    client, engine, session_factory = _build_admin_test_client(library_path)
    calls: list[tuple[Path, Path, Path]] = []

    try:
        with session_factory() as db:
            db.add(User(email="admin@example.com", role="admin"))
            db.commit()

        def fake_refresh_library(settings):
            calls.append(
                (
                    Path(settings.incoming_source_dir),
                    Path(settings.library_path).parent,
                    Path(settings.sync_log_dir),
                )
            )
            return {"article_count": 7, "log_path": "/tmp/sync-log.json", "total_article_count": 7}

        monkeypatch.setattr("app.routers.admin.refresh_library", fake_refresh_library)

        response = client.post(
            "/admin/refresh-library",
            headers={"X-Debug-User": "admin@example.com"},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    body = response.json()
    assert body["article_count"] == 7
    assert body["log_path"] == "/tmp/sync-log.json"
    assert calls == [
        (
            Path("/Users/pauline/Desktop/国际遗产观察/3.26-国际观察mptext抓取/本次新增"),
            Path(library_path).parent,
            Path("data/sync_logs"),
        )
    ]


def test_admin_refresh_library_missing_header_is_rejected(tmp_path):
    library_path = tmp_path / "library" / "articles.jsonl"
    library_path.parent.mkdir(parents=True, exist_ok=True)
    client, engine, _ = _build_admin_test_client(library_path)

    try:
        response = client.post("/admin/refresh-library")
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 400
    assert response.json()["detail"] == "Missing X-Debug-User"


def test_admin_messages_returns_all_user_questions_for_admin(tmp_path):
    library_path = tmp_path / "library" / "articles.jsonl"
    library_path.parent.mkdir(parents=True, exist_ok=True)
    client, engine, session_factory = _build_admin_test_client(library_path)

    try:
        with session_factory() as db:
            admin = User(email="admin@example.com", role="admin")
            guest = User(email="guest-1@guest.local", role="user")
            db.add_all([admin, guest])
            db.flush()

            conversation = Conversation(user_id=guest.id, title="第一问")
            db.add(conversation)
            db.flush()

            first_message = Message(conversation_id=conversation.id, role="user", content="第一问")
            assistant_message = Message(conversation_id=conversation.id, role="assistant", content="第一答")
            second_message = Message(conversation_id=conversation.id, role="user", content="第二问")
            db.add_all([first_message, assistant_message, second_message])
            db.flush()

            db.execute(
                Message.__table__.update()
                .where(Message.id == first_message.id)
                .values(created_at=datetime(2024, 1, 1, 0, 0, 0))
            )
            db.execute(
                Message.__table__.update()
                .where(Message.id == assistant_message.id)
                .values(created_at=datetime(2024, 1, 1, 0, 1, 0))
            )
            db.execute(
                Message.__table__.update()
                .where(Message.id == second_message.id)
                .values(created_at=datetime(2024, 1, 1, 0, 2, 0))
            )
            db.commit()

        response = client.get(
            "/admin/messages",
            headers={"X-Debug-User": "admin@example.com"},
        )
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 2
    assert body[0]["content"] == "第二问"
    assert body[0]["conversation_title"] == "第一问"
    assert body[0]["user_email"] == "guest-1@guest.local"
    assert body[1]["content"] == "第一问"
    assert set(body[0].keys()) == {
        "message_id",
        "conversation_id",
        "conversation_title",
        "content",
        "user_email",
        "created_at",
    }
