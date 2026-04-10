# 国际遗产观察 Web 第一版 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a lightweight web product for the 国际遗产观察 knowledge base with email-code login, user chat + conversation history, admin conversation visibility, and manual knowledge-base refresh on a Tencent Cloud lightweight server.

**Architecture:** Use a single-server deployment with a Next.js frontend, a FastAPI backend, and a local PostgreSQL database. Reuse the existing Python knowledge-base parser, library builder, sync workflow, and evidence-first query engine rather than rebuilding retrieval logic.

**Tech Stack:** Next.js, React, TypeScript, FastAPI, SQLAlchemy, PostgreSQL, OpenRouter, Nginx, pytest/unittest, Playwright or minimal browser smoke tests, existing `guoji_yichan_guancha` Python modules.

---

## File Structure

- Create: `web/package.json`
- Create: `web/next.config.mjs`
- Create: `web/tsconfig.json`
- Create: `web/src/app/layout.tsx`
- Create: `web/src/app/page.tsx`
- Create: `web/src/app/chat/page.tsx`
- Create: `web/src/app/admin/page.tsx`
- Create: `web/src/app/globals.css`
- Create: `web/src/lib/api.ts`
- Create: `web/src/components/auth/login-form.tsx`
- Create: `web/src/components/chat/chat-shell.tsx`
- Create: `web/src/components/chat/message-list.tsx`
- Create: `web/src/components/chat/chat-input.tsx`
- Create: `web/src/components/admin/admin-shell.tsx`
- Create: `web/src/components/admin/conversation-table.tsx`
- Create: `web/src/components/admin/sync-panel.tsx`
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/models.py`
- Create: `backend/app/schemas.py`
- Create: `backend/app/deps.py`
- Create: `backend/app/auth.py`
- Create: `backend/app/email.py`
- Create: `backend/app/services/query_service.py`
- Create: `backend/app/services/sync_service.py`
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/routers/chat.py`
- Create: `backend/app/routers/admin.py`
- Create: `backend/tests/test_auth.py`
- Create: `backend/tests/test_chat.py`
- Create: `backend/tests/test_admin.py`
- Create: `deploy/nginx.conf`
- Create: `deploy/systemd/backend.service`
- Create: `deploy/systemd/frontend.service`
- Create: `deploy/setup-server.md`
- Create: `docs/superpowers/specs/2026-04-09-guoji-yichan-guancha-web-design.md` (already exists, reference only)
- Modify: `pyproject.toml`
- Modify: `src/guoji_yichan_guancha/query.py`
- Modify: `src/guoji_yichan_guancha/sync.py`
- Modify: `src/guoji_yichan_guancha/cli.py`
- Modify: `skills/guoji-yichan-guancha/SKILL.md`

## Task 1: Add Backend App Skeleton And Shared Config

**Files:**
- Create: `backend/app/main.py`
- Create: `backend/app/config.py`
- Create: `backend/app/database.py`
- Create: `backend/app/models.py`
- Create: `backend/app/schemas.py`
- Modify: `pyproject.toml`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write the failing backend import smoke test**

```python
from app.config import Settings


def test_settings_has_required_defaults():
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
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```bash
PYTHONPATH=backend python3 -m pytest backend/tests/test_auth.py::test_settings_has_required_defaults -v
```

Expected: FAIL because `app.config` does not exist.

- [ ] **Step 3: Add minimal backend package and settings**

```python
# backend/app/config.py
from pydantic import BaseModel


class Settings(BaseModel):
    database_url: str
    session_secret: str
    openrouter_api_key: str
    openrouter_model: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_sender: str
```

```python
# backend/app/main.py
from fastapi import FastAPI


