from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import run_generation as runner  # noqa: E402


def config_for(root: Path, *, session_mode: str = "module-session") -> runner.RunnerConfig:
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
    )


class FoundationForkRunnerTests(unittest.TestCase):
    def test_default_codex_prefers_desktop_configured_cli_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            configured = Path(temp) / "codex.exe"
            configured.write_bytes(b"stub")
            with patch.dict(runner.os.environ, {"CODEX_CLI_PATH": str(configured)}, clear=False), patch.object(
                runner.shutil, "which", return_value="path-codex"
            ):
                self.assertEqual(
                    runner.resolve_codex_binary("codex"), str(configured.resolve())
                )

    def test_explicit_codex_name_without_configured_path_uses_path(self) -> None:
        with patch.dict(runner.os.environ, {"CODEX_CLI_PATH": "", "LOCALAPPDATA": ""}, clear=False), patch.object(
            runner.shutil, "which", return_value="path-codex"
        ):
            with patch.object(runner.Path, "home", return_value=Path(tempfile.gettempdir())):
                self.assertEqual(runner.resolve_codex_binary("codex"), "path-codex")

    def test_default_codex_discovers_versioned_desktop_install_when_env_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            appdata = Path(temp) / "AppData"
            old = appdata / "OpenAI" / "Codex" / "bin" / "old" / "codex.exe"
            latest = appdata / "OpenAI" / "Codex" / "bin" / "latest" / "codex.exe"
            old.parent.mkdir(parents=True)
            latest.parent.mkdir(parents=True)
            old.write_bytes(b"old")
            latest.write_bytes(b"latest")
            with patch.dict(
                runner.os.environ,
                {"CODEX_CLI_PATH": "", "LOCALAPPDATA": str(appdata)},
                clear=False,
            ), patch.object(runner.shutil, "which", return_value="path-codex"), patch.object(
                runner.Path, "home", return_value=Path(tempfile.gettempdir())
            ):
                latest.touch()
                self.assertEqual(runner.resolve_codex_binary("codex"), str(latest.resolve()))

    def test_foundation_is_new_and_all_other_stages_fork_same_parent(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            output = config.output_dir
            assert output is not None

            foundation = runner.codex_command(config, root / "foundation.md", ())
            planning = runner.codex_command(
                config, root / "planning.md", (), "foundation-thread"
            )
            batch = runner.codex_command(
                config,
                root / "batch.md",
                (output / "batch-results" / "BATCH-001",),
                "foundation-thread",
                execution_workdir=output / "batches" / "BATCH-001",
            )
            finalization = runner.codex_command(
                config, root / "finalization.md", (), "foundation-thread"
            )
            readiness = runner.codex_command(
                config, root / "readiness.md", (), "foundation-thread"
            )

            self.assertNotIn("fork", foundation)
            for command in (planning, batch, finalization, readiness):
                self.assertNotIn("resume", command)
                fork_index = command.index("fork")
                self.assertEqual(command[fork_index + 1], "foundation-thread")
                self.assertLess(command.index("--cd"), fork_index)
                self.assertLess(command.index("--output-last-message"), fork_index)
            self.assertEqual(
                Path(batch[batch.index("--cd") + 1]),
                (output / "batches" / "BATCH-001").resolve(),
            )

    def test_batch_prompt_contains_only_batch_identity_not_sibling_content(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            config = config_for(root)
            output = config.output_dir
            assert output is not None
            prompt_1 = runner.build_stage_prompt_v2(config, output, "batch", batch_id="BATCH-001")
            prompt_2 = runner.build_stage_prompt_v2(config, output, "batch", batch_id="BATCH-002")

            self.assertIn("BATCH-001-input.md", prompt_1)
            self.assertNotIn("BATCH-002-input.md", prompt_1)
            self.assertIn("BATCH-002-input.md", prompt_2)
            self.assertNotIn("BATCH-001-input.md", prompt_2)
            self.assertNotIn("runner-logs", prompt_1.split("不得读取 runner-logs")[0])

    def test_module_session_uses_stage_delta_but_isolated_uses_full_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "module" / "test-points"
            output.mkdir(parents=True)
            for filename in (
                "finalization-input.md",
                "finalization-session-input.md",
                "case-readiness-input.md",
                "case-readiness-session-input.md",
            ):
                (output / filename).write_text(filename, encoding="utf-8")

            module_config = config_for(root)
            isolated_config = config_for(root, session_mode="isolated")
            module_final = runner.build_stage_prompt_v2(module_config, output, "finalization")
            isolated_final = runner.build_stage_prompt_v2(isolated_config, output, "finalization")
            module_readiness = runner.build_stage_prompt_v2(module_config, output, "case-readiness")
            isolated_readiness = runner.build_stage_prompt_v2(isolated_config, output, "case-readiness")

            self.assertIn("finalization-session-input.md", module_final)
            self.assertIn("finalization-input.md", isolated_final)
            self.assertNotIn("finalization-session-input.md", isolated_final)
            self.assertIn("case-readiness-session-input.md", module_readiness)
            self.assertIn("case-readiness-input.md", isolated_readiness)
            self.assertNotIn("case-readiness-session-input.md", isolated_readiness)

    def test_module_session_requires_fork_but_isolated_does_not(self) -> None:
        completed = subprocess.CompletedProcess(["codex"], 0, "Usage: codex exec\n", "")
        with patch.object(runner, "resolve_codex_binary", return_value="codex"), patch.object(
            runner.subprocess, "run", return_value=completed
        ):
            with self.assertRaisesRegex(runner.RunnerError, "requires `codex exec fork`"):
                runner.select_codex_binary("codex", require_fork=True)
            self.assertEqual(runner.select_codex_binary("codex", require_fork=False), "codex")

    def test_supported_cli_layout_is_recognized(self) -> None:
        completed = subprocess.CompletedProcess(
            ["codex"], 0, "Usage: codex exec fork [OPTIONS] <SESSION_ID> [PROMPT]", ""
        )
        with patch.object(runner.subprocess, "run", return_value=completed):
            self.assertTrue(runner.codex_supports_exec_fork("codex"))

    def test_parent_rolls_back_worker_state_write_before_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            state_path = Path(temp) / "generation-state.json"
            original = {"schema_version": 4, "case_readiness": {"status": "prepared"}}
            state_path.write_text(
                json.dumps(original, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            before = state_path.read_bytes()
            state_path.write_text(
                json.dumps({**original, "case_readiness": {"status": "validated"}}),
                encoding="utf-8",
            )

            self.assertTrue(
                runner.restore_parent_state_if_modified(state_path, before, "case-readiness")
            )
            self.assertEqual(json.loads(state_path.read_text(encoding="utf-8")), original)
            self.assertFalse(
                runner.restore_parent_state_if_modified(
                    state_path, state_path.read_bytes(), "case-readiness"
                )
            )


if __name__ == "__main__":
    unittest.main()
