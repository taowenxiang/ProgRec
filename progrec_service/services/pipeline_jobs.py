from __future__ import annotations

import uuid


def create_job_id() -> str:
    return f"job_{uuid.uuid4().hex[:12]}"
