# Pipeline Chat Backend P0 Delta Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fill the remaining pipeline and chat API contracts needed by the current frontend update.

**Architecture:** Extend the existing FastAPI routes with small service/repository helpers. Keep PostgreSQL/SQLAlchemy models as the system of record, normalize frontend response shapes at the service layer, and expose skill usage through the existing SSE and persisted assistant message payload path.

**Tech Stack:** FastAPI, SQLAlchemy 2.x, stdlib unittest, existing `progrec_service` repositories and runtime adapters.

---

### Task 1: Pipeline List, Detail, And Result Contracts

**Files:**
- Modify: `progrec_service/db/repositories/pipeline_jobs.py`
- Modify: `progrec_service/services/pipeline_jobs.py`
- Modify: `progrec_service/runtime/result_mapper.py`
- Modify: `progrec_service/api/routes/pipeline.py`
- Modify: `progrec_service/tests/test_pipeline_routes.py`

- [ ] Write failing route tests for `GET /pipeline/jobs`, richer detail fields, retry metadata, and normalized result sections.
- [ ] Run `python3 -m unittest progrec_service.tests.test_pipeline_routes -v` and confirm the new tests fail for missing behavior.
- [ ] Add repository listing and latest-event helpers.
- [ ] Add service serializers for job cards, details, request summaries, retryability, and normalized result sections.
- [ ] Wire `GET /pipeline/jobs` and expand `GET /pipeline/jobs/{job_id}` and result responses.
- [ ] Re-run `python3 -m unittest progrec_service.tests.test_pipeline_routes -v`.

### Task 2: Chat Session List And Skill Usage Contract

**Files:**
- Modify: `progrec_service/db/repositories/agent_sessions.py`
- Modify: `progrec_service/services/agent_sessions.py`
- Modify: `progrec_service/runtime/agent_v2_runner.py`
- Modify: `progrec_service/services/sse.py`
- Modify: `progrec_service/api/routes/agent.py`
- Modify: `progrec_service/tests/test_agent_routes.py`
- Modify: `progrec_service/tests/test_agent_stream.py`

- [ ] Write failing tests for `GET /agent/sessions`, `agent.skill` SSE events, and persisted `structured_payload.skill_usage`.
- [ ] Run `python3 -m unittest progrec_service.tests.test_agent_routes progrec_service.tests.test_agent_stream -v` and confirm the new tests fail for missing behavior.
- [ ] Add session listing repository and service serializers.
- [ ] Derive skill usage in the agent runtime adapter and pass it through SSE/result persistence.
- [ ] Wire `GET /agent/sessions`.
- [ ] Re-run the agent route and stream tests.

### Task 3: Worker Stage And Failure Contract

**Files:**
- Modify: `progrec_service/worker_loop.py`
- Modify: `progrec_service/tests/test_worker.py`

- [ ] Write failing tests proving stage events are recorded and runtime failures populate `failed`, `error_code`, and `error_message`.
- [ ] Run `python3 -m unittest progrec_service.tests.test_worker -v` and confirm the new tests fail for missing behavior.
- [ ] Add stage update helper to worker loop.
- [ ] Persist stage changes before runtime execution and before result writing.
- [ ] Persist failed job state when both primary and fallback paths fail.
- [ ] Re-run worker tests.

### Task 4: Final Verification

**Files:**
- No production files unless tests reveal integration issues.

- [ ] Run focused backend contract tests:

```bash
python3 -m unittest progrec_service.tests.test_pipeline_routes progrec_service.tests.test_agent_routes progrec_service.tests.test_agent_stream progrec_service.tests.test_worker -v
```

- [ ] Run full `progrec_service` tests:

```bash
python3 -m unittest discover -s progrec_service/tests -v
```
