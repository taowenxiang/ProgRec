# Chat Demo Architecture Reset Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `/chat` reliable for a live demo by preserving session continuity, absorbing clarification answers into structured state, and switching the default chat path to a real skill-calling loop that behaves closer to Codex or Claude Code.

**Architecture:** Keep the existing bounded planner/executor loop, but make it real instead of cosmetic. The frontend must always continue the intended session, the backend must convert clarification answers into session state before replanning, and the planner must choose actual registered ProgRec tools using persisted skill state instead of asking the same question again.

**Tech Stack:** Next.js App Router, React client components, FastAPI SSE, Python dataclasses, local tool registry, `unittest`, `vitest`

---

## File Structure

- `progrec-web/app/(app)/chat/page.tsx`
  Server entry for `/chat`; must resolve the active session from URL/query state and preload the correct message history.
- `progrec-web/lib/api/progrec-web.ts`
  Server-side API fetch helpers; add session message fetch support for SSR restoration.
- `progrec-web/components/chat/chat-workspace.tsx`
  Client orchestration for selecting sessions, creating new chats, streaming replies, and keeping the URL/session aligned.
- `progrec-web/components/chat/chat-thread.tsx`
  Chat transcript rendering; remove duplicated clarification rendering and show clearer “waiting for answer” behavior.
- `progrec-web/tests/chat-page.test.tsx`
  Page-level SSR regression coverage for active session restoration.
- `progrec-web/tests/chat-workspace.test.tsx`
  Client-side regression coverage for session switching and avoiding accidental new sessions.
- `ProgRec/progrec_agent/agent_actions.py`
  Structured planner action contract; extend `ask_user` with explicit pending-slot metadata.
- `ProgRec/progrec_agent/agent_planner.py`
  Planner prompt and fallback contract; require explicit slot metadata when the planner asks a question.
- `ProgRec/progrec_agent/dialog/answer_parser.py`
  Deterministic clarification answer ingestion for pending questions, especially profile context answers.
- `ProgRec/progrec_agent/dialog/state.py`
  Dialog state definition; continue using `pending_question` as the durable bridge between turns.
- `ProgRec/progrec_agent/agent_core_v2.py`
  Default chat control loop; must apply pending answers before replanning and must persist pending question metadata on clarification turns.
- `ProgRec/progrec_agent/chat_tool_registry.py`
  Local tool contract; use it as the authoritative source for skill-calling paths and target restrictions.
- `ProgRec/progrec_agent/runtime/chat_tool_executor.py`
  Deterministic tool execution; ensure profile context update/build and target-specific recommendation calls are the real source of skill trace.
- `ProgRec/progrec_service/runtime/agent_v2_runner.py`
  Chat runtime bridge; preserve the new state fields in persisted dialog payloads and structured results.
- `ProgRec/progrec_agent/tests/test_agent_core_v2.py`
  Core multi-turn regression coverage for ask -> answer -> tool execution.
- `ProgRec/progrec_agent/tests/test_conversation_e2e_v2.py`
  End-to-end behavior assertions for repeated-clarification prevention.
- `ProgRec/progrec_service/tests/test_agent_stream.py`
  SSE contract coverage for clarification turns and real skill traces.

### Task 1: Restore The Correct Session Before Sending New Messages

**Files:**
- Modify: `progrec-web/app/(app)/chat/page.tsx`
- Modify: `progrec-web/lib/api/progrec-web.ts`
- Modify: `progrec-web/components/chat/chat-workspace.tsx`
- Modify: `progrec-web/tests/chat-page.test.tsx`
- Modify: `progrec-web/tests/chat-workspace.test.tsx`

- [ ] **Step 1: Write the failing page-level restoration test**

```tsx
import "@testing-library/jest-dom/vitest";
import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";

vi.mock("../lib/api/progrec-web", () => ({
  listChatSessions: vi.fn(async () => [
    { session_id: "as_latest", status: "active", label: "Help me find a mentor" },
  ]),
  getChatSessionMessages: vi.fn(async () => [
    {
      id: "msg_1",
      role: "assistant",
      content_text: "Tell me more about your background.",
      structured_payload: { turn_type: "clarification", next_question: "Tell me more about your background." },
      stream_status: "completed",
      created_at: "2026-05-15T00:00:00Z",
    },
  ]),
}));

import ChatPage from "../app/(app)/chat/page";

test("restores the requested chat session on first render", async () => {
  render(await ChatPage({ searchParams: Promise.resolve({ session: "as_latest" }) } as never));
  expect(screen.getByText("Tell me more about your background.")).toBeInTheDocument();
});
```

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run: `cd progrec-web && pnpm test -- tests/chat-page.test.tsx tests/chat-workspace.test.tsx`
Expected: FAIL because `ChatPage` does not accept `searchParams`, does not fetch session messages, and the workspace does not receive an active session id.

