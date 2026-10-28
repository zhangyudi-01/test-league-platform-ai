from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import init_generation  # noqa: E402
import common  # noqa: E402
import prepare_next_tp  # noqa: E402
import run_generation  # noqa: E402
import validate_tp_test_cases  # noqa: E402


class GenerationRecoveryTests(unittest.TestCase):
    def test_preanalysis_validation_excludes_default_and_explicit_case_roots(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module_dir = Path(temp) / "module"
            preanalysis_dir = module_dir
            points_dir = module_dir / "test-points"
            default_case_dir = module_dir / "test-cases"
            explicit_case_dir = module_dir / "test-run-isolated"
            historical_case_dir = module_dir / "test-run-history"
            unrelated_dir = module_dir / "test-run-not-a-case-workspace"
            for path in (
                points_dir,
                default_case_dir,
                explicit_case_dir,
                historical_case_dir,
                unrelated_dir,
            ):
                path.mkdir(parents=True, exist_ok=True)
            (historical_case_dir / "generation-state.json").write_text(
                json.dumps(
                    {
                        "schema_version": "tp-test-case-generation/v2",
                        "module_dir": module_dir.as_posix(),
                        "case_output_dir": historical_case_dir.as_posix(),
                    }
                ),
                encoding="utf-8",
            )
            (unrelated_dir / "generation-state.json").write_text(
                json.dumps(
                    {
                        "schema_version": "another-workflow/v1",
                        "module_dir": module_dir.as_posix(),
                    }
                ),
                encoding="utf-8",
            )
            validator = module_dir / "validate_preanalysis.py"
            validator.write_text("# validator stub", encoding="utf-8")
            layout = SimpleNamespace(
                module_dir=module_dir,
                preanalysis_dir=preanalysis_dir,
                manifest_path=None,
                default_output_dir=points_dir,
            )
            completed = subprocess.CompletedProcess([], 0, "ok", "")

            with patch.object(
                common.upstream, "find_preanalysis_validator", return_value=validator
            ), patch.object(common.subprocess, "run", return_value=completed) as run:
                common.run_preanalysis_validation(layout, explicit_case_dir)

            command = run.call_args.args[0]
            excluded = [
                Path(command[index + 1]).resolve()
                for index, value in enumerate(command)
                if value == "--exclude-root"
            ]
            self.assertEqual(
                excluded,
                [
                    points_dir.resolve(),
                    default_case_dir.resolve(),
                    explicit_case_dir.resolve(),
                    historical_case_dir.resolve(),
                ],
            )

    def test_case_input_keeps_sql_materialization_contract(self) -> None:
        self.assertTrue(callable(common.registry_manifest))
        self.assertTrue(callable(common.relevant_assets_manifest))
        self.assertTrue(callable(common.relevant_assets_index_text))

    def test_revalidate_selects_validated_tp_without_disturbing_next_pending(self) -> None:
        state = {
            "tps": [
                {"tp_id": "TP-001", "status": "validated"},
                {"tp_id": "TP-002", "status": "pending"},
            ]
        }

        selected = validate_tp_test_cases.select_validation_record(
            state, "TP-001", revalidate=True
        )

        self.assertEqual(selected["tp_id"], "TP-001")
        self.assertEqual(state["tps"][1]["status"], "pending")

    def test_revalidate_rejects_nonvalidated_tp(self) -> None:
        state = {"tps": [{"tp_id": "TP-001", "status": "prepared"}]}

        with self.assertRaisesRegex(common.WorkflowError, "is not already validated"):
            validate_tp_test_cases.select_validation_record(
                state, "TP-001", revalidate=True
            )

    def test_normal_validation_still_requires_next_pending_tp(self) -> None:
        state = {
            "tps": [
                {"tp_id": "TP-001", "status": "validated"},
                {"tp_id": "TP-002", "status": "prepared"},
                {"tp_id": "TP-003", "status": "pending"},
            ]
        }

        with self.assertRaisesRegex(common.WorkflowError, "only next TP TP-002"):
            validate_tp_test_cases.select_validation_record(
                state, "TP-003", revalidate=False
            )

    def test_refresh_archives_derived_session_inputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            case_dir = Path(temp)
            delta = case_dir / "session-inputs" / "TP-001-delta.md"
            delta.parent.mkdir(parents=True)
            delta.write_text("derived delta", encoding="utf-8")

            archived = common.archive_generated_artifacts(case_dir, "source changed")

            self.assertIsNotNone(archived)
            self.assertTrue((archived / "session-inputs" / delta.name).is_file())
            self.assertFalse((case_dir / "session-inputs").exists())

    def test_refresh_archives_baseline_fork_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            case_dir = Path(temp)
            baseline = case_dir / "baselines" / "contexts" / "sig-baseline.md"
            baseline.parent.mkdir(parents=True)
            baseline.write_text("context baseline", encoding="utf-8")

            archived = common.archive_generated_artifacts(case_dir, "source changed")

            self.assertIsNotNone(archived)
            self.assertTrue(
                (archived / "baselines" / "contexts" / baseline.name).is_file()
            )
            self.assertTrue((case_dir / "baselines").is_dir())
            self.assertEqual(
                [path.name for path in (case_dir / "baselines").iterdir()],
                ["contexts"],
            )
            self.assertFalse(any((case_dir / "baselines" / "contexts").iterdir()))

    def test_case_input_embeds_dynamic_closure_but_only_anchors_fixed_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            final_points_dir = root / "test-points"
            final_points_dir.mkdir()
            (final_points_dir / common.FINAL_POINTS_NAME).write_text(
                "final points", encoding="utf-8"
            )
            case_dir = root / "test-cases"
            common.ensure_dirs(case_dir)

            resources = {}
            bodies = {
                "SRC-GLOBAL": "GLOBAL-FIXED-BODY",
                "SRC-MOD": "MODULE-FIXED-BODY",
                "CTX": "LOGIC-FIXED-BODY",
                "FC-003": "DYNAMIC-FEATURE-BODY",
                "DC-002": "DYNAMIC-CLOSURE-BODY",
                "DC-003": "DYNAMIC-CLOSURE-BODY-SECOND",
                "DC-INDEX": "DYNAMIC-CLOSURE-INDEX",
            }
            for resource_id, body in bodies.items():
                path = root / f"{resource_id}.md"
                path.write_text(body, encoding="utf-8")
                resources[resource_id] = SimpleNamespace(path=path)

            rsu_cells = ("RSU-001",) + tuple(
                "value" for _ in common.RSU_HEADERS[1:]
            )
            model = SimpleNamespace(
                fixed_resource_ids=("SRC-GLOBAL", "SRC-MOD", "CTX"),
                resources=resources,
                data_closure_enabled=True,
                questions={},
                rsu_by_id={"RSU-001": SimpleNamespace(cells=rsu_cells)},
            )
            readiness = common.CaseReadiness(
                result="ready",
                tp_status={"TP-001": "ready", "TP-002": "ready"},
                tp_ciq_refs={"TP-001": (), "TP-002": ()},
                questions={},
                document_sha256="readiness-hash",
                output_sha256="output-hash",
            )
            tp = common.TestPoint(
                tp_id="TP-001",
                cells=("TP-001",),
                headers=("TP-ID",),
                order=1,
                primary_rsu="RSU-001",
                source_rsus=("RSU-001",),
                question_refs=(),
                context_refs=("SRC-GLOBAL", "SRC-MOD", "CTX", "FC-003", "DC-INDEX"),
                data_closure_refs=("DC-002", "DC-003"),
                text="test point",
            )

            bundle = common.materialize_case_input(
                model,
                readiness,
                "EXECUTION-CONTEXT-BODY",
                "context-hash",
                tp,
                final_points_dir,
                case_dir,
            )
            reordered_tp = replace(
                tp,
                tp_id="TP-002",
                cells=("TP-002",),
                context_refs=tuple(reversed(tp.context_refs)),
                data_closure_refs=tuple(reversed(tp.data_closure_refs)),
            )
            reordered_bundle = common.materialize_case_input(
                model,
                readiness,
                "EXECUTION-CONTEXT-BODY",
                "context-hash",
                reordered_tp,
                final_points_dir,
                case_dir,
            )

            self.assertFalse(bundle.blockers)
            for fixed_body in ("GLOBAL-FIXED-BODY", "MODULE-FIXED-BODY", "LOGIC-FIXED-BODY"):
                self.assertNotIn(fixed_body, bundle.text)
            for dynamic_body in (
                "DYNAMIC-FEATURE-BODY",
                "DYNAMIC-CLOSURE-BODY",
                "DYNAMIC-CLOSURE-INDEX",
                "EXECUTION-CONTEXT-BODY",
            ):
                self.assertIn(dynamic_body, bundle.text)
            self.assertIn("固定来源溯源锚点", bundle.text)
            self.assertIn("EXECUTION-CONTEXT-BODY", bundle.module_baseline_text)
            self.assertNotIn("DYNAMIC-FEATURE-BODY", bundle.module_baseline_text)
            self.assertIn("DYNAMIC-FEATURE-BODY", bundle.context_baseline_text)
            self.assertIn("DYNAMIC-CLOSURE-BODY", bundle.context_baseline_text)
            self.assertNotIn("EXECUTION-CONTEXT-BODY", bundle.context_baseline_text)
            self.assertIn("TP-001", bundle.delta_text)
            self.assertIn("RSU-001", bundle.delta_text)
            self.assertNotIn("DYNAMIC-FEATURE-BODY", bundle.delta_text)
            self.assertEqual(len(bundle.baseline_signature), 24)
            self.assertNotIn("SESSION_INPUT", bundle.text)
            self.assertEqual(bundle.baseline_signature, reordered_bundle.baseline_signature)
            self.assertEqual(
                bundle.context_baseline_sha256,
                reordered_bundle.context_baseline_sha256,
            )
            self.assertEqual(bundle.context_baseline_text, reordered_bundle.context_baseline_text)

    def test_init_preserves_prepared_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            case_dir = Path(temp)
            output = case_dir / "by-tp" / "TP-001.md"
            output.parent.mkdir(parents=True)
            output.write_text("generated output", encoding="utf-8")
            point = SimpleNamespace(tp_id="TP-001", order=1)
            readiness = SimpleNamespace(
                tp_status={"TP-001": "ready"}, tp_ciq_refs={"TP-001": ()}
            )
            existing = {
                "tps": [
                    {
                        "tp_id": "TP-001",
                        "status": "prepared",
                        "input_sha256": "semantic",
                        "input_document_sha256": "document",
                        "input_file": "inputs/TP-001-input.md",
                        "output_file": "by-tp/TP-001.md",
                        "prepared_at": "2026-09-07T00:00:00Z",
                    }
                ]
            }

            record = init_generation._records(
                [point], readiness, existing, case_dir, preserve=True
            )[0]

            self.assertEqual(record["status"], "prepared")
            self.assertEqual(record["input_sha256"], "semantic")
            self.assertEqual(record["input_file"], "inputs/TP-001-input.md")
            self.assertEqual(record["output_file"], "by-tp/TP-001.md")

    def test_init_requires_refresh_for_pre_batch_states(self) -> None:
        self.assertTrue(
            init_generation._state_incompatible(
                {"schema_version": "tp-test-case-generation/v2"}
            )
        )
        self.assertTrue(
            init_generation._state_incompatible(
                {"schema_version": "tp-test-case-generation/v3"}
            )
        )
        self.assertFalse(
            init_generation._state_incompatible(
                {
                    "schema_version": "tp-test-case-generation/v3",
                    "planning": {"status": "pending"},
                    "sql_planning": {"status": "pending"},
                    "batches": [],
                    "legacy_excel_field": "ignored",
                }
            )
        )

    def test_prepare_recovers_matching_preexisting_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            case_dir = Path(temp)
            input_path = case_dir / "inputs" / "TP-001-input.md"
            output_path = case_dir / "by-tp" / "TP-001.md"
            input_path.parent.mkdir(parents=True)
            output_path.parent.mkdir(parents=True)
            input_path.write_text("deterministic input", encoding="utf-8")
            output_path.write_text("generated output", encoding="utf-8")
            bundle = SimpleNamespace(
                text="deterministic input", input_sha256="semantic-sha"
            )
            pending = {"status": "pending", "prepared_at": None}

            recovered = prepare_next_tp.recover_preexisting_preparation(
                pending, bundle, input_path, output_path, case_dir
            )

            self.assertTrue(recovered)
            self.assertEqual(pending["status"], "prepared")
            self.assertEqual(pending["input_sha256"], "semantic-sha")
            self.assertEqual(pending["input_file"], "inputs/TP-001-input.md")
            self.assertEqual(pending["output_file"], "by-tp/TP-001.md")
            self.assertIsNotNone(pending["prepared_at"])

    def test_prepare_rejects_conflicting_preexisting_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            case_dir = Path(temp)
            input_path = case_dir / "inputs" / "TP-001-input.md"
            output_path = case_dir / "by-tp" / "TP-001.md"
            input_path.parent.mkdir(parents=True)
            output_path.parent.mkdir(parents=True)
            input_path.write_text("stale input", encoding="utf-8")
            output_path.write_text("generated output", encoding="utf-8")
            bundle = SimpleNamespace(text="current input", input_sha256="semantic-sha")
            pending = {"status": "pending"}

            recovered = prepare_next_tp.recover_preexisting_preparation(
                pending, bundle, input_path, output_path, case_dir
            )

            self.assertFalse(recovered)
            self.assertEqual(pending["status"], "pending")

    def test_windows_interrupt_terminates_process_tree(self) -> None:
        process = Mock()
        process.pid = 4321
        process.poll.return_value = None
        process.wait.return_value = 0
        with patch.object(run_generation.os, "name", "nt"), patch.object(
            run_generation.subprocess, "run"
        ) as run:
            run_generation.terminate_process_tree(process)

        run.assert_called_once_with(
            ["taskkill", "/PID", "4321", "/T", "/F"],
            stdout=run_generation.subprocess.DEVNULL,
            stderr=run_generation.subprocess.DEVNULL,
            check=False,
        )
        process.wait.assert_called_once_with(timeout=10.0)


if __name__ == "__main__":
    unittest.main()
