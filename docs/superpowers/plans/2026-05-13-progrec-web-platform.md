# ProgRec Web Platform Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `progrec-web` as a public web product on Vercel and add a deployable `progrec-api` service in the current `ProgRec` repository, with PostgreSQL, Redis, worker execution, and Docker Compose deployment on a dedicated Linux host.

**Architecture:** Keep `ProgRec` as the recommendation runtime and add a backend service layer inside this repository for HTTP APIs, background jobs, runtime profile persistence, and artifact indexing. Create a separate sibling repository, `progrec-web`, for the Next.js frontend and Vercel deployment, with `basePath=/progrec` and a light BFF layer that calls `https://progrec-api.wenxiangtao.com`.

**Tech Stack:** FastAPI, Pydantic, PostgreSQL, Redis, Docker Compose, Python 3, stdlib `unittest`, Next.js App Router, TypeScript, Tailwind CSS, shadcn/ui, lucide-react, motion, Zod, React Hook Form, TanStack Query, Drizzle ORM.

---

## File Structure

### New frontend repository

- Create: `/Users/mount/Desktop/Programming/progrec-web`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/(marketing)/page.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/(app)/setup/page.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/(app)/chat/page.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/(app)/pipeline/page.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/(app)/jobs/[id]/page.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/(app)/history/page.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/api/runtime-profiles/test/route.ts`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/api/agent/sessions/route.ts`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/api/pipeline/jobs/route.ts`
- Create: `/Users/mount/Desktop/Programming/progrec-web/components/...`
- Create: `/Users/mount/Desktop/Programming/progrec-web/lib/...`
- Create: `/Users/mount/Desktop/Programming/progrec-web/drizzle/...`
- Create: `/Users/mount/Desktop/Programming/progrec-web/next.config.ts`
- Test: `/Users/mount/Desktop/Programming/progrec-web/tests/...`

### New backend service files in current repository

- Create: `progrec_service/__init__.py`
- Create: `progrec_service/app.py`
- Create: `progrec_service/config.py`
- Create: `progrec_service/api/routes/system.py`
- Create: `progrec_service/api/routes/runtime_profiles.py`
- Create: `progrec_service/api/routes/agent.py`
- Create: `progrec_service/api/routes/pipeline.py`
- Create: `progrec_service/api/routes/artifacts.py`
- Create: `progrec_service/db/models.py`
- Create: `progrec_service/db/session.py`
- Create: `progrec_service/db/repositories/...`
- Create: `progrec_service/services/runtime_profiles.py`
- Create: `progrec_service/services/agent_sessions.py`
- Create: `progrec_service/services/pipeline_jobs.py`
- Create: `progrec_service/services/encryption.py`
- Create: `progrec_service/worker.py`
- Create: `progrec_service/queue.py`
- Create: `progrec_service/tests/...`

### Deployment and infrastructure files in current repository

- Create: `deployment/docker-compose.yml`
- Create: `deployment/Caddyfile`
- Create: `deployment/.env.example`
- Create: `deployment/backend.Dockerfile`
- Create: `deployment/worker.Dockerfile`
- Create: `deployment/scripts/migrate.py`
- Create: `deployment/scripts/bootstrap_linux.sh`
- Create: `deployment/README.md`

### Existing files to modify

- Modify: `README.md`
- Modify: `requirements.txt` or create a dedicated backend service dependency manifest if the repository does not already manage service dependencies cleanly

---

### Task 1: Scaffold `progrec-web` as a Next.js App With `/progrec` Base Path

**Files:**
- Create: `/Users/mount/Desktop/Programming/progrec-web/package.json`
- Create: `/Users/mount/Desktop/Programming/progrec-web/next.config.ts`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/layout.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/(marketing)/page.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/tests/base-path.test.ts`

- [ ] **Step 1: Write the failing frontend base-path test**

```ts
import { describe, expect, it } from "vitest";
import nextConfig from "../next.config";

describe("next base path", () => {
  it("uses /progrec as the public base path", () => {
    expect(nextConfig.basePath).toBe("/progrec");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/mount/Desktop/Programming/progrec-web && pnpm vitest run tests/base-path.test.ts`

Expected: FAIL because the repository and config do not exist yet.

- [ ] **Step 3: Create the minimal frontend scaffold**

