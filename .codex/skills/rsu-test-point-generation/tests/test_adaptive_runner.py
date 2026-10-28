from __future__ import annotations

import json
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from adaptive_validation import (  # noqa: E402
    BASELINE_SCHEMA,
    FORK_SCHEMA,
    complexity_risk_signals,
    duplicate_candidate_ids,
    merge_dispositions,
    validate_baseline_manifest,
    validate_fork_manifest,
)
from adaptive_runner import (  # noqa: E402
    _baseline_validation_repair_prompt,
    _load_reusable_baseline,
    _invoke_semantic_worker,
    _merge_adaptive_metrics,
    _render_baseline_input,
)
from common import WorkflowError, ensure_adaptive_state  # noqa: E402


class AdaptiveValidationTests(unittest.TestCase):
    def test_reusable_baseline_is_rejected_when_baseline_authorization_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "baseline.json"
            path.write_text('{"rsus": [], "candidates": []}', encoding="utf-8")
            fingerprints = {"packet_sha256": "a" * 64}
            state = {
                "status": "validated",
                "packet_sha256": fingerprints["packet_sha256"],
                "semantic_result_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            authorizations = {"RSU-006": {"allowed_context_ids": {"SRC-MOD"}}}

            with patch(
                "adaptive_runner.validate_semantic_baseline_result",
                side_effect=WorkflowError(
                    "candidate TP-COMPLEX-001-05 references context outside its materialized input"
                ),
            ) as validate:
                result = _load_reusable_baseline(
                    path, state, fingerprints, SimpleNamespace(), authorizations
                )

            self.assertIsNone(result)
            self.assertEqual(
                validate.call_args.kwargs["rsu_authorizations"], authorizations
            )

    def test_reusable_baseline_requires_matching_result_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "baseline.json"
            path.write_text('{"rsus": [], "candidates": []}', encoding="utf-8")
            with patch("adaptive_runner.validate_semantic_baseline_result") as validate:
                result = _load_reusable_baseline(
                    path,
                    {
                        "status": "validated",
                        "packet_sha256": "a" * 64,
                        "semantic_result_sha256": "0" * 64,
                    },
                    {"packet_sha256": "a" * 64},
                    SimpleNamespace(),
                    {},
                )

            self.assertIsNone(result)
            validate.assert_not_called()

    def test_valid_reusable_baseline_is_validated_with_its_packet_and_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "baseline.json"
            path.write_text('{"rsus": [], "candidates": []}', encoding="utf-8")
            fingerprints = {"packet_sha256": "a" * 64}
            state = {
                "status": "validated",
                "packet_sha256": fingerprints["packet_sha256"],
                "semantic_result_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            }
            expected = {"schema": "test", "rsus": [], "candidates": []}
            with patch("adaptive_runner.load_semantic_result", return_value=expected), patch(
                "adaptive_runner.validate_semantic_baseline_result"
            ) as validate:
                result = _load_reusable_baseline(
                    path, state, fingerprints, SimpleNamespace(), {"RSU-001": {}}
                )

            self.assertEqual(result, expected)
            validate.assert_called_once_with(
                expected,
                unittest.mock.ANY,
                fingerprints["packet_sha256"],
                require_pre_generation_routing=True,
                baseline_only=False,
                rsu_authorizations={"RSU-001": {}},
            )

    def test_baseline_repair_prompt_is_bounded_to_contract_correction(self) -> None:
        model = SimpleNamespace(
            fixed_resource_ids=("SRC-GLOBAL", "SRC-MOD", "CTX"),
            data_closure_ids=("DC-001",),
            resources={
                "SRC-GLOBAL": object(), "SRC-MOD": object(), "CTX": object(),
                "FC-001": object(), "DC-001": object(),
            },
            questions={"Q-001": object()},
        )
        semantic = {"schema": "example", "context_dispositions": []}

        prompt = _baseline_validation_repair_prompt(
            semantic,
            WorkflowError("context disposition coverage is incomplete"),
            model,
            "a" * 64,
        )

        self.assertIn("Return the complete corrected JSON only", prompt)
        self.assertIn('"resource_id": "FC-001"', prompt)
        self.assertIn('"resource_type": "data-closure"', prompt)
        self.assertIn('"resource_id": "Q-001"', prompt)
        self.assertIn("context disposition coverage is incomplete", prompt)

    def test_baseline_input_materializes_only_bundle_dependencies_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module_source = root / "module.md"
            question_source = root / "questions.md"
            giant_evidence = root / "giant-db.md"
            manifest = root / "preanalysis-manifest.json"
            module_source.write_text("MODULE_BODY_SENTINEL\n", encoding="utf-8")
            question_source.write_text("question index\n", encoding="utf-8")
            giant_evidence.write_text("GIANT_UNRELATED_BODY\n" * 200, encoding="utf-8")
            manifest.write_text("{}\n", encoding="utf-8")

            rsu = SimpleNamespace(
                rsu_id="RSU-001",
                cells=(
                    "RSU-001",
                    "none",
                    "requirement",
                    "SRC-MOD",
                    "section 1",
                    "FC-001",
                    "Q-001",
                    "captured",
                ),
            )
            question = SimpleNamespace(
                q_id="Q-001",
                headers=("问题 ID", "答案"),
                cells=("Q-001", "QUESTION_BODY_SENTINEL"),
            )
            bundle = SimpleNamespace(
                fixed_materials=[SimpleNamespace(
                    resource_id="SRC-MOD",
                    path=module_source,
                    role="fixed",
                    content="MODULE_BODY_SENTINEL\n",
                )],
                dynamic_materials=[],
                evidence_materials=[SimpleNamespace(path=giant_evidence)],
                questions=[question],
            )
            model = SimpleNamespace(
                module_name="sample",
                module_dir=root,
                manifest_path=manifest,
                artifact_paths={
                    "00-module-requirement-pack.md": module_source,
                    "03-clarification-questions.md": question_source,
                },
                resources={
                    "SRC-MOD": SimpleNamespace(
                        path=module_source,
                        purpose="module requirement",
                    ),
                    "SRC-DB-MAIN": SimpleNamespace(
                        path=giant_evidence,
                        purpose="database evidence",
                    ),
                },
                rsus=[rsu],
            )

            text = _render_baseline_input(
                model,
                {},
                root / "test-points",
                {"RSU-001": bundle},
            )

            self.assertEqual(text.count("MODULE_BODY_SENTINEL"), 1)
            self.assertEqual(text.count("QUESTION_BODY_SENTINEL"), 1)
            self.assertNotIn("GIANT_UNRELATED_BODY", text)
            self.assertEqual(text.count("module.md"), 1)
            self.assertEqual(text.count("giant-db.md"), 1)
            self.assertIn("证据索引，不展开", text)

    def test_baseline_requires_map_order_and_every_rsu(self) -> None:
        payload = {
            "schema": BASELINE_SCHEMA,
            "input_sha256": "a" * 64,
            "rsus": [
                {"rsu_id": "RSU-001", "status": "generated", "candidate_ids": ["C-1"]},
                {"rsu_id": "RSU-002", "status": "zero-test-points", "candidate_ids": [], "reason": "covered by RSU-001"},
            ],
        }
        rows = validate_baseline_manifest(payload, ["RSU-001", "RSU-002"], "a" * 64)
        self.assertEqual(rows["RSU-002"]["status"], "zero-test-points")
        with self.assertRaises(Exception):
            validate_baseline_manifest(payload, ["RSU-002", "RSU-001"], "a" * 64)

    def test_fork_scope_is_fingerprinted(self) -> None:
        payload = {
            "schema": FORK_SCHEMA,
            "input_sha256": "b" * 64,
            "rsu_id": "RSU-001",
            "status": "generated",
        }
        self.assertEqual(validate_fork_manifest(payload, "RSU-001", "b" * 64)["status"], "generated")
        with self.assertRaises(Exception):
            validate_fork_manifest(payload, "RSU-002", "b" * 64)

    def test_duplicate_candidate_ids_are_deterministic(self) -> None:
        self.assertEqual(duplicate_candidate_ids([["C-1"], ["C-2"], ["C-1"]]), {"C-1"})

    def test_adaptive_state_preserves_legacy_fields(self) -> None:
        state = {"schema_version": 4, "legacy_field": {"keep": True}}
        ensure_adaptive_state(state)
        self.assertEqual(state["legacy_field"], {"keep": True})
        self.assertEqual(state["architecture"], "module-baseline")
        self.assertIn("completion", state["adaptive"])

    def test_resume_keeps_original_generation_metrics(self) -> None:
        generated = {
            "duration_seconds": 120.5,
            "baseline_turns": 1,
            "tool_calls": 8,
            "usage": {"input_tokens": 1000},
        }
        resumed = {
            "duration_seconds": 2.5,
            "baseline_turns": 0,
            "tool_calls": 0,
            "usage": {},
        }

        merged = _merge_adaptive_metrics(generated, resumed, reused=True)

        self.assertEqual(merged["duration_seconds"], 120.5)
        self.assertEqual(merged["tool_calls"], 8)
        self.assertEqual(merged["usage"], {"input_tokens": 1000})
        self.assertEqual(merged["last_resume"], resumed)
        self.assertEqual(merged["resume_history"], [resumed])
        self.assertNotIn("resume_history", generated)

    def test_semantic_worker_rejects_any_child_tool_call(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            schema = root / "schema.json"
            schema.write_text("{}", encoding="utf-8")

            def fake_invoke(config, run_dir, turn_number, phase, prompt, scope_id, **kwargs):
                return SimpleNamespace(returncode=0, tool_calls=1)

            with self.assertRaisesRegex(WorkflowError, "zero-tool contract"):
                _invoke_semantic_worker(
                    SimpleNamespace(), root, 1, "baseline-worker", "INLINE_PACKET",
                    None, schema, fake_invoke,
                )

    def test_semantic_worker_passes_inline_packet_and_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            schema = root / "schema.json"
            schema.write_text("{}", encoding="utf-8")
            observed = {}

            def fake_invoke(config, run_dir, turn_number, phase, prompt, scope_id, **kwargs):
                observed.update(prompt=prompt, output_schema=kwargs.get("output_schema"))
                return SimpleNamespace(returncode=0, tool_calls=0)

            result = _invoke_semantic_worker(
                SimpleNamespace(), root, 1, "baseline-worker", "INLINE_PACKET",
                None, schema, fake_invoke,
            )

            self.assertEqual(result.returncode, 0)
            self.assertEqual(observed["prompt"], "INLINE_PACKET")
            self.assertEqual(observed["output_schema"], schema)

    def test_invalid_status_is_rejected_without_partial_acceptance(self) -> None:
        payload = {
            "schema": BASELINE_SCHEMA,
            "input_sha256": "c" * 64,
            "rsus": [
                {"rsu_id": "RSU-001", "status": "needs-fork", "candidate_ids": []},
            ],
        }
        with self.assertRaises(Exception):
            validate_baseline_manifest(payload, ["RSU-001"], "c" * 64)

    def test_generated_and_zero_candidate_dispositions_are_consistent(self) -> None:
        generated_without_ids = {
            "schema": BASELINE_SCHEMA,
            "input_sha256": "c" * 64,
            "rsus": [{"rsu_id": "RSU-001", "status": "generated", "candidate_ids": []}],
        }
        with self.assertRaises(Exception):
            validate_baseline_manifest(generated_without_ids, ["RSU-001"], "c" * 64)

        zero_with_ids = {
            "schema": BASELINE_SCHEMA,
            "input_sha256": "c" * 64,
            "rsus": [{
                "rsu_id": "RSU-001",
                "status": "zero-test-points",
                "candidate_ids": ["CAND-RSU-001-001"],
                "reason": "该行为已由其他候选完整覆盖",
            }],
        }
        with self.assertRaises(Exception):
            validate_baseline_manifest(zero_with_ids, ["RSU-001"], "c" * 64)

    def test_fork_result_must_resolve_scope(self) -> None:
        payload = {
            "schema": FORK_SCHEMA,
            "input_sha256": "d" * 64,
            "rsu_id": "RSU-001",
            "status": "blocked",
        }
        with self.assertRaises(Exception):
            validate_fork_manifest(payload, "RSU-001", "d" * 64)

    def test_fork_merge_rejects_out_of_scope_and_conflict(self) -> None:
        base = {"RSU-001": {"status": "needs-fork", "candidate_ids": []}}
        merged = merge_dispositions(base, {"RSU-001": {"status": "generated", "candidate_ids": ["C-1"]}}, ["RSU-001"])
        self.assertEqual(merged["RSU-001"]["status"], "generated")
        with self.assertRaises(Exception):
            merge_dispositions(base, {"RSU-002": {"status": "generated", "candidate_ids": []}}, ["RSU-001"])

    def test_complexity_signals_capture_external_polling_lifecycle(self) -> None:
        signals = complexity_risk_signals(
            "调用 IN15 推送第三方审计，自动轮询 IN17，达到最大次数后查询超时并允许重试"
        )
        self.assertEqual(
            signals,
            {"external-submit", "async-poll", "timeout-boundary", "retry-recovery"},
        )

    def test_simple_static_status_display_has_no_complexity_signal(self) -> None:
        self.assertEqual(complexity_risk_signals("已结束任务仅显示查看按钮"), set())

    def test_complexity_signals_capture_concurrency_and_locking(self) -> None:
        self.assertEqual(
            complexity_risk_signals("重复提交时使用锁机制保证幂等"),
            {"concurrency-idempotency"},
        )

    def test_complexity_signals_capture_state_transition(self) -> None:
        self.assertEqual(
            complexity_risk_signals("轮询成功后执行状态迁移"),
            {"async-poll", "state-transition"},
        )


if __name__ == "__main__":
    unittest.main()
