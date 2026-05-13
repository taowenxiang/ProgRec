from __future__ import annotations

from progrec_service.queue import queue_name


def worker_name() -> str:
    return f"progrec-worker:{queue_name()}"