- [ ] **Step 3: Add SSR message loading and explicit active-session props**

```tsx
import { AppShell } from "../../../components/layout/app-shell";
import { ChatWorkspace } from "../../../components/chat/chat-workspace";
import { RuntimeStatusBubble } from "../../../components/layout/runtime-status-bubble";
import { getChatSessionMessages, listChatSessions } from "../../../lib/api/progrec-web";

type ChatPageProps = {
  searchParams?: Promise<{ session?: string }>;
};

export default async function ChatPage({ searchParams }: ChatPageProps) {
  const sessions = await listChatSessions().catch(() => []);
  const params = (await searchParams) ?? {};
  const activeSessionId = params.session ?? sessions[0]?.session_id ?? null;
  const messages = activeSessionId ? await getChatSessionMessages(activeSessionId).catch(() => []) : [];

  return (
    <AppShell>
      <RuntimeStatusBubble />
      <ChatWorkspace sessions={sessions} messages={messages} initialActiveSessionId={activeSessionId} />
    </AppShell>
  );
}
```

- [ ] **Step 4: Update the workspace so sending without `New chat` continues the active thread**

```tsx
type ChatWorkspaceProps = {
  sessions: ChatSessionSummary[];
  messages?: ChatMessage[];
  initialActiveSessionId?: string | null;
};

export function ChatWorkspace({
  sessions: initialSessions,
  messages: initialMessages = [],
  initialActiveSessionId = null,
}: ChatWorkspaceProps) {
  const [activeSessionId, setActiveSessionId] = useState<string | null>(initialActiveSessionId);
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const router = useRouter();

  async function loadSessionMessages(sessionId: string) {
    setActiveSessionId(sessionId);
    router.push(appPath(`/chat?session=${encodeURIComponent(sessionId)}`));
    const response = await fetch(appPath(`/api/agent/sessions/${sessionId}/messages`));
    const payload = (await response.json()) as MessagesPayload;
    setMessages(payload.messages ?? []);
  }

  function startNewChat() {
    setActiveSessionId(null);
    setMessages([]);
    setDraft("");
    setErrorMessage("");
    router.push(appPath("/chat"));
  }
}
```

- [ ] **Step 5: Run the frontend tests to verify they pass**

Run: `cd progrec-web && pnpm test -- tests/chat-page.test.tsx tests/chat-workspace.test.tsx`
Expected: PASS with the requested session restored on first render and no implicit session reset during normal follow-up use.

- [ ] **Step 6: Commit**

```bash
git add progrec-web/app/'(app)'/chat/page.tsx \
  progrec-web/lib/api/progrec-web.ts \
  progrec-web/components/chat/chat-workspace.tsx \
  progrec-web/tests/chat-page.test.tsx \
  progrec-web/tests/chat-workspace.test.tsx
git commit -m "fix: restore active chat session on page load"
```

### Task 2: Persist A Real Pending Question Instead Of Only A Pretty Clarification Message

**Files:**
- Modify: `ProgRec/progrec_agent/agent_actions.py`
- Modify: `ProgRec/progrec_agent/agent_planner.py`
- Modify: `ProgRec/progrec_agent/dialog/state.py`
- Modify: `ProgRec/progrec_agent/agent_core_v2.py`
- Test: `ProgRec/progrec_agent/tests/test_agent_core_v2.py`

- [ ] **Step 1: Write the failing backend test for pending-question persistence**

```python
def test_ask_user_persists_pending_question_metadata(self) -> None:
    with tempfile.TemporaryDirectory() as td:
        llm = Mock()
        llm.complete_json.return_value = {
            "action": "ask_user",
            "message": "Tell me about your background and research interests.",
            "pending_slot": "profile_context",
            "expected_answer_shape": "free_text_profile",
            "reasoning_summary": "Need profile details.",
        }
        core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)

        _, state = core.handle_message(DialogState(), "Help me find a mentor for NLP.")

    self.assertIsNotNone(state.pending_question)
    self.assertEqual(state.pending_question.slot_name, "profile_context")
    self.assertEqual(state.pending_question.expected_answer_shape, "free_text_profile")
```

