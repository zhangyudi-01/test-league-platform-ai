from __future__ import annotations

import copy
import os
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from test_run_generation import config_for, initialized, read, runner, save, turn_result, write_state
import init_generation as initializer


class FoundationRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        home = patch.dict(os.environ, {"CODEX_HOME": str(self.root / "home")})
        home.start()
        self.addCleanup(home.stop)
        self.config = replace(config_for(self.root), retry_base_delay_seconds=0)
        self.state_file = self.config.module_dir / "test-cases" / "generation-state.json"
        write_state(self.state_file, planning="validated", sql="validated", batches=[
            {"batch_id": "BATCH-001", "mode": "simple", "tp_ids": ["TP-001"], "status": "pending"},
            {"batch_id": "BATCH-002", "mode": "simple", "tp_ids": ["TP-002"], "status": "pending"},
        ], tp_statuses=["pending", "pending"])
        self.calls = []

    def cache(self) -> dict:
        state = read(self.state_file)
        state["foundation_session"] = {
            "version": 1, "thread_id": "cached-parent",
            "fingerprint": runner._foundation_fingerprint(self.config, state),
            "created_at": "2026-10-14T00:00:00Z",
        }
        save(self.state_file, state)
        return state["foundation_session"]

    def stage(self, _config, name, _positional):
        state = read(self.state_file)
        if name == "prepare_next_batch.py":
            target = next(b for b in state["batches"] if b["status"] != "validated")
            target["status"] = "prepared"
            for tp in state["tps"]:
                if tp["tp_id"] in target["tp_ids"]:
                    tp["status"] = "prepared"
        elif name == "prepare_finalization.py":
            state["finalization"] = {"status": "prepared"}
        elif name == "validate_module_test_cases.py":
            state["finalization"] = {"status": "validated"}
        save(self.state_file, state)
        return ""

    def invoke(self, _config, run_dir, number, phase, _prompt, label, parent):
        self.calls.append((phase, label, parent))
        if phase == "batch":
            state = read(self.state_file)
            target = next(b for b in state["batches"] if b["batch_id"] == label)
            target["status"] = "validated"
            for tp in state["tps"]:
                if tp["tp_id"] in target["tp_ids"]:
                    tp["status"] = "validated"
            save(self.state_file, state)
        return turn_result(run_dir, number, phase)

    def run_pipeline(self, invoke=None, config=None):
        return runner.run_pipeline(
            config or self.config, lambda _cfg: initialized(self.state_file),
            invoke or self.invoke, self.stage,
        )

    def test_resume_reuses_persisted_parent_and_keeps_independent_forks(self):
        config = replace(self.config, max_batch_turns=1)
        with self.assertRaisesRegex(runner.AttentionRequired, "max batch"):
            self.run_pipeline(config=config)
        parent = read(self.state_file)["foundation_session"]
        result = self.run_pipeline(config=config)
        self.assertEqual([c[0] for c in self.calls], ["foundation", "batch", "batch"])
        self.assertEqual([c[2] for c in self.calls[1:]], [parent["thread_id"]] * 2)
        self.assertEqual(read(self.state_file)["foundation_session"], parent)
        self.assertEqual(result.codex_turns, 1)

    def test_missing_malformed_or_stale_record_builds_new_parent(self):
        for record in (None, "bad", {}, {"version": 9},
                       {"version": 1, "thread_id": "old", "fingerprint": "stale"}):
            with self.subTest(record=record):
                state = read(self.state_file)
                state["foundation_session"] = record
                for batch in state["batches"]:
                    batch["status"] = "pending"
                for tp in state["tps"]:
                    tp["status"] = "pending"
                state["finalization"] = {"status": "not-ready"}
                save(self.state_file, state)
                self.calls.clear()
                self.run_pipeline()
                self.assertEqual(self.calls[0][0], "foundation")
                self.assertEqual(read(self.state_file)["foundation_session"]["version"], 1)

    def test_isolated_mode_does_not_use_or_overwrite_cached_parent(self):
        cached = self.cache()
        self.run_pipeline(config=replace(self.config, session_mode="isolated"))
        self.assertEqual([c[0] for c in self.calls], ["batch", "batch"])
        self.assertTrue(all(c[2] is None for c in self.calls))
        self.assertEqual(read(self.state_file)["foundation_session"], cached)

    def test_unavailable_cached_parent_rebuilds_once_then_forks(self):
        self.cache()
        def invoke(*args):
            if args[-1] == "cached-parent":
                self.calls.append((args[3], args[5], args[-1]))
                return turn_result(args[1], args[2], args[3], code=1,
                                   message="no rollout found for cached-parent")
            return self.invoke(*args)
        self.run_pipeline(invoke)
        self.assertEqual([c[0] for c in self.calls], ["batch", "foundation", "batch", "batch"])
        self.assertEqual(self.calls[2][2], self.calls[3][2])
        self.assertNotEqual(read(self.state_file)["foundation_session"]["thread_id"], "cached-parent")

    def test_persistent_missing_parent_does_not_loop(self):
        self.cache()
        def invoke(*args):
            if args[3] == "foundation":
                return self.invoke(*args)
            self.calls.append((args[3], args[5], args[-1]))
            return turn_result(args[1], args[2], args[3], code=1,
                               message="parent session does not exist")
        with self.assertRaises(runner.RunnerError):
            self.run_pipeline(invoke)
        self.assertEqual([c[0] for c in self.calls], ["batch", "foundation", "batch"])

    def test_hard_provider_errors_override_transient_and_missing_parent_errors(self):
        errors = (
            "billing_error · insufficient balance; stream disconnected before completion",
            "account concurrency window is full; unexpected status 429",
            "The 'gpt-6.1-sol' model requires a newer version of Codex. stream disconnected",
            "insufficient_quota; no rollout found for cached-parent; unexpected status 429",
        )
        for error in errors:
            with self.subTest(error=error):
                cached = self.cache()
                self.calls.clear()
                def invoke(*args):
                    self.calls.append((args[3], args[5], args[-1]))
                    return turn_result(args[1], args[2], args[3], code=1, message=error)
                with self.assertRaises(runner.RunnerError):
                    self.run_pipeline(invoke)
                self.assertEqual(len(self.calls), 1)
                self.assertEqual(read(self.state_file)["foundation_session"], cached)

    def test_transient_errors_have_finite_retries_and_do_not_rebuild_parent(self):
        for error in ("502 Bad Gateway", "unexpected status 429"):
            with self.subTest(error=error):
                self.cache()
                self.calls.clear()
                def invoke(*args):
                    self.calls.append((args[3], args[5], args[-1]))
                    return turn_result(args[1], args[2], args[3], code=1, message=error)
                with self.assertRaises(runner.RunnerError):
                    self.run_pipeline(invoke, replace(self.config, max_transient_retries=2))
                self.assertEqual(len(self.calls), 3)
                self.assertTrue(all(c[2] == "cached-parent" for c in self.calls))

    def test_foundation_cannot_mutate_generation_state(self):
        def invoke(*args):
            state = read(self.state_file)
            state["unexpected"] = "mutation"
            save(self.state_file, state)
            return turn_result(args[1], args[2], args[3])
        with self.assertRaisesRegex(runner.RunnerError, "bootstrap changed"):
            self.run_pipeline(invoke)

    def test_batch_cannot_overwrite_foundation_record(self):
        self.cache()
        def invoke(*args):
            result = self.invoke(*args)
            state = read(self.state_file)
            state["foundation_session"]["thread_id"] = "polluted"
            save(self.state_file, state)
            return result
        with self.assertRaisesRegex(runner.RunnerError, "outside its authorized fields"):
            self.run_pipeline(invoke)

    def test_fingerprint_changes_for_runtime_options_and_source_binding(self):
        state = read(self.state_file)
        original = runner._foundation_fingerprint(self.config, state)
        variants = {
            "model": "another-model", "profile": "another-profile", "sandbox": "read-only",
            "reasoning_effort": "high", "codex_bin": str(self.root / "another.exe"),
            "workdir": self.root / "another-workdir", "case_output_dir": self.root / "other-output",
            "manifest": self.root / "manifest.json", "preanalysis_dir": self.root / "preanalysis",
            "module_dir": self.root / "another-module",
        }
        for key, value in variants.items():
            with self.subTest(option=key):
                self.assertNotEqual(original, runner._foundation_fingerprint(
                    replace(self.config, **{key: value}), state))
        changed = copy.deepcopy(state)
        changed["source_hashes"]["points"] = "changed"
        self.assertNotEqual(original, runner._foundation_fingerprint(self.config, changed))
        changed = copy.deepcopy(state)
        changed["updated_at"] = "later"
        changed["tps"][0]["status"] = "prepared"
        changed["foundation_session"] = {"thread_id": "ignored"}
        self.assertEqual(original, runner._foundation_fingerprint(self.config, changed))

    def test_fingerprint_tracks_rules_config_cli_and_provider_without_storing_secrets(self):
        skill = self.root / "mini-skill"
        skill.mkdir()
        entry = skill / "SKILL.md"
        entry.write_text("rules", encoding="utf-8")
        home = self.root / "home"
        home.mkdir()
        binary = self.root / "codex.exe"
        binary.write_bytes(b"cli-v1")
        config = replace(self.config, codex_bin=str(binary))
        state = read(self.state_file)
        with patch.object(runner, "SKILL_DIR", skill), patch.object(runner, "SKILL_FILE", entry):
            original = runner._foundation_fingerprint(config, state)
            for target in (entry, skill / "references" / "output-contract.md",
                           skill / "scripts" / "worker.py", skill / "assets" / "template.md",
                           home / "config.toml", home / "AGENTS.md", home / "instructions.md",
                           self.root / "AGENTS.override.md", self.root / ".codex" / "config.toml"):
                with self.subTest(file=target.name):
                    target.parent.mkdir(parents=True, exist_ok=True)
                    old = target.read_bytes() if target.exists() else None
                    target.write_bytes(b"changed")
                    self.assertNotEqual(original, runner._foundation_fingerprint(config, state))
                    if old is None:
                        target.unlink()
                    else:
                        target.write_bytes(old)
            binary.write_bytes(b"cli-v2-longer")
            self.assertNotEqual(original, runner._foundation_fingerprint(config, state))
            baseline = runner._foundation_fingerprint(config, state)
            with patch.dict(os.environ, {"OPENAI_API_KEY": "private-test-value"}):
                fingerprint = runner._foundation_fingerprint(config, state)
                self.assertNotEqual(baseline, fingerprint)
                runner._save_foundation(self.state_file, state, "parent", fingerprint)
                self.assertNotIn("private-test-value", self.state_file.read_text(encoding="utf-8"))

    def test_optional_empty_id_record_is_not_reused(self):
        self.cache()
        state = read(self.state_file)
        state["foundation_session"]["thread_id"] = "   "
        save(self.state_file, state)
        self.run_pipeline()
        self.assertEqual(self.calls[0][0], "foundation")

    def test_save_foundation_rejects_concurrent_state_change(self):
        before = read(self.state_file)
        changed = copy.deepcopy(before)
        changed["planning"]["status"] = "prepared"
        save(self.state_file, changed)
        with self.assertRaisesRegex(runner.RunnerError, "changed while recording"):
            runner._save_foundation(self.state_file, before, "parent", "fingerprint")
        self.assertNotIn("foundation_session", read(self.state_file))

    def test_prompt_requires_real_contracts_templates_and_bounded_revalidation(self):
        foundation = runner._foundation_prompt()
        for name in ("output-contract.md", "tp-worker-contract.md", "sql-assets.md"):
            self.assertIn(name, foundation)
        batch = runner._stage_prompt(self.config, "batch", "BATCH-001")
        for text in ("读取清单中每个 OUTPUT 模板", "<br>", "每条数据变量声明只含一个",
                     "必填单元格不得为空", "三列测试结果填未执行", "最多 2 轮修正重验",
                     "含首次共最多 3 次", "SQL资产/报告不一致", "不能直接把状态 JSON 改为 validated"):
            self.assertIn(text, batch)
        self.assertNotIn("只运行一次", batch)