```json
{
  "name": "progrec-web",
  "private": true,
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "test": "vitest run"
  },
  "dependencies": {
    "next": "^16.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@types/node": "^24.0.0",
    "@types/react": "^19.0.0",
    "typescript": "^5.9.0",
    "vitest": "^4.0.0"
  }
}
```

```ts
const nextConfig = {
  basePath: "/progrec",
};

export default nextConfig;
```

```tsx
export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
```

```tsx
export default function MarketingPage() {
  return (
    <main>
      <h1>ProgRec</h1>
      <p>Mentor, project, and teammate recommendations powered by your own model configuration.</p>
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/mount/Desktop/Programming/progrec-web && pnpm vitest run tests/base-path.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/mount/Desktop/Programming/progrec-web
git add package.json next.config.ts app/layout.tsx app/\(marketing\)/page.tsx tests/base-path.test.ts
git commit -m "feat: scaffold progrec-web with base path"
```

### Task 2: Add Backend Service Skeleton and Health/System Routes

**Files:**
- Create: `progrec_service/app.py`
- Create: `progrec_service/config.py`
- Create: `progrec_service/api/routes/system.py`
- Test: `progrec_service/tests/test_system_routes.py`

- [ ] **Step 1: Write the failing backend system-route test**

```python
import unittest
from fastapi.testclient import TestClient

from progrec_service.app import create_app


class TestSystemRoutes(unittest.TestCase):
    def test_health_returns_ok(self) -> None:
        client = TestClient(create_app())
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "ok")

    def test_models_recommended_returns_default_model(self) -> None:
        client = TestClient(create_app())
        response = client.get("/models/recommended")
        self.assertEqual(response.status_code, 200)
        self.assertIn("recommended", response.json())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_system_routes -v`

Expected: FAIL because `progrec_service` does not exist yet.

- [ ] **Step 3: Implement the minimal FastAPI skeleton**

```python
from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass
class Settings:
    recommended_model_base_url: str = os.getenv("RECOMMENDED_MODEL_BASE_URL", "https://api.openai.com/v1")
    recommended_model_name: str = os.getenv("RECOMMENDED_MODEL_NAME", "gpt-4.1-mini")


settings = Settings()
```

```python
from __future__ import annotations

from fastapi import APIRouter

from progrec_service.config import settings

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    return {"status": "ok", "service": "progrec-api", "version": "1.0.0"}


@router.get("/models/recommended")
def recommended_model() -> dict[str, object]:
    return {
        "recommended": {
            "label": "Recommended",
            "base_url": settings.recommended_model_base_url,
            "model": settings.recommended_model_name,
        }
    }
```

```python
from __future__ import annotations

from fastapi import FastAPI

from progrec_service.api.routes.system import router as system_router


def create_app() -> FastAPI:
    app = FastAPI(title="ProgRec API")
    app.include_router(system_router)
    return app
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest progrec_service.tests.test_system_routes -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_service/app.py progrec_service/config.py progrec_service/api/routes/system.py progrec_service/tests/test_system_routes.py
git commit -m "feat: add progrec-api system routes"
```

### Task 3: Add PostgreSQL Schema and Runtime Profile Encryption

**Files:**
- Create: `progrec_service/db/models.py`
- Create: `progrec_service/db/session.py`
- Create: `progrec_service/services/encryption.py`
- Create: `progrec_service/services/runtime_profiles.py`
- Create: `progrec_service/api/routes/runtime_profiles.py`
- Test: `progrec_service/tests/test_runtime_profiles.py`

- [ ] **Step 1: Write the failing runtime-profile tests**

```python
import unittest

from progrec_service.services.encryption import decrypt_secret, encrypt_secret


class TestRuntimeProfileEncryption(unittest.TestCase):
    def test_encrypt_and_decrypt_roundtrip(self) -> None:
        token = "sk-test"
        ciphertext = encrypt_secret(token, "0123456789abcdef0123456789abcdef")
        self.assertNotEqual(ciphertext, token)
        plaintext = decrypt_secret(ciphertext, "0123456789abcdef0123456789abcdef")
        self.assertEqual(plaintext, token)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_runtime_profiles -v`

Expected: FAIL because the encryption service and runtime-profile files do not exist yet.

- [ ] **Step 3: Implement encryption and runtime profile route skeleton**