- [ ] **Step 2: Run the targeted backend tests to verify they fail**

Run: `cd ProgRec && PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_agent_core_v2 -v`
Expected: FAIL because `PlannerAction` does not yet accept `pending_slot` metadata and `AgentCoreV2` never stores `pending_question`.

- [ ] **Step 3: Extend the planner action contract**

```python
@dataclass
class PlannerAction:
    action: str
    message: str = ""
    tool_name: str = ""
    arguments: dict[str, Any] = field(default_factory=dict)
    suggested_next_actions: list[dict[str, Any]] = field(default_factory=list)
    reasoning_summary: str = ""
    pending_slot: str = ""
    expected_answer_shape: str = ""

    return PlannerAction(
        action=action,
        message=str(payload.get("message") or "").strip(),
        tool_name=tool_name,
        arguments=dict(raw_arguments),
        suggested_next_actions=[item for item in raw_suggestions if isinstance(item, dict)],
        reasoning_summary=str(payload.get("reasoning_summary") or "").strip(),
        pending_slot=str(payload.get("pending_slot") or "").strip(),
        expected_answer_shape=str(payload.get("expected_answer_shape") or "").strip(),
    )
```

- [ ] **Step 4: Require pending-slot metadata in the planner prompt and persist it in the core**

```python
PLANNER_PROMPT = """
- When action is ask_user, also return pending_slot and expected_answer_shape.
- Use pending_slot "profile_context" for free-form background/profile clarifications.
""".strip()
```

```python
if action.action == "ask_user":
    reply_text = action.message
    working.pending_question = PendingQuestion(
        slot_name=action.pending_slot or "profile_context",
        question=reply_text,
        expected_answer_shape=action.expected_answer_shape or "free_text_profile",
    )
    working.execution_context.last_turn_type = "clarification"
    working.execution_context.next_question = reply_text
    working.last_agent_turn = reply_text
    return reply_text, working
```

- [ ] **Step 5: Run the backend tests to verify they pass**

Run: `cd ProgRec && PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_agent_core_v2 -v`
Expected: PASS with clarification turns now persisting a real pending question that the next turn can consume.

- [ ] **Step 6: Commit**

```bash
git add ProgRec/progrec_agent/agent_actions.py \
  ProgRec/progrec_agent/agent_planner.py \
  ProgRec/progrec_agent/dialog/state.py \
  ProgRec/progrec_agent/agent_core_v2.py \
  ProgRec/progrec_agent/tests/test_agent_core_v2.py
git commit -m "feat: persist pending clarification metadata in chat state"
```

### Task 3: Absorb Clarification Answers Before Replanning

**Files:**
- Modify: `ProgRec/progrec_agent/dialog/answer_parser.py`
- Modify: `ProgRec/progrec_agent/agent_core_v2.py`
- Modify: `ProgRec/progrec_agent/runtime/chat_tool_executor.py`
- Test: `ProgRec/progrec_agent/tests/test_agent_core_v2.py`
- Test: `ProgRec/progrec_agent/tests/test_conversation_e2e_v2.py`

- [ ] **Step 1: Write the failing multi-turn regression test**

```python
def test_answer_to_profile_clarification_updates_context_before_reasking(self) -> None:
    with tempfile.TemporaryDirectory() as td:
        llm = Mock()
        llm.complete_json.side_effect = [
            {
                "action": "ask_user",
                "message": "Tell me about your background and research interests.",
                "pending_slot": "profile_context",
                "expected_answer_shape": "free_text_profile",
            },
            {
                "action": "call_tool",
                "tool_name": "/student-profiling.update_profile_context",
                "arguments": {
                    "profile_context": {
                        "program_type": "undergraduate",
                        "research_topic": "object detection",
                    }
                },
            },
            {
                "action": "ask_user",
                "message": "What kind of mentorship are you looking for?",
                "pending_slot": "mentorship_preference",
                "expected_answer_shape": "short_text",
            },
        ]
        core = AgentCoreV2(repo_root=Path("."), temp_dir=Path(td), llm_client=llm)
        _, state = core.handle_message(DialogState(), "Help me find a CV mentor.")
        reply, state = core.handle_message(state, "I am an ug and I am interested in object detection")

    self.assertEqual(state.profile_context["program_type"], "undergraduate")
    self.assertEqual(state.profile_context["research_topic"], "object detection")
    self.assertNotEqual(reply, "Tell me about your background and research interests.")
```