class InitializerFoundationTests(unittest.TestCase):
    def test_unchanged_init_preserves_optional_fields_but_refresh_removes_them(self):
        for refresh in (False, True):
            with self.subTest(refresh=refresh), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                config = config_for(root)
                case_dir = config.module_dir / "test-cases"
                state_file = case_dir / "generation-state.json"
                write_state(state_file)
                state = read(state_file)
                cached = {"version": 1, "thread_id": "parent", "fingerprint": "hash"}
                state.update(foundation_session=cached, compatibility_field={"keep": True})
                save(state_file, state)
                (case_dir / "execution-context.md").write_text("ready", encoding="utf-8")
                (case_dir / "README.md").write_text("existing", encoding="utf-8")
                args = SimpleNamespace(module_dir=config.module_dir, preanalysis_dir=None,
                                       manifest=None, case_output_dir=None, refresh=refresh)
                model = SimpleNamespace(module_dir=config.module_dir,
                                        preanalysis_dir=config.module_dir / "preanalysis",
                                        manifest_path=None, module_name="test")
                point = SimpleNamespace(tp_id="TP-001", order=1)
                readiness = SimpleNamespace(tp_status={"TP-001": "ready"}, tp_ciq_refs={}, result="ready")
                with patch.object(initializer, "arguments", return_value=args), \
                     patch.object(initializer, "module_paths", return_value=(None, model, root / "points", case_dir)), \
                     patch.object(initializer, "run_preanalysis_validation"), \
                     patch.object(initializer, "load_final_test_points", return_value=([point], None, "p")), \
                     patch.object(initializer, "parse_case_readiness", return_value=readiness), \
                     patch.object(initializer, "sha256_file", return_value="r"), \
                     patch.object(initializer, "ensure_upstream_validation"), \
                     patch.object(initializer, "read_context", return_value=(None, "c", True)), \
                     patch.object(initializer, "source_hashes", return_value=state["source_hashes"]), \
                     patch.object(initializer, "archive_generated_artifacts") as archive:
                    self.assertEqual(initializer.main(), 0)
                result = read(state_file)
                if refresh:
                    archive.assert_called_once()
                    self.assertNotIn("foundation_session", result)
                    self.assertNotIn("compatibility_field", result)
                else:
                    archive.assert_not_called()
                    self.assertEqual(result["foundation_session"], cached)
                    self.assertEqual(result["compatibility_field"], {"keep": True})


if __name__ == "__main__":
    unittest.main()
