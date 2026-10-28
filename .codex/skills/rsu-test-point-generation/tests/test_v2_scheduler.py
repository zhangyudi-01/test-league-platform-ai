from __future__ import annotations

import json
import shutil
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import common  # noqa: E402
import run_generation as runner  # noqa: E402


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def config_for(
    root: Path,
    *,
    module_concurrency: int = 2,
    session_mode: str = "isolated",
) -> runner.RunnerConfig:
    module_dir = root / "module"
    module_dir.mkdir(parents=True, exist_ok=True)
    return runner.RunnerConfig(
        module_dir=module_dir,
        manifest=None,
        preanalysis_dir=None,
        output_dir=module_dir / "test-points",
        workdir=root,
        logs_dir=root / "logs",
        codex_bin="codex",
        model=None,
        profile=None,
        sandbox="workspace-write",
        max_rsu_turns=None,
        session_mode=session_mode,
        module_concurrency=module_concurrency,
    )


def state_value(output_dir: Path, *, complete: bool = False) -> dict:
    rsu_status = "validated" if complete else "pending"
    batch_status = "validated" if complete else "pending"
    return {
        "schema_version": 4,
        "scheduler_schema": "rsu-test-point-generation/state-v2",
        "module_dir": output_dir.parent.as_posix(),
        "output_dir": output_dir.as_posix(),
        "session_source_fingerprint_sha256": "fixed-source",
        "foundation": {"status": "pending", "thread_id": None},
        "planning": {"status": "validated"},
        "batches": [
            {
                "batch_id": "BATCH-001",
                "mode": "simple",
                "rsu_ids": ["RSU-001"],
                "active_rsu_ids": [],
                "status": batch_status,
                "result_file": "batch-results/BATCH-001/result.json",
            },
            {
                "batch_id": "BATCH-002",
                "mode": "simple",
                "rsu_ids": ["RSU-002"],
                "active_rsu_ids": [],
                "status": batch_status,
                "result_file": "batch-results/BATCH-002/result.json",
            },
        ],
        "rsus": [
            {"rsu_id": "RSU-001", "generation_status": rsu_status, "blockers": []},
            {"rsu_id": "RSU-002", "generation_status": rsu_status, "blockers": []},
        ],
        "finalization": {"status": "validated" if complete else "not-ready"},
        "case_readiness": {
            "status": "validated" if complete else "not-ready",
            "result": "ready" if complete else None,
        },
    }


def successful_turn(run_dir: Path, turn_number: int, phase: str) -> runner.CodexTurnResult:
    prefix = run_dir / f"{turn_number:03d}-{phase}"
    for path in (prefix.with_suffix(".jsonl"), prefix.with_suffix(".stderr"), prefix.with_suffix(".md")):
        path.write_text("", encoding="utf-8")
    return runner.CodexTurnResult(
        0,
        prefix.with_suffix(".jsonl"),
        prefix.with_suffix(".stderr"),
        prefix.with_suffix(".md"),
    )


