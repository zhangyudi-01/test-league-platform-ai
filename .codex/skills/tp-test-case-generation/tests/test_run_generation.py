from __future__ import annotations

import json
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import run_generation as runner  # noqa: E402


def config_for(root: Path, *, mode: str = "module-session") -> runner.RunnerConfig:
    module_dir = root / "module"
    case_dir = module_dir / "test-cases"
    case_dir.mkdir(parents=True, exist_ok=True)
    return runner.RunnerConfig(
        module_dir=module_dir.resolve(), manifest=None, preanalysis_dir=None,
        case_output_dir=None, workdir=root.resolve(), logs_dir=(root / "logs").resolve(),
        codex_bin="codex", model=None, profile=None, sandbox="workspace-write",
        max_batch_turns=None, session_mode=mode,
    )


def write_state(
    path: Path, *, planning: str = "pending", sql: str = "pending",
    batches: list[dict] | None = None, tp_statuses: list[str] | None = None,
    finalization: str = "not-ready", schema: str = runner.STATE_SCHEMA_VERSION,
) -> None:
    batches = batches or []
    count = sum(len(item["tp_ids"]) for item in batches) or len(tp_statuses or ["pending"])
    statuses = tp_statuses or ["pending"] * count
    data = {
        "schema_version": schema,
        "module_dir": path.parent.parent.as_posix(),
        "case_output_dir": path.parent.as_posix(),
        "readiness_result": "ready",
        "source_hashes": {"points": "p", "readiness": "r", "context": "c"},
        "created_at": "2026-09-10T00:00:00Z",
        "updated_at": "2026-09-10T00:00:00Z",
        "planning": {"status": planning},
        "sql_planning": {"status": sql},
        "batches": batches,
        "tps": [
            {
                "tp_id": f"TP-{index:03d}", "order": index,
                "readiness_status": "ready", "status": status,
                "planned_sql_refs": [], "blockers": [],
            }
            for index, status in enumerate(statuses, start=1)
        ],
        "finalization": {"status": finalization},
    }
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def save(path: Path, state: dict) -> None:
    state["updated_at"] = "2026-09-10T00:01:00Z"
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


def turn_result(
    run_dir: Path, number: int, phase: str, *, code: int = 0, message: str = "",
) -> runner.CodexTurnResult:
    base = run_dir / f"{number:03d}-{phase}"
    jsonl = base.with_suffix(".jsonl")
    stderr = base.with_suffix(".stderr.log")
    last = base.with_suffix(".last-message.md")
    jsonl.write_text(message, encoding="utf-8")
    stderr.write_text(message, encoding="utf-8")
    return runner.CodexTurnResult(
        code, jsonl, stderr, last, failure_evidence=message, thread_id=f"{phase}-{number}"
    )


def initialized(state_file: Path) -> runner.InitializationResult:
    return runner.InitializationResult(state_file, state_file.parent, True)


