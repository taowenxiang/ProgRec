from __future__ import annotations

import unittest

from progrec_agent.dialog.state import ExecutionContext
from progrec_agent.runtime.result_state import (
    active_result_payload,
    hydrate_result_arguments,
    latest_result_payload,
    record_shown_entity,
    resolve_result_payload,
    result_registry_from_execution_context,
    result_handle_from_payload,
    result_state_snapshot,
    store_result_payload,
)


class TestResultState(unittest.TestCase):
    def test_store_result_payload_updates_execution_context_indexes(self) -> None:
        context = ExecutionContext()
        payload = {
            "result_ref": "rr_mentor_001",
            "result_type": "mentor_result",
            "payload": {"skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}]}},
        }

        result_ref = store_result_payload(context, payload)

        self.assertEqual(result_ref, "rr_mentor_001")
        self.assertEqual(context.result_handle, "rr_mentor_001")
        self.assertEqual(context.latest_result_refs["mentor_result"], "rr_mentor_001")

    def test_hydrate_result_arguments_replaces_string_refs(self) -> None:
        context = ExecutionContext(
            result_ref_payloads={
                "rr_mentor_001": {"result_ref": "rr_mentor_001", "payload": {"skill3_result": {}}},
            }
        )

        hydrated = hydrate_result_arguments(
            context,
            {"mentor_result_ref": "rr_mentor_001", "rank": 1},
        )

        self.assertIsInstance(hydrated["mentor_result_ref"], dict)
        self.assertEqual(hydrated["mentor_result_ref"]["result_ref"], "rr_mentor_001")

    def test_hydrate_result_arguments_fills_latest_ref_when_argument_is_omitted(self) -> None:
        context = ExecutionContext(
            latest_result_refs={"mentor_result": "rr_mentor_001"},
            result_ref_payloads={
                "rr_mentor_001": {
                    "result_ref": "rr_mentor_001",
                    "result_type": "mentor_result",
                    "payload": {"skill3_result": {}},
                }
            },
        )

        hydrated = hydrate_result_arguments(context, {"rank": 1})

        self.assertEqual(hydrated["mentor_result_ref"]["result_ref"], "rr_mentor_001")

    def test_record_shown_entity_tracks_last_seen_ids(self) -> None:
        context = ExecutionContext()

        record_shown_entity(context, "mentor", "m1")

        self.assertEqual(context.last_shown_entities["mentor"], "m1")

    def test_result_state_snapshot_is_serialization_safe(self) -> None:
        context = ExecutionContext(
            result_handle="rr_mentor_001",
            latest_result_refs={"mentor_result": "rr_mentor_001"},
            active_result_ref="rr_mentor_001",
            last_shown_entities={"mentor": "m1"},
        )

        snapshot = result_state_snapshot(context)

        self.assertEqual(snapshot["last_result_handle"], "rr_mentor_001")
        self.assertEqual(snapshot["latest_result_refs"]["mentor_result"], "rr_mentor_001")
        self.assertEqual(snapshot["last_shown_entities"]["mentor"], "m1")

    def test_latest_and_active_payload_helpers_resolve_stored_payloads(self) -> None:
        context = ExecutionContext(
            active_result_ref="rr_mentor_001",
            latest_result_refs={"mentor_result": "rr_mentor_001"},
            result_ref_payloads={
                "rr_mentor_001": {
                    "result_ref": "rr_mentor_001",
                    "result_type": "mentor_result",
                    "payload": {"skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}]}},
                }
            },
        )

        latest = latest_result_payload(context, "mentor_result")
        active = active_result_payload(context)

        self.assertEqual(latest["result_ref"], "rr_mentor_001")
        self.assertEqual(active["result_ref"], "rr_mentor_001")

    def test_result_registry_can_be_rebuilt_from_execution_context(self) -> None:
        context = ExecutionContext(
            result_ref_payloads={
                "rr_mentor_001": {
                    "result_ref": "rr_mentor_001",
                    "result_type": "mentor_result",
                    "owner_skill": "/mentor-discovery",
                    "input_refs": ["sp_001"],
                    "summary": {"count": 2},
                    "followups": ["/mentor-discovery.get_mentor_by_rank"],
                    "payload": {"skill3_result": {"mentor_candidates": [{"mentor_id": "m1"}]}},
                }
            }
        )

        registry = result_registry_from_execution_context(context)

        self.assertEqual(registry.latest_ref("mentor_result"), "rr_mentor_001")
        self.assertEqual(registry.get("rr_mentor_001").summary["count"], 2)

    def test_result_handle_from_payload_falls_back_to_dialog_state(self) -> None:
        handle = result_handle_from_payload(
            structured_payload={},
            dialog_state_payload={"execution_context": {"result_handle": "rr_project_001"}},
        )

        self.assertEqual(handle, "rr_project_001")

    def test_resolve_result_payload_raises_for_unknown_ref(self) -> None:
        context = ExecutionContext()

        with self.assertRaises(KeyError):
            resolve_result_payload(context, "missing")


if __name__ == "__main__":
    unittest.main()