class V2SchedulerTests(unittest.TestCase):
    def setUp(self) -> None:
        # Scheduler tests use injected fake workers. Telemetry must not launch
        # whichever Codex CLI happens to be installed on the test machine.
        version_probe = patch.object(runner, "probe_codex_version", return_value="test-codex")
        version_probe.start()
        self.addCleanup(version_probe.stop)

    def test_json_templates_are_valid_after_rendering(self) -> None:
        state_text = common.load_template(
            "generation-state.json.tmpl",
            {
                "MODULE_DIR": "D:/workspace/module",
                "PREANALYSIS_DIR": "D:/workspace/module/preanalysis",
                "MANIFEST_PATH_JSON": json.dumps("D:/workspace/module/preanalysis/manifest.json"),
                "MANIFEST_SHA256_JSON": json.dumps("abc123"),
                "OUTPUT_DIR": "D:/workspace/module/test-points",
                "CREATED_AT": "2026-09-10T00:00:00Z",
                "UPDATED_AT": "2026-09-10T00:00:00Z",
            },
        )
        batch_text = common.load_template(
            "batch-result.json.tmpl",
            {
                "BATCH_ID": "BATCH-001",
                "RSU_RESULTS": json.dumps(
                    {"rsu_id": "RSU-001", "status": "draft", "reason": ""},
                    ensure_ascii=False,
                ),
            },
        )

        self.assertEqual(json.loads(state_text)["schema_version"], 4)
        self.assertEqual(json.loads(batch_text)["rsus"][0]["rsu_id"], "RSU-001")

    def test_complete_v2_state_returns_without_stage_or_ai_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            output_dir = config.output_dir
            assert output_dir is not None
            state_file = output_dir / "generation-state.json"
            write_json(state_file, state_value(output_dir, complete=True))

            result = runner._run_pipeline(
                config,
                initialize_fn=lambda _config: state_file,
                invoke_fn=lambda *_args: self.fail("AI must not run for a complete v2 state"),
                stage_fn=lambda *_args: self.fail("stage scripts must not run for a complete v2 state"),
            )

            self.assertEqual(result.case_readiness_result, "ready")
            self.assertEqual(result.codex_turns, 0)

    def test_parallel_batches_finish_out_of_order_but_parent_commits_stably(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root, module_concurrency=2)
            output_dir = config.output_dir
            assert output_dir is not None
            state_file = output_dir / "generation-state.json"
            write_json(state_file, state_value(output_dir))
            completion_order: list[str] = []
            validation_order: list[str] = []
            phase_order: list[str] = []
            order_lock = threading.Lock()

            def save_state(value: dict) -> None:
                write_json(state_file, value)

            def stage(_config, script_name: str, positional: tuple[str, ...]) -> str:
                value = json.loads(state_file.read_text(encoding="utf-8"))
                if script_name == "prepare_generation_plan.py":
                    return "STATUS=validated"
                if script_name == "prepare_next_batch.py":
                    batch_id = positional[-1]
                    batch = next(item for item in value["batches"] if item["batch_id"] == batch_id)
                    batch["status"] = "prepared"
                    batch["active_rsu_ids"] = list(batch["rsu_ids"])
                    for rsu in value["rsus"]:
                        if rsu["rsu_id"] in batch["rsu_ids"]:
                            rsu["generation_status"] = "prepared"
                    result_file = output_dir / batch["result_file"]
                    write_json(
                        result_file,
                        {
                            "schema_version": "rsu-test-point-generation/batch-result-v1",
                            "batch_id": batch_id,
                            "status": "draft",
                            "rsus": [
                                {"rsu_id": rsu_id, "status": "draft", "reason": ""}
                                for rsu_id in batch["rsu_ids"]
                            ],
                            "notes": "",
                        },
                    )
                    save_state(value)
                    return "STATUS=prepared"
                if script_name == "validate_batch_candidates.py":
                    batch_id = positional[-1]
                    batch = next(item for item in value["batches"] if item["batch_id"] == batch_id)
                    for rsu_id in batch["active_rsu_ids"]:
                        private_file = output_dir / "batches" / batch_id / f"{rsu_id}.md"
                        formal_file = output_dir / "by-rsu" / f"{rsu_id}.md"
                        formal_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(private_file, formal_file)
                        record = next(item for item in value["rsus"] if item["rsu_id"] == rsu_id)
                        record["generation_status"] = "validated"
                    batch["status"] = "validated"
                    batch["active_rsu_ids"] = []
                    batch["runner_pid"] = None
                    batch["runner_run_id"] = None
                    validation_order.append(batch_id)
                    save_state(value)
                    return "STATUS=validated"
                if script_name == "prepare_finalization.py":
                    value["finalization"] = {"status": "prepared"}
                    phase_order.append("prepare-finalization")
                    save_state(value)
                    return "STATUS=prepared"
                if script_name == "validate_module_test_points.py":
                    value["finalization"] = {"status": "validated"}
                    phase_order.append("validate-finalization")
                    save_state(value)
                    return "STATUS=validated"
                if script_name == "prepare_case_readiness.py":
                    value["case_readiness"] = {"status": "prepared", "result": None}
                    phase_order.append("prepare-readiness")
                    save_state(value)
                    return "STATUS=prepared"
                if script_name == "validate_case_readiness.py":
                    value["case_readiness"] = {"status": "validated", "result": "ready"}
                    phase_order.append("validate-readiness")
                    save_state(value)
                    return "STATUS=validated"
                self.fail(f"unexpected stage: {script_name}")

            def invoke(
                _config,
                run_dir: Path,
                turn_number: int,
                phase: str,
                _prompt: str,
                label: str | None,
                _parent_thread: str | None = None,
            ) -> runner.CodexTurnResult:
                if phase == "batch":
                    assert label is not None
                    if label == "BATCH-001":
                        time.sleep(0.08)
                    batch = next(
                        item
                        for item in json.loads(state_file.read_text(encoding="utf-8"))["batches"]
                        if item["batch_id"] == label
                    )
                    private_dir = output_dir / "batches" / label
                    private_dir.mkdir(parents=True, exist_ok=True)
                    for rsu_id in batch["active_rsu_ids"]:
                        (private_dir / f"{rsu_id}.md").write_text(
                            f"# {rsu_id}\n", encoding="utf-8"
                        )
                    result_file = output_dir / batch["result_file"]
                    result = json.loads(result_file.read_text(encoding="utf-8"))
                    result["status"] = "complete"
                    for item in result["rsus"]:
                        item["status"] = "complete"
                    write_json(result_file, result)
                    with order_lock:
                        completion_order.append(label)
                elif phase == "finalization":
                    self.assertEqual(validation_order, ["BATCH-001", "BATCH-002"])
                    (output_dir / "module-test-points.md").write_text("# final\n", encoding="utf-8")
                    (output_dir / "coverage-matrix.md").write_text("# coverage\n", encoding="utf-8")
                    phase_order.append("ai-finalization")
                elif phase == "case-readiness":
                    (output_dir / "test-case-readiness.md").write_text("# ready\n", encoding="utf-8")
                    phase_order.append("ai-readiness")
                else:
                    self.fail(f"unexpected AI phase: {phase}")
                return successful_turn(run_dir, turn_number, phase)

            result = runner._run_pipeline(
                config,
                initialize_fn=lambda _config: state_file,
                invoke_fn=invoke,
                stage_fn=stage,
            )

            self.assertEqual(completion_order, ["BATCH-002", "BATCH-001"])
            self.assertEqual(validation_order, ["BATCH-001", "BATCH-002"])
            self.assertEqual(
                phase_order,
                [
                    "prepare-finalization",
                    "ai-finalization",
                    "validate-finalization",
                    "prepare-readiness",
                    "ai-readiness",
                    "validate-readiness",
                ],
            )
            self.assertEqual(result.batch_turns, 2)
            self.assertEqual(result.rsu_turns, 2)
            self.assertEqual(result.case_readiness_result, "ready")

    def test_resume_reuses_foundation_and_commits_private_result_before_new_ai(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root, module_concurrency=1, session_mode="module-session")
            output_dir = config.output_dir
            assert output_dir is not None
            output_dir.mkdir(parents=True, exist_ok=True)
            state_file = output_dir / "generation-state.json"
            state = state_value(output_dir)
            state["batches"] = state["batches"][:1]
            state["rsus"] = state["rsus"][:1]
            state["batches"][0].update(
                {
                    "status": "prepared",
                    "active_rsu_ids": ["RSU-001"],
                }
            )
            state["rsus"][0]["generation_status"] = "prepared"
            foundation_input = output_dir / "foundation-input.md"
            foundation_input.write_text("# fixed foundation\n", encoding="utf-8")
            state["foundation"] = {
                "status": "validated",
                "thread_id": "saved-foundation-thread",
                "source_fingerprint_sha256": "fixed-source",
                "input_file": "foundation-input.md",
                "input_sha256": runner.file_sha256(foundation_input),
            }
            result_file = output_dir / "batch-results" / "BATCH-001" / "result.json"
            write_json(
                result_file,
                {
                    "schema_version": "rsu-test-point-generation/batch-result-v1",
                    "batch_id": "BATCH-001",
                    "status": "complete",
                    "rsus": [
                        {"rsu_id": "RSU-001", "status": "complete", "reason": ""}
                    ],
                    "notes": "",
                },
            )
            write_json(state_file, state)
            invoked: list[tuple[str, str | None]] = []
            validated_batches: list[str] = []

            def save_state(value: dict) -> None:
                write_json(state_file, value)

            def stage(_config, script_name: str, positional: tuple[str, ...]) -> str:
                value = json.loads(state_file.read_text(encoding="utf-8"))
                if script_name == "prepare_generation_plan.py":
                    return "STATUS=validated"
                if script_name == "prepare_next_batch.py":
                    return "STATUS=prepared"
                if script_name == "validate_batch_candidates.py":
                    batch_id = positional[-1]
                    validated_batches.append(batch_id)
                    value["batches"][0].update(
                        {"status": "validated", "active_rsu_ids": []}
                    )
                    value["rsus"][0]["generation_status"] = "validated"
                    save_state(value)
                    return "STATUS=validated"
                if script_name == "prepare_finalization.py":
                    value["finalization"] = {"status": "prepared"}
                    save_state(value)
                    return "STATUS=prepared"
                if script_name == "validate_module_test_points.py":
                    value["finalization"] = {"status": "validated"}
                    save_state(value)
                    return "STATUS=validated"
                if script_name == "prepare_case_readiness.py":
                    value["case_readiness"] = {"status": "prepared", "result": None}
                    save_state(value)
                    return "STATUS=prepared"
                if script_name == "validate_case_readiness.py":
                    value["case_readiness"] = {"status": "validated", "result": "ready"}
                    save_state(value)
                    return "STATUS=validated"
                self.fail(f"unexpected stage: {script_name}")

            def invoke(
                _config,
                run_dir: Path,
                turn_number: int,
                phase: str,
                _prompt: str,
                _label: str | None,
                parent_thread: str | None = None,
            ) -> runner.CodexTurnResult:
                invoked.append((phase, parent_thread))
                self.assertIn(phase, {"finalization", "case-readiness"})
                if phase == "finalization":
                    (output_dir / "module-test-points.md").write_text("# final\n", encoding="utf-8")
                    (output_dir / "coverage-matrix.md").write_text("# coverage\n", encoding="utf-8")
                else:
                    (output_dir / "test-case-readiness.md").write_text("# ready\n", encoding="utf-8")
                base = successful_turn(run_dir, turn_number, phase)
                return runner.CodexTurnResult(
                    **{**base.__dict__, "thread_id": f"{phase}-child"}
                )

            result = runner._run_pipeline(
                config,
                initialize_fn=lambda _config: state_file,
                invoke_fn=invoke,
                stage_fn=stage,
            )

            self.assertEqual(validated_batches, ["BATCH-001"])
            self.assertEqual(
                invoked,
                [
                    ("finalization", "saved-foundation-thread"),
                    ("case-readiness", "saved-foundation-thread"),
                ],
            )
            self.assertEqual(result.batch_turns, 0)
            events = [
                json.loads(line)
                for line in (result.run_dir / "runner-events.jsonl")
                .read_text(encoding="utf-8")
                .splitlines()
                if line.strip()
            ]
            self.assertTrue(any(item.get("event") == "foundation_session_reused" for item in events))


if __name__ == "__main__":
    unittest.main()
