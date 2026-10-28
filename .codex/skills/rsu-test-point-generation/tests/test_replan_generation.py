from __future__ import annotations

import json
import sys
import tempfile
import unittest
from contextlib import nullcontext
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import replan_generation as replan  # noqa: E402


class ReplanGenerationTests(unittest.TestCase):
    def test_replan_isolates_only_affected_rsu_and_preserves_validated_results(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module_dir = Path(temp) / "module"
            output_dir = module_dir / "test-points"
            output_dir.mkdir(parents=True)
            plan_file = output_dir / "generation-plan.json"
            plan_file.write_text(
                json.dumps(
                    {
                        "status": "validated",
                        "rsus": [
                            {
                                "rsu_id": "RSU-001",
                                "mode": "simple",
                                "batch_id": "BATCH-001",
                                "context_signature": "ctx",
                                "rationale": "普通规则",
                            },
                            {
                                "rsu_id": "RSU-002",
                                "mode": "simple",
                                "batch_id": "BATCH-001",
                                "context_signature": "ctx",
                                "rationale": "存在复杂时序，需要独立处理",
                            },
                            {
                                "rsu_id": "RSU-003",
                                "mode": "simple",
                                "batch_id": "BATCH-001",
                                "context_signature": "ctx",
                                "rationale": "普通规则",
                            },
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            state = {
                "rsus": [
                    {
                        "rsu_id": "RSU-001",
                        "generation_status": "validated",
                        "batch_id": "BATCH-001",
                    },
                    {
                        "rsu_id": "RSU-002",
                        "generation_status": "replan-required",
                        "batch_id": "BATCH-001",
                        "last_error": "需要独立上下文",
                    },
                    {
                        "rsu_id": "RSU-003",
                        "generation_status": "validated",
                        "batch_id": "BATCH-001",
                    },
                ],
                "planning": {"status": "validated", "output_sha256": "old"},
                "batches": [{"batch_id": "BATCH-001", "status": "replan-required"}],
            }
            layout = SimpleNamespace(module_dir=module_dir)
            model = SimpleNamespace()
            argv = [
                "replan_generation.py",
                str(module_dir),
                "--output-dir",
                str(output_dir),
            ]
            with patch.object(replan, "resolve_module_layout", return_value=layout), patch.object(
                replan, "default_output_dir", return_value=output_dir
            ), patch.object(replan, "run_preanalysis_validation", return_value="ok"), patch.object(
                replan, "state_lock", side_effect=lambda _path: nullcontext()
            ), patch.object(replan, "parse_module", return_value=model), patch.object(
                replan, "load_state", return_value=state
            ), patch.object(replan, "reconcile_state", return_value=(state, {})), patch.object(
                sys, "argv", argv
            ):
                self.assertEqual(replan.main(), 0)

            committed = json.loads(
                (output_dir / "generation-state.json").read_text(encoding="utf-8")
            )
            records = {item["rsu_id"]: item for item in committed["rsus"]}
            self.assertEqual(records["RSU-001"]["generation_status"], "validated")
            self.assertEqual(records["RSU-003"]["generation_status"], "validated")
            self.assertEqual(records["RSU-002"]["generation_status"], "stale")
            self.assertIsNone(records["RSU-002"]["batch_id"])
            self.assertEqual(committed["planning"]["status"], "prepared")
            self.assertEqual(committed["batches"], [])
            self.assertEqual(committed["replan_history"][0]["rsu_ids"], ["RSU-002"])

            replanned = json.loads(plan_file.read_text(encoding="utf-8"))
            plan_by_rsu = {item["rsu_id"]: item for item in replanned["rsus"]}
            self.assertEqual(plan_by_rsu["RSU-002"]["mode"], "complex")
            self.assertNotEqual(
                plan_by_rsu["RSU-001"]["batch_id"],
                plan_by_rsu["RSU-002"]["batch_id"],
            )
            self.assertNotEqual(
                plan_by_rsu["RSU-002"]["batch_id"],
                plan_by_rsu["RSU-003"]["batch_id"],
            )


if __name__ == "__main__":
    unittest.main()