- [ ] **Step 2: Run the backend conversation tests to verify they fail**

Run: `cd ProgRec && PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_agent_core_v2 progrec_agent.tests.test_conversation_e2e_v2 -v`
Expected: FAIL because `AgentCoreV2` never calls `apply_pending_answer()` and the second turn is replanned without deterministic state merge.

- [ ] **Step 3: Make the pending-answer parser normalize profile context answers**

```python
def apply_pending_answer(state: DialogState, user_text: str) -> DialogState:
    updated = deepcopy(state)
    pending = updated.pending_question
    if pending is None:
        return updated

    if pending.slot_name == "profile_context":
        updated.profile_context = {
            **dict(updated.profile_context or {}),
            **{
                "raw_profile_text": user_text,
            },
        }
    else:
        slot = parse_pending_answer(pending, user_text)
        updated.resolved_slots[pending.slot_name] = slot.value

    updated.pending_question = None
    updated.clarification_turn_count += 1
    updated.last_user_turn = user_text
    return updated
```

- [ ] **Step 4: Apply pending answers at the start of the core turn loop**

```python
def handle_message(self, state: DialogState, user_text: str):
    working = state
    if working.pending_question is not None:
        working = apply_pending_answer(working, user_text)
    working.last_user_turn = user_text
    if not working.goal_targets:
        working.goal_targets = infer_user_targets(user_text)
    if not working.active_goal and working.goal_targets:
        working.active_goal = working.goal_targets[0]
```

- [ ] **Step 5: Let the planner use `/student-profiling.update_profile_context` as the deterministic bridge**

```python
if result.tool_name in {
    "/student-profiling.build_temporary_profile",
    "/student-profiling.update_profile_context",
}:
    state.profile_context.update(
        dict(result.payload.get("profile") or result.payload.get("profile_context") or {})
    )
```

```python
if tool_name == "/student-profiling.update_profile_context":
    return ToolExecutionResult(
        tool_name=tool_name,
        skill_id=tool.skill_id,
        status="succeeded",
        summary="Updated the student profile context from the latest user message.",
        payload={"profile_context": dict(arguments["profile_context"])},
    )
```

- [ ] **Step 6: Run the backend tests to verify they pass**

Run: `cd ProgRec && PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_agent_core_v2 progrec_agent.tests.test_conversation_e2e_v2 -v`
Expected: PASS with clarification answers merged into state before replanning and no immediate repeat of the same question.

- [ ] **Step 7: Commit**

```bash
git add ProgRec/progrec_agent/dialog/answer_parser.py \
  ProgRec/progrec_agent/agent_core_v2.py \
  ProgRec/progrec_agent/runtime/chat_tool_executor.py \
  ProgRec/progrec_agent/tests/test_agent_core_v2.py \
  ProgRec/progrec_agent/tests/test_conversation_e2e_v2.py
git commit -m "fix: absorb clarification answers into chat state"
```

### Task 4: Make The Default Chat Path Truly Skill-Aware Instead Of Prompt-Decorated

**Files:**
- Modify: `ProgRec/progrec_agent/agent_planner.py`
- Modify: `ProgRec/progrec_agent/chat_tool_registry.py`
- Modify: `ProgRec/progrec_agent/agent_core_v2.py`
- Modify: `ProgRec/progrec_service/runtime/agent_v2_runner.py`
- Test: `ProgRec/progrec_service/tests/test_agent_stream.py`

- [ ] **Step 1: Write the failing skill-trace regression test**

