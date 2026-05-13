from __future__ import annotations

import uuid


def create_session_id() -> str:
    return f"as_{uuid.uuid4().hex[:12]}"
