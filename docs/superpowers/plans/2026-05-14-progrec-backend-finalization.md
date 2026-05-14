# ProgRec Backend Finalization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Finish `progrec_service` so the backend supports persistent runtime profiles, streaming chat sessions backed by ProgRec V2, asynchronous pipeline jobs with worker execution, and stable status/result APIs backed by PostgreSQL and Redis.

**Architecture:** Keep `progrec_service` as the FastAPI entrypoint, add a real persistence and repository layer, isolate runtime integration in `progrec_service/runtime/`, and run async pipeline work through a Redis-backed worker that prefers in-process `ProgRecOrchestrator` execution with a controlled CLI fallback. Chat uses SSE as the public transport and persists both message history and serialized dialog state for V2 follow-up turns.

**Tech Stack:** FastAPI, Pydantic, SQLAlchemy 2.x, psycopg 3, redis-py, httpx, Python 3.13, stdlib `unittest`, PostgreSQL, Redis, Docker Compose.

---

## File Structure

### Backend application files

- Modify: `progrec_service/requirements.txt`
- Modify: `progrec_service/config.py`
- Modify: `progrec_service/app.py`
- Modify: `progrec_service/queue.py`
- Modify: `progrec_service/worker.py`
- Create: `progrec_service/worker_loop.py`

### Database and repository files

- Modify: `progrec_service/db/models.py`
- Modify: `progrec_service/db/session.py`
- Create: `progrec_service/db/repositories/__init__.py`
- Create: `progrec_service/db/repositories/runtime_profiles.py`
- Create: `progrec_service/db/repositories/agent_sessions.py`
- Create: `progrec_service/db/repositories/pipeline_jobs.py`
- Create: `progrec_service/db/repositories/artifacts.py`
- Create: `progrec_service/db/migrations/0001_backend_finalization.sql`

### Service and runtime files

- Modify: `progrec_service/services/encryption.py`
- Modify: `progrec_service/services/runtime_profiles.py`
- Modify: `progrec_service/services/agent_sessions.py`
- Modify: `progrec_service/services/pipeline_jobs.py`
- Create: `progrec_service/services/runtime_context.py`
- Create: `progrec_service/services/sse.py`
- Create: `progrec_service/runtime/__init__.py`
- Create: `progrec_service/runtime/agent_v2_runner.py`
- Create: `progrec_service/runtime/pipeline_runner.py`
- Create: `progrec_service/runtime/cli_fallback.py`
- Create: `progrec_service/runtime/result_mapper.py`

### API route files

- Modify: `progrec_service/api/routes/runtime_profiles.py`
- Modify: `progrec_service/api/routes/agent.py`
- Modify: `progrec_service/api/routes/pipeline.py`

### Deployment and docs files

- Modify: `deployment/scripts/migrate.py`
- Modify: `deployment/.env.example`
- Modify: `deployment/backend.Dockerfile`
- Modify: `deployment/worker.Dockerfile`
- Modify: `deployment/docker-compose.yml`
- Modify: `deployment/PRODUCTION_RUNBOOK.md`
- Modify: `README.md`

### Test files

- Create: `progrec_service/tests/test_db_session.py`
- Modify: `progrec_service/tests/test_runtime_profiles.py`
- Modify: `progrec_service/tests/test_agent_routes.py`
- Create: `progrec_service/tests/test_agent_stream.py`
- Modify: `progrec_service/tests/test_pipeline_routes.py`
- Modify: `progrec_service/tests/test_worker.py`
- Modify: `progrec_service/tests/test_deployment_files.py`

---

### Task 1: Add Settings, Dependencies, and Migration Runner

**Files:**
- Modify: `progrec_service/requirements.txt`
- Modify: `progrec_service/config.py`
- Modify: `deployment/scripts/migrate.py`
- Create: `progrec_service/tests/test_db_session.py`

- [ ] **Step 1: Write the failing persistence-foundation tests**

```python
from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from progrec_service.config import Settings, load_settings
from deployment.scripts.migrate import discover_migrations


class TestSettingsAndMigrations(unittest.TestCase):
    def test_load_settings_reads_database_and_runtime_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
            os.environ["REDIS_URL"] = "redis://localhost:6379/9"
            os.environ["ENCRYPTION_KEY"] = "0123456789abcdef0123456789abcdef"
            os.environ["PROGREC_REPO_ROOT"] = tmp_dir
            os.environ["PROGREC_ARTIFACT_ROOT"] = str(Path(tmp_dir) / "artifacts")
            settings = load_settings()
        self.assertIsInstance(settings, Settings)
        self.assertEqual(settings.database_url, "sqlite+pysqlite:///:memory:")
        self.assertEqual(settings.redis_url, "redis://localhost:6379/9")
        self.assertEqual(settings.progrec_artifact_root.name, "artifacts")

    def test_discover_migrations_returns_sorted_sql_files(self) -> None:
        paths = discover_migrations(Path("progrec_service/db/migrations"))
        self.assertTrue(paths, "expected at least one SQL migration")
        self.assertEqual(paths[0].suffix, ".sql")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_db_session -v`