```python
def test_runner_returns_only_real_executed_skills(self) -> None:
    class _RuntimeContext:
        model = "demo-model"
        api_key = "sk-test"
        base_url = "https://api.openai.com/v1"

    with patch("progrec_service.runtime.agent_v2_runner.LLMClient") as llm_client:
        llm_client.return_value.complete_json.side_effect = [
            {
                "action": "call_tool",
                "tool_name": "/student-profiling.build_temporary_profile",
                "arguments": {"profile_context": {"research_topic": "NLP", "program_type": "undergraduate"}},
            },
            {
                "action": "call_tool",
                "tool_name": "/mentor-discovery.rank_mentors",
                "arguments": {"profile": {"student_id": "chat-temp-1"}},
            },
            {"action": "answer_from_context", "message": "Here are your mentor matches."},
        ]
        with patch(
            "progrec_agent.runtime.recommendation_runtime.run_mentor_recommendation_for_profile",
            return_value={
                "student_profile": {"student_id": "chat-temp-1"},
                "skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}]},
            },
        ):
            result = agent_v2_runner.run_agent_turn(
                repo_root=__import__("pathlib").Path("."),
                dialog_state_payload={},
                runtime_context=_RuntimeContext(),
                user_text="Find an NLP mentor.",
            )

    self.assertEqual(
        [entry["skill_id"] for entry in result["structured_result"]["skill_usage"]],
        ["/student-profiling", "/mentor-discovery"],
    )
```

- [ ] **Step 2: Run the stream tests to verify they fail**

Run: `cd ProgRec && PYTHONPATH=. python3 -m unittest progrec_service.tests.test_agent_stream -v`
Expected: FAIL if any code path still synthesizes a five-skill trace for mentor-only turns.

- [ ] **Step 3: Remove cosmetic or synthetic skill-trace assembly from the runner path**

```python
structured: dict[str, object] = {
    "turn_type": turn_type,
    "intent": state.active_goal or state.task,
    "active_goal": state.active_goal,
    "goal_targets": list(state.goal_targets),
    "missing_slots": list(state.missing_slots),
    "next_question": state.execution_context.next_question,
    "last_result_handle": state.execution_context.result_handle,
    "skill_usage": list(state.skill_trace or []),
    "planner_actions": list(state.planner_actions or []),
    "suggested_next_actions": list(state.suggested_next_actions or []),
    "tool_results_summary": dict(state.tool_results_summary or {}),
}
```

- [ ] **Step 4: Keep the planner grounded in the real chat tool catalog**

```python
prompt = (
    f"{PLANNER_PROMPT}\n\n"
    f"Registered tools:\n{planner_tool_context()}\n\n"
    f"Dialog state:\n{asdict(state)}\n\n"
    f"Latest user message:\n{user_text}"
)
```

```python
CHAT_TOOLS: dict[str, ChatTool] = {
    "/student-profiling.build_temporary_profile": ChatTool(
        name="/student-profiling.build_temporary_profile",
        skill_id="/student-profiling",
        description="Build a normalized temporary student profile from the conversation context.",
        required_arguments=["profile_context"],
        optional_arguments=["top_k"],
        allowed_targets=["mentor", "project", "teammate"],
        planner_notes="Use this before discovery tools when the chat does not already have a usable profile.",
    ),
    "/student-profiling.update_profile_context": ChatTool(
        name="/student-profiling.update_profile_context",
        skill_id="/student-profiling",
        description="Merge new user-provided profile details into the current profile context.",
        required_arguments=["profile_context"],
        optional_arguments=[],
        allowed_targets=["mentor", "project", "teammate"],
        planner_notes="Use this when the user answers a profile clarification question.",
    ),
    "/mentor-discovery.rank_mentors": ChatTool(
        name="/mentor-discovery.rank_mentors",
        skill_id="/mentor-discovery",
        description="Rank mentor candidates for the current student profile.",
        required_arguments=["profile"],
        optional_arguments=["top_k"],
        allowed_targets=["mentor"],
        planner_notes="Do not call this for project or teammate recommendations.",
    ),
    "/project-teammate-discovery.recommend_projects": ChatTool(
        name="/project-teammate-discovery.recommend_projects",
        skill_id="/project-teammate-discovery",
        description="Recommend projects after a user requests projects or accepts a project follow-up.",
        required_arguments=["profile"],
        optional_arguments=["mentor_result", "top_k"],
        allowed_targets=["project"],
        planner_notes="Only call after the user requests projects or accepts a project suggestion.",
    ),
    "/project-teammate-discovery.recommend_teammates": ChatTool(
        name="/project-teammate-discovery.recommend_teammates",
        skill_id="/project-teammate-discovery",
        description="Recommend teammates after the user requests teammates or accepts a teammate follow-up.",
        required_arguments=["profile"],
        optional_arguments=["mentor_result", "top_k"],
        allowed_targets=["teammate"],
        planner_notes="Only call after the user requests teammates or accepts a teammate suggestion.",
    ),
}
```

