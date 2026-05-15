# Chat Product Loop Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/chat` reliably handle recommendation-domain requests end to end, from intent recognition through clarification, execution, streaming status, persisted history, and result rendering.

**Architecture:** Add a deterministic domain guard and fallback parser around the LLM NLU so obvious ProgRec requests cannot be misclassified as out-of-scope. Normalize every agent turn into a structured turn contract (`turn_type`, `intent`, `missing_slots`, `next_question`, `skill_usage`, optional recommendations) and teach the web chat to render those states instead of raw text only.

**Tech Stack:** Python dataclasses/unittest/FastAPI SSE for backend agent behavior; Next.js React components/Vitest for frontend chat rendering.

---

### Task 1: Harden V2 Intent Recognition

**Files:**
- Create: `progrec_agent/nlu/domain_guard.py`
- Modify: `progrec_agent/nlu/parser.py`
- Modify: `progrec_agent/agent_core_v2.py`
- Test: `progrec_agent/tests/test_agent_core_v2.py`
- Test: `progrec_agent/tests/test_nlu_parser.py`

- [ ] **Step 1: Write failing tests**

Add tests proving that a mentor/NLP request is treated as a recommendation even when the LLM returns `out_of_scope`, and that local parsing extracts a research topic when the LLM is unavailable or invalid.

- [ ] **Step 2: Verify red**

Run: `cd ProgRec && python3 -m unittest progrec_agent.tests.test_agent_core_v2 progrec_agent.tests.test_nlu_parser -v`

Expected: FAIL on the new fallback tests.

- [ ] **Step 3: Implement domain guard**

Create `progrec_agent/nlu/domain_guard.py` with functions that detect ProgRec-domain keywords, infer `recommendation_request`, extract a topic phrase for mentor/project/team requests, and preserve true unrelated requests as out-of-scope.

- [ ] **Step 4: Wire fallback parser**

Update `parse_user_message()` so malformed LLM output, missing LLM, or low-confidence/out-of-scope output for a domain-looking message returns the deterministic fallback frame.

- [ ] **Step 5: Verify green**

Run: `cd ProgRec && python3 -m unittest progrec_agent.tests.test_agent_core_v2 progrec_agent.tests.test_nlu_parser -v`

Expected: PASS.

### Task 2: Productize Agent Turn Contract

**Files:**
- Modify: `progrec_agent/dialog/state.py`
- Modify: `progrec_agent/agent_core_v2.py`
- Modify: `progrec_agent/response/replies.py`
- Modify: `progrec_service/runtime/agent_v2_runner.py`
- Modify: `progrec_service/services/sse.py`
- Test: `progrec_agent/tests/test_conversation_e2e_v2.py`
- Test: `progrec_service/tests/test_agent_stream.py`

- [ ] **Step 1: Write failing backend contract tests**

Add tests asserting clarification turns expose `turn_type=clarification`, `next_question`, and `missing_slots`; recommendation turns expose `turn_type=recommendation_result`, `skill_usage`, and normalized recommendation sections; refusal turns expose `turn_type=refusal`.

- [ ] **Step 2: Verify red**

Run: `cd ProgRec && python3 -m unittest progrec_agent.tests.test_conversation_e2e_v2 progrec_service.tests.test_agent_stream -v`

Expected: FAIL because the structured payload is currently too sparse and SSE stage is generic.

- [ ] **Step 3: Add structured turn metadata**

Store turn metadata in the dialog state or return value from `AgentCoreV2.handle_message()`, then map it in `agent_v2_runner.run_agent_turn()` into `structured_result`.

- [ ] **Step 4: Emit meaningful SSE events**

Update `emit_chat_stream()` so clarification emits `agent.stage` with `collecting_context`, recommendation emits `running_recommendation`, refusal emits `refusal`, and result payloads remain JSON-decodable.

- [ ] **Step 5: Verify green**

Run: `cd ProgRec && python3 -m unittest progrec_agent.tests.test_conversation_e2e_v2 progrec_service.tests.test_agent_stream -v`

Expected: PASS.

### Task 3: Render Chat As A Product Surface

**Files:**
- Modify: `progrec-web/lib/types/progrec.ts`
- Modify: `progrec-web/components/chat/chat-workspace.tsx`
- Modify: `progrec-web/components/chat/chat-thread.tsx`
- Modify: `progrec-web/components/chat/chat-session-rail.tsx`
- Modify: `progrec-web/components/chat/chat-composer.tsx`
- Test: `progrec-web/tests/chat-workspace.test.tsx`

- [ ] **Step 1: Write failing frontend tests**

Add tests for formatted session times, visible stage/skill progress during streaming, clarification callouts, and recommendation cards rendered from structured chat payloads.

- [ ] **Step 2: Verify red when tooling exists**

Run: `cd progrec-web && pnpm test tests/chat-workspace.test.tsx`

Expected: FAIL on new product rendering expectations. If `pnpm` is unavailable, record that limitation and verify backend tests fully.

- [ ] **Step 3: Extend chat types**

Add `turn_type`, `intent`, `missing_slots`, `next_question`, `stage`, and optional recommendation result section types to `ChatMessage.structured_payload`.

- [ ] **Step 4: Render turn states**

Update `ChatThread` to render clarification, refusal, skill progress, and recommendation result sections. Update `ChatWorkspace` to consume `agent.stage` and `agent.skill` during the stream, not only final `agent.result`.

- [ ] **Step 5: Polish session/composer UX**

Format timestamps for the session rail, add a New chat action that clears `activeSessionId` and local messages, and make composer helper text reflect the current error or context state.

- [ ] **Step 6: Verify green when tooling exists**

Run: `cd progrec-web && pnpm test tests/chat-workspace.test.tsx`

Expected: PASS if `pnpm` is installed.

### Task 4: Full Regression

**Files:**
- Verify only.

- [ ] **Step 1: Run agent suite**

Run: `cd ProgRec && python3 -m unittest discover -s progrec_agent/tests -v`

Expected: PASS.

- [ ] **Step 2: Run service chat tests**

Run: `cd ProgRec && python3 -m unittest progrec_service.tests.test_agent_routes progrec_service.tests.test_agent_stream -v`

Expected: PASS.

- [ ] **Step 3: Run frontend chat tests if available**

Run: `cd progrec-web && pnpm test tests/chat-workspace.test.tsx tests/chat-page.test.tsx`

Expected: PASS if `pnpm` is installed; otherwise report `/bin/bash: pnpm: command not found`.

## Self-Review

- Spec coverage: covers intent fallback, structured agent turns, SSE semantics, chat rendering, session UX, and regression.
- Placeholder scan: no TBD/TODO placeholders remain.
- Type consistency: backend `structured_result` keys match frontend `structured_payload` keys planned for rendering.
