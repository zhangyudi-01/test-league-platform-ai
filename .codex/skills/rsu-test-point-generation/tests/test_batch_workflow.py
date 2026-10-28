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

import common  # noqa: E402
import prepare_next_batch as batch_preparation  # noqa: E402
import run_generation as runner  # noqa: E402
import validate_batch_candidates as batch_validation  # noqa: E402


class BatchWorkflowTests(unittest.TestCase):
    @staticmethod
    def write_scheduler_state(path: Path, *, status: str = "prepared") -> None:
        value = {
            "rsus": [
                {
                    "rsu_id": "RSU-001",
                    "generation_status": "prepared" if status != "running" else "running",
                    "blockers": [],
                }
            ],
            "batches": [
                {
                    "batch_id": "BATCH-001",
                    "mode": "complex",
                    "rsu_ids": ["RSU-001"],
                    "active_rsu_ids": ["RSU-001"],
                    "status": status,
                }
            ],
            "planning": {"status": "validated"},
            "finalization": {"status": "not-ready"},
            "case_readiness": {"status": "not-ready", "result": None},
        }
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_batch_result_requires_stable_member_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "result.json"
            batch = {"batch_id": "BATCH-001", "rsu_ids": ["RSU-001", "RSU-002"]}
            value = {
                "schema_version": batch_validation.BATCH_RESULT_SCHEMA,
                "batch_id": "BATCH-001",
                "status": "complete",
                "rsus": [
                    {"rsu_id": "RSU-002", "status": "complete", "reason": ""},
                    {"rsu_id": "RSU-001", "status": "complete", "reason": ""},
                ],
            }
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(common.WorkflowError, "order mismatch"):
                batch_validation.load_batch_result(path, batch)

    def test_replan_requires_concrete_reason_and_matching_aggregate_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "result.json"
            batch = {"batch_id": "BATCH-001", "rsu_ids": ["RSU-001"]}
            value = {
                "schema_version": batch_validation.BATCH_RESULT_SCHEMA,
                "batch_id": "BATCH-001",
                "status": "replan-required",
                "rsus": [{"rsu_id": "RSU-001", "status": "replan-required", "reason": "太复杂"}],
            }
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(common.WorkflowError, "concrete reason"):
                batch_validation.load_batch_result(path, batch)

            value["status"] = "complete"
            value["rsus"][0]["reason"] = "存在跨状态时序，需要独立上下文处理"
            path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(common.WorkflowError, "aggregate status conflicts"):
                batch_validation.load_batch_result(path, batch)

    def test_interrupted_draft_with_completed_member_is_recoverable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "result.json"
            batch = {"batch_id": "BATCH-001", "rsu_ids": ["RSU-001", "RSU-002"]}
            value = {
                "schema_version": batch_validation.BATCH_RESULT_SCHEMA,
                "batch_id": "BATCH-001",
                "status": "draft",
                "rsus": [
                    {"rsu_id": "RSU-001", "status": "complete", "reason": ""},
                    {"rsu_id": "RSU-002", "status": "draft", "reason": ""},
                ],
            }
            path.write_text(json.dumps(value), encoding="utf-8")
            rows = batch_validation.load_batch_result(path, batch)
            self.assertEqual([item["status"] for item in rows], ["complete", "draft"])

            value["rsus"][0]["status"] = "draft"
            path.write_text(json.dumps(value), encoding="utf-8")
            with self.assertRaisesRegex(common.WorkflowError, "no recoverable progress"):
                batch_validation.load_batch_result(path, batch)

    def test_partial_commit_preserves_completed_member_and_reprepares_only_remaining_rsu(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module_dir = Path(temp) / "module"
            output_dir = module_dir / "test-points"
            for relative in (
                "inputs",
                "session-inputs",
                "by-rsu",
                "batches",
                "batch-results/BATCH-001",
                "batches/BATCH-001/by-rsu",
            ):
                (output_dir / relative).mkdir(parents=True, exist_ok=True)

            staged_one = output_dir / "batches" / "BATCH-001" / "by-rsu" / "RSU-001.md"
            staged_two = output_dir / "batches" / "BATCH-001" / "by-rsu" / "RSU-002.md"
            staged_one.write_text("# validated RSU-001\n", encoding="utf-8")
            staged_two.write_text("# unfinished RSU-002\n", encoding="utf-8")
            result_file = output_dir / "batch-results" / "BATCH-001" / "result.json"
            result_file.write_text(
                json.dumps(
                    {
                        "schema_version": batch_validation.BATCH_RESULT_SCHEMA,
                        "batch_id": "BATCH-001",
                        "status": "partial",
                        "rsus": [
                            {"rsu_id": "RSU-001", "status": "complete", "reason": ""},
                            {"rsu_id": "RSU-002", "status": "draft", "reason": ""},
                        ],
                    }
                ),
                encoding="utf-8",
            )
            state = {
                "rsus": [
                    {
                        "rsu_id": "RSU-001",
                        "generation_status": "running",
                        "staged_candidate_file": "batches/BATCH-001/by-rsu/RSU-001.md",
                        "blockers": [],
                    },
                    {
                        "rsu_id": "RSU-002",
                        "generation_status": "running",
                        "staged_candidate_file": "batches/BATCH-001/by-rsu/RSU-002.md",
                        "blockers": [],
                    },
                ],
                "batches": [
                    {
                        "batch_id": "BATCH-001",
                        "mode": "simple",
                        "context_signature": "ctx-sha",
                        "rsu_ids": ["RSU-001", "RSU-002"],
                        "active_rsu_ids": ["RSU-001", "RSU-002"],
                        "status": "running",
                        "result_file": "batch-results/BATCH-001/result.json",
                        "runner_pid": 123,
                        "runner_run_id": "old-run",
                    }
                ],
                "planning": {"status": "validated"},
                "finalization": {"status": "not-ready"},
                "case_readiness": {"status": "not-ready", "result": None},
            }
            bundles = {
                rsu_id: SimpleNamespace(
                    input_sha256=f"input-{rsu_id}",
                    rendered=f"# full {rsu_id}\n",
                    session_rendered=f"# delta {rsu_id}\n",
                    dynamic_materials=[],
                )
                for rsu_id in ("RSU-001", "RSU-002")
            }
            layout = SimpleNamespace(module_dir=module_dir)
            model = SimpleNamespace(data_closure_enabled=False)

            validation_patches = (
                patch.object(batch_validation, "resolve_module_layout", return_value=layout),
                patch.object(batch_validation, "default_output_dir", return_value=output_dir),
                patch.object(batch_validation, "run_preanalysis_validation", return_value="ok"),
                patch.object(batch_validation, "state_lock", side_effect=lambda _path: nullcontext()),
                patch.object(batch_validation, "parse_module", return_value=model),
                patch.object(batch_validation, "load_state", return_value=state),
                patch.object(batch_validation, "reconcile_state", return_value=(state, bundles)),
                patch.object(
                    batch_validation,
                    "validate_candidate_document",
                    return_value=(SimpleNamespace(rows=[["candidate"]]), []),
                ),
                patch.object(
                    sys,
                    "argv",
                    [
                        "validate_batch_candidates.py",
                        str(module_dir),
                        "--output-dir",
                        str(output_dir),
                        "BATCH-001",
                    ],
                ),
            )
            for active_patch in validation_patches:
                active_patch.start()
            try:
                self.assertEqual(batch_validation.main(), 3)
            finally:
                for active_patch in reversed(validation_patches):
                    active_patch.stop()

            committed = json.loads((output_dir / "generation-state.json").read_text(encoding="utf-8"))
            records = {item["rsu_id"]: item for item in committed["rsus"]}
            self.assertEqual(records["RSU-001"]["generation_status"], "validated")
            self.assertEqual(records["RSU-002"]["generation_status"], "prepared")
            self.assertEqual(
                (output_dir / "by-rsu" / "RSU-001.md").read_text(encoding="utf-8"),
                "# validated RSU-001\n",
            )
            self.assertEqual(committed["batches"][0]["status"], "prepared")
            self.assertEqual(
                committed["batches"][0]["active_rsu_ids"],
                ["RSU-001", "RSU-002"],
            )

            preparation_patches = (
                patch.object(batch_preparation, "resolve_module_layout", return_value=layout),
                patch.object(batch_preparation, "default_output_dir", return_value=output_dir),
                patch.object(batch_preparation, "run_preanalysis_validation", return_value="ok"),
                patch.object(batch_preparation, "state_lock", side_effect=lambda _path: nullcontext()),
                patch.object(batch_preparation, "parse_module", return_value=model),
                patch.object(batch_preparation, "ensure_output_scaffold", return_value=None),
                patch.object(batch_preparation, "load_state", return_value=committed),
                patch.object(batch_preparation, "reconcile_state", return_value=(committed, bundles)),
                patch.object(
                    sys,
                    "argv",
                    [
                        "prepare_next_batch.py",
                        str(module_dir),
                        "--output-dir",
                        str(output_dir),
                        "--batch-id",
                        "BATCH-001",
                    ],
                ),
            )
            for active_patch in preparation_patches:
                active_patch.start()
            try:
                self.assertEqual(batch_preparation.main(), 0)
            finally:
                for active_patch in reversed(preparation_patches):
                    active_patch.stop()

            reprepared = json.loads((output_dir / "generation-state.json").read_text(encoding="utf-8"))
            self.assertEqual(reprepared["batches"][0]["active_rsu_ids"], ["RSU-002"])
            retry_result = json.loads(result_file.read_text(encoding="utf-8"))
            self.assertEqual([item["rsu_id"] for item in retry_result["rsus"]], ["RSU-002"])
            self.assertTrue((output_dir / "by-rsu" / "RSU-001.md").is_file())

    def test_parent_marks_running_and_recovers_stale_owner_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state_file = Path(temp) / "generation-state.json"
            self.write_scheduler_state(state_file)

            runner.mark_batches_running(state_file, ("BATCH-001",), "run-1")
            running = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(running["batches"][0]["status"], "running")
            self.assertEqual(running["batches"][0]["runner_run_id"], "run-1")
            self.assertEqual(running["rsus"][0]["generation_status"], "running")

            with patch.object(runner, "process_is_alive", return_value=False):
                recovered = runner.recover_stale_running_batches(state_file, "run-2")
            self.assertEqual(recovered, ["BATCH-001"])
            value = json.loads(state_file.read_text(encoding="utf-8"))
            self.assertEqual(value["batches"][0]["status"], "prepared")
            self.assertIsNone(value["batches"][0]["runner_pid"])
            self.assertEqual(value["rsus"][0]["generation_status"], "prepared")

    def test_live_running_owner_is_not_reclaimed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state_file = Path(temp) / "generation-state.json"
            self.write_scheduler_state(state_file, status="running")
            value = json.loads(state_file.read_text(encoding="utf-8"))
            value["batches"][0]["runner_pid"] = 12345
            value["batches"][0]["runner_run_id"] = "other-run"
            state_file.write_text(json.dumps(value), encoding="utf-8")
            with patch.object(runner, "process_is_alive", return_value=True):
                with self.assertRaisesRegex(runner.AttentionRequired, "still owned"):
                    runner.recover_stale_running_batches(state_file, "run-2")

    def test_invalid_private_result_is_quarantined(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "test-points"
            result = output / "batch-results" / "BATCH-001" / "result.json"
            result.parent.mkdir(parents=True)
            result.write_text("{broken", encoding="utf-8")
            self.assertEqual(runner.inspect_batch_result(result), "invalid")
            target = runner.quarantine_invalid_batch_result(output, "BATCH-001", result)
            self.assertFalse(result.exists())
            self.assertTrue(target.is_file())
            self.assertTrue(target.is_relative_to(output / "history" / "batch-results"))

    def test_protected_snapshot_detects_shared_and_sibling_batch_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module = Path(temp) / "module"
            own = module / "test-points" / "batches" / "BATCH-001"
            own.mkdir(parents=True)
            state = module / "test-points" / "generation-state.json"
            final = module / "test-points" / "module-test-points.md"
            sibling = module / "test-points" / "batches" / "BATCH-002" / "RSU-002.md"
            sibling.parent.mkdir(parents=True)
            state.write_text("{}", encoding="utf-8")
            final.write_text("final", encoding="utf-8")
            sibling.write_text("sibling", encoding="utf-8")
            before = runner.protected_workspace_snapshot(module, allowed_paths=(own,))

            for target, content in (
                (state, '{"changed":true}'),
                (final, "changed final"),
                (sibling, "changed sibling"),
            ):
                original = target.read_text(encoding="utf-8")
                target.write_text(content, encoding="utf-8")
                after = runner.protected_workspace_snapshot(module, allowed_paths=(own,))
                with self.assertRaisesRegex(runner.RunnerError, "outside its authorization"):
                    runner.require_protected_snapshot_unchanged(before, after, "batch")
                target.write_text(original, encoding="utf-8")

    def test_private_batch_files_are_excluded_from_protected_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module = Path(temp) / "module"
            own = module / "test-points" / "batches" / "BATCH-001"
            own.mkdir(parents=True)
            file = own / "RSU-001.md"
            file.write_text("before", encoding="utf-8")
            before = runner.protected_workspace_snapshot(module, allowed_paths=(own,))
            file.write_text("after", encoding="utf-8")
            after = runner.protected_workspace_snapshot(module, allowed_paths=(own,))
            runner.require_protected_snapshot_unchanged(before, after, "batch")


if __name__ == "__main__":
    unittest.main()
