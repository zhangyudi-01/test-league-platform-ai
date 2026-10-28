from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from adaptive_worker import (  # noqa: E402
    DEFAULT_PACKET_BUDGET_BYTES,
    SEMANTIC_BASELINE_SCHEMA,
    COMPLEX_GENERATION_SCHEMA,
    build_deterministic_final_intents,
    compile_baseline_worker_packet,
    compile_complex_generation_packet,
    detect_complex_generation_scopes,
    merge_complex_generation_result,
    normalize_complex_scope_dispositions,
    required_context_dispositions,
    render_candidate_artifacts,
    render_final_artifacts,
    semantic_baseline_json_schema,
    complex_generation_json_schema,
    validate_semantic_baseline_result,
    validate_complex_generation_result,
    worker_prompt,
)
from adaptive_runner import _complex_scope_authorizations  # noqa: E402
from common import WorkflowError, sha256_text  # noqa: E402


class FakeRsu:
    def __init__(self, rsu_id: str, parent: str, source: str, context: str, order: int) -> None:
        self.rsu_id = rsu_id
        self.cells = (rsu_id, parent, source, "SRC-MOD", f"section {order}", context, "无", "已确认")
        self.order = order

    @property
    def parent_text(self) -> str:
        return self.cells[1]

    @property
    def source_text(self) -> str:
        return self.cells[2]

    @property
    def source_id(self) -> str:
        return self.cells[3]

    @property
    def source_location(self) -> str:
        return self.cells[4]

    @property
    def related_context(self) -> str:
        return self.cells[5]

    @property
    def related_questions(self) -> str:
        return self.cells[6]

    @property
    def source_status(self) -> str:
        return self.cells[7]


def make_model(root: Path, rsus: list[FakeRsu]) -> SimpleNamespace:
    source = root / "module.md"
    source.write_text("module requirement", encoding="utf-8")
    resources = {}
    for resource_id in ("SRC-GLOBAL", "SRC-MOD", "CTX"):
        path = root / f"{resource_id}.md"
        path.write_text(resource_id, encoding="utf-8")
        resources[resource_id] = SimpleNamespace(path=path, purpose=resource_id)
    return SimpleNamespace(
        module_name="sample",
        module_dir=root,
        preanalysis_dir=root,
        map_path=source,
        manifest_path=None,
        manifest_sha256=None,
        artifact_paths={"module": source},
        resource_roles={
            "project_context": "SRC-GLOBAL",
            "module_requirement": "SRC-MOD",
            "context_pack": "CTX",
        },
        resources=resources,
        fixed_resource_ids=("SRC-GLOBAL", "SRC-MOD", "CTX"),
        data_closure_ids=(),
        data_closure_enabled=False,
        questions={},
        rsus=rsus,
        rsu_by_id={rsu.rsu_id: rsu for rsu in rsus},
    )


def candidate(key: str, rsu_id: str, text: str, *, contexts: list[str] | None = None) -> dict:
    return {
        "key": key,
        "primary_rsu": rsu_id,
        "source_rsus": [rsu_id],
        "test_item": "业务规则",
        "test_point": text,
        "remarks": "",
        "question_refs": [],
        "context_refs": contexts or ["SRC-GLOBAL", "SRC-MOD", "CTX"],
        "data_closure_refs": [],
        "derivation": "来自当前 RSU",
    }


def baseline_result(rsus: list[FakeRsu], candidates: list[dict], packet_hash: str) -> dict:
    by_rsu = {rsu.rsu_id: [] for rsu in rsus}
    for row in candidates:
        by_rsu[row["primary_rsu"]].append(row["key"])
    return {
        "schema": SEMANTIC_BASELINE_SCHEMA,
        "packet_sha256": packet_hash,
        "rsus": [
            {
                "rsu_id": rsu.rsu_id,
                "status": "generated" if by_rsu[rsu.rsu_id] else "zero-test-points",
                "candidate_keys": by_rsu[rsu.rsu_id],
                "reason": "" if by_rsu[rsu.rsu_id] else "无独立测试意图",
            }
            for rsu in rsus
        ],
        "candidates": candidates,
        "complex_scopes": [],
        "context_dispositions": [],
    }


def route_complex(result: dict, groups: list[dict]) -> dict:
    result["candidates"] = []
    for row in result["rsus"]:
        row["status"] = "needs-fork"
        row["candidate_keys"] = []
        row["reason"] = "生成前识别为复杂语义范围"
    result["complex_scopes"] = groups
    return result