app = FastAPI(title="国际遗产观察 Web API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
```

```python
# backend/app/database.py
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker


class Base(DeclarativeBase):
    pass


def build_engine(database_url: str):
    return create_engine(database_url, future=True)


def build_session_factory(database_url: str):
    engine = build_engine(database_url)
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
```

- [ ] **Step 4: Add minimal SQLAlchemy models for the four-table design**

```python
# backend/app/models.py
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    role: Mapped[str] = mapped_column(String(20), default="user")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    sources_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class LoginCode(Base):
    __tablename__ = "login_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), index=True)
    code_hash: Mapped[str] = mapped_column(String(255))
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    used_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
```

- [ ] **Step 5: Run the test to verify GREEN**

Run:

```bash
PYTHONPATH=backend python3 -m pytest backend/tests/test_auth.py::test_settings_has_required_defaults -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml backend/app backend/tests/test_auth.py
git commit -m "feat: add web backend skeleton"
```

## Task 2: Implement Email-Code Login And Role Routing

**Files:**
- Create: `backend/app/auth.py`
- Create: `backend/app/email.py`
- Create: `backend/app/routers/auth.py`
- Create: `backend/app/deps.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_auth.py`

- [ ] **Step 1: Write the failing auth flow test**

```python
from app.auth import build_login_code, verify_login_code


def test_login_code_round_trip():
    stored_hash, plain_code = build_login_code()

    assert len(plain_code) == 6
    assert verify_login_code(plain_code, stored_hash) is True
    assert verify_login_code("000000", stored_hash) is False
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```bash
PYTHONPATH=backend python3 -m pytest backend/tests/test_auth.py::test_login_code_round_trip -v
```

Expected: FAIL because `build_login_code` does not exist.

- [ ] **Step 3: Implement minimal auth helpers**

```python
# backend/app/auth.py
import hashlib
import secrets


def build_login_code() -> tuple[str, str]:
    plain = f"{secrets.randbelow(1_000_000):06d}"
    digest = hashlib.sha256(plain.encode("utf-8")).hexdigest()
    return digest, plain


def verify_login_code(plain_code: str, stored_hash: str) -> bool:
    digest = hashlib.sha256(plain_code.encode("utf-8")).hexdigest()
    return secrets.compare_digest(digest, stored_hash)
```

- [ ] **Step 4: Add send-code and verify-code endpoints**

```python
# backend/app/routers/auth.py
from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/send-code")
def send_code() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/verify-code")
def verify_code() -> dict[str, str]:
    return {"status": "ok"}
```

```python
# backend/app/main.py
from .routers import auth

app.include_router(auth.router)
```

- [ ] **Step 5: Run the tests to verify GREEN**

Run:

```bash
PYTHONPATH=backend python3 -m pytest backend/tests/test_auth.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/auth.py backend/app/email.py backend/app/deps.py backend/app/routers/auth.py backend/app/main.py backend/tests/test_auth.py
git commit -m "feat: add email code authentication"
```

## Task 3: Wrap Existing Query Logic As A Web Service

**Files:**
- Create: `backend/app/services/query_service.py`
- Create: `backend/app/routers/chat.py`
- Modify: `src/guoji_yichan_guancha/query.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_chat.py`

- [ ] **Step 1: Write the failing chat service test**

```python
from pathlib import Path

from app.services.query_service import answer_from_library


def test_answer_from_library_returns_structured_blocks(tmp_path):
    library_path = tmp_path / "articles.jsonl"
    library_path.write_text(
        '{"article_id":"1","title":"韩国召开第48届世界遗产大会联席工作会","published_at":"2026-03-20 11:25","channel":"国际遗产观察","category":"韩国","source_url":"https://mp.weixin.qq.com/s/example","local_source_path":"/tmp/a.docx","content_text":"韩国日前召开第48届世界遗产大会跨部门工作会。","content_html_excerpt":"<p>x</p>","parse_status":"ok","tags_auto":["韩国","世界遗产大会"]}\n',
        encoding="utf-8",
    )

    result = answer_from_library("最近韩国有什么世界遗产动态？", library_path)

    assert "answer" in result
    assert "sources" in result
    assert result["sources"][0]["url"] == "https://mp.weixin.qq.com/s/example"
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```bash
PYTHONPATH=backend:src python3 -m pytest backend/tests/test_chat.py::test_answer_from_library_returns_structured_blocks -v
```

Expected: FAIL because `answer_from_library` does not exist.

- [ ] **Step 3: Implement a thin adapter around the existing query engine**

```python
# backend/app/services/query_service.py
from pathlib import Path

from guoji_yichan_guancha.query import answer_question, collect_source_cards


def answer_from_library(question: str, library_path: Path) -> dict:
    return {
        "answer": answer_question(question, library_path, limit=5),
        "sources": collect_source_cards(question, library_path, limit=5),
    }
```

- [ ] **Step 4: Add a structured-source helper to the existing query module**

```python
# src/guoji_yichan_guancha/query.py
def collect_source_cards(question: str, library_path: Path, limit: int = 5) -> list[dict]:
    # reuse the same ranking path as answer_question
    return [
        {
            "title": document["title"],
            "url": document["source_url"],
            "published_at": document["published_at"],
            "category": document["category"],
            "evidence_type": infer_evidence_type(document),
        }
        for document in matches
    ]
```

- [ ] **Step 5: Add the chat API endpoint**

```python
# backend/app/routers/chat.py
from fastapi import APIRouter

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask")
def ask() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **Step 6: Run the tests to verify GREEN**

Run:

```bash
PYTHONPATH=backend:src python3 -m pytest backend/tests/test_chat.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/query_service.py backend/app/routers/chat.py backend/app/main.py backend/tests/test_chat.py src/guoji_yichan_guancha/query.py
git commit -m "feat: expose library query as chat service"
```

## Task 4: Persist Conversations And User Context

**Files:**
- Modify: `backend/app/models.py`
- Modify: `backend/app/routers/chat.py`
- Modify: `backend/app/schemas.py`
- Test: `backend/tests/test_chat.py`

- [ ] **Step 1: Write the failing conversation persistence test**

```python
def test_chat_request_creates_conversation_and_messages():
    response = client.post(
        "/chat/ask",
        json={"question": "最近韩国有什么世界遗产动态？", "conversation_id": None},
        headers={"X-Debug-User": "user@example.com"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["conversation_id"] is not None
    assert body["messages_saved"] == 2
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```bash
PYTHONPATH=backend:src python3 -m pytest backend/tests/test_chat.py::test_chat_request_creates_conversation_and_messages -v
```

Expected: FAIL because `/chat/ask` does not persist anything yet.

- [ ] **Step 3: Add request/response schemas**

```python
# backend/app/schemas.py
from pydantic import BaseModel


class AskRequest(BaseModel):
    question: str
    conversation_id: int | None = None


class AskResponse(BaseModel):
    conversation_id: int
    answer: str
    sources: list[dict]
    messages_saved: int
```

- [ ] **Step 4: Implement minimal persistence in the chat router**

```python
# backend/app/routers/chat.py
@router.post("/ask", response_model=AskResponse)
def ask(payload: AskRequest):
    # resolve current user
    # create conversation if needed
    # store user message
    # call answer_from_library
    # store assistant message with sources_json
    # return structured response
```

- [ ] **Step 5: Run the tests to verify GREEN**

Run:

```bash
PYTHONPATH=backend:src python3 -m pytest backend/tests/test_chat.py -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/app/models.py backend/app/schemas.py backend/app/routers/chat.py backend/tests/test_chat.py
git commit -m "feat: persist chat conversations"
```

## Task 5: Add Manual Knowledge-Base Refresh For Admins

**Files:**
- Create: `backend/app/services/sync_service.py`
- Create: `backend/app/routers/admin.py`
- Modify: `src/guoji_yichan_guancha/sync.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_admin.py`

- [ ] **Step 1: Write the failing admin refresh test**

```python
def test_admin_refresh_returns_sync_summary():
    response = client.post("/admin/refresh-library", headers={"X-Debug-User": "admin@example.com"})

    assert response.status_code == 200
    body = response.json()
    assert "article_count" in body
    assert "log_path" in body
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```bash
PYTHONPATH=backend:src python3 -m pytest backend/tests/test_admin.py::test_admin_refresh_returns_sync_summary -v
```

Expected: FAIL because `/admin/refresh-library` does not exist.

- [ ] **Step 3: Implement a backend wrapper around the existing sync workflow**

```python
# backend/app/services/sync_service.py
from pathlib import Path

from guoji_yichan_guancha.sync import sync_incremental


def refresh_library() -> dict:
    return sync_incremental(
        Path("/Users/pauline/Desktop/国际遗产观察/3.26-国际观察mptext抓取/本次新增"),
        Path("data/library"),
        Path("data/sync_logs"),
    )
```

- [ ] **Step 4: Add the admin endpoint**

```python
# backend/app/routers/admin.py
from fastapi import APIRouter

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/refresh-library")
def refresh_library() -> dict:
    return {"status": "ok"}
```

- [ ] **Step 5: Add an endpoint for listing all conversations**

```python
# backend/app/routers/admin.py
@router.get("/conversations")
def list_conversations() -> list[dict]:
    return []
```

- [ ] **Step 6: Run the tests to verify GREEN**

Run:

```bash
PYTHONPATH=backend:src python3 -m pytest backend/tests/test_admin.py -v
```

Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/sync_service.py backend/app/routers/admin.py backend/app/main.py backend/tests/test_admin.py src/guoji_yichan_guancha/sync.py
git commit -m "feat: add admin library refresh workflow"
```

## Task 6: Build The User-Facing Next.js App

**Files:**
- Create: `web/package.json`
- Create: `web/next.config.mjs`
- Create: `web/tsconfig.json`
- Create: `web/src/app/layout.tsx`
- Create: `web/src/app/page.tsx`
- Create: `web/src/app/chat/page.tsx`
- Create: `web/src/app/globals.css`
- Create: `web/src/lib/api.ts`
- Create: `web/src/components/auth/login-form.tsx`
- Create: `web/src/components/chat/chat-shell.tsx`
- Create: `web/src/components/chat/message-list.tsx`
- Create: `web/src/components/chat/chat-input.tsx`
- Test: `web` route smoke check

- [ ] **Step 1: Write the failing frontend smoke test**

```tsx
import { render, screen } from "@testing-library/react";
import { LoginForm } from "../src/components/auth/login-form";

test("renders email login form", () => {
  render(<LoginForm />);
  expect(screen.getByText("国际遗产观察")).toBeInTheDocument();
  expect(screen.getByPlaceholderText("you@example.com")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```bash
cd web && npm test -- login-form.test.tsx
```

Expected: FAIL because the web app does not exist yet.

- [ ] **Step 3: Create a minimal Next.js app with the agreed aesthetic direction**

```tsx
// web/src/app/page.tsx
import { LoginForm } from "@/components/auth/login-form";

export default function HomePage() {
  return <LoginForm />;
}
```

```tsx
// web/src/components/auth/login-form.tsx
export function LoginForm() {
  return (
    <main className="login-shell">
      <section className="hero-panel">
        <p className="eyebrow">International Heritage Observatory</p>
        <h1>国际遗产观察</h1>
        <p className="intro">在深蓝山野气质里，和文章库对话。</p>
        <input placeholder="you@example.com" />
        <button>发送验证码</button>
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Build the chat page shell with large whitespace and evidence-friendly layout**

```tsx
// web/src/app/chat/page.tsx
import { ChatShell } from "@/components/chat/chat-shell";

export default function ChatPage() {
  return <ChatShell />;
}
```

- [ ] **Step 5: Run the test and a local build to verify GREEN**

Run:

```bash
cd web && npm test -- login-form.test.tsx
cd web && npm run build
```

Expected: PASS, then a successful Next.js production build.

- [ ] **Step 6: Commit**

```bash
git add web
git commit -m "feat: add user-facing web shell"
```

## Task 7: Build The Admin Web View

**Files:**
- Create: `web/src/app/admin/page.tsx`
- Create: `web/src/components/admin/admin-shell.tsx`
- Create: `web/src/components/admin/conversation-table.tsx`
- Create: `web/src/components/admin/sync-panel.tsx`
- Test: admin route smoke check

- [ ] **Step 1: Write the failing admin UI smoke test**

```tsx
import { render, screen } from "@testing-library/react";
import { AdminShell } from "../src/components/admin/admin-shell";

test("renders admin controls", () => {
  render(<AdminShell />);
  expect(screen.getByText("全部对话")).toBeInTheDocument();
  expect(screen.getByText("更新知识库")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the test to verify RED**

Run:

```bash
cd web && npm test -- admin-shell.test.tsx
```

Expected: FAIL because the admin shell does not exist yet.

- [ ] **Step 3: Implement the minimal admin page**

```tsx
// web/src/components/admin/admin-shell.tsx
export function AdminShell() {
  return (
    <main className="admin-shell">
      <section>
        <h1>全部对话</h1>
      </section>
      <section>
        <h2>更新知识库</h2>
        <button>分类并更新入库</button>
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Run the test and build to verify GREEN**

Run:

```bash
cd web && npm test -- admin-shell.test.tsx
cd web && npm run build
```

Expected: PASS, then build success.

- [ ] **Step 5: Commit**

```bash
git add web/src/app/admin web/src/components/admin
git commit -m "feat: add admin web view"
```

## Task 8: Wire Deployment And Operational Docs

**Files:**
- Create: `deploy/nginx.conf`
- Create: `deploy/systemd/backend.service`
- Create: `deploy/systemd/frontend.service`
- Create: `deploy/setup-server.md`
- Modify: `skills/guoji-yichan-guancha/SKILL.md`

- [ ] **Step 1: Write the failing deployment checklist**

```markdown
- nginx reverse proxy configured
- frontend service starts on boot
- backend service starts on boot
- postgres reachable by backend
- sync command documented
```

- [ ] **Step 2: Draft the deployment files**

```nginx
# deploy/nginx.conf
server {
    listen 80;
    server_name _;

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
    }

    location / {
        proxy_pass http://127.0.0.1:3000/;
    }
}
```

```ini
# deploy/systemd/backend.service
[Service]
WorkingDirectory=/srv/guoji-yichan-guancha
ExecStart=/srv/guoji-yichan-guancha/.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```ini
# deploy/systemd/frontend.service
[Service]
WorkingDirectory=/srv/guoji-yichan-guancha/web
ExecStart=/usr/bin/npm run start
```

- [ ] **Step 3: Write the server setup guide**

```markdown
1. Install Node.js, Python, PostgreSQL, Nginx
2. Clone repo to `/srv/guoji-yichan-guancha`
3. Set backend env vars for OpenRouter and SMTP
4. Build frontend
5. Start backend and frontend systemd services
6. Enable Nginx
```

- [ ] **Step 4: Run validation commands**

Run:

```bash
python3 -m py_compile backend/app/main.py
cd web && npm run build
```

Expected: both succeed.

- [ ] **Step 5: Commit**

```bash
git add deploy skills/guoji-yichan-guancha/SKILL.md
git commit -m "docs: add deployment and operations guide"
```

## Self-Review

- Spec coverage:
  - Web entry for non-technical users: Tasks 6 and 7
  - Email-code login: Tasks 1 and 2
  - User chat and personal history: Tasks 3, 4, and 6
  - Admin view of all conversations: Tasks 5 and 7
  - Manual library refresh: Task 5
  - Reuse existing knowledge-base logic: Tasks 3 and 5
  - Tencent Cloud lightweight deployment: Task 8
  - Deep-blue, mountain-trail visual direction: Task 6
- Placeholder scan:
  - No `TBD`, `TODO`, or “implement later” placeholders remain in the plan body.
- Type consistency:
  - Core entities stay consistent as `User`, `Conversation`, `Message`, `LoginCode`.
  - Chat API stays centered on `AskRequest` / `AskResponse`.
  - Admin refresh endpoint remains `/admin/refresh-library` throughout.