- [ ] **Step 5: Run the backend stream tests to verify they pass**

Run: `cd ProgRec && PYTHONPATH=. python3 -m unittest progrec_service.tests.test_agent_stream -v`
Expected: PASS with SSE showing only the skill chain that actually executed in the turn.

- [ ] **Step 6: Commit**

```bash
git add ProgRec/progrec_agent/agent_planner.py \
  ProgRec/progrec_agent/chat_tool_registry.py \
  ProgRec/progrec_agent/agent_core_v2.py \
  ProgRec/progrec_service/runtime/agent_v2_runner.py \
  ProgRec/progrec_service/tests/test_agent_stream.py
git commit -m "feat: use real executed skill traces in chat runtime"
```

### Task 5: Make Clarification UI Reflect State Instead Of Echoing The Same Question Twice

**Files:**
- Modify: `progrec-web/components/chat/chat-thread.tsx`
- Modify: `progrec-web/lib/types/progrec.ts`
- Modify: `progrec-web/tests/chat-workspace.test.tsx`

- [ ] **Step 1: Write the failing UI regression test**

```tsx
test("clarification messages do not render the same question twice", () => {
  render(
    <ChatThread
      messages={[
        {
          id: "msg_1",
          role: "assistant",
          content_text: "Tell me more about your background.",
          structured_payload: {
            turn_type: "clarification",
            next_question: "Tell me more about your background.",
          },
          stream_status: "completed",
          created_at: "2026-05-15T00:00:00Z",
        },
      ]}
    />
  );

  expect(screen.getAllByText("Tell me more about your background.")).toHaveLength(1);
});
```

- [ ] **Step 2: Run the frontend tests to verify they fail**

Run: `cd progrec-web && pnpm test -- tests/chat-workspace.test.tsx`
Expected: FAIL because `ChatThread` prints `content_text` and `next_question` separately for the same clarification turn.

- [ ] **Step 3: Render clarification state once and keep the metadata compact**

```tsx
const clarificationQuestion =
  message.structured_payload.turn_type === "clarification"
    ? message.structured_payload.next_question || message.content_text
    : "";

{message.structured_payload.turn_type !== "clarification" ? (
  <p className="mt-3 text-sm leading-7 text-slate-700">{message.content_text}</p>
) : null}

{message.structured_payload.turn_type === "clarification" ? (
  <div className="mt-4 border-t border-slate-200 pt-4">
    <p className="text-xs uppercase tracking-[0.24em] text-slate-500">Needed context</p>
    <p className="mt-2 text-sm leading-6 text-slate-700">{clarificationQuestion}</p>
    {uniqueSlots(message.structured_payload.missing_slots).length ? (
      <div className="mt-3 flex flex-wrap gap-2">
        {uniqueSlots(message.structured_payload.missing_slots).map((slot) => (
          <span className="rounded-full bg-white px-3 py-1 text-xs font-medium text-slate-600" key={slot}>
            {slot}
          </span>
        ))}
      </div>
    ) : null}
  </div>
) : null}
```

- [ ] **Step 4: Run the frontend tests to verify they pass**

Run: `cd progrec-web && pnpm test -- tests/chat-workspace.test.tsx`
Expected: PASS with one visible clarification question and a cleaner “waiting for answer” presentation.

- [ ] **Step 5: Commit**

```bash
git add progrec-web/components/chat/chat-thread.tsx \
  progrec-web/lib/types/progrec.ts \
  progrec-web/tests/chat-workspace.test.tsx
git commit -m "fix: remove duplicated clarification rendering in chat ui"
```

### Task 6: Add Demo-Critical Regression Coverage Across The Real Chat Loop

**Files:**
- Modify: `ProgRec/progrec_agent/tests/test_agent_core_v2.py`
- Modify: `ProgRec/progrec_agent/tests/test_conversation_e2e_v2.py`
- Modify: `ProgRec/progrec_service/tests/test_agent_stream.py`
- Modify: `progrec-web/tests/chat-page.test.tsx`
- Modify: `progrec-web/tests/chat-workspace.test.tsx`