class AdaptiveWorkerTests(unittest.TestCase):
    def test_parent_finalization_keeps_distinct_candidates_one_to_one(self) -> None:
        first = candidate("c1", "RSU-001", "待推送文件允许批量推送")
        second = candidate("c2", "RSU-001", "推送失败文件允许重新推送")

        intents = build_deterministic_final_intents([first, second])

        self.assertEqual([row["source_candidate_keys"] for row in intents], [["c1"], ["c2"]])

    def test_parent_finalization_merges_only_exact_title_and_result_duplicates(self) -> None:
        first = candidate("c1", "RSU-001", "批量推送后取消选中")
        duplicate = candidate("c2", "RSU-001", "批量推送后取消选中")
        similar = candidate("c3", "RSU-001", "重新推送后取消当前行选中")

        intents = build_deterministic_final_intents([first, duplicate, similar])

        self.assertEqual(len(intents), 2)
        self.assertEqual(intents[0]["source_candidate_keys"], ["c1", "c2"])
        self.assertEqual(intents[1]["source_candidate_keys"], ["c3"])

    def test_worker_prompt_requires_explicit_traceability_labels(self) -> None:
        prompt = worker_prompt("packet", "a" * 64)
        self.assertIn("原文内容：", prompt)
        self.assertIn("父级条件：", prompt)

    def test_worker_policy_preserves_independently_verifiable_behaviors(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model = make_model(
                root,
                [FakeRsu("RSU-001", "文件核查", "推送、轮询、权限和日志", "SRC-MOD", 1)],
            )
            packet, _, _ = compile_baseline_worker_packet(
                model,
                "business",
                sha256_text("business"),
                "a" * 64,
            )

            self.assertIn("one independently verifiable requirement behavior or rule", packet)
            self.assertIn("equivalence classes, boundary values", packet)
            self.assertIn("atomicity self-review", packet)
            self.assertIn("several independent behaviors in", packet)
            self.assertIn("The requirement text defines the acceptance boundary", packet)
            self.assertIn("Question answers may interpret or constrain behavior already", packet)
            self.assertIn("do not create a standalone point", packet)
            self.assertIn("implementation detail as business language to evade this boundary", packet)
            self.assertIn("table/column names, joins, query paths", packet)
            self.assertIn("only when the user explicitly declares a new requirement/acceptance behavior", packet)

    def test_responses_schema_declares_types_for_all_object_properties(self) -> None:
        """The CC Switch Responses adapter requires a type on every property schema."""

        def assert_property_types(node: object, path: str) -> None:
            if not isinstance(node, dict):
                return
            properties = node.get("properties")
            if isinstance(properties, dict):
                for name, property_schema in properties.items():
                    self.assertIsInstance(property_schema, dict, f"{path}/{name} must be an object")
                    self.assertIn("type", property_schema, f"{path}/{name} is missing type")
                    assert_property_types(property_schema, f"{path}/{name}")
            for key in ("items", "allOf", "anyOf", "oneOf", "not"):
                value = node.get(key)
                if isinstance(value, list):
                    for index, item in enumerate(value):
                        assert_property_types(item, f"{path}/{key}[{index}]")
                elif isinstance(value, dict):
                    assert_property_types(value, f"{path}/{key}")

        assert_property_types(semantic_baseline_json_schema(), "baseline")
        assert_property_types(complex_generation_json_schema(), "complex-generation")

    def test_packet_contains_complete_contract_and_business_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model = make_model(root, [FakeRsu("RSU-001", "查询", "展示列表", "SRC-MOD", 1)])
            business = "COMPLETE_BUSINESS_INPUT"
            schema = semantic_baseline_json_schema()
            packet, fingerprints, risks = compile_baseline_worker_packet(
                model,
                business,
                sha256_text(business),
                "a" * 64,
                schema,
            )

            self.assertIn(business, packet)
            self.assertIn("Exact semantic output schema", packet)
            self.assertIn(SEMANTIC_BASELINE_SCHEMA, packet)
            self.assertNotIn("$rsu-test-point-generation", packet)
            self.assertEqual(fingerprints["packet_sha256"], sha256_text(packet))
            self.assertIn("source_fingerprints_sha256", fingerprints)
            self.assertEqual(risks, [])

    def test_packet_budget_fails_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model = make_model(root, [FakeRsu("RSU-001", "查询", "展示列表", "SRC-MOD", 1)])
            with self.assertRaisesRegex(WorkflowError, "exceeds configured budget"):
                compile_baseline_worker_packet(
                    model, "x" * 1000, sha256_text("x" * 1000), "a" * 64,
                    packet_budget_bytes=100,
                )

    def test_complex_packet_does_not_expand_provenance_only_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [FakeRsu("RSU-001", "parent", "polling", "SRC-MOD", 1)]
            model = make_model(root, rsus)
            evidence = root / "evidence.md"
            evidence.write_text("UNRELATED_EVIDENCE" * 10000, encoding="utf-8")
            model.resources["SRC-DB"] = SimpleNamespace(path=evidence, purpose="provenance")
            scope = {
                "scope_id": "COMPLEX-001", "rsu_ids": ["RSU-001"],
                "context_refs": ["SRC-MOD", "SRC-DB"],
                "question_refs": [], "data_closure_refs": [],
            }
            result = baseline_result(rsus, [], "a" * 64)
            packet, _ = compile_complex_generation_packet(
                model, result, scope, {}, materialized_context_ids={"SRC-MOD"},
                packet_budget_bytes=30000,
            )
            self.assertNotIn("UNRELATED_EVIDENCE", packet)
            self.assertIn("provenance-only", packet)
            self.assertIn('"resource_id": "SRC-DB"', packet)
            self.assertIn('"content": "SRC-MOD"', packet)
            self.assertIn("may clarify the requirement but cannot create commitments", packet)
            self.assertIn("Database table/column names, joins, query paths", packet)

    def test_packet_fingerprint_changes_with_business_or_policy_contract(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model = make_model(root, [FakeRsu("RSU-001", "查询", "展示列表", "SRC-MOD", 1)])
            first, first_hashes, _ = compile_baseline_worker_packet(
                model, "business-v1", sha256_text("business-v1"), "a" * 64
            )
            second, second_hashes, _ = compile_baseline_worker_packet(
                model, "business-v2", sha256_text("business-v2"), "a" * 64
            )

            self.assertNotEqual(first_hashes["business_input_sha256"], second_hashes["business_input_sha256"])
            self.assertNotEqual(first_hashes["packet_sha256"], second_hashes["packet_sha256"])
            self.assertNotEqual(first, second)

    def test_dynamic_context_requires_one_explicit_disposition(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [FakeRsu("RSU-001", "文件核查", "仅有权限用户可推送", "FC-002", 1)]
            model = make_model(root, rsus)
            permission = root / "FC-002.md"
            permission.write_text("文件核查按钮受角色权限控制", encoding="utf-8")
            model.resources["FC-002"] = SimpleNamespace(path=permission, purpose="权限")
            row = candidate(
                "c1", "RSU-001", "文件核查操作权限",
                contexts=["SRC-GLOBAL", "SRC-MOD", "CTX", "FC-002"],
            )
            result = baseline_result(rsus, [row], "7" * 64)
            with self.assertRaises(WorkflowError):
                validate_semantic_baseline_result(result, model, "7" * 64)
            result["context_dispositions"] = [{
                "resource_type": "context", "resource_id": "FC-002",
                "rsu_ids": ["RSU-001"], "candidate_keys": ["c1"],
                "disposition": "generated", "reason": "权限规则形成独立候选",
            }]
            validate_semantic_baseline_result(result, model, "7" * 64)

    def test_semantic_validation_rejects_provenance_only_context_before_publish(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [FakeRsu("RSU-001", "文件核查", "展示文件状态", "SRC-MOD", 1)]
            model = make_model(root, rsus)
            database = root / "database.md"
            database.write_text("database provenance", encoding="utf-8")
            model.resources["SRC-DB"] = SimpleNamespace(path=database, purpose="database evidence")
            row = candidate(
                "c1",
                "RSU-001",
                "展示文件核查状态",
                contexts=["SRC-GLOBAL", "SRC-MOD", "CTX", "SRC-DB"],
            )
            result = baseline_result(rsus, [row], "9" * 64)
            result["context_dispositions"] = [{
                "resource_type": "context",
                "resource_id": "SRC-DB",
                "rsu_ids": ["RSU-001"],
                "candidate_keys": ["c1"],
                "disposition": "generated",
                "reason": "模型错误引用了仅用于追溯的数据库附件",
            }]
            authorizations = {
                "RSU-001": {
                    "allowed_rsu_ids": {"RSU-001"},
                    "allowed_q_ids": set(),
                    "allowed_context_ids": {"SRC-GLOBAL", "SRC-MOD", "CTX"},
                    "required_context_ids": {"SRC-GLOBAL", "SRC-MOD", "CTX"},
                    "allowed_data_closure_ids": set(),
                }
            }

            with self.assertRaisesRegex(WorkflowError, "outside its materialized input"):
                validate_semantic_baseline_result(
                    result,
                    model,
                    "9" * 64,
                    rsu_authorizations=authorizations,
                )

    def test_packet_materializes_exact_context_disposition_ledger(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [FakeRsu("RSU-001", "parent", "permission rule", "FC-002", 1)]
            model = make_model(root, rsus)
            permission = root / "FC-002.md"
            permission.write_text("permission", encoding="utf-8")
            model.resources["FC-002"] = SimpleNamespace(path=permission, purpose="permission")
            model.questions["Q-001"] = SimpleNamespace(
                headers=("Q-ID", "question", "status"),
                cells=("Q-001", "permission source", "answered"),
            )

            ledger = required_context_dispositions(model)
            packet, _, _ = compile_baseline_worker_packet(
                model, "business", sha256_text("business"), "a" * 64
            )

            self.assertEqual(
                ledger,
                [
                    {"resource_type": "context", "resource_id": "FC-002"},
                    {"resource_type": "question", "resource_id": "Q-001"},
                ],
            )
            self.assertIn("Required context disposition ledger", packet)
            self.assertIn(json.dumps(ledger, ensure_ascii=False, indent=2), packet)

    def test_complex_packet_embeds_scope_specific_context_and_question_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [FakeRsu("RSU-001", "文件核查", "轮询超时后重试", "FC-009", 1)]
            rsus[0].cells = (*rsus[0].cells[:6], "Q-009", rsus[0].cells[7])
            model = make_model(root, rsus)
            context_path = root / "FC-009.md"
            context_path.write_text("专属轮询次数与重试规则", encoding="utf-8")
            model.resources["FC-009"] = SimpleNamespace(path=context_path, purpose="轮询规则")
            model.questions["Q-009"] = SimpleNamespace(
                q_id="Q-009",
                headers=("Q-ID", "问题", "状态"), cells=("Q-009", "重试是否重置计数", "answered"),
                status="answered",
            )
            baseline = route_complex(baseline_result(rsus, [], "8" * 64), [{
                "scope_key": "poll", "rsu_ids": ["RSU-001"], "context_refs": ["FC-009"],
                "question_refs": ["Q-009"], "data_closure_refs": [],
                "risk_signals": ["async-poll", "timeout-boundary", "retry-recovery"],
                "reason": "复杂轮询恢复",
            }])
            scope = detect_complex_generation_scopes(baseline, model, [])[0]
            packet, _ = compile_complex_generation_packet(model, baseline, scope, {})
            self.assertIn("专属轮询次数与重试规则", packet)
            self.assertIn("重试是否重置计数", packet)
            self.assertIn("FIRST candidate generation", packet)

    def test_complex_scope_dependencies_are_rebuilt_from_rsu_bundles(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [FakeRsu("RSU-001", "文件核查", "轮询超时后重试", "FC-009、DC-001", 1)]
            rsus[0].cells = (*rsus[0].cells[:6], "Q-009、Q-010", rsus[0].cells[7])
            model = make_model(root, rsus)
            for resource_id in ("FC-009", "DC-001", "SRC-EVIDENCE"):
                path = root / f"{resource_id}.md"
                path.write_text(resource_id, encoding="utf-8")
                model.resources[resource_id] = SimpleNamespace(path=path, purpose=resource_id)
            model.questions["Q-009"] = SimpleNamespace(
                q_id="Q-009",
                headers=("Q-ID", "问题", "状态"), cells=("Q-009", "轮询次数", "answered"),
                status="answered",
            )
            model.questions["Q-010"] = SimpleNamespace(
                q_id="Q-010",
                headers=("Q-ID", "问题", "状态"), cells=("Q-010", "重试计数", "answered"),
                status="answered",
            )
            model.data_closure_ids = ("DC-001",)
            model.data_closure_enabled = True
            baseline = route_complex(baseline_result(rsus, [], "6" * 64), [{
                "scope_key": "poll", "rsu_ids": ["RSU-001"],
                # Simulate a Baseline omission plus a provenance-only overreach.
                "context_refs": ["FC-009", "SRC-EVIDENCE"],
                "question_refs": ["Q-009"], "data_closure_refs": [],
                "risk_signals": ["async-poll", "timeout-boundary", "retry-recovery"],
                "reason": "复杂轮询恢复",
            }])

            scope = detect_complex_generation_scopes(baseline, model, [])[0]

            self.assertEqual(scope["question_refs"], ["Q-009", "Q-010"])
            self.assertIn("FC-009", scope["context_refs"])
            self.assertIn("DC-001", scope["context_refs"])
            self.assertNotIn("SRC-EVIDENCE", scope["context_refs"])
            self.assertEqual(scope["data_closure_refs"], ["DC-001"])

    def test_complex_scope_ledger_excludes_unmaterialized_provenance(self) -> None:
        result = {
            "context_dispositions": [
                {
                    "resource_type": "context", "resource_id": "FC-009",
                    "rsu_ids": ["RSU-001"], "candidate_keys": [],
                    "disposition": "needs-fork", "reason": "复杂规则",
                },
                {
                    "resource_type": "context", "resource_id": "SRC-EVIDENCE",
                    "rsu_ids": ["RSU-001"], "candidate_keys": [],
                    "disposition": "needs-fork", "reason": "来源证据",
                },
            ],
        }
        scopes = [{
            "context_refs": ["FC-009"], "question_refs": [],
            "data_closure_refs": [],
        }]

        normalized = normalize_complex_scope_dispositions(result, scopes)

        by_id = {
            row["resource_id"]: row
            for row in normalized["context_dispositions"]
        }
        self.assertEqual(by_id["FC-009"]["disposition"], "needs-fork")
        self.assertEqual(by_id["SRC-EVIDENCE"]["disposition"], "excluded")
        self.assertEqual(by_id["SRC-EVIDENCE"]["candidate_keys"], [])

    def test_parent_assigns_ids_and_renders_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [FakeRsu("RSU-001", "查询", "展示列表", "SRC-MOD", 1)]
            model = make_model(root, rsus)
            result = baseline_result(rsus, [candidate("c1", "RSU-001", "展示任务列表")], "b" * 64)
            validate_semantic_baseline_result(result, model, "b" * 64)
            assigned = render_candidate_artifacts(
                result,
                model,
                {"rsus": [{"rsu_id": "RSU-001", "current_input_sha256": "c" * 64}]},
                root,
            )
            render_final_artifacts(result, model, root, "d" * 64, assigned)

            self.assertIn("CAND-RSU-001-001", (root / "by-rsu" / "RSU-001.md").read_text(encoding="utf-8"))
            self.assertIn("TP-001", (root / "module-test-points.md").read_text(encoding="utf-8"))
            self.assertIn("retained", (root / "coverage-matrix.md").read_text(encoding="utf-8"))

    def test_baseline_allows_candidate_listed_for_declared_source_rsu(self) -> None:
        """One semantic candidate may cover several RSUs via source_rsus."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [
                FakeRsu("RSU-001", "查询", "展示列表", "SRC-MOD", 1),
                FakeRsu("RSU-002", "操作", "提交文件", "SRC-MOD", 2),
            ]
            model = make_model(root, rsus)
            row = candidate("c1", "RSU-001", "跨 RSU 业务链路")
            row["source_rsus"] = ["RSU-001", "RSU-002"]
            result = baseline_result(rsus, [row], "b" * 64)
            result["rsus"][0]["candidate_keys"] = ["c1"]
            result["rsus"][0]["status"] = "generated"
            result["rsus"][1]["candidate_keys"] = ["c1"]
            result["rsus"][1]["status"] = "generated"
            result["rsus"][1]["reason"] = "跨 RSU 候选由 RSU-001 统一归属"
            validate_semantic_baseline_result(result, model, "b" * 64)
            render_candidate_artifacts(
                result,
                model,
                {"rsus": [
                    {"rsu_id": "RSU-001", "current_input_sha256": "c" * 64},
                    {"rsu_id": "RSU-002", "current_input_sha256": "d" * 64},
                ]},
                root,
            )

            secondary = (root / "by-rsu" / "RSU-002.md").read_text(encoding="utf-8")
            self.assertIn("| 生成结果 | `zero-candidate` |", secondary)
            self.assertIn("原文内容：", secondary)
            self.assertIn("父级条件：", secondary)
            self.assertIn("CAND-RSU-001-001", secondary)

    def test_single_rsu_async_recovery_routes_one_complex_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [FakeRsu("RSU-001", "文件核查", "自动轮询，查询超时后点击重试恢复", "SRC-MOD", 1)]
            model = make_model(root, rsus)
            result = route_complex(baseline_result(rsus, [], "e" * 64), [{
                "scope_key": "poll-retry", "rsu_ids": ["RSU-001"],
                "context_refs": [], "question_refs": [], "data_closure_refs": [],
                "risk_signals": ["async-poll", "timeout-boundary", "retry-recovery"],
                "reason": "异步轮询、超时与重试属于复杂生命周期",
            }])
            validate_semantic_baseline_result(result, model, "e" * 64)
            scopes = detect_complex_generation_scopes(
                result,
                model,
                [{"rsu_id": "RSU-001", "signals": ["async-poll", "timeout-boundary", "retry-recovery"]}],
            )

            self.assertEqual(len(scopes), 1)
            self.assertEqual(scopes[0]["rsu_ids"], ["RSU-001"])

    def test_simple_static_module_routes_zero_complex_scopes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [FakeRsu("RSU-001", "任务列表", "按条件查询并展示列表", "SRC-MOD", 1)]
            model = make_model(root, rsus)
            result = baseline_result(
                rsus, [candidate("c1", "RSU-001", "按查询条件展示匹配任务")], "9" * 64
            )

            self.assertEqual(detect_complex_generation_scopes(result, model, []), [])

    def test_high_risk_lifecycle_cannot_be_generated_in_baseline(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [
                FakeRsu("RSU-001", "文件核查", "推送第三方", "FC-001", 1),
                FakeRsu("RSU-002", "文件核查", "轮询超时重试", "FC-001", 2),
            ]
            model = make_model(root, rsus)
            rows = [
                candidate("c1", "RSU-001", "推送第三方", contexts=["SRC-GLOBAL", "SRC-MOD", "CTX", "FC-001"]),
                candidate("c2", "RSU-002", "轮询超时后重试", contexts=["SRC-GLOBAL", "SRC-MOD", "CTX", "FC-001"]),
            ]
            result = baseline_result(rsus, rows, "f" * 64)
            with self.assertRaises(WorkflowError):
                validate_semantic_baseline_result(result, model, "f" * 64)

    def test_connected_cross_rsu_lifecycle_routes_one_complex_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [
                FakeRsu("RSU-001", "文件核查", "向第三方推送核查文件", "FC-001", 1),
                FakeRsu("RSU-002", "文件核查", "轮询核查结果，超时后允许重试", "FC-001", 2),
            ]
            model = make_model(root, rsus)
            flow_path = root / "FC-001.md"
            flow_path.write_text("文件推送、结果轮询、超时与重试属于同一生命周期", encoding="utf-8")
            model.resources["FC-001"] = SimpleNamespace(path=flow_path, purpose="flow")
            result = route_complex(baseline_result(rsus, [], "0" * 64), [{
                "scope_key": "file-check-lifecycle", "rsu_ids": ["RSU-001", "RSU-002"],
                "context_refs": ["FC-001"], "question_refs": [], "data_closure_refs": [],
                "risk_signals": ["external-submit", "async-poll", "timeout-boundary", "retry-recovery"],
                "reason": "推送与轮询恢复是直接耦合生命周期",
            }])
            result["context_dispositions"] = [{
                "resource_type": "context", "resource_id": "FC-001",
                "rsu_ids": ["RSU-001", "RSU-002"], "candidate_keys": [],
                "disposition": "needs-fork", "reason": "复杂生命周期专属上下文",
            }]
            validate_semantic_baseline_result(result, model, "0" * 64)

            scopes = detect_complex_generation_scopes(
                result,
                model,
                [
                    {"rsu_id": "RSU-001", "signals": ["external-submit"]},
                    {
                        "rsu_id": "RSU-002",
                        "signals": ["async-poll", "timeout-boundary", "retry-recovery"],
                    },
                ],
            )

            self.assertEqual(len(scopes), 1)
            self.assertEqual(scopes[0]["rsu_ids"], ["RSU-001", "RSU-002"])
            self.assertEqual(scopes[0]["candidate_keys"], [])

    def test_unrelated_complex_operations_remain_separate_scopes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [
                FakeRsu("RSU-001", "操作甲", "轮询超时重试", "SRC-MOD", 1),
                FakeRsu("RSU-002", "操作乙", "并发重复推送", "SRC-MOD", 2),
            ]
            model = make_model(root, rsus)
            result = route_complex(baseline_result(rsus, [], "1" * 64), [
                {"scope_key": "poll", "rsu_ids": ["RSU-001"], "context_refs": [],
                 "question_refs": [], "data_closure_refs": [],
                 "risk_signals": ["async-poll", "timeout-boundary", "retry-recovery"],
                 "reason": "轮询恢复生命周期"},
                {"scope_key": "submit", "rsu_ids": ["RSU-002"], "context_refs": [],
                 "question_refs": [], "data_closure_refs": [],
                 "risk_signals": ["external-submit", "concurrency-idempotency"],
                 "reason": "并发幂等提交生命周期"},
            ])
            validate_semantic_baseline_result(result, model, "1" * 64)
            scopes = detect_complex_generation_scopes(
                result,
                model,
                [
                    {"rsu_id": "RSU-001", "signals": ["async-poll", "timeout-boundary", "retry-recovery"]},
                    {"rsu_id": "RSU-002", "signals": ["external-submit", "concurrency-idempotency"]},
                ],
            )

            self.assertEqual(len(scopes), 2)
            self.assertEqual([scope["rsu_ids"] for scope in scopes], [["RSU-001"], ["RSU-002"]])

    def test_complex_generation_is_bounded_and_merged_parent_side(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [FakeRsu("RSU-001", "文件核查", "轮询超时重试", "SRC-MOD", 1)]
            model = make_model(root, rsus)
            original = route_complex(baseline_result(rsus, [], "2" * 64), [{
                "scope_key": "poll", "rsu_ids": ["RSU-001"], "context_refs": [],
                "question_refs": [], "data_closure_refs": [], "risk_signals": ["async-poll"],
                "reason": "复杂生命周期",
            }])
            scope = {
                "scope_id": "COMPLEX-001", "rsu_ids": ["RSU-001"],
                "candidate_keys": [], "context_refs": [], "question_refs": [],
                "data_closure_refs": [], "risk_signals": ["async-poll"], "reason": "generation",
            }
            replacement = candidate("c2", "RSU-001", "轮询、超时与重试生命周期")
            complex_result = {
                "schema": COMPLEX_GENERATION_SCHEMA,
                "packet_sha256": "3" * 64,
                "scope_id": "COMPLEX-001",
                "status": "resolved",
                "rsus": [{"rsu_id": "RSU-001", "status": "generated", "candidate_keys": ["c2"], "reason": "已收敛"}],
                "candidates": [replacement],
                "reason": "已完成局部语义收敛",
            }
            validate_complex_generation_result(complex_result, model, scope, "3" * 64)
            merged = merge_complex_generation_result(original, scope, complex_result)

            self.assertEqual([row["key"] for row in merged["candidates"]], ["c2"])
            self.assertEqual([row["key"] for row in merged["final_intents"]], ["intent:c2"])

    def test_complex_merge_restores_stable_rsu_order(self) -> None:
        rsus = [
            FakeRsu("RSU-001", "文件核查", "列表", "SRC-MOD", 1),
            FakeRsu("RSU-002", "文件核查", "推送", "SRC-MOD", 2),
            FakeRsu("RSU-003", "文件核查", "入口", "SRC-MOD", 3),
        ]
        late_primary = candidate("c3", "RSU-003", "入口")
        late_primary["source_rsus"] = ["RSU-002", "RSU-003"]
        original = baseline_result(
            rsus,
            [candidate("c1", "RSU-001", "列表"), late_primary],
            "2" * 64,
        )
        original["rsus"][1] = {
            "rsu_id": "RSU-002", "status": "needs-fork",
            "candidate_keys": [], "reason": "复杂提交生命周期",
        }
        original["complex_scopes"] = [{
            "scope_key": "submit", "rsu_ids": ["RSU-002"],
            "context_refs": [], "question_refs": [], "data_closure_refs": [],
            "risk_signals": ["external-submit"], "reason": "复杂提交生命周期",
        }]
        scope = {
            "scope_id": "COMPLEX-001", "rsu_ids": ["RSU-002"],
            "candidate_keys": [], "context_refs": [], "question_refs": [],
            "data_closure_refs": [], "risk_signals": ["external-submit"],
            "reason": "generation",
        }
        complex_result = {
            "rsus": [{
                "rsu_id": "RSU-002", "status": "generated",
                "candidate_keys": ["c2"], "reason": "已生成",
            }],
            "candidates": [candidate("c2", "RSU-002", "推送")],
        }

        merged = merge_complex_generation_result(original, scope, complex_result)

        self.assertEqual([row["key"] for row in merged["candidates"]], ["c1", "c2", "c3"])
        self.assertEqual(
            [row["source_candidate_keys"][0] for row in merged["final_intents"]],
            ["c1", "c2", "c3"],
        )

    def test_complex_generation_references_only_scope_authorized_resources(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [FakeRsu("RSU-001", "文件核查", "轮询", "SRC-MOD", 1)]
            model = make_model(root, rsus)
            for resource_id in ("FC-001", "FC-002"):
                path = root / f"{resource_id}.md"
                path.write_text(resource_id, encoding="utf-8")
                model.resources[resource_id] = SimpleNamespace(path=path, purpose=resource_id)
            model.questions = {"Q-001": object(), "Q-002": object()}
            scope = {
                "scope_id": "COMPLEX-001", "rsu_ids": ["RSU-001"],
                "candidate_keys": [],
                "context_refs": ["SRC-GLOBAL", "SRC-MOD", "CTX", "FC-001"],
                "question_refs": ["Q-001"], "data_closure_refs": [],
                "risk_signals": ["async-poll"], "reason": "generation",
            }
            scoped = candidate(
                "c1", "RSU-001", "轮询生命周期",
                contexts=["SRC-GLOBAL", "SRC-MOD", "CTX", "FC-001"],
            )
            scoped["question_refs"] = ["Q-001"]
            result = {
                "schema": COMPLEX_GENERATION_SCHEMA,
                "packet_sha256": "4" * 64,
                "scope_id": "COMPLEX-001",
                "status": "resolved",
                "rsus": [{"rsu_id": "RSU-001", "status": "generated", "candidate_keys": ["c1"], "reason": "已收敛"}],
                "candidates": [scoped],
                "reason": "已完成局部语义收敛",
            }

            validate_complex_generation_result(result, model, scope, "4" * 64)
            result["candidates"][0]["question_refs"] = ["Q-002"]
            with self.assertRaisesRegex(WorkflowError, "unknown questions"):
                validate_complex_generation_result(result, model, scope, "4" * 64)
            result["candidates"][0]["question_refs"] = ["Q-001"]
            result["candidates"][0]["context_refs"] = [
                "SRC-GLOBAL", "SRC-MOD", "CTX", "FC-001", "FC-002",
            ]
            with self.assertRaisesRegex(WorkflowError, "invalid or incomplete context"):
                validate_complex_generation_result(result, model, scope, "4" * 64)

    def test_complex_generation_accepts_scope_data_closure_as_context_reference(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [FakeRsu("RSU-001", "文件核查", "轮询", "SRC-MOD", 1)]
            model = make_model(root, rsus)
            dc_path = root / "DC-001.md"
            dc_path.write_text("审核文件数据闭包", encoding="utf-8")
            model.resources["DC-001"] = SimpleNamespace(path=dc_path, purpose="数据闭包")
            scope = {
                "scope_id": "COMPLEX-001", "rsu_ids": ["RSU-001"],
                "candidate_keys": [], "context_refs": [], "question_refs": [],
                "data_closure_refs": ["DC-001"], "risk_signals": ["async-poll"],
                "reason": "generation",
            }
            scoped = candidate(
                "c1", "RSU-001", "轮询数据落库",
                contexts=["SRC-GLOBAL", "SRC-MOD", "CTX", "DC-001"],
            )
            scoped["data_closure_refs"] = ["DC-001"]
            result = {
                "schema": COMPLEX_GENERATION_SCHEMA,
                "packet_sha256": "5" * 64,
                "scope_id": "COMPLEX-001",
                "status": "resolved",
                "rsus": [{"rsu_id": "RSU-001", "status": "generated", "candidate_keys": ["c1"], "reason": "已收敛"}],
                "candidates": [scoped],
                "reason": "已完成局部语义收敛",
            }

            validate_complex_generation_result(result, model, scope, "5" * 64)
            authorization = _complex_scope_authorizations(
                [scope], model.fixed_resource_ids
            )["RSU-001"]
            self.assertIn("DC-001", authorization["allowed_context_ids"])
            self.assertIn("DC-001", authorization["allowed_data_closure_ids"])

    def test_complex_generation_allows_one_candidate_in_multiple_declared_rsu_dispositions(self) -> None:
        """A cross-RSU complex candidate may be listed by every declared RSU."""
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            rsus = [
                FakeRsu("RSU-001", "文件核查", "推送文件", "SRC-MOD", 1),
                FakeRsu("RSU-002", "文件核查", "轮询结果", "SRC-MOD", 2),
            ]
            model = make_model(root, rsus)
            shared = candidate("baseline:c1", "RSU-001", "文件核查生命周期", contexts=["SRC-GLOBAL", "SRC-MOD", "CTX"])
            shared["source_rsus"] = ["RSU-001", "RSU-002"]
            complex_result = {
                "schema": COMPLEX_GENERATION_SCHEMA,
                "packet_sha256": "4" * 64,
                "scope_id": "COMPLEX-001",
                "status": "resolved",
                "rsus": [
                    {"rsu_id": "RSU-001", "status": "generated", "candidate_keys": ["baseline:c1"], "reason": "已覆盖"},
                    {"rsu_id": "RSU-002", "status": "generated", "candidate_keys": ["baseline:c1"], "reason": "已覆盖"},
                ],
                "candidates": [shared],
                "reason": "跨 RSU 生命周期已收敛",
            }
            scope = {
                "scope_id": "COMPLEX-001",
                "rsu_ids": ["RSU-001", "RSU-002"],
                "candidate_keys": ["baseline:c1"],
            }

            validate_complex_generation_result(complex_result, model, scope, "4" * 64)


if __name__ == "__main__":
    unittest.main()


