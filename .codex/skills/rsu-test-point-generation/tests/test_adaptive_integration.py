from __future__ import annotations

import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from adaptive_validation import (  # noqa: E402
    BASELINE_SCHEMA,
    FORK_SCHEMA,
    merge_dispositions,
    validate_baseline_manifest,
    validate_fork_manifest,
)
class AdaptiveIntegrationContractTests(unittest.TestCase):
    def test_baseline_only_and_zero_candidate_are_publishable_dispositions(self) -> None:
        payload = {
            "schema": BASELINE_SCHEMA,
            "input_sha256": "e" * 64,
            "rsus": [
                {"rsu_id": "RSU-001", "status": "generated", "candidate_ids": ["C-1"]},
                {"rsu_id": "RSU-002", "status": "zero-test-points", "candidate_ids": [], "reason": "行为已由 C-1 覆盖"},
            ],
        }
        result = validate_baseline_manifest(payload, ["RSU-001", "RSU-002"], "e" * 64)
        self.assertEqual(result["RSU-002"]["status"], "zero-test-points")

    def test_needs_fork_is_bounded_and_mergeable(self) -> None:
        base = {
            "RSU-001": {"rsu_id": "RSU-001", "status": "needs-fork", "candidate_ids": [], "reason": "跨状态语义冲突"},
            "RSU-002": {"rsu_id": "RSU-002", "status": "generated", "candidate_ids": ["C-2"]},
        }
        fork = {"rsu_id": "RSU-001", "status": "generated", "candidate_ids": ["C-1"], "reason": "已补充状态边界"}
        validate_fork_manifest({"schema": FORK_SCHEMA, "input_sha256": "f" * 64, **fork}, "RSU-001", "f" * 64)
        merged = merge_dispositions(base, {"RSU-001": fork}, ["RSU-001"])
        self.assertEqual(merged["RSU-001"]["status"], "generated")

    def test_conflict_and_scope_fail_closed(self) -> None:
        base = {"RSU-001": {"status": "generated", "candidate_ids": ["C-1"]}}
        with self.assertRaises(Exception):
            merge_dispositions(base, {"RSU-001": {"status": "generated", "candidate_ids": ["C-2"]}}, ["RSU-001"])
        with self.assertRaises(Exception):
            merge_dispositions(base, {"RSU-003": {"status": "generated", "candidate_ids": []}}, ["RSU-001"])

if __name__ == "__main__":
    unittest.main()