```python
from __future__ import annotations

import base64
import hashlib


def _keystream(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def encrypt_secret(value: str, secret: str) -> str:
    raw = value.encode("utf-8")
    key = _keystream(secret)
    payload = bytes(raw[i] ^ key[i % len(key)] for i in range(len(raw)))
    return base64.urlsafe_b64encode(payload).decode("utf-8")


def decrypt_secret(value: str, secret: str) -> str:
    payload = base64.urlsafe_b64decode(value.encode("utf-8"))
    key = _keystream(secret)
    raw = bytes(payload[i] ^ key[i % len(key)] for i in range(len(payload)))
    return raw.decode("utf-8")
```

```python
from __future__ import annotations

from pydantic import BaseModel, SecretStr


class RuntimeProfileCreate(BaseModel):
    label: str
    base_url: str
    model: str
    api_key: SecretStr


class RuntimeProfileRead(BaseModel):
    id: str
    label: str
    base_url: str
    model: str
    api_key_last4: str
```

```python
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/runtime-profiles", tags=["runtime-profiles"])


@router.post("/test")
def test_profile(payload: dict[str, str]) -> dict[str, object]:
    if not payload.get("api_key"):
        return {"ok": False, "message": "Missing API key"}
    return {"ok": True, "message": "Connection successful"}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m unittest progrec_service.tests.test_runtime_profiles -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_service/db/models.py progrec_service/db/session.py progrec_service/services/encryption.py progrec_service/services/runtime_profiles.py progrec_service/api/routes/runtime_profiles.py progrec_service/tests/test_runtime_profiles.py
git commit -m "feat: add runtime profile encryption and API"
```

### Task 4: Add Agent Session APIs Backed by `ProgRec` V2

**Files:**
- Create: `progrec_service/services/agent_sessions.py`
- Create: `progrec_service/api/routes/agent.py`
- Test: `progrec_service/tests/test_agent_routes.py`

- [ ] **Step 1: Write the failing agent-route tests**

```python
import unittest
from fastapi.testclient import TestClient

from progrec_service.app import create_app


class TestAgentRoutes(unittest.TestCase):
    def test_create_agent_session(self) -> None:
        client = TestClient(create_app())
        response = client.post("/agent/sessions", json={"runtime_profile": {"mode": "ephemeral", "base_url": "https://api.openai.com/v1", "model": "gpt-4.1-mini", "api_key": "sk-test"}})
        self.assertEqual(response.status_code, 200)
        self.assertIn("session_id", response.json())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_agent_routes -v`

Expected: FAIL because `/agent/sessions` does not exist yet.

- [ ] **Step 3: Implement minimal agent-session route and adapter**

```python
from __future__ import annotations

import uuid


def create_session_id() -> str:
    return f"as_{uuid.uuid4().hex[:12]}"
```

```python
from __future__ import annotations

from fastapi import APIRouter

from progrec_service.services.agent_sessions import create_session_id

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/sessions")
def create_session(payload: dict[str, object]) -> dict[str, object]:
    return {"session_id": create_session_id(), "status": "ready"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest progrec_service.tests.test_agent_routes -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_service/services/agent_sessions.py progrec_service/api/routes/agent.py progrec_service/tests/test_agent_routes.py
git commit -m "feat: add agent session API skeleton"
```

### Task 5: Add Async Pipeline Job API and Worker Queue

**Files:**
- Create: `progrec_service/services/pipeline_jobs.py`
- Create: `progrec_service/api/routes/pipeline.py`
- Create: `progrec_service/queue.py`
- Create: `progrec_service/worker.py`
- Test: `progrec_service/tests/test_pipeline_routes.py`

- [ ] **Step 1: Write the failing pipeline tests**

```python
import unittest
from fastapi.testclient import TestClient

from progrec_service.app import create_app


class TestPipelineRoutes(unittest.TestCase):
    def test_create_pipeline_job(self) -> None:
        client = TestClient(create_app())
        payload = {
            "runtime_profile": {
                "mode": "ephemeral",
                "base_url": "https://api.openai.com/v1",
                "model": "gpt-4.1-mini",
                "api_key": "sk-test"
            },
            "job_type": "recommend_existing_student",
            "mode": "graph",
            "student_id": "jamie-taylor-00008",
            "top_k": 10
        }
        response = client.post("/pipeline/jobs", json=payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "queued")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_pipeline_routes -v`

Expected: FAIL because the pipeline route does not exist yet.

- [ ] **Step 3: Implement minimal queue and pipeline route**

