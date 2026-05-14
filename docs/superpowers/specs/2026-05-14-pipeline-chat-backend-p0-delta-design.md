# Pipeline And Chat Backend P0 Delta Design

Date: 2026-05-14
Status: Approved in chat
Owner: Codex

## Goal

Add the remaining P0 backend contracts required by the updated pipeline and chat frontend without replacing the existing `progrec_service` backend.

## Scope

This delta extends the backend finalization work with frontend-facing contracts:

- pipeline job list API
- richer pipeline job detail API
- stable pipeline result package sections
- pipeline stage progression visibility
- chat session list API
- persisted and streamed skill usage visibility
- consistent retry and runtime profile metadata in session and job responses

Deployment parity is documented, but live deployment actions remain outside this code change.

## API Design

### Pipeline List

`GET /pipeline/jobs` returns:

- `jobs[]`
- each item has `job_id`, `status`, `progress_stage`, `progress_message`, `created_at`, `updated_at`, `last_event_at`, `attempt_count`, `is_retryable`, `request_summary`, and `runtime_profile_id`

Jobs are ordered newest first. `created_at` maps to `queued_at`; `updated_at` is the latest worker event timestamp when present, otherwise the newest known job timestamp.

### Pipeline Detail

`GET /pipeline/jobs/{job_id}` returns the same card fields plus:

- `started_at`
- `finished_at`
- `error_code`
- `error_message`
- `supersedes_job_id`

`is_retryable` is true for failed or explicit retryable jobs.

### Pipeline Result

`GET /pipeline/jobs/{job_id}/result` keeps the existing top-level `job_id`, `summary`, and raw artifacts, but normalizes frontend sections under `result`:

- `result.mentors`
- `result.projects`
- `result.teammates`

Each section has:

- `items`
- `count`
- `summary`

Raw runtime payload stays available under `raw_result` so backend evolution does not block debugging.

### Pipeline Stages

The finite stage identifiers are:

- `validating_input`
- `preparing_runtime`
- `running_skill3`
- `running_skill4`
- `running_skill5`
- `writing_artifacts`
- `completed`

The worker records stage events and updates the job progress before and after runtime execution. The current orchestrator runs Skills 3 to 5 as one call, so the worker emits bounded stage transitions around that call rather than trying to stream internal callbacks that do not exist yet.

### Chat Session List

`GET /agent/sessions` returns:

- `sessions[]`
- each item has `session_id`, `status`, `created_at`, `updated_at`, `runtime_profile_id`, `label`, `summary`, and `latest_message_preview`

Labels are generated from the latest user message when available, otherwise the session mode.

### Chat Skill Usage

Assistant turns expose `skill_usage` in both SSE and persisted assistant message payloads.

The current implementation derives usage from the structured agent result. Recommendation turns include the five stable ProgRec skill identifiers, with Skills 3 to 5 marked as runtime execution steps and Skills 1 to 2 marked as artifact/context providers. Non-recommendation turns can return an empty list.

SSE events remain stable:

- `message.accepted`
- `agent.stage`
- `agent.delta`
- `agent.skill`
- `agent.result`
- `done`
- `agent.error` on failures

## Testing

Use TDD against service-level and route-level behavior:

- pipeline list and detail contract tests
- normalized pipeline result test
- failed job retryability test
- chat session list contract test
- chat SSE skill usage and persisted payload test
- worker stage progression test

Run:

```bash
python3 -m unittest progrec_service.tests.test_pipeline_routes progrec_service.tests.test_agent_routes progrec_service.tests.test_agent_stream progrec_service.tests.test_worker -v
```