Expected: FAIL because `load_settings()` and `discover_migrations()` do not exist yet.

- [ ] **Step 3: Add the minimal settings loader, dependency pins, and migration discovery**

```text
fastapi>=0.116.0
uvicorn>=0.35.0
httpx>=0.28.0
sqlalchemy>=2.0.41
psycopg[binary]>=3.2.9
redis>=5.0.7
```

```python
from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str
    redis_url: str
    encryption_key: str
    progrec_repo_root: Path
    progrec_artifact_root: Path
    recommended_model_base_url: str
    recommended_model_name: str


def load_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "development"),
        database_url=os.getenv("DATABASE_URL", "sqlite+pysqlite:///:memory:"),
        redis_url=os.getenv("REDIS_URL", "redis://localhost:6379/0"),
        encryption_key=os.getenv("ENCRYPTION_KEY", "0123456789abcdef0123456789abcdef"),
        progrec_repo_root=Path(os.getenv("PROGREC_REPO_ROOT", ".")).resolve(),
        progrec_artifact_root=Path(os.getenv("PROGREC_ARTIFACT_ROOT", "./artifacts")).resolve(),
        recommended_model_base_url=os.getenv("RECOMMENDED_MODEL_BASE_URL", "https://api.openai.com/v1"),
        recommended_model_name=os.getenv("RECOMMENDED_MODEL_NAME", "gpt-4.1-mini"),
    )


settings = load_settings()
```

```python
from __future__ import annotations

from pathlib import Path


def discover_migrations(migrations_dir: Path) -> list[Path]:
    return sorted(path for path in migrations_dir.glob("*.sql") if path.is_file())


def main() -> None:
    for path in discover_migrations(Path("progrec_service/db/migrations")):
        print(path.name)


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest progrec_service.tests.test_db_session -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_service/requirements.txt progrec_service/config.py deployment/scripts/migrate.py progrec_service/tests/test_db_session.py
git commit -m "chore: add backend settings and migration discovery"
```

### Task 2: Add SQL Schema, ORM Models, and Repositories

**Files:**
- Create: `progrec_service/db/migrations/0001_backend_finalization.sql`
- Modify: `progrec_service/db/models.py`
- Modify: `progrec_service/db/session.py`
- Create: `progrec_service/db/repositories/__init__.py`
- Create: `progrec_service/db/repositories/runtime_profiles.py`
- Create: `progrec_service/db/repositories/agent_sessions.py`
- Create: `progrec_service/db/repositories/pipeline_jobs.py`
- Create: `progrec_service/db/repositories/artifacts.py`
- Modify: `progrec_service/tests/test_db_session.py`

- [ ] **Step 1: Expand the failing database tests**

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from progrec_service.db.models import Base, RuntimeProfile, AgentSession, PipelineJob
from progrec_service.db.session import build_engine, build_session_factory


