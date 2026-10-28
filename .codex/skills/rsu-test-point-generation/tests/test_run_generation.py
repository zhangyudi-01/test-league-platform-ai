from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import run_generation as runner  # noqa: E402


def write_state(path: Path, statuses: list[tuple[str, str]], *, readiness_result=None) -> None:
    data = {
        "schema_version": 3,
        "module_dir": path.parent.parent.as_posix(),
        "preanalysis_dir": (path.parent.parent / "preanalysis").as_posix(),
        "manifest_path": None,
        "manifest_sha256": None,
        "output_dir": path.parent.as_posix(),
        "created_at": "2026-01-01T00:00:00Z",
        "updated_at": "2026-01-01T00:00:00Z",
        "finalization": {"status": "not-ready"},
        "case_readiness": {"status": "not-ready", "result": readiness_result},
        "rsus": [
            {
                "rsu_id": rsu_id,
                "generation_status": status,
                "blockers": ["Q-001 is pending"] if status == "blocked" else [],
            }
            for rsu_id, status in statuses
        ],
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def config_for(root: Path) -> runner.RunnerConfig:
    module_dir = root / "module"
    module_dir.mkdir(parents=True, exist_ok=True)
    return runner.RunnerConfig(
        module_dir=module_dir,
        manifest=None,
        preanalysis_dir=None,
        output_dir=None,
        workdir=root,
        logs_dir=root / "logs",
        codex_bin="codex",
        model=None,
        profile=None,
        sandbox="workspace-write",
        max_rsu_turns=None,
    )


def successful_turn(run_dir: Path, turn_number: int, phase: str) -> runner.CodexTurnResult:
    prefix = run_dir / f"{turn_number:03d}-{phase}"
    return runner.CodexTurnResult(0, prefix.with_suffix(".jsonl"), prefix.with_suffix(".stderr"), prefix.with_suffix(".md"))


def failed_turn(
    run_dir: Path,
    turn_number: int,
    phase: str,
    message: str,
) -> runner.CodexTurnResult:
    prefix = run_dir / f"{turn_number:03d}-{phase}"
    jsonl = prefix.with_suffix(".jsonl")
    stderr = prefix.with_suffix(".stderr")
    last_message = prefix.with_suffix(".md")
    jsonl.write_text(
        json.dumps({"type": "turn.failed", "message": message}) + "\n",
        encoding="utf-8",
    )
    stderr.write_text(message + "\n", encoding="utf-8")
    return runner.CodexTurnResult(1, jsonl, stderr, last_message)


class RunnerPipelineTests(unittest.TestCase):
    def test_cli_help_renders_windows_temp_default_without_format_error(self) -> None:
        completed = subprocess.run(
            [sys.executable, str(SCRIPT_DIR / "run_generation.py"), "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("--global-lock-dir", completed.stdout)
        self.assertIn("--pipeline-architecture", completed.stdout)
        self.assertIn("%TEMP%/codex-rsu-runner-slots/<workdir-hash>", completed.stdout)

    def test_cli_defaults_to_module_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            config = runner.parse_args([temp, "--workdir", temp])

            self.assertEqual(config.pipeline_architecture, "module-baseline")

    def test_pipeline_architecture_routes_foundation_and_isolated_manual_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            base = config_for(root)
            sentinel = object()
            with patch.object(runner, "_run_pipeline", return_value=sentinel) as v2, patch.object(
                runner, "_run_pipeline_legacy", return_value=sentinel
            ) as legacy:
                self.assertIs(
                    runner.run_pipeline(
                        replace(base, pipeline_architecture="foundation-fork")
                    ),
                    sentinel,
                )
                v2.assert_called_once()
                legacy.assert_not_called()

            with patch.object(runner, "_run_pipeline", return_value=sentinel) as v2, patch.object(
                runner, "_run_pipeline_legacy", return_value=sentinel
            ) as legacy:
                self.assertIs(
                    runner.run_pipeline(
                        replace(base, session_mode="isolated")
                    ),
                    sentinel,
                )
                legacy.assert_called_once()
                v2.assert_not_called()

    def test_removed_legacy_architecture_is_rejected_by_argparse(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "run_generation.py"),
                    temp,
                    "--workdir",
                    temp,
                    "--pipeline-architecture",
                    "legacy-resume",
                ],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("invalid choice", completed.stderr)

    def test_runner_reconfigures_windows_stdio_as_utf8(self) -> None:
        stdout = type("Stream", (), {"reconfigure": lambda self, **kwargs: setattr(self, "options", kwargs)})()
        stderr = type("Stream", (), {"reconfigure": lambda self, **kwargs: setattr(self, "options", kwargs)})()

        with patch.object(runner.sys, "stdout", stdout), patch.object(runner.sys, "stderr", stderr):
            runner.configure_process_stdio()

        self.assertEqual(stdout.options, {"encoding": "utf-8", "errors": "replace"})
        self.assertEqual(stderr.options, {"encoding": "utf-8", "errors": "replace"})

    def test_codex_command_uses_workspace_approval_review(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            with patch.object(runner, "resolve_codex_binary", return_value="codex"):
                command = runner.codex_command(
                    config,
                    root / "last.md",
                    (config.module_dir,),
                )

            self.assertIn("--approve-for-me", command)
            self.assertNotIn("--sandbox", command)
            self.assertNotIn("--ephemeral", command)
            self.assertNotIn("resume", command)
            self.assertEqual(command[-1], "-")

    def test_codex_command_forks_from_the_recorded_foundation_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            session_id = "01a06149-3cbd-7913-9f16-d7a0ebd380ed"
            with patch.object(runner, "resolve_codex_binary", return_value="codex"):
                command = runner.codex_command(
                    config,
                    root / "last.md",
                    (config.module_dir,),
                    session_id,
                )

            self.assertEqual(command[-3:], ["fork", session_id, "-"])
            self.assertNotIn("resume", command)

    def test_codex_command_passes_semantic_output_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            schema = root / "semantic.schema.json"
            schema.write_text("{}", encoding="utf-8")
            with patch.object(runner, "resolve_codex_binary", return_value="codex"):
                command = runner.codex_command(
                    config,
                    root / "last.md",
                    (config.module_dir,),
                    output_schema=schema,
                )

            index = command.index("--output-schema")
            self.assertEqual(Path(command[index + 1]), schema.resolve())
            self.assertEqual(command[-1], "-")

    def test_session_modes_and_refresh_interval_are_configurable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module_dir = root / "module"
            default_config = runner.parse_args([str(module_dir), "--workdir", str(root)])
            isolated_config = runner.parse_args(
                [
                    str(module_dir),
                    "--workdir",
                    str(root),
                    "--session-mode",
                    "isolated",
                    "--context-refresh-interval",
                    "0",
                ]
            )

            self.assertEqual(default_config.session_mode, "module-session")
            self.assertEqual(
                default_config.context_refresh_interval,
                runner.DEFAULT_CONTEXT_REFRESH_INTERVAL,
            )
            self.assertEqual(isolated_config.session_mode, "isolated")
            self.assertEqual(isolated_config.context_refresh_interval, 0)
            self.assertEqual(default_config.max_transient_retries, 6)
            self.assertEqual(default_config.global_concurrency, 3)
            self.assertEqual(default_config.max_validation_repairs, 2)
            self.assertEqual(default_config.session_recovery, "fresh-session")

    def test_watchdog_terminates_a_silent_codex_process(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "run"
            run_dir.mkdir()
            config = replace(
                config_for(root),
                session_mode="isolated",
                stage_timeout_seconds=2,
                stall_timeout_seconds=0.15,
                heartbeat_interval_seconds=0.03,
            )
            command = [sys.executable, "-c", "import time; time.sleep(5)"]
            with patch.object(runner, "codex_command", return_value=command):
                telemetry = runner.RunTelemetry(run_dir)
                result = runner.invoke_codex(
                    config,
                    run_dir,
                    1,
                    "rsu",
                    "prompt",
                    "RSU-001",
                    telemetry=telemetry,
                )

            self.assertEqual(result.termination_reason, "stall-timeout")
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("runner.watchdog", result.jsonl_log.read_text(encoding="utf-8"))
            events = [
                json.loads(line)
                for line in telemetry.path.read_text(encoding="utf-8").splitlines()
            ]
            watchdog_events = [event for event in events if event["event"] == "watchdog_terminated"]
            self.assertEqual(len(watchdog_events), 1)
            self.assertEqual(watchdog_events[0]["reason"], "stall-timeout")

    def test_repeated_action_detector_terminates_a_looping_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            run_dir = root / "run"
            run_dir.mkdir()
            config = replace(
                config_for(root),
                session_mode="isolated",
                repeated_action_limit=3,
                stage_timeout_seconds=2,
                stall_timeout_seconds=1,
                heartbeat_interval_seconds=0.03,
            )
            event = json.dumps(
                {
                    "type": "item.started",
                    "item": {"type": "command_execution", "command": "same-command"},
                }
            )
            script = (
                "import time\n"
                f"event={event!r}\n"
                "for _ in range(4): print(event, flush=True)\n"
                "time.sleep(5)\n"
            )
            with patch.object(runner, "codex_command", return_value=[sys.executable, "-c", script]):
                result = runner.invoke_codex(
                    config,
                    run_dir,
                    1,
                    "rsu",
                    "prompt",
                    "RSU-001",
                )

            self.assertEqual(result.termination_reason, "repeated-action")

    def test_global_concurrency_wait_is_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "slots"
            directory.mkdir()
            holder = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(2)"])
            slot = directory / "slot-000.json"
            slot.write_text(
                json.dumps({"pid": holder.pid, "phase": "rsu", "turn": 1}),
                encoding="utf-8",
            )
            try:
                second = runner.GlobalConcurrency(directory, 1, 0.05, 0.01)
                with self.assertRaisesRegex(runner.AttentionRequired, "wait timed out"):
                    with second.slot("rsu", 2):
                        self.fail("second coordinator must not acquire the occupied slot")
            finally:
                holder.terminate()
                holder.wait(timeout=5)

    def test_dead_global_slot_is_reclaimed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp) / "slots"
            directory.mkdir()
            stale = directory / "slot-000.json"
            stale.write_text(json.dumps({"pid": 99999999}), encoding="utf-8")
            coordinator = runner.GlobalConcurrency(directory, 1, 0.1, 0.01)
            with patch.object(runner, "process_is_alive", return_value=False):
                with coordinator.slot("rsu", 1):
                    self.assertTrue(stale.exists())
            self.assertFalse(stale.exists())

    def test_dead_module_lock_is_reclaimed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp) / "test-points"
            output_dir.mkdir()
            lock = output_dir / ".generation-runner.lock"
            lock.write_text("pid=99999999 created_at=2026-09-05T00:00:00Z\n", encoding="utf-8")
            with patch.object(runner, "process_is_alive", return_value=False):
                with runner.RunnerLock(output_dir):
                    self.assertTrue(lock.exists())
                    self.assertIn(f"pid={os.getpid()}", lock.read_text(encoding="utf-8"))
            self.assertFalse(lock.exists())

    def test_old_module_lock_owner_cannot_remove_replaced_lock(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp) / "test-points"
            output_dir.mkdir()
            old = runner.RunnerLock(output_dir)
            old.__enter__()
            old_details = old.path.read_text(encoding="utf-8")
            replacement = "pid=987654 created_at=2026-09-05T00:00:00Z owner_token=new-owner\n"
            old.path.write_text(replacement, encoding="utf-8")
            old.__exit__(None, None, None)
            self.assertEqual(old.path.read_text(encoding="utf-8"), replacement)

    def test_live_module_lock_is_not_stolen(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            output_dir = Path(temp) / "test-points"
            output_dir.mkdir()
            lock = output_dir / ".generation-runner.lock"
            lock.write_text("pid=1234 created_at=2026-09-05T00:00:00Z\n", encoding="utf-8")
            with patch.object(runner, "process_is_alive", return_value=True):
                with self.assertRaisesRegex(runner.AttentionRequired, "another runner may be active"):
                    with runner.RunnerLock(output_dir):
                        pass

    def test_module_session_refreshes_first_and_periodic_rsus(self) -> None:
        session = runner.CodexSession("module-session")
        self.assertTrue(session.should_refresh_context(5, "pending"))
        session.validated_rsus = 1
        self.assertFalse(session.should_refresh_context(5, "pending"))
        self.assertFalse(session.should_refresh_context(5, "stale"))
        session.validated_rsus = 5
        self.assertTrue(session.should_refresh_context(5, "pending"))
        session.validated_rsus = 6
        self.assertFalse(session.should_refresh_context(0, "pending"))
        self.assertTrue(runner.CodexSession("isolated").should_refresh_context(0, "pending"))

    def test_transient_error_classifier_covers_provider_network_variants(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            cases = [
                "provider connection failed",
                "DNS resolution failed",
                "TLS handshake failed",
                "unexpected status 524",
                "522 connection timed out",
                "供应商连接失败，请稍后重试",
                "连接供应商超时",
                "网络连接异常",
                "流式中断",
                "unexpected status 403 Forbidden",
                "供应商额度不足",
            ]
            for index, message in enumerate(cases):
                result = failed_turn(root, index + 1, "rsu", message)
                if "403" in message or "额度不足" in message:
                    self.assertFalse(runner.is_transient_codex_failure(result), message)
                else:
                    self.assertTrue(runner.is_transient_codex_failure(result), message)

    def test_retry_after_is_honored_without_shortening_exponential_backoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = failed_turn(root, 1, "rsu", "429 Too Many Requests\nRetry-After: 45")
            self.assertEqual(runner.retry_after_seconds(result), 45.0)
            for hint, expected in (
                ('"retry_after": 45', 45.0),
                ("retry_after_seconds=120", 120.0),
                ("retry-after: 7", 7.0),
            ):
                hinted = failed_turn(root, 2, "rsu", hint)
                self.assertEqual(runner.retry_after_seconds(hinted), expected)

    def test_windows_process_tree_cleanup_does_not_taskkill_after_wrapper_exits(self) -> None:
        class FakeProcess:
            pid = 4321
            returncode = 0

            def __init__(self) -> None:
                self.running = True
                self.terminated = False

            def poll(self):
                return None if self.running else self.returncode

            def terminate(self) -> None:
                self.terminated = True
                self.running = False

            def wait(self, timeout=None) -> int:
                return self.returncode

            def kill(self) -> None:
                self.running = False

        process = FakeProcess()
        with patch.object(runner.os, "name", "nt"), patch.object(
            runner.shutil, "which", return_value="taskkill"
        ), patch.object(runner.subprocess, "run") as taskkill:
            runner.terminate_process_tree(process, graceful_timeout_seconds=0)
        taskkill.assert_not_called()

    def test_windows_process_tree_cleanup_runs_taskkill_while_wrapper_is_still_alive(self) -> None:
        class StuckProcess:
            pid = 4321

            def __init__(self) -> None:
                self.running = True

            def poll(self):
                return None if self.running else 1

            def terminate(self) -> None:
                # Simulate a wrapper that ignores graceful termination while a
                # child process remains active.
                pass

            def wait(self, timeout=None) -> int:
                raise runner.subprocess.TimeoutExpired("codex", timeout)

            def kill(self) -> None:
                self.running = False

        process = StuckProcess()
        with patch.object(runner.os, "name", "nt"), patch.object(
            runner.shutil, "which", return_value="taskkill"
        ), patch.object(runner.subprocess, "run") as taskkill:
            runner.terminate_process_tree(process, graceful_timeout_seconds=0)
        taskkill.assert_called_once()
        self.assertEqual(
            taskkill.call_args.args[0],
            ["taskkill", "/PID", "4321", "/T", "/F"],
        )

    def test_rsu_prompt_pins_module_and_exact_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            prompt = runner.build_prompt(config, "rsu", "RSU-001")

            self.assertIn(str(config.module_dir), prompt)
            self.assertIn("禁止扫描、选择、读取或处理其他模块", prompt)
            self.assertIn("prepare_next_rsu.py", prompt)
            self.assertIn("validate_rsu_test_points.py", prompt)
            self.assertIn("SESSION_CONTEXT_POLICY=refresh-current-rsu-full", prompt)

            reuse_prompt = runner.build_prompt(
                config,
                "rsu",
                "RSU-002",
                force_context_refresh=False,
                source_fingerprint_sha256="fixed-source-digest",
            )
            self.assertIn(
                "SESSION_CONTEXT_POLICY=module-session-incremental-current-rsu",
                reuse_prompt,
            )
            self.assertIn("SESSION_INPUT", reuse_prompt)
            self.assertIn(
                "EXPECTED_SESSION_SOURCE_FINGERPRINT_SHA256=fixed-source-digest",
                reuse_prompt,
            )
            self.assertIn("上下文可能被摘要/压缩", reuse_prompt)

            isolated_prompt = runner.build_prompt(
                replace(config, session_mode="isolated"),
                "rsu",
                "RSU-001",
                force_context_refresh=False,
            )
            self.assertIn("SESSION_CONTEXT_POLICY=isolated-full", isolated_prompt)

    def test_initializer_forces_utf8_for_windows_child_processes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending")])

            completed = type(
                "Completed",
                (),
                {"returncode": 0, "stdout": f"STATE_FILE={state_file}\n", "stderr": ""},
            )()
            with patch.object(runner.subprocess, "run", return_value=completed) as mocked:
                resolved = runner.initialize_generation(config)

            self.assertEqual(resolved, state_file.resolve())
            self.assertEqual(mocked.call_args.kwargs["env"]["PYTHONUTF8"], "1")

    def test_full_pipeline_advances_one_rsu_per_turn_and_separates_phases(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending"), ("RSU-002", "pending")])
            phases: list[tuple[str, str | None]] = []
            context_policies: list[str] = []

            def initialize(_config):
                return state_file

            def invoke(_config, run_dir, turn_number, phase, prompt, rsu_id):
                self.assertIn("$rsu-test-point-generation", prompt)
                phases.append((phase, rsu_id))
                if phase == "rsu":
                    marker = next(
                        line for line in prompt.splitlines()
                        if line.startswith("SESSION_CONTEXT_POLICY=")
                    )
                    context_policies.append(marker)
                data = json.loads(state_file.read_text(encoding="utf-8"))
                if phase == "rsu":
                    current = next(item for item in data["rsus"] if item["rsu_id"] == rsu_id)
                    current["generation_status"] = "validated"
                elif phase == "finalization":
                    data["finalization"]["status"] = "validated"
                elif phase == "case-readiness":
                    data["case_readiness"] = {"status": "validated", "result": "ready"}
                state_file.write_text(json.dumps(data), encoding="utf-8")
                return successful_turn(run_dir, turn_number, phase)

            result = runner._run_pipeline_legacy(config, initialize, invoke)

            self.assertEqual(
                phases,
                [
                    ("rsu", "RSU-001"),
                    ("rsu", "RSU-002"),
                    ("finalization", None),
                    ("case-readiness", None),
                ],
            )
            self.assertEqual(result.rsu_turns, 2)
            self.assertEqual(result.codex_turns, 4)
            self.assertEqual(result.case_readiness_result, "ready")
            self.assertEqual(
                context_policies,
                [
                    "SESSION_CONTEXT_POLICY=refresh-current-rsu-full",
                    "SESSION_CONTEXT_POLICY=module-session-incremental-current-rsu",
                ],
            )
            events = [
                json.loads(line)
                for line in (result.run_dir / "runner-events.jsonl").read_text(encoding="utf-8").splitlines()
            ]
            terminal = [
                event for event in events
                if event["event"] in {
                    "pipeline_completed",
                    "pipeline_attention",
                    "pipeline_failed",
                    "pipeline_interrupted",
                }
            ]
            self.assertEqual(len(terminal), 1)
            self.assertEqual(terminal[0]["event"], "pipeline_completed")

    def test_default_pipeline_passes_one_session_to_every_codex_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending"), ("RSU-002", "pending")])
            observed_session_ids: list[str | None] = []

            def invoke(
                _config,
                run_dir,
                turn_number,
                phase,
                _prompt,
                rsu_id,
                *,
                session,
            ):
                observed_session_ids.append(session.thread_id)
                if session.thread_id is None:
                    self.assertIsNone(session.observe_thread("shared-session-id"))
                data = json.loads(state_file.read_text(encoding="utf-8"))
                if phase == "rsu":
                    current = next(item for item in data["rsus"] if item["rsu_id"] == rsu_id)
                    current["generation_status"] = "validated"
                elif phase == "finalization":
                    data["finalization"]["status"] = "validated"
                else:
                    data["case_readiness"] = {"status": "validated", "result": "ready"}
                state_file.write_text(json.dumps(data), encoding="utf-8")
                return successful_turn(run_dir, turn_number, phase)

            with patch.object(runner, "invoke_codex", side_effect=invoke):
                result = runner._run_pipeline_legacy(config, lambda _config: state_file)

            self.assertEqual(
                observed_session_ids,
                [None, "shared-session-id", "shared-session-id", "shared-session-id"],
            )
            self.assertEqual(result.case_readiness_result, "ready")

    def test_transient_provider_failure_retries_the_same_rsu(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = replace(
                config_for(root),
                max_transient_retries=2,
                retry_base_delay_seconds=0,
            )
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending")])
            calls: list[tuple[int, str, str | None]] = []

            def invoke(_config, run_dir, turn_number, phase, _prompt, rsu_id):
                calls.append((turn_number, phase, rsu_id))
                if phase == "rsu" and len(calls) == 1:
                    return failed_turn(
                        run_dir,
                        turn_number,
                        phase,
                        "unexpected status 503 Service Unavailable",
                    )
                data = json.loads(state_file.read_text(encoding="utf-8"))
                if phase == "rsu":
                    data["rsus"][0]["generation_status"] = "validated"
                elif phase == "finalization":
                    data["finalization"]["status"] = "validated"
                else:
                    data["case_readiness"] = {"status": "validated", "result": "ready"}
                state_file.write_text(json.dumps(data), encoding="utf-8")
                return successful_turn(run_dir, turn_number, phase)

            result = runner._run_pipeline_legacy(config, lambda _config: state_file, invoke)

            self.assertEqual(
                calls,
                [
                    (1, "rsu", "RSU-001"),
                    (2, "rsu", "RSU-001"),
                    (3, "finalization", None),
                    (4, "case-readiness", None),
                ],
            )
            self.assertEqual(result.rsu_turns, 1)
            self.assertEqual(result.codex_turns, 4)

    def test_session_resume_failure_starts_a_fresh_module_session(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = replace(
                config_for(root),
                retry_base_delay_seconds=0,
                session_reset_after=99,
                session_recovery="fresh-session",
            )
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending")])
            run_dir = root / "run"
            run_dir.mkdir()
            before = runner.load_state(state_file)[1]
            session = runner.CodexSession("module-session", thread_id="old-session")
            observed_ids: list[str | None] = []
            observed_prompts: list[str] = []

            def invoke(_config, invoke_dir, turn_number, phase, prompt, _rsu_id):
                observed_ids.append(session.thread_id)
                observed_prompts.append(prompt)
                if len(observed_ids) == 1:
                    return failed_turn(
                        invoke_dir,
                        turn_number,
                        phase,
                        "unexpected status 503 Service Unavailable; session old-session not found",
                    )
                data = json.loads(state_file.read_text(encoding="utf-8"))
                data["rsus"][0]["generation_status"] = "validated"
                state_file.write_text(json.dumps(data), encoding="utf-8")
                session.observe_thread("new-session")
                return successful_turn(invoke_dir, turn_number, phase)

            result, after, attempts = runner.invoke_phase_with_retries(
                config,
                run_dir,
                state_file,
                1,
                "rsu",
                "original prompt",
                "RSU-001",
                before,
                invoke,
                session=session,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(after.next_rsu, None)
            self.assertEqual(attempts, 2)
            self.assertEqual(observed_ids, ["old-session", None])
            self.assertIn("SESSION_RECOVERY_OVERRIDE=module-session", observed_prompts[1])
            self.assertEqual(session.recovery_count, 1)
            self.assertEqual(session.thread_id, "new-session")

    def test_repeated_module_session_failures_reset_before_retry_budget_exhaustion(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = replace(
                config_for(root),
                retry_base_delay_seconds=0,
                session_reset_after=2,
                max_transient_retries=3,
            )
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending")])
            run_dir = root / "run"
            run_dir.mkdir()
            before = runner.load_state(state_file)[1]
            session = runner.CodexSession("module-session", thread_id="old-session")
            observed_ids: list[str | None] = []

            def invoke(_config, invoke_dir, turn_number, phase, _prompt, _rsu_id):
                observed_ids.append(session.thread_id)
                if len(observed_ids) < 3:
                    return failed_turn(
                        invoke_dir,
                        turn_number,
                        phase,
                        "unexpected status 503 Service Unavailable",
                    )
                data = json.loads(state_file.read_text(encoding="utf-8"))
                data["rsus"][0]["generation_status"] = "validated"
                state_file.write_text(json.dumps(data), encoding="utf-8")
                session.observe_thread("fresh-session")
                return successful_turn(invoke_dir, turn_number, phase)

            _result, after, attempts = runner.invoke_phase_with_retries(
                config,
                run_dir,
                state_file,
                1,
                "rsu",
                "original prompt",
                "RSU-001",
                before,
                invoke,
                session=session,
            )

            self.assertEqual(after.next_rsu, None)
            self.assertEqual(attempts, 3)
            self.assertEqual(observed_ids, ["old-session", "old-session", None])
            self.assertEqual(session.recovery_count, 1)

    def test_deterministic_validation_failure_gets_a_bounded_repair_turn(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = replace(
                config_for(root),
                retry_base_delay_seconds=0,
                max_validation_repairs=1,
            )
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending")])
            run_dir = root / "run"
            run_dir.mkdir()
            before = runner.load_state(state_file)[1]
            prompts: list[str] = []

            def invoke(_config, invoke_dir, turn_number, phase, prompt, _rsu_id):
                prompts.append(prompt)
                if len(prompts) == 1:
                    return failed_turn(
                        invoke_dir,
                        turn_number,
                        phase,
                        "ERROR: Context Refs mismatch; deterministic validation failed",
                    )
                data = json.loads(state_file.read_text(encoding="utf-8"))
                data["rsus"][0]["generation_status"] = "validated"
                state_file.write_text(json.dumps(data), encoding="utf-8")
                return successful_turn(invoke_dir, turn_number, phase)

            _result, after, attempts = runner.invoke_phase_with_retries(
                config,
                run_dir,
                state_file,
                1,
                "rsu",
                "original prompt",
                "RSU-001",
                before,
                invoke,
            )

            self.assertEqual(after.next_rsu, None)
            self.assertEqual(attempts, 2)
            self.assertIn("VALIDATION_REPAIR_MODE=deterministic-only", prompts[1])

    def test_blocked_or_upstream_gap_is_never_classified_as_repairable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for index, message in enumerate(
                (
                    "ERROR: validation failed: blocked-input requires human confirmation",
                    "ERROR: validation failed: upstream-gap requires upstream repair",
                ),
                start=1,
            ):
                result = failed_turn(root, index, "rsu", message)
                self.assertFalse(runner.is_repairable_validation_failure(result))

    def test_nontransient_failure_does_not_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = replace(config_for(root), retry_base_delay_seconds=0)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending")])
            calls = 0

            def invoke(_config, run_dir, turn_number, phase, _prompt, _rsu_id):
                nonlocal calls
                calls += 1
                return failed_turn(
                    run_dir,
                    turn_number,
                    phase,
                    "candidate validation failed",
                )

            with self.assertRaisesRegex(runner.RunnerError, "exited with code 1"):
                runner._run_pipeline_legacy(config, lambda _config: state_file, invoke)

            self.assertEqual(calls, 1)

    def test_provider_quota_failure_takes_precedence_over_earlier_503(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = replace(config_for(root), retry_base_delay_seconds=0)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending")])
            calls = 0

            def invoke(_config, run_dir, turn_number, phase, _prompt, _rsu_id):
                nonlocal calls
                calls += 1
                return failed_turn(
                    run_dir,
                    turn_number,
                    phase,
                    "unexpected status 503 Service Unavailable: 所有供应商已熔断\n"
                    "upstream_status: HTTP 403; cause: 用户额度不足, 剩余额度: ¥-0.01",
                )

            with self.assertRaisesRegex(runner.RunnerError, "exited with code 1"):
                runner._run_pipeline_legacy(config, lambda _config: state_file, invoke)

            self.assertEqual(calls, 1)

    def test_nonzero_exit_after_state_completion_is_not_retried(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = replace(config_for(root), retry_base_delay_seconds=0)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending")])
            rsu_calls = 0

            def invoke(_config, run_dir, turn_number, phase, _prompt, _rsu_id):
                nonlocal rsu_calls
                data = json.loads(state_file.read_text(encoding="utf-8"))
                if phase == "rsu":
                    rsu_calls += 1
                    data["rsus"][0]["generation_status"] = "validated"
                    state_file.write_text(json.dumps(data), encoding="utf-8")
                    return failed_turn(
                        run_dir,
                        turn_number,
                        phase,
                        "unexpected status 503 Service Unavailable",
                    )
                if phase == "finalization":
                    data["finalization"]["status"] = "validated"
                else:
                    data["case_readiness"] = {"status": "validated", "result": "ready"}
                state_file.write_text(json.dumps(data), encoding="utf-8")
                return successful_turn(run_dir, turn_number, phase)

            result = runner._run_pipeline_legacy(config, lambda _config: state_file, invoke)

            self.assertEqual(rsu_calls, 1)
            self.assertEqual(result.codex_turns, 3)

    def test_blocked_rsu_stops_before_invoking_codex(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "blocked")])

            def invoke(*_args):
                self.fail("Codex must not run for a blocked RSU")

            with patch.object(
                runner,
                "_run_pipeline",
                side_effect=lambda cfg, init, inv, _stage: runner._run_pipeline_legacy(cfg, init, inv),
            ):
                with self.assertRaisesRegex(runner.AttentionRequired, "Q-001 is pending"):
                    runner.run_pipeline(config, lambda _config: state_file, invoke)

            event_files = list((root / "logs").rglob("runner-events.jsonl"))
            self.assertEqual(len(event_files), 1)
            events = [
                json.loads(line)
                for line in event_files[0].read_text(encoding="utf-8").splitlines()
            ]
            terminal = [
                event for event in events
                if event["event"] in {
                    "pipeline_completed",
                    "pipeline_attention",
                    "pipeline_failed",
                    "pipeline_interrupted",
                }
            ]
            self.assertEqual(len(terminal), 1)
            self.assertEqual(terminal[0]["event"], "pipeline_attention")
            self.assertIn("Q-001 is pending", terminal[0]["error"])

    def test_runner_error_writes_pipeline_failed_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending")])

            def invoke(_config, run_dir, turn_number, phase, _prompt, _rsu_id):
                return failed_turn(run_dir, turn_number, phase, "ordinary non-transient failure")

            with patch.object(
                runner,
                "_run_pipeline",
                side_effect=lambda cfg, init, inv, _stage: runner._run_pipeline_legacy(cfg, init, inv),
            ):
                with self.assertRaisesRegex(runner.RunnerError, "exited with code 1"):
                    runner.run_pipeline(config, lambda _config: state_file, invoke)

            event_files = list((root / "logs").rglob("runner-events.jsonl"))
            self.assertEqual(len(event_files), 1)
            events = [
                json.loads(line)
                for line in event_files[0].read_text(encoding="utf-8").splitlines()
            ]
            terminal = [
                event for event in events
                if event["event"] in {
                    "pipeline_completed",
                    "pipeline_attention",
                    "pipeline_failed",
                    "pipeline_interrupted",
                }
            ]
            self.assertEqual(len(terminal), 1)
            self.assertEqual(terminal[0]["event"], "pipeline_failed")
            self.assertEqual(terminal[0]["error_type"], "RunnerError")

    def test_unexpected_exception_writes_pipeline_failed_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending")])

            def invoke(*_args):
                raise ValueError("simulated implementation failure")

            with patch.object(
                runner,
                "_run_pipeline",
                side_effect=lambda cfg, init, inv, _stage: runner._run_pipeline_legacy(cfg, init, inv),
            ):
                with self.assertRaisesRegex(ValueError, "simulated implementation failure"):
                    runner.run_pipeline(config, lambda _config: state_file, invoke)

            event_files = list((root / "logs").rglob("runner-events.jsonl"))
            self.assertEqual(len(event_files), 1)
            events = [
                json.loads(line)
                for line in event_files[0].read_text(encoding="utf-8").splitlines()
            ]
            terminal = [
                event for event in events
                if event["event"] in {
                    "pipeline_completed",
                    "pipeline_attention",
                    "pipeline_failed",
                    "pipeline_interrupted",
                }
            ]
            self.assertEqual(len(terminal), 1)
            self.assertEqual(terminal[0]["event"], "pipeline_failed")
            self.assertEqual(terminal[0]["error_type"], "ValueError")
            self.assertTrue(terminal[0]["unexpected"])

    def test_startup_failure_writes_a_dedicated_telemetry_record(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)

            def initialize(_config):
                raise runner.RunnerError("simulated initialization failure")

            with self.assertRaisesRegex(runner.RunnerError, "simulated initialization failure"):
                runner.run_pipeline(config, initialize)

            event_files = list((root / "logs" / "startup-failures").rglob("runner-events.jsonl"))
            self.assertEqual(len(event_files), 1)
            events = [
                json.loads(line)
                for line in event_files[0].read_text(encoding="utf-8").splitlines()
            ]
            self.assertEqual(len(events), 1)
            self.assertEqual(events[0]["event"], "pipeline_failed")
            self.assertTrue(events[0]["startup"])
            self.assertEqual(events[0]["error_type"], "RunnerError")

    def test_keyboard_interrupt_writes_pipeline_interrupted_telemetry(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending")])

            def invoke(*_args):
                raise KeyboardInterrupt

            with patch.object(
                runner,
                "_run_pipeline",
                side_effect=lambda cfg, init, inv, _stage: runner._run_pipeline_legacy(cfg, init, inv),
            ):
                with self.assertRaises(KeyboardInterrupt):
                    runner.run_pipeline(config, lambda _config: state_file, invoke)

            event_files = list((root / "logs").rglob("runner-events.jsonl"))
            self.assertEqual(len(event_files), 1)
            events = [
                json.loads(line)
                for line in event_files[0].read_text(encoding="utf-8").splitlines()
            ]
            terminal = [
                event for event in events
                if event["event"] in {
                    "pipeline_completed",
                    "pipeline_attention",
                    "pipeline_failed",
                    "pipeline_interrupted",
                }
            ]
            self.assertEqual(len(terminal), 1)
            self.assertEqual(terminal[0]["event"], "pipeline_interrupted")
            self.assertEqual(terminal[0]["error_type"], "KeyboardInterrupt")

    def test_successful_codex_exit_without_state_progress_stops(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "pending")])

            def invoke(_config, run_dir, turn_number, phase, _prompt, _rsu_id):
                return successful_turn(run_dir, turn_number, phase)

            with self.assertRaisesRegex(runner.AttentionRequired, "without validating RSU-001"):
                runner._run_pipeline_legacy(config, lambda _config: state_file, invoke)

    def test_prepared_rsu_can_be_recovered_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "prepared")])

            def invoke(_config, run_dir, turn_number, phase, _prompt, rsu_id):
                data = json.loads(state_file.read_text(encoding="utf-8"))
                if phase == "rsu":
                    data["rsus"][0]["generation_status"] = "validated"
                elif phase == "finalization":
                    data["finalization"]["status"] = "validated"
                else:
                    data["case_readiness"] = {"status": "validated", "result": "ready"}
                state_file.write_text(json.dumps(data), encoding="utf-8")
                return successful_turn(run_dir, turn_number, phase)

            result = runner._run_pipeline_legacy(config, lambda _config: state_file, invoke)
            self.assertEqual(result.rsu_turns, 1)

    def test_ready_review_is_not_enough_when_result_requires_follow_up(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            state_file = config.module_dir / "test-points" / "generation-state.json"
            write_state(state_file, [("RSU-001", "validated")])
            data = json.loads(state_file.read_text(encoding="utf-8"))
            data["finalization"]["status"] = "validated"
            data["case_readiness"] = {"status": "validated", "result": "blocked-input"}
            state_file.write_text(json.dumps(data), encoding="utf-8")

            with self.assertRaisesRegex(runner.AttentionRequired, "blocked-input"):
                runner._run_pipeline_legacy(config, lambda _config: state_file, lambda *_args: self.fail())


if __name__ == "__main__":
    unittest.main()
