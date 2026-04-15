from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import build_login_code, verify_login_code
from app.config import Settings
from app.database import Base, build_session_factory
from app.deps import get_db_session, get_settings
from app.main import app
from app.models import LoginCode, User
from app.routers.auth import router as auth_router

from pydantic import ValidationError


def test_settings_requires_fields_and_behaves_like_a_real_model():
    settings = Settings(
        database_url="postgresql://user:pass@localhost:5432/heritage",
        session_secret="secret",
        openrouter_api_key="test-key",
        openrouter_model="openai/gpt-4.1-mini",
        smtp_host="smtp.example.com",
        smtp_port=587,
        smtp_username="user",
        smtp_password="pass",
        smtp_sender="bot@example.com",
    )

    assert settings.openrouter_model == "openai/gpt-4.1-mini"
    assert settings.smtp_sender == "bot@example.com"

    try:
        Settings(
            database_url="postgresql://user:pass@localhost:5432/heritage",
            session_secret="secret",
            openrouter_api_key="test-key",
            openrouter_model="openai/gpt-4.1-mini",
            smtp_host="smtp.example.com",
            smtp_port=587,
            smtp_username="user",
            smtp_password="pass",
        )
    except ValidationError:
        pass
    else:
        raise AssertionError("Settings should require smtp_sender")


def test_login_code_round_trip():
    stored_hash, plain_code = build_login_code()
    assert len(plain_code) == 6
    assert verify_login_code(plain_code, stored_hash) is True
    assert verify_login_code("000000", stored_hash) is False


def test_auth_router_registers_expected_endpoints():
    paths = {route.path for route in auth_router.routes}

    assert "/auth/send-code" in paths
    assert "/auth/verify-code" in paths
    assert "/auth/password-login" in paths


def test_build_session_factory_reuses_engine_and_factory(monkeypatch):
    build_session_factory.cache_clear()
    calls = {"engine": 0, "factory": 0}
    sentinel_factory = object()

    def fake_create_engine(*args, **kwargs):
        calls["engine"] += 1
        return object()

    def fake_sessionmaker(*args, **kwargs):
        calls["factory"] += 1
        return sentinel_factory

    monkeypatch.setattr("app.database.create_engine", fake_create_engine)
    monkeypatch.setattr("app.database.sessionmaker", fake_sessionmaker)

    factory1 = build_session_factory("sqlite:///tmp/test.db")
    factory2 = build_session_factory("sqlite:///tmp/test.db")

    assert factory1 is factory2
    assert calls == {"engine": 1, "factory": 1}


@pytest.fixture
def auth_test_context(tmp_path: Path):
    database_url = f"sqlite:///{tmp_path / 'auth.db'}"
    engine = create_engine(
        database_url,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def override_get_db_session():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

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
        )

    app.dependency_overrides[get_db_session] = override_get_db_session
    app.dependency_overrides[get_settings] = override_get_settings

    client = TestClient(app, raise_server_exceptions=False)
    try:
        yield client, session_factory
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()


def test_send_code_does_not_persist_when_email_fails(auth_test_context, monkeypatch):
    client, session_factory = auth_test_context
    stored_hash, plain_code = build_login_code()

    monkeypatch.setattr("app.routers.auth.build_login_code", lambda: (stored_hash, plain_code))

    def fail_send_login_code_email(*args, **kwargs):
        raise RuntimeError("smtp failed")

    monkeypatch.setattr("app.routers.auth.send_login_code_email", fail_send_login_code_email)

    response = client.post("/auth/send-code", json={"email": "user@example.com"})

    assert response.status_code == 500

    with session_factory() as db:
        count = db.execute(select(func.count()).select_from(LoginCode)).scalar_one()
    assert count == 0


def test_verify_code_cannot_be_used_twice(auth_test_context, monkeypatch):
    client, _ = auth_test_context
    stored_hash, plain_code = build_login_code()

    monkeypatch.setattr("app.routers.auth.build_login_code", lambda: (stored_hash, plain_code))
    monkeypatch.setattr("app.routers.auth.send_login_code_email", lambda *args, **kwargs: None)

    send_response = client.post("/auth/send-code", json={"email": "user@example.com"})
    assert send_response.status_code == 200

    first_response = client.post(
        "/auth/verify-code",
        json={"email": "user@example.com", "code": plain_code},
    )
    assert first_response.status_code == 200
    assert first_response.json()["verified"] is True

    second_response = client.post(
        "/auth/verify-code",
        json={"email": "user@example.com", "code": plain_code},
    )
    assert second_response.status_code == 400


def test_verify_code_creates_user_and_returns_role(auth_test_context, monkeypatch):
    client, session_factory = auth_test_context
    stored_hash, plain_code = build_login_code()

    monkeypatch.setattr("app.routers.auth.build_login_code", lambda: (stored_hash, plain_code))
    monkeypatch.setattr("app.routers.auth.send_login_code_email", lambda *args, **kwargs: None)

    send_response = client.post("/auth/send-code", json={"email": "new@example.com"})
    assert send_response.status_code == 200

    verify_response = client.post(
        "/auth/verify-code",
        json={"email": "new@example.com", "code": plain_code},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["role"] == "user"

    with session_factory() as db:
        user = db.execute(select(User).where(User.email == "new@example.com")).scalar_one()
    assert user.role == "user"


def test_verify_code_returns_admin_for_admin_user(auth_test_context, monkeypatch):
    client, session_factory = auth_test_context
    stored_hash, plain_code = build_login_code()

    monkeypatch.setattr("app.routers.auth.build_login_code", lambda: (stored_hash, plain_code))
    monkeypatch.setattr("app.routers.auth.send_login_code_email", lambda *args, **kwargs: None)

    with session_factory() as db:
        db.add(User(email="admin@example.com", role="admin"))
        db.commit()

    send_response = client.post("/auth/send-code", json={"email": "admin@example.com"})
    assert send_response.status_code == 200

    verify_response = client.post(
        "/auth/verify-code",
        json={"email": "admin@example.com", "code": plain_code},
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["role"] == "admin"


def test_password_login_creates_or_updates_admin_user(auth_test_context):
    client, session_factory = auth_test_context

    response = client.post(
        "/auth/password-login",
        json={"username": "admin", "password": "admin"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "email": "admin",
        "role": "admin",
        "verified": True,
    }

    with session_factory() as db:
        user = db.execute(select(User).where(User.email == "admin")).scalar_one()

    assert user.role == "admin"


def test_password_login_rejects_invalid_credentials(auth_test_context):
    client, _ = auth_test_context

    response = client.post(
        "/auth/password-login",
        json={"username": "admin", "password": "wrong"},
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password"