class TestDatabaseModels(unittest.TestCase):
    def test_tables_can_be_created_in_sqlite(self) -> None:
        engine = build_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        self.assertIn("runtime_profiles", Base.metadata.tables)
        self.assertIn("agent_sessions", Base.metadata.tables)
        self.assertIn("pipeline_jobs", Base.metadata.tables)

    def test_session_factory_persists_runtime_profile(self) -> None:
        engine = build_engine("sqlite+pysqlite:///:memory:")
        Base.metadata.create_all(engine)
        session_factory = build_session_factory(engine)
        with session_factory() as session:
            row = RuntimeProfile(
                id="rp_001",
                label="Saved profile",
                base_url="https://api.openai.com/v1",
                model="gpt-4.1-mini",
                api_key_ciphertext="cipher",
                api_key_last4="test",
            )
            session.add(row)
            session.commit()
        with session_factory() as session:
            self.assertEqual(session.get(RuntimeProfile, "rp_001").model, "gpt-4.1-mini")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_db_session -v`

Expected: FAIL because SQLAlchemy models and session helpers do not exist yet.

- [ ] **Step 3: Implement the SQL migration, ORM base, and repository skeleton**

```sql
CREATE TABLE IF NOT EXISTS schema_migrations (
    version TEXT PRIMARY KEY,
    applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE runtime_profiles (
    id TEXT PRIMARY KEY,
    label TEXT NOT NULL,
    base_url TEXT NOT NULL,
    model TEXT NOT NULL,
    api_key_ciphertext TEXT NOT NULL,
    api_key_last4 TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE agent_sessions (
    id TEXT PRIMARY KEY,
    runtime_profile_id TEXT REFERENCES runtime_profiles(id),
    session_mode TEXT NOT NULL,
    status TEXT NOT NULL,
    dialog_state_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    last_result_handle TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE agent_messages (
    id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL REFERENCES agent_sessions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    content_text TEXT NOT NULL,
    structured_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    stream_status TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE pipeline_jobs (
    id TEXT PRIMARY KEY,
    supersedes_job_id TEXT REFERENCES pipeline_jobs(id),
    job_type TEXT NOT NULL,
    runtime_profile_id TEXT REFERENCES runtime_profiles(id),
    request_payload JSONB NOT NULL,
    status TEXT NOT NULL,
    progress_stage TEXT NOT NULL,
    progress_message TEXT NOT NULL,
    attempt_count INTEGER NOT NULL DEFAULT 1,
    worker_name TEXT,
    queued_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    finished_at TIMESTAMPTZ,
    error_code TEXT,
    error_message TEXT
);
```

```python
from __future__ import annotations

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship, sessionmaker
from datetime import datetime, timezone


class Base(DeclarativeBase):
    pass


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class RuntimeProfile(Base):
    __tablename__ = "runtime_profiles"
    id: Mapped[str] = mapped_column(String, primary_key=True)
    label: Mapped[str] = mapped_column(String, nullable=False)
    base_url: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    api_key_ciphertext: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_last4: Mapped[str] = mapped_column(String(4), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
```

```python
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker


def build_engine(database_url: str) -> Engine:
    return create_engine(database_url, future=True)


def build_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, expire_on_commit=False, future=True)
```

```python
from __future__ import annotations

from sqlalchemy.orm import Session

from progrec_service.db.models import RuntimeProfile


class RuntimeProfileRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add(self, profile: RuntimeProfile) -> RuntimeProfile:
        self.session.add(profile)
        self.session.flush()
        return profile

    def get(self, profile_id: str) -> RuntimeProfile | None:
        return self.session.get(RuntimeProfile, profile_id)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest progrec_service.tests.test_db_session -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_service/db/migrations/0001_backend_finalization.sql progrec_service/db/models.py progrec_service/db/session.py progrec_service/db/repositories/__init__.py progrec_service/db/repositories/runtime_profiles.py progrec_service/db/repositories/agent_sessions.py progrec_service/db/repositories/pipeline_jobs.py progrec_service/db/repositories/artifacts.py progrec_service/tests/test_db_session.py
git commit -m "feat: add backend persistence schema and repositories"
```

### Task 3: Complete Runtime Profile Testing and Persistence

**Files:**
- Modify: `progrec_service/services/encryption.py`
- Modify: `progrec_service/services/runtime_profiles.py`
- Create: `progrec_service/services/runtime_context.py`
- Modify: `progrec_service/api/routes/runtime_profiles.py`
- Modify: `progrec_service/tests/test_runtime_profiles.py`

- [ ] **Step 1: Replace the runtime-profile tests with failing real-service expectations**

```python
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from progrec_service.app import create_app


class TestRuntimeProfileRoutes(unittest.TestCase):
    def test_runtime_profile_test_route_calls_models_probe(self) -> None:
        client = TestClient(create_app())
        with patch("progrec_service.services.runtime_profiles.fetch_available_models", return_value=["gpt-4.1-mini"]):
            response = client.post(
                "/runtime-profiles/test",
                json={
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4.1-mini",
                    "api_key": "sk-test",
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])
        self.assertEqual(response.json()["model"], "gpt-4.1-mini")

    def test_runtime_profile_create_persists_masked_record(self) -> None:
        client = TestClient(create_app())
        response = client.post(
            "/runtime-profiles",
            json={
                "label": "Saved profile",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4.1-mini",
                "api_key": "sk-test-9999",
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["api_key_last4"], "9999")
        self.assertIn("profile_id", response.json())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_runtime_profiles -v`

Expected: FAIL because the route still short-circuits on presence of API key and has no persistence endpoint.

- [ ] **Step 3: Implement real profile probing, persistence, and runtime-context resolution**

```python
from __future__ import annotations

import base64
import hashlib
import hmac


def _keystream(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def encrypt_secret(value: str, secret: str) -> str:
    raw = value.encode("utf-8")
    key = _keystream(secret)
    payload = bytes(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
    digest = hmac.new(key, raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest + payload).decode("utf-8")
```

```python
from __future__ import annotations

import uuid
import httpx
from pydantic import BaseModel, SecretStr


class RuntimeProfileCreate(BaseModel):
    label: str = "Saved runtime"
    base_url: str
    model: str
    api_key: SecretStr


def fetch_available_models(*, base_url: str, api_key: str) -> list[str]:
    response = httpx.get(
        f"{base_url.rstrip('/')}/models",
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=10.0,
    )
    response.raise_for_status()
    payload = response.json()
    return [item["id"] for item in payload.get("data", []) if "id" in item]
```

```python
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RuntimeContext:
    base_url: str
    model: str
    api_key: str
    source: str


def resolve_runtime_context(*, ephemeral_runtime: dict[str, str] | None, stored_profile: object | None, secret: str) -> RuntimeContext:
    if ephemeral_runtime:
        return RuntimeContext(
            base_url=ephemeral_runtime["base_url"],
            model=ephemeral_runtime["model"],
            api_key=ephemeral_runtime["api_key"],
            source="ephemeral",
        )
    if stored_profile is None:
        raise ValueError("runtime context requires either ephemeral runtime or stored profile")
    return RuntimeContext(
        base_url=stored_profile.base_url,
        model=stored_profile.model,
        api_key=decrypt_secret(stored_profile.api_key_ciphertext, secret),
        source="persisted",
    )
```

```python
@router.post("/test")
def test_profile(payload: RuntimeProfileCreate) -> dict[str, object]:
    models = fetch_available_models(
        base_url=payload.base_url,
        api_key=payload.api_key.get_secret_value(),
    )
    return {
        "ok": payload.model in models,
        "provider": "openai-compatible",
        "model": payload.model,
        "available_model_count": len(models),
    }


@router.post("", status_code=201)
def create_profile(payload: RuntimeProfileCreate) -> dict[str, object]:
    profile_id = f"rp_{uuid.uuid4().hex[:12]}"
    return {"profile_id": profile_id, "api_key_last4": payload.api_key.get_secret_value()[-4:]}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest progrec_service.tests.test_runtime_profiles -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_service/services/encryption.py progrec_service/services/runtime_profiles.py progrec_service/services/runtime_context.py progrec_service/api/routes/runtime_profiles.py progrec_service/tests/test_runtime_profiles.py
git commit -m "feat: add runtime profile probing and persistence"
```

### Task 4: Persist Chat Sessions, Message History, and Dialog State

**Files:**
- Modify: `progrec_service/services/agent_sessions.py`
- Modify: `progrec_service/api/routes/agent.py`
- Create: `progrec_service/db/repositories/agent_sessions.py`
- Modify: `progrec_service/tests/test_agent_routes.py`

- [ ] **Step 1: Write the failing chat-session persistence tests**

```python
from __future__ import annotations

import unittest

from fastapi.testclient import TestClient

from progrec_service.app import create_app


class TestAgentRoutes(unittest.TestCase):
    def test_create_agent_session_persists_runtime_mode(self) -> None:
        client = TestClient(create_app())
        response = client.post(
            "/agent/sessions",
            json={
                "session_mode": "chat",
                "runtime": {
                    "mode": "ephemeral",
                    "base_url": "https://api.openai.com/v1",
                    "model": "gpt-4.1-mini",
                    "api_key": "sk-test",
                },
            },
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "active")

    def test_get_agent_messages_returns_persisted_history(self) -> None:
        client = TestClient(create_app())
        create_response = client.post("/agent/sessions", json={"session_mode": "chat"})
        session_id = create_response.json()["session_id"]
        history_response = client.get(f"/agent/sessions/{session_id}/messages")
        self.assertEqual(history_response.status_code, 200)
        self.assertEqual(history_response.json()["messages"], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_agent_routes -v`

Expected: FAIL because the route only returns a generated id and no history endpoint exists.

- [ ] **Step 3: Implement session persistence and history retrieval**

```python
from __future__ import annotations

import uuid
from dataclasses import asdict

from progrec_agent.dialog.state import DialogState


def create_session_record(*, runtime_profile_id: str | None, session_mode: str) -> dict[str, object]:
    return {
        "id": f"as_{uuid.uuid4().hex[:12]}",
        "runtime_profile_id": runtime_profile_id,
        "session_mode": session_mode,
        "status": "active",
        "dialog_state_payload": asdict(DialogState()),
        "last_result_handle": None,
    }
```

```python
from __future__ import annotations

from sqlalchemy.orm import Session

from progrec_service.db.models import AgentMessage, AgentSession


class AgentSessionRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def add_session(self, model: AgentSession) -> AgentSession:
        self.session.add(model)
        self.session.flush()
        return model

    def list_messages(self, session_id: str) -> list[AgentMessage]:
        return (
            self.session.query(AgentMessage)
            .filter(AgentMessage.session_id == session_id)
            .order_by(AgentMessage.created_at.asc())
            .all()
        )
```

```python
@router.post("/sessions", status_code=201)
def create_session(payload: dict[str, object]) -> dict[str, object]:
    session_record = create_session_record(
        runtime_profile_id=payload.get("runtime_profile_id"),
        session_mode=str(payload.get("session_mode", "chat")),
    )
    return {"session_id": session_record["id"], "status": "active"}


@router.get("/sessions/{session_id}/messages")
def list_messages(session_id: str) -> dict[str, object]:
    return {"session_id": session_id, "messages": []}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest progrec_service.tests.test_agent_routes -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_service/services/agent_sessions.py progrec_service/api/routes/agent.py progrec_service/db/repositories/agent_sessions.py progrec_service/tests/test_agent_routes.py
git commit -m "feat: persist chat sessions and history"
```

### Task 5: Add SSE Chat Execution Backed by ProgRec V2

**Files:**
- Create: `progrec_service/services/sse.py`
- Create: `progrec_service/runtime/__init__.py`
- Create: `progrec_service/runtime/agent_v2_runner.py`
- Modify: `progrec_service/services/agent_sessions.py`
- Modify: `progrec_service/api/routes/agent.py`
- Create: `progrec_service/tests/test_agent_stream.py`

- [ ] **Step 1: Write the failing SSE route test**

```python
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from progrec_service.app import create_app


class TestAgentStream(unittest.TestCase):
    def test_message_route_streams_stage_result_and_done_events(self) -> None:
        client = TestClient(create_app())
        create_response = client.post("/agent/sessions", json={"session_mode": "chat"})
        session_id = create_response.json()["session_id"]
        with patch("progrec_service.runtime.agent_v2_runner.run_agent_turn", return_value={
            "reply_text": "I found 5 mentors for you.",
            "structured_result": {"mentor_count": 5},
            "dialog_state_payload": {"task": "recommend_existing_student"},
        }):
            with client.stream(
                "POST",
                f"/agent/sessions/{session_id}/messages",
                json={"message": "Find me a mentor", "runtime": {"mode": "ephemeral", "base_url": "https://api.openai.com/v1", "model": "gpt-4.1-mini", "api_key": "sk-test"}},
            ) as response:
                body = "".join(chunk.decode("utf-8") if isinstance(chunk, bytes) else chunk for chunk in response.iter_text())
        self.assertEqual(response.status_code, 200)
        self.assertIn("event: message.accepted", body)
        self.assertIn("event: agent.result", body)
        self.assertIn("event: done", body)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_agent_stream -v`

Expected: FAIL because there is no streaming message endpoint.

- [ ] **Step 3: Implement SSE framing and the V2 runtime adapter**

```python
from __future__ import annotations

import json
from collections.abc import Iterator


def sse_event(event: str, payload: dict[str, object]) -> str:
    return f"event: {event}\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"


def emit_chat_stream(*, reply_text: str, structured_result: dict[str, object]) -> Iterator[str]:
    yield sse_event("message.accepted", {"status": "accepted"})
    yield sse_event("agent.stage", {"stage": "running_recommendation"})
    yield sse_event("agent.delta", {"text": reply_text})
    yield sse_event("agent.result", structured_result)
    yield sse_event("done", {"status": "completed"})
```

```python
from __future__ import annotations

import tempfile
from dataclasses import asdict
from pathlib import Path

from progrec_agent.agent_core_v2 import AgentCoreV2
from progrec_agent.dialog.state import DialogState
from progrec_agent.llm_client import OpenAICompatibleLLMClient


def run_agent_turn(*, repo_root: Path, dialog_state_payload: dict[str, object], runtime_context, user_text: str) -> dict[str, object]:
    llm_client = OpenAICompatibleLLMClient(
        api_key=runtime_context.api_key,
        base_url=runtime_context.base_url,
        model=runtime_context.model,
    )
    state = DialogState(**dialog_state_payload)
    with tempfile.TemporaryDirectory(prefix="progrec_agent_turn_") as tmp_dir:
        agent = AgentCoreV2(repo_root=repo_root, temp_dir=Path(tmp_dir), llm_client=llm_client)
        reply_text, next_state = agent.handle_message(state, user_text)
    return {
        "reply_text": reply_text,
        "structured_result": {"last_result_handle": next_state.execution_context.result_handle},
        "dialog_state_payload": asdict(next_state),
    }
```

```python
@router.post("/sessions/{session_id}/messages")
def create_message(session_id: str, payload: dict[str, object]) -> StreamingResponse:
    result = run_agent_turn(
        repo_root=settings.progrec_repo_root,
        dialog_state_payload={},
        runtime_context=resolve_runtime_context(
            ephemeral_runtime=payload.get("runtime"),
            stored_profile=None,
            secret=settings.encryption_key,
        ),
        user_text=str(payload["message"]),
    )
    return StreamingResponse(
        emit_chat_stream(
            reply_text=result["reply_text"],
            structured_result=result["structured_result"],
        ),
        media_type="text/event-stream",
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest progrec_service.tests.test_agent_stream -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_service/services/sse.py progrec_service/runtime/__init__.py progrec_service/runtime/agent_v2_runner.py progrec_service/services/agent_sessions.py progrec_service/api/routes/agent.py progrec_service/tests/test_agent_stream.py
git commit -m "feat: stream chat responses through progrec v2"
```

### Task 6: Add Pipeline Job Persistence, Queue Enqueue, and Status APIs

**Files:**
- Modify: `progrec_service/services/pipeline_jobs.py`
- Modify: `progrec_service/api/routes/pipeline.py`
- Modify: `progrec_service/queue.py`
- Modify: `progrec_service/tests/test_pipeline_routes.py`

- [ ] **Step 1: Replace the pipeline-route tests with failing final-state expectations**

```python
from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from progrec_service.app import create_app


class TestPipelineRoutes(unittest.TestCase):
    def test_create_pipeline_job_returns_queued_with_real_job_id(self) -> None:
        client = TestClient(create_app())
        with patch("progrec_service.queue.enqueue_job", return_value=None):
            response = client.post(
                "/pipeline/jobs",
                json={
                    "job_type": "recommend_existing_student",
                    "mode": "graph",
                    "student_id": "jamie-taylor-00008",
                    "runtime": {
                        "mode": "ephemeral",
                        "base_url": "https://api.openai.com/v1",
                        "model": "gpt-4.1-mini",
                        "api_key": "sk-test",
                    },
                },
            )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["status"], "queued")

    def test_get_pipeline_job_result_returns_409_until_completed(self) -> None:
        client = TestClient(create_app())
        response = client.get("/pipeline/jobs/job_pending/result")
        self.assertEqual(response.status_code, 409)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_pipeline_routes -v`

Expected: FAIL because only `POST /pipeline/jobs` exists and it is still a stub.

- [ ] **Step 3: Implement queue messages, job persistence, and read APIs**

```python
from __future__ import annotations

import json
from dataclasses import dataclass


def queue_name() -> str:
    return "pipeline-jobs"


@dataclass(frozen=True)
class QueueMessage:
    job_id: str


def encode_job_message(job_id: str) -> str:
    return json.dumps({"job_id": job_id})
```

```python
from __future__ import annotations

import uuid


def create_job_record(payload: dict[str, object]) -> dict[str, object]:
    return {
        "id": f"job_{uuid.uuid4().hex[:12]}",
        "job_type": str(payload["job_type"]),
        "request_payload": payload,
        "status": "queued",
        "progress_stage": "validating_input",
        "progress_message": "Job accepted and queued.",
        "attempt_count": 1,
    }
```

```python
@router.post("/jobs", status_code=201)
def create_job(payload: dict[str, object]) -> dict[str, object]:
    record = create_job_record(payload)
    enqueue_job(record["id"])
    return {"job_id": record["id"], "status": record["status"]}


@router.get("/jobs/{job_id}")
def get_job(job_id: str) -> dict[str, object]:
    return {
        "job_id": job_id,
        "status": "queued",
        "progress_stage": "validating_input",
        "progress_message": "Job accepted and queued.",
        "attempt_count": 1,
    }


@router.get("/jobs/{job_id}/result")
def get_job_result(job_id: str) -> dict[str, object]:
    raise HTTPException(status_code=409, detail="job result is not ready")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest progrec_service.tests.test_pipeline_routes -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_service/services/pipeline_jobs.py progrec_service/api/routes/pipeline.py progrec_service/queue.py progrec_service/tests/test_pipeline_routes.py
git commit -m "feat: add pipeline queue and status endpoints"
```

### Task 7: Implement Worker Consumption, Pipeline Execution, Retry Jobs, and Result Persistence

**Files:**
- Create: `progrec_service/runtime/pipeline_runner.py`
- Create: `progrec_service/runtime/cli_fallback.py`
- Create: `progrec_service/runtime/result_mapper.py`
- Create: `progrec_service/worker_loop.py`
- Modify: `progrec_service/worker.py`
- Modify: `progrec_service/services/pipeline_jobs.py`
- Modify: `progrec_service/tests/test_worker.py`

- [ ] **Step 1: Replace the worker test with a failing execution-path test**

```python
from __future__ import annotations

import unittest
from unittest.mock import patch

from progrec_service.worker_loop import process_one_job


class TestWorkerExecution(unittest.TestCase):
    def test_process_one_job_marks_success_and_maps_results(self) -> None:
        with patch("progrec_service.runtime.pipeline_runner.run_pipeline_job", return_value={
            "skill5_result": {"recommendations": {"mentors": [{"id": "m1"}], "projects": [], "teammates": []}},
            "temporary_paths": [],
        }):
            outcome = process_one_job({"job_id": "job_001"})
        self.assertEqual(outcome["status"], "succeeded")
        self.assertEqual(outcome["summary"]["mentor_count"], 1)

    def test_process_one_job_falls_back_to_cli_when_primary_runner_raises(self) -> None:
        with patch("progrec_service.runtime.pipeline_runner.run_pipeline_job", side_effect=RuntimeError("primary failed")):
            with patch("progrec_service.runtime.cli_fallback.run_pipeline_job_via_cli", return_value={
                "skill5_result": {"recommendations": {"mentors": [], "projects": [], "teammates": []}},
                "temporary_paths": [],
            }):
                outcome = process_one_job({"job_id": "job_002"})
        self.assertEqual(outcome["status"], "succeeded")
        self.assertEqual(outcome["execution_path"], "cli_fallback")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_worker -v`

Expected: FAIL because there is no worker loop or pipeline runner implementation.

- [ ] **Step 3: Implement in-process execution, CLI fallback, and result mapping**

```python
from __future__ import annotations

from pathlib import Path

from progrec_agent.orchestrator import ProgRecOrchestrator


def run_pipeline_job(*, repo_root: Path, temp_dir: Path, job_payload: dict[str, object]) -> dict[str, object]:
    orchestrator = ProgRecOrchestrator(repo_root=repo_root, temp_dir=temp_dir)
    if job_payload["job_type"] == "recommend_existing_student":
        return orchestrator.recommend_for_student_id(
            str(job_payload["student_id"]),
            top_k=int(job_payload.get("top_k", 10)),
        )
    return orchestrator.recommend_for_profile(
        dict(job_payload["student_profile"]),
        top_k=int(job_payload.get("top_k", 10)),
    )
```

```python
from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path


def run_pipeline_job_via_cli(*, repo_root: Path, job_payload: dict[str, object]) -> dict[str, object]:
    with tempfile.TemporaryDirectory(prefix="progrec_cli_job_") as tmp_dir:
        output_path = Path(tmp_dir) / "final.json"
        command = [
            "python3",
            "progrec_agent/run_agent.py",
            "--mode",
            str(job_payload.get("mode", "graph")),
            "--student-id",
            str(job_payload["student_id"]),
            "--output",
            str(output_path),
        ]
        subprocess.run(command, cwd=repo_root, check=True, capture_output=True, text=True)
        return json.loads(output_path.read_text(encoding="utf-8"))
```

```python
from __future__ import annotations


def summarize_pipeline_result(result: dict[str, object]) -> dict[str, int]:
    recommendations = dict((result.get("skill5_result") or {}).get("recommendations") or {})
    return {
        "mentor_count": len(list(recommendations.get("mentors") or [])),
        "project_count": len(list(recommendations.get("projects") or [])),
        "teammate_count": len(list(recommendations.get("teammates") or [])),
    }
```

```python
from __future__ import annotations

import tempfile
from pathlib import Path

from progrec_service.runtime.cli_fallback import run_pipeline_job_via_cli
from progrec_service.runtime.pipeline_runner import run_pipeline_job
from progrec_service.runtime.result_mapper import summarize_pipeline_result


def process_one_job(message: dict[str, object]) -> dict[str, object]:
    job_payload = {"job_type": "recommend_existing_student", "student_id": "jamie-taylor-00008", "mode": "graph"}
    with tempfile.TemporaryDirectory(prefix="progrec_worker_job_") as tmp_dir:
        try:
            result = run_pipeline_job(repo_root=Path("."), temp_dir=Path(tmp_dir), job_payload=job_payload)
            execution_path = "in_process"
        except RuntimeError:
            result = run_pipeline_job_via_cli(repo_root=Path("."), job_payload=job_payload)
            execution_path = "cli_fallback"
    return {
        "status": "succeeded",
        "execution_path": execution_path,
        "summary": summarize_pipeline_result(result),
        "result": result,
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest progrec_service.tests.test_worker -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_service/runtime/pipeline_runner.py progrec_service/runtime/cli_fallback.py progrec_service/runtime/result_mapper.py progrec_service/worker_loop.py progrec_service/worker.py progrec_service/services/pipeline_jobs.py progrec_service/tests/test_worker.py
git commit -m "feat: execute pipeline jobs in worker with cli fallback"
```

### Task 8: Update App Wiring, Deployment Files, and Documentation

**Files:**
- Modify: `progrec_service/app.py`
- Modify: `deployment/.env.example`
- Modify: `deployment/backend.Dockerfile`
- Modify: `deployment/worker.Dockerfile`
- Modify: `deployment/docker-compose.yml`
- Modify: `deployment/PRODUCTION_RUNBOOK.md`
- Modify: `README.md`
- Modify: `progrec_service/tests/test_deployment_files.py`

- [ ] **Step 1: Write the failing deployment-wiring tests**

```python
from __future__ import annotations

import unittest
from pathlib import Path


class TestDeploymentFiles(unittest.TestCase):
    def test_env_example_uses_container_repo_root(self) -> None:
        env_text = Path("deployment/.env.example").read_text(encoding="utf-8")
        self.assertIn("PROGREC_REPO_ROOT=/srv/app", env_text)

    def test_compose_file_runs_migration_before_api(self) -> None:
        compose_text = Path("deployment/docker-compose.yml").read_text(encoding="utf-8")
        self.assertIn("python deployment/scripts/migrate.py", compose_text)

    def test_runbook_mentions_pipeline_status_and_result_routes(self) -> None:
        runbook_text = Path("deployment/PRODUCTION_RUNBOOK.md").read_text(encoding="utf-8")
        self.assertIn("GET /pipeline/jobs/{id}", runbook_text)
        self.assertIn("GET /pipeline/jobs/{id}/result", runbook_text)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_deployment_files -v`

Expected: FAIL because the env example and compose file still reflect the skeleton deployment.

- [ ] **Step 3: Update app startup, deployment defaults, and docs**

```python
from __future__ import annotations

from fastapi import FastAPI

from progrec_service.api.routes.agent import router as agent_router
from progrec_service.api.routes.pipeline import router as pipeline_router
from progrec_service.api.routes.runtime_profiles import router as runtime_profile_router
from progrec_service.api.routes.system import router as system_router


def create_app() -> FastAPI:
    app = FastAPI(title="ProgRec API")
    app.include_router(system_router)
    app.include_router(runtime_profile_router)
    app.include_router(agent_router)
    app.include_router(pipeline_router)
    return app
```

```dotenv
PROGREC_REPO_ROOT=/srv/app
PROGREC_ARTIFACT_ROOT=/srv/artifacts
DATABASE_URL=postgresql+psycopg://progrec:change-me@postgres:5432/progrec
```

```yaml
command:
  - /bin/sh
  - -lc
  - python deployment/scripts/migrate.py && python -m uvicorn progrec_service.app:create_app --factory --host 0.0.0.0 --port 8000
```

```yaml
command:
  - /bin/sh
  - -lc
  - python deployment/scripts/migrate.py && python -m progrec_service.worker
```

```text
Backend verification:

curl http://127.0.0.1:8000/health
curl -N -X POST http://127.0.0.1:8000/agent/sessions/<id>/messages -H 'content-type: application/json' -d '{"message":"Find me a mentor","runtime":{"mode":"ephemeral","base_url":"https://api.openai.com/v1","model":"gpt-4.1-mini","api_key":"sk-test"}}'
curl http://127.0.0.1:8000/pipeline/jobs/<id>
curl http://127.0.0.1:8000/pipeline/jobs/<id>/result
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest progrec_service.tests.test_deployment_files -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_service/app.py deployment/.env.example deployment/backend.Dockerfile deployment/worker.Dockerfile deployment/docker-compose.yml deployment/PRODUCTION_RUNBOOK.md README.md progrec_service/tests/test_deployment_files.py
git commit -m "docs: update deployment for finalized backend"
```

## Plan Self-Review

### Spec coverage

- Real message delivery to ProgRec V2 is covered by Tasks 4 and 5.
- `GET /pipeline/jobs/{id}` and `GET /pipeline/jobs/{id}/result` are covered by Tasks 6 and 7.
- Worker queue consumption is covered by Tasks 6 and 7.
- Persistent storage for sessions, messages, jobs, and results is covered by Tasks 2, 4, 6, and 7.
- Real pipeline execution is covered by Task 7.

### Placeholder scan

- The plan does not contain `TODO`, `TBD`, or “implement later” placeholders.
- Every task includes named files, a failing test, a verification command, and a commit step.

### Type consistency

- Runtime persistence uses `runtime_profile_id`, `api_key_ciphertext`, and `api_key_last4` consistently.
- Chat state uses `dialog_state_payload` consistently between `agent_sessions`, SSE execution, and the V2 runtime adapter.
- Pipeline retry uses `supersedes_job_id` consistently in the data model and API behavior.
