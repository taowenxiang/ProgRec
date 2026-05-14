from __future__ import annotations

import logging
import signal
from threading import Event

from progrec_service.queue import queue_name

logger = logging.getLogger(__name__)
stop_event = Event()


def worker_name() -> str:
    return f"progrec-worker:{queue_name()}"


def _handle_stop_signal(signum: int, _frame: object) -> None:
    logger.info("Received signal %s, stopping worker", signum)
    stop_event.set()


def main(poll_interval_seconds: float = 30.0) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )

    signal.signal(signal.SIGTERM, _handle_stop_signal)
    signal.signal(signal.SIGINT, _handle_stop_signal)

    logger.info(
        "Worker started for queue %s. Queue consumption is not implemented yet; keeping the process alive for deployment stability.",
        queue_name(),
    )

    while not stop_event.wait(timeout=poll_interval_seconds):
        logger.info("Worker heartbeat queue=%s status=idle", queue_name())

    logger.info("Worker stopped")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