```python
from __future__ import annotations

import uuid


def create_job_id() -> str:
    return f"job_{uuid.uuid4().hex[:12]}"
```

```python
from __future__ import annotations

from fastapi import APIRouter

from progrec_service.services.pipeline_jobs import create_job_id

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


@router.post("/jobs")
def create_job(payload: dict[str, object]) -> dict[str, object]:
    return {"job_id": create_job_id(), "status": "queued"}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest progrec_service.tests.test_pipeline_routes -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add progrec_service/services/pipeline_jobs.py progrec_service/api/routes/pipeline.py progrec_service/queue.py progrec_service/worker.py progrec_service/tests/test_pipeline_routes.py
git commit -m "feat: add pipeline job API and worker skeleton"
```

### Task 6: Build Runtime Setup and Product Shell in `progrec-web`

**Files:**
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/(app)/setup/page.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/components/setup/runtime-profile-form.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/components/layout/app-shell.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/tests/setup-page.test.tsx`

- [ ] **Step 1: Write the failing setup-page test**

```tsx
import { render, screen } from "@testing-library/react";
import SetupPage from "../app/(app)/setup/page";

test("renders runtime setup form", () => {
  render(<SetupPage />);
  expect(screen.getByText("Configure your model runtime")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/mount/Desktop/Programming/progrec-web && pnpm vitest run tests/setup-page.test.tsx`

Expected: FAIL because the setup page does not exist yet.

- [ ] **Step 3: Implement the setup page**

```tsx
export default function SetupPage() {
  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-3xl font-semibold">Configure your model runtime</h1>
      <p className="mt-2 text-sm text-muted-foreground">
        Provide your API key, base URL, and model name before using ProgRec.
      </p>
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/mount/Desktop/Programming/progrec-web && pnpm vitest run tests/setup-page.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/mount/Desktop/Programming/progrec-web
git add app/\(app\)/setup/page.tsx components/setup/runtime-profile-form.tsx components/layout/app-shell.tsx tests/setup-page.test.tsx
git commit -m "feat: add runtime setup page"
```

### Task 7: Build Chat, Pipeline, Job, and History Pages Against Stable BFF Routes

**Files:**
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/(app)/chat/page.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/(app)/pipeline/page.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/(app)/jobs/[id]/page.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/(app)/history/page.tsx`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/api/agent/sessions/route.ts`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/api/pipeline/jobs/route.ts`
- Test: `/Users/mount/Desktop/Programming/progrec-web/tests/chat-page.test.tsx`

- [ ] **Step 1: Write the failing chat-page test**

```tsx
import { render, screen } from "@testing-library/react";
import ChatPage from "../app/(app)/chat/page";

test("renders the chat workspace", () => {
  render(<ChatPage />);
  expect(screen.getByText("Interactive Agent")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/mount/Desktop/Programming/progrec-web && pnpm vitest run tests/chat-page.test.tsx`

Expected: FAIL because the chat page does not exist yet.

- [ ] **Step 3: Implement the chat page shell**

```tsx
export default function ChatPage() {
  return (
    <main className="grid min-h-screen grid-cols-[280px_1fr]">
      <aside className="border-r p-6">Session summary</aside>
      <section className="p-6">
        <h1 className="text-2xl font-semibold">Interactive Agent</h1>
      </section>
    </main>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/mount/Desktop/Programming/progrec-web && pnpm vitest run tests/chat-page.test.tsx`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/mount/Desktop/Programming/progrec-web
git add app/\(app\)/chat/page.tsx app/\(app\)/pipeline/page.tsx app/\(app\)/jobs/\[id\]/page.tsx app/\(app\)/history/page.tsx app/api/agent/sessions/route.ts app/api/pipeline/jobs/route.ts tests/chat-page.test.tsx
git commit -m "feat: add chat and pipeline page shells"
```

### Task 8: Add Docker Compose, Reverse Proxy, and Deployment Scripts

**Files:**
- Create: `deployment/docker-compose.yml`
- Create: `deployment/Caddyfile`
- Create: `deployment/.env.example`
- Create: `deployment/backend.Dockerfile`
- Create: `deployment/worker.Dockerfile`
- Create: `deployment/scripts/bootstrap_linux.sh`
- Create: `deployment/README.md`
- Test: `progrec_service/tests/test_deployment_files.py`

- [ ] **Step 1: Write the failing deployment-files test**

```python
import unittest
from pathlib import Path


class TestDeploymentFiles(unittest.TestCase):
    def test_compose_file_exists(self) -> None:
        self.assertTrue(Path("deployment/docker-compose.yml").is_file())
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m unittest progrec_service.tests.test_deployment_files -v`

Expected: FAIL because the deployment directory does not exist yet.

- [ ] **Step 3: Add deployment files**

```yaml
services:
  reverse-proxy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
  postgres:
    image: postgres:17
  redis:
    image: redis:8
  progrec-api:
    build:
      context: ..
      dockerfile: deployment/backend.Dockerfile
  progrec-worker:
    build:
      context: ..
      dockerfile: deployment/worker.Dockerfile
```

```txt
progrec-api.wenxiangtao.com {
  reverse_proxy progrec-api:8000
}
```

```bash
#!/usr/bin/env bash
set -euo pipefail
mkdir -p /opt/progrec/data/postgres
mkdir -p /opt/progrec/data/redis
mkdir -p /opt/progrec/data/artifacts
mkdir -p /opt/progrec/logs
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m unittest progrec_service.tests.test_deployment_files -v`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add deployment/docker-compose.yml deployment/Caddyfile deployment/.env.example deployment/backend.Dockerfile deployment/worker.Dockerfile deployment/scripts/bootstrap_linux.sh deployment/README.md progrec_service/tests/test_deployment_files.py
git commit -m "ops: add compose and deployment scaffolding"
```

### Task 9: Wire Vercel BFF to `progrec-api` and Finalize Domain-Path Behavior

**Files:**
- Modify: `/Users/mount/Desktop/Programming/progrec-web/next.config.ts`
- Create: `/Users/mount/Desktop/Programming/progrec-web/app/api/runtime-profiles/test/route.ts`
- Create: `/Users/mount/Desktop/Programming/progrec-web/lib/config/env.ts`
- Create: `/Users/mount/Desktop/Programming/progrec-web/tests/runtime-profile-bff.test.ts`

- [ ] **Step 1: Write the failing BFF test**

```ts
import { describe, expect, it } from "vitest";
import { appConfig } from "../lib/config/env";

describe("frontend env", () => {
  it("uses /progrec as the public base path", () => {
    expect(appConfig.basePath).toBe("/progrec");
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /Users/mount/Desktop/Programming/progrec-web && pnpm vitest run tests/runtime-profile-bff.test.ts`

Expected: FAIL because the environment helper and route do not exist yet.

- [ ] **Step 3: Add the environment helper and BFF route**

```ts
export const appConfig = {
  basePath: process.env.NEXT_PUBLIC_APP_BASE_PATH || "/progrec",
  appUrl: process.env.NEXT_PUBLIC_APP_URL || "https://demo.wenxiangtao.com/progrec",
  apiBaseUrl: process.env.PROGREC_API_BASE_URL || "https://progrec-api.wenxiangtao.com",
};
```

```ts
import { NextRequest, NextResponse } from "next/server";
import { appConfig } from "../../../../lib/config/env";

export async function POST(request: NextRequest) {
  const payload = await request.json();
  const response = await fetch(`${appConfig.apiBaseUrl}/runtime-profiles/test`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(payload),
  });
  return NextResponse.json(await response.json(), { status: response.status });
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /Users/mount/Desktop/Programming/progrec-web && pnpm vitest run tests/runtime-profile-bff.test.ts`

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd /Users/mount/Desktop/Programming/progrec-web
git add next.config.ts app/api/runtime-profiles/test/route.ts lib/config/env.ts tests/runtime-profile-bff.test.ts
git commit -m "feat: wire Vercel BFF to progrec-api"
```

## Self-Review Coverage

- The frontend repository creation, subpath deployment, and UI library decisions are covered by Tasks 1, 6, 7, and 9.
- The backend API contract, runtime profile handling, agent sessions, pipeline jobs, and artifact access are covered by Tasks 2 through 5.
- PostgreSQL storage and application-layer secret handling are covered by Task 3.
- Linux Docker Compose deployment, reverse proxy setup, and host layout are covered by Task 8.
- The Vercel and domain-routing integration requirements are covered by Tasks 1 and 9.
- The phased build order from the approved spec is preserved: backend contract first, then persistence, then chat and pipeline APIs, then frontend shells, then deployment wiring.

