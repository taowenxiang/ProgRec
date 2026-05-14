from __future__ import annotations

import unittest
from unittest.mock import patch

from progrec_service.worker import main, worker_name


class TestWorker(unittest.TestCase):
    def test_worker_name_includes_queue_name(self) -> None:
        self.assertEqual(worker_name(), "progrec-worker:pipeline-jobs")

    def test_main_exits_cleanly_when_stop_event_is_set(self) -> None:
        with patch("progrec_service.worker.stop_event.wait", return_value=True):
            with patch("progrec_service.worker.signal.signal"):
                self.assertEqual(main(poll_interval_seconds=0.01), 0)


if __name__ == "__main__":
    unittest.main()