class RunnerConfigurationTests(unittest.TestCase):
    def test_runner_uses_batch_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = runner.parse_args(
                [str(root / "module"), "--workdir", str(root), "--max-tp-turns", "2"]
            )
        self.assertEqual(config.max_batch_turns, 2)
        self.assertEqual(config.max_tp_turns, 2)

    def test_codex_command_forks_and_never_resumes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            with patch.object(runner, "resolve_codex_binary", return_value="codex"):
                command = runner.codex_command(config, root / "last.md", (config.module_dir,), "base")
        self.assertEqual(command[-3:], ["fork", "base", "-"])
        self.assertNotIn("resume", command)

    def test_module_session_selects_a_fork_capable_cli(self) -> None:
        with patch.object(
            runner, "codex_binary_candidates", return_value=("old.exe", "desktop.exe")
        ), patch.object(
            runner, "codex_supports_exec_fork", side_effect=lambda value: value == "desktop.exe"
        ):
            selected = runner.select_codex_binary("codex", require_fork=True)
        self.assertEqual(selected, "desktop.exe")

    def test_prompts_encode_sql_first_and_concise_case_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = config_for(Path(temp))
            planning = runner._stage_prompt(config, "planning")
            sql = runner._stage_prompt(config, "sql")
            batch = runner._stage_prompt(config, "batch", "BATCH-001")
        self.assertIn("复杂度与 SQL 必要性独立判断", planning)
        self.assertIn("不得因引用 DC 就写 SQL", planning)
        self.assertIn("只实现计划中的 SELECT SQL", sql)
        self.assertIn("functional_module", planning)
        self.assertIn("原型功能区/需求功能模块组织", sql)
        self.assertIn("对批内每个TP单独判断用例数量", batch)
        self.assertNotIn("默认 1 TP = 1 TC", batch)
        self.assertIn("四项同时成立才拆分", batch)
        self.assertIn("简单前置填无或一句关键条件", batch)
        self.assertIn("步骤和预期从 1. 连续编号", batch)
        self.assertIn("查询预期简洁写", batch)
        self.assertIn("不生成 DML", batch)
        self.assertIn("不得使用当前 TP、来源场景", batch)

    def test_v2_state_cannot_enter_the_new_runner(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = config_for(Path(temp))
            state_file = config.module_dir / "test-cases" / "generation-state.json"
            write_state(state_file, schema="tp-test-case-generation/v2")
            with self.assertRaisesRegex(runner.RunnerError, "--refresh"):
                runner.load_state(state_file)

    def test_early_v3_state_without_batch_scheduler_cannot_enter(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = config_for(Path(temp))
            state_file = config.module_dir / "test-cases" / "generation-state.json"
            write_state(state_file)
            state = read(state_file)
            for key in ("planning", "sql_planning", "batches"):
                state.pop(key)
            save(state_file, state)
            with self.assertRaisesRegex(runner.RunnerError, "legacy generation state"):
                runner.load_state(state_file)


class RunnerPipelineTests(unittest.TestCase):
    def test_module_session_runs_plan_sql_first_batches_and_deterministic_finalization(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            state_file = config.module_dir / "test-cases" / "generation-state.json"
            write_state(state_file, tp_statuses=["pending", "pending"])
            calls: list[tuple[str, str | None, str | None]] = []

            def stage(_config, name, _positional):
                state = read(state_file)
                if name == "prepare_generation_plan.py":
                    state["planning"] = {"status": "prepared"}
                elif name == "prepare_sql_generation.py":
                    state["sql_planning"] = {"status": "prepared"}
                elif name == "prepare_next_batch.py":
                    batch = next(item for item in state["batches"] if item["status"] != "validated")
                    batch["status"] = "prepared"
                    for tp_id in batch["tp_ids"]:
                        state["tps"][int(tp_id[-3:]) - 1]["status"] = "prepared"
                elif name == "prepare_finalization.py":
                    state["finalization"] = {"status": "prepared"}
                elif name == "validate_module_test_cases.py":
                    state["finalization"] = {"status": "validated"}
                save(state_file, state)
                return ""

            def invoke(_config, run_dir, number, phase, _prompt, label, parent):
                calls.append((phase, label, parent))
                state = read(state_file)
                if phase == "planning":
                    state["planning"] = {"status": "validated"}
                    state["sql_planning"] = {"status": "pending"}
                    state["batches"] = [{
                        "batch_id": "BATCH-001", "mode": "simple",
                        "tp_ids": ["TP-001", "TP-002"], "status": "pending",
                    }]
                    state["finalization"] = {"status": "not-ready"}
                elif phase == "sql":
                    state["sql_planning"] = {"status": "validated"}
                elif phase == "batch":
                    state["batches"][0].update({"status": "validated", "case_count": 2})
                    for item in state["tps"]:
                        item.update({"status": "validated", "case_count": 1, "output_sha256": item["tp_id"]})
                save(state_file, state)
                return turn_result(run_dir, number, phase)

            pipeline = runner.run_pipeline(
                config, lambda _cfg: initialized(state_file), invoke, stage
            )
        self.assertEqual(pipeline.batch_turns, 1)
        self.assertEqual([item[0] for item in calls], ["foundation", "planning", "sql", "batch"])
        self.assertTrue(all(parent == "foundation-1" for _, _, parent in calls[1:]))

    def test_no_sql_plan_skips_sql_codex_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root, mode="isolated")
            state_file = config.module_dir / "test-cases" / "generation-state.json"
            batches = [{"batch_id": "BATCH-001", "mode": "simple", "tp_ids": ["TP-001"], "status": "pending"}]
            write_state(state_file, planning="validated", sql="pending", batches=batches)
            phases: list[str] = []

            def stage(_config, name, _positional):
                state = read(state_file)
                if name == "prepare_sql_generation.py":
                    state["sql_planning"] = {"status": "validated", "sql_count": 0}
                elif name == "prepare_next_batch.py":
                    state["batches"][0]["status"] = "prepared"
                    state["tps"][0]["status"] = "prepared"
                elif name == "prepare_finalization.py":
                    state["finalization"] = {"status": "prepared"}
                elif name == "validate_module_test_cases.py":
                    state["finalization"] = {"status": "validated"}
                save(state_file, state)
                return ""

            def invoke(_config, run_dir, number, phase, _prompt, _label, _parent):
                phases.append(phase)
                state = read(state_file)
                if phase == "batch":
                    state["batches"][0]["status"] = "validated"
                    state["tps"][0]["status"] = "validated"
                save(state_file, state)
                return turn_result(run_dir, number, phase)

            runner.run_pipeline(config, lambda _cfg: initialized(state_file), invoke, stage)
        self.assertEqual(phases, ["batch"])

    def test_completed_pipeline_starts_no_codex_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            state_file = config.module_dir / "test-cases" / "generation-state.json"
            batches = [{"batch_id": "BATCH-001", "mode": "simple", "tp_ids": ["TP-001"], "status": "validated"}]
            write_state(
                state_file, planning="validated", sql="validated", batches=batches,
                tp_statuses=["validated"], finalization="validated",
            )
            pipeline = runner.run_pipeline(
                config, lambda _cfg: initialized(state_file),
                lambda *_args: self.fail("Codex must not start"),
                lambda *_args: self.fail("stage script must not run"),
            )
        self.assertEqual(pipeline.codex_turns, 0)

    def test_batch_cannot_change_a_sibling_tp(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root, mode="isolated")
            state_file = config.module_dir / "test-cases" / "generation-state.json"
            batches = [
                {"batch_id": "BATCH-001", "mode": "simple", "tp_ids": ["TP-001"], "status": "pending"},
                {"batch_id": "BATCH-002", "mode": "simple", "tp_ids": ["TP-002"], "status": "pending"},
            ]
            write_state(state_file, planning="validated", sql="validated", batches=batches, tp_statuses=["pending", "pending"])

            def stage(_config, name, _positional):
                state = read(state_file)
                if name == "prepare_next_batch.py":
                    state["batches"][0]["status"] = "prepared"
                    state["tps"][0]["status"] = "prepared"
                save(state_file, state)
                return ""

            def invoke(_config, run_dir, number, phase, _prompt, _label, _parent):
                state = read(state_file)
                state["batches"][0]["status"] = "validated"
                state["tps"][0]["status"] = "validated"
                state["tps"][1]["blockers"] = ["polluted"]
                save(state_file, state)
                return turn_result(run_dir, number, phase)

            with self.assertRaisesRegex(runner.RunnerError, "outside the batch"):
                runner.run_pipeline(config, lambda _cfg: initialized(state_file), invoke, stage)

    def test_transient_retry_uses_same_foundation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = replace(config_for(root), retry_base_delay_seconds=0)
            state_file = config.module_dir / "test-cases" / "generation-state.json"
            batches = [{"batch_id": "BATCH-001", "mode": "simple", "tp_ids": ["TP-001"], "status": "pending"}]
            write_state(state_file, planning="validated", sql="validated", batches=batches)
            parents: list[str | None] = []

            def stage(_config, name, _positional):
                state = read(state_file)
                if name == "prepare_next_batch.py":
                    state["batches"][0]["status"] = "prepared"
                    state["tps"][0]["status"] = "prepared"
                elif name == "prepare_finalization.py":
                    state["finalization"] = {"status": "prepared"}
                elif name == "validate_module_test_cases.py":
                    state["finalization"] = {"status": "validated"}
                save(state_file, state)
                return ""

            attempts = 0
            def invoke(_config, run_dir, number, phase, _prompt, _label, parent):
                nonlocal attempts
                if phase == "batch":
                    attempts += 1
                    parents.append(parent)
                    if attempts == 1:
                        return turn_result(run_dir, number, phase, code=1, message="503 Service Unavailable")
                    state = read(state_file)
                    state["batches"][0]["status"] = "validated"
                    state["tps"][0]["status"] = "validated"
                    save(state_file, state)
                return turn_result(run_dir, number, phase)

            runner.run_pipeline(config, lambda _cfg: initialized(state_file), invoke, stage)
        self.assertEqual(attempts, 2)
        self.assertEqual(parents[0], parents[1])


if __name__ == "__main__":
    unittest.main()