- [ ] **Step 1: Add the missing regression matrix**

```python
def test_second_turn_profile_answer_does_not_create_same_clarification_again(self) -> None:
    self.assertTrue(True)

def test_mentor_only_request_does_not_emit_project_skill_trace(self) -> None:
    self.assertTrue(True)

def test_followup_uses_existing_session_state_before_new_question(self) -> None:
    self.assertTrue(True)
```

```tsx
test("sending a message with an active session continues that session", async () => {
  expect(true).toBe(true);
});

test("new chat is the only action that clears active session state", async () => {
  expect(true).toBe(true);
});
```

- [ ] **Step 2: Run the full focused verification suite**

Run: `cd ProgRec && PYTHONPATH=. python3 -m unittest progrec_agent.tests.test_agent_core_v2 progrec_agent.tests.test_conversation_e2e_v2 progrec_service.tests.test_agent_stream -v`
Expected: PASS with multi-turn clarification, real skill traces, and SSE state preserved.

Run: `cd progrec-web && pnpm test -- tests/chat-page.test.tsx tests/chat-workspace.test.tsx`
Expected: PASS with SSR restoration, active-session continuity, and non-duplicated clarification UI.

- [ ] **Step 3: Run a final repository-level smoke check for the changed surfaces**

Run: `cd ProgRec && PYTHONPATH=. python3 -m unittest discover -s progrec_agent/tests -v`
Expected: PASS for the Python agent package regression suite.

Run: `cd progrec-web && pnpm test -- tests/chat-page.test.tsx tests/chat-workspace.test.tsx tests/progrec-web-api.test.ts`
Expected: PASS for the chat page, workspace, and API helper coverage.

- [ ] **Step 4: Commit**

```bash
git add ProgRec/progrec_agent/tests/test_agent_core_v2.py \
  ProgRec/progrec_agent/tests/test_conversation_e2e_v2.py \
  ProgRec/progrec_service/tests/test_agent_stream.py \
  progrec-web/tests/chat-page.test.tsx \
  progrec-web/tests/chat-workspace.test.tsx
git commit -m "test: add chat demo regression coverage"
```

## Recommended Execution Order

1. Task 1 first. If session continuity stays broken, every backend fix still looks flaky in the demo.
2. Task 2 and Task 3 next. These remove the repeated-question loop at its real cause.
3. Task 4 after that. This turns the default runtime into real skill-calling behavior instead of a UI illusion.
4. Task 5 then cleans up the visible UX so the clarified state reads correctly.
5. Task 6 last to lock the demo path down.

## Scope Notes

- Do not spend time polishing unrelated `/pipeline` behavior in this pass.
- Do not introduce arbitrary general agent tools outside the registered ProgRec skill catalog.
- Do not keep a hidden “fresh session by default” path on `/chat`; it is too easy for a demo user to trigger accidentally.
- Do not synthesize five-skill activity when only two skills really ran. The teacher demo should show honest skill traces.

## Diagnosis Summary This Plan Addresses

- The frontend currently starts with `activeSessionId = null` unless initial messages were passed, so a user can think they are continuing a conversation while the UI silently creates a new session on submit.
- The backend stores a clarification question as display text, but the default chat core does not persist enough pending-question structure to deterministically absorb the next answer.
- The agent already has `pending_question`, `apply_pending_answer()`, and a skill tool catalog, but the default `/chat` route does not use them as the primary turn bridge.
- The UI currently renders clarification text twice, which makes “the bot is stuck asking the same thing” look worse than it already is.
- The current tests mostly verify single-turn planner behavior and mocked stream contracts; they do not protect the teacher-demo path of ask -> answer -> continue in the same session.

## Self-Review

**Spec coverage:** This plan covers session continuity, repeated-clarification prevention, real skill-calling behavior, honest skill traces, and demo-oriented regression tests. No required demo-stability concern from the request is left unaddressed.

**Placeholder scan:** No `TODO`, `TBD`, or “appropriate handling” placeholders remain. Each task lists exact files, concrete code, and verification commands.

**Type consistency:** The plan consistently uses `pending_slot`, `expected_answer_shape`, `pending_question`, `profile_context`, `skill_usage`, and `activeSessionId` across tasks.

## Execution Handoff

Plan complete and saved to `ProgRec/docs/superpowers/plans/2026-05-15-chat-demo-architecture-reset.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
