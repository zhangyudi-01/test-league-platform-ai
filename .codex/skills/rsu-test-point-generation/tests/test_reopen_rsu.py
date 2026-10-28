from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import common  # noqa: E402
import reopen_rsu  # noqa: E402


def state_with(statuses: list[tuple[str, str]]) -> dict:
    state = {
        "schema_version": 4,
        "scheduler_schema": "rsu-test-point-generation/state-v2",
        "updated_at": "2026-01-01T00:00:00+00:00",
        "finalization": {
            "status": "prepared",
            "input_sha256": "final-input",
            "input_document_sha256": "final-document",
        },
        "case_readiness": {
            "status": "validated",
            "result": "ready",
            "output_sha256": "readiness-output",
        },
        "rsus": [
            {
                "rsu_id": rsu_id,
                "generation_status": status,
                "input_sha256": f"input-{rsu_id}",
                "current_input_sha256": f"input-{rsu_id}",
                "output_sha256": f"output-{rsu_id}",
                "candidate_count": index,
                "validated_at": "2026-01-01T00:00:00+00:00",
                "blockers": [],
                "batch_id": f"BATCH-{index:03d}",
            }
            for index, (rsu_id, status) in enumerate(statuses, start=1)
        ],
    }
    state["batches"] = [
        {
            "batch_id": f"BATCH-{index:03d}",
            "rsu_ids": [rsu_id],
            "status": "validated" if status == "validated" else "pending",
            "active_rsu_ids": [rsu_id],
            "input_file": f"batches/BATCH-{index:03d}-input.md",
            "input_sha256": f"batch-input-{index}",
            "prepared_at": "2026-01-01T00:00:00+00:00",
            "validated_at": "2026-01-01T00:00:00+00:00" if status == "validated" else None,
            "last_error": None,
        }
        for index, (rsu_id, status) in enumerate(statuses, start=1)
    ]
    return state


class ReopenRsuTests(unittest.TestCase):
    def test_reopens_only_target_and_preserves_later_validated_rsus(self) -> None:
        original = state_with(
            [
                ("RSU-001", "validated"),
                ("RSU-002", "validated"),
                ("RSU-003", "validated"),
            ]
        )
        untouched = copy.deepcopy(original)

        updated = reopen_rsu.reopen_validated_rsu(
            original,
            "RSU-002",
            "finalization found a compound candidate",
            "2026-09-03T13:30:00+00:00",
        )

        self.assertEqual(original, untouched)
        self.assertEqual(updated["rsus"][0], original["rsus"][0])
        self.assertEqual(updated["rsus"][1]["generation_status"], "stale")
        self.assertIsNone(updated["rsus"][1]["output_sha256"])
        self.assertIsNone(updated["rsus"][1]["candidate_count"])
        self.assertIsNone(updated["rsus"][1]["validated_at"])
        self.assertEqual(updated["rsus"][2], original["rsus"][2])
        self.assertEqual(updated["batches"][1]["status"], "pending")
        self.assertEqual(updated["batches"][1]["active_rsu_ids"], [])
        self.assertEqual(updated["batches"][0], original["batches"][0])
        self.assertEqual(updated["batches"][2], original["batches"][2])

    def test_invalidates_finalization_and_readiness_and_records_audit(self) -> None:
        original = state_with([("RSU-001", "validated")])

        updated = reopen_rsu.reopen_validated_rsu(
            original,
            "RSU-001",
            "  split   independent intents  ",
            "2026-09-03T13:30:00+00:00",
        )

        self.assertEqual(updated["finalization"], reopen_rsu.not_ready_finalization())
        self.assertEqual(updated["case_readiness"], reopen_rsu.not_ready_case_readiness())
        self.assertEqual(updated["updated_at"], "2026-09-03T13:30:00+00:00")
        audit = updated["reopen_history"][0]
        self.assertEqual(audit["rsu_id"], "RSU-001")
        self.assertEqual(audit["reason"], "split independent intents")
        self.assertEqual(audit["previous_rsu_state"], original["rsus"][0])
        self.assertEqual(audit["previous_finalization"], original["finalization"])
        self.assertEqual(audit["previous_case_readiness"], original["case_readiness"])

    def test_allows_reopen_when_an_earlier_rsu_is_not_validated(self) -> None:
        state = state_with(
            [("RSU-001", "stale"), ("RSU-002", "validated")]
        )

        updated = reopen_rsu.reopen_validated_rsu(
            state,
            "RSU-002",
            "reason",
            "2026-09-03T13:30:00+00:00",
        )

        self.assertEqual(updated["rsus"][0]["generation_status"], "stale")
        self.assertEqual(updated["rsus"][1]["generation_status"], "stale")

    def test_rejects_missing_or_nonvalidated_target(self) -> None:
        state = state_with([("RSU-001", "prepared")])

        with self.assertRaisesRegex(common.WorkflowError, "only be reopened from validated"):
            reopen_rsu.reopen_validated_rsu(
                state,
                "RSU-001",
                "reason",
                "2026-09-03T13:30:00+00:00",
            )
        with self.assertRaisesRegex(common.WorkflowError, "does not exist"):
            reopen_rsu.reopen_validated_rsu(
                state,
                "RSU-999",
                "reason",
                "2026-09-03T13:30:00+00:00",
            )

    def test_rejects_active_runner_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp)
            (output_dir / ".generation-runner.lock").write_text("pid=1", encoding="utf-8")

            with self.assertRaisesRegex(common.WorkflowError, "runner lock exists"):
                reopen_rsu.ensure_runner_not_active(output_dir)


if __name__ == "__main__":
    unittest.main()
