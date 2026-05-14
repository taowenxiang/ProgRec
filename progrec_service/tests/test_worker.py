from __future__ import annotations

import unittest
from unittest.mock import patch

from progrec_service.worker import main, worker_name
from progrec_service.worker_loop import process_one_job


class TestWorkerExecution(unittest.TestCase):
    def test_process_one_job_marks_success_and_maps_results(self) -> None:
        with patch(
            "progrec_service.runtime.pipeline_runner.run_pipeline_job",
            return_value={
                "skill5_result": {
                    "recommendations": {"mentors": [{"id": "m1"}], "projects": [], "teammates": []}
                },
                "temporary_paths": [],
            },
        ):
            outcome = process_one_job({"job_id": "job_001"})
        self.assertEqual(outcome["status"], "succeeded")
        self.assertEqual(outcome["summary"]["mentor_count"], 1)

    def test_process_one_job_falls_back_to_cli_when_primary_runner_raises(self) -> None:
        with patch("progrec_service.runtime.pipeline_runner.run_pipeline_job", side_effect=RuntimeError("primary failed")):
            with patch(
                "progrec_service.runtime.cli_fallback.run_pipeline_job_via_cli",
                return_value={
                    "skill5_result": {"recommendations": {"mentors": [], "projects": [], "teammates": []}},
                    "temporary_paths": [],
                },
            ):
                outcome = process_one_job({"job_id": "job_002"})
        self.assertEqual(outcome["status"], "succeeded")
        self.assertEqual(outcome["execution_path"], "cli_fallback")


class TestWorkerMain(unittest.TestCase):
    def test_worker_name_includes_queue_name(self) -> None:
        self.assertEqual(worker_name(), "progrec-worker:pipeline-jobs")

    def test_main_exits_cleanly_when_stop_event_is_set(self) -> None:
        with patch("progrec_service.worker.stop_event.wait", return_value=True):
            with patch("progrec_service.worker.signal.signal"):
                self.assertEqual(main(poll_interval_seconds=0.01), 0)

    def test_main_processes_dequeued_job(self) -> None:
        with patch("progrec_service.worker.dequeue_job_message", return_value={"job_id": "job_001"}):
            with patch("progrec_service.worker.process_one_job", return_value={"status": "succeeded"}) as process_mock:
                with patch("progrec_service.worker.stop_event.wait", side_effect=[False, True]):
                    with patch("progrec_service.worker.signal.signal"):
                        self.assertEqual(main(poll_interval_seconds=0.01), 0)
        process_mock.assert_called_once_with({"job_id": "job_001"})


if __name__ == "__main__":
    unittest.main()
