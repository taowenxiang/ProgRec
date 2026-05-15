from __future__ import annotations

from collections.abc import Iterator
import uuid

from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from progrec_service.config import settings
from progrec_service.runtime import agent_v2_runner
from progrec_service.services.agent_sessions import (
    create_session as create_session_entry,
    get_session_dialog_state,
    list_sessions as list_session_entries,
    list_session_messages,
    persist_assistant_turn,
    persist_user_message,
)
from progrec_service.services.runtime_context import resolve_runtime_context
from progrec_service.services.sse import emit_chat_prelude, emit_chat_stream

router = APIRouter(prefix="/agent", tags=["agent"])
SESSION_OWNER_COOKIE = "progrec_session_owner"
SESSION_OWNER_HEADER = "x-progrec-session-owner"


def _resolve_session_owner(
    request: Request,
    response: Response | None = None,
    owner_header: str | None = None,
    *,
    create_if_missing: bool,
) -> str | None:
    owner_token = (owner_header or "").strip() or request.cookies.get(SESSION_OWNER_COOKIE, "").strip()
    if owner_token:
        return owner_token
    if not create_if_missing:
        return None
    owner_token = f"own_{uuid.uuid4().hex[:24]}"
    if response is not None:
        response.set_cookie(
            SESSION_OWNER_COOKIE,
            owner_token,
            httponly=True,
            samesite="lax",
            secure=False,
            path="/",
        )
    return owner_token


def _require_session_owner(request: Request, owner_header: str | None = None) -> str:
    owner_token = _resolve_session_owner(
        request,
        None,
        owner_header,
        create_if_missing=False,
    )
    if owner_token is None:
        raise HTTPException(status_code=403, detail="Session owner token is required.")
    return owner_token


@router.post("/sessions", status_code=201)
def create_session(
    payload: dict[str, object],
    request: Request,
    response: Response,
    x_progrec_session_owner: str | None = Header(default=None, alias=SESSION_OWNER_HEADER),
) -> dict[str, object]:
    owner_token = _resolve_session_owner(
        request,
        response,
        x_progrec_session_owner,
        create_if_missing=True,
    )
    record = create_session_entry(
        runtime_profile_id=payload.get("runtime_profile_id"),
        session_mode=str(payload.get("session_mode", "chat")),
        owner_token=owner_token,
    )
    return {"session_id": record.id, "status": record.status}


@router.get("/sessions")
def list_sessions(
    request: Request,
    response: Response,
    x_progrec_session_owner: str | None = Header(default=None, alias=SESSION_OWNER_HEADER),
) -> dict[str, object]:
    owner_token = _resolve_session_owner(
        request,
        response,
        x_progrec_session_owner,
        create_if_missing=True,
    )
    return {"sessions": list_session_entries(owner_token=owner_token)}


@router.get("/sessions/{session_id}/messages")
def list_messages(
    session_id: str,
    request: Request,
    x_progrec_session_owner: str | None = Header(default=None, alias=SESSION_OWNER_HEADER),
) -> dict[str, object]:
    owner_token = _require_session_owner(request, x_progrec_session_owner)
    try:
        messages = list_session_messages(session_id, owner_token=owner_token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return {"session_id": session_id, "messages": messages}


@router.post("/sessions/{session_id}/messages")
def create_message(
    session_id: str,
    payload: dict[str, object],
    request: Request,
    x_progrec_session_owner: str | None = Header(default=None, alias=SESSION_OWNER_HEADER),
) -> StreamingResponse:
    owner_token = _require_session_owner(request, x_progrec_session_owner)
    try:
        persist_user_message(session_id, str(payload["message"]), owner_token=owner_token)
        dialog_state_payload = get_session_dialog_state(session_id, owner_token=owner_token)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    runtime_context = resolve_runtime_context(
        ephemeral_runtime=payload.get("runtime"),
        runtime_profile_id=payload.get("runtime_profile_id"),
    )

    def event_stream() -> Iterator[str]:
        yield from emit_chat_prelude()
        result = agent_v2_runner.run_agent_turn(
            repo_root=settings.progrec_repo_root,
            dialog_state_payload=dialog_state_payload,
            runtime_context=runtime_context,
            user_text=str(payload["message"]),
        )
        for event in emit_chat_stream(
            reply_text=result["reply_text"],
            structured_result=result["structured_result"],
            include_prelude=False,
        ):
            yield event
        try:
            persist_assistant_turn(
                session_id=session_id,
                content_text=result["reply_text"],
                structured_payload=result["structured_result"],
                dialog_state_payload=result["dialog_state_payload"],
                owner_token=owner_token,
            )
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    return StreamingResponse(event_stream(), media_type="text/event-stream")
