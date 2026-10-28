from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import common  # noqa: E402


def requirement_unit(
    rsu_id: str,
    order: int,
    related_context: str,
) -> common.RequirementUnit:
    return common.RequirementUnit(
        rsu_id,
        (
            rsu_id,
            "无",
            f"{rsu_id} 原文内容",
            "SRC-MOD",
            f"业务规则 {order}",
            related_context,
            "无",
            "captured",
        ),
        order + 10,
        order,
    )


def create_model(root: Path, current_context: str) -> tuple[common.ModuleModel, str, str]:
    contents = {
        "SRC-GLOBAL": "全局上下文",
        "SRC-MOD": "模块需求原文",
        "CTX": "模块 Context Pack",
        "DC-001": (
            "# DC-001 查询闭包\n\n"
            "关联 RSU：RSU-001、RSU-002\n\n"
            "来源证据：SRC-HUGE\n"
        ),
        "SRC-HUGE": "HUGE-EVIDENCE-BODY-" * 2000,
        "SRC-UNRELATED": "UNRELATED-SUPPORT-DEPENDENCY-" * 2000,
    }
    resources: dict[str, common.Resource] = {}
    for index, (resource_id, content) in enumerate(contents.items(), start=1):
        path = root / f"{resource_id}.md"
        path.write_text(content, encoding="utf-8")
        resources[resource_id] = common.Resource(
            resource_id,
            path,
            f"{resource_id} 定位用途",
            index,
        )

    current = requirement_unit("RSU-001", 1, current_context)
    support = requirement_unit("RSU-002", 2, "SRC-UNRELATED")
    model = common.ModuleModel(
        module_dir=root,
        preanalysis_dir=root,
        manifest_path=None,
        manifest_sha256=None,
        artifact_paths={},
        resource_roles={
            "global_context": "SRC-GLOBAL",
            "module_requirement": "SRC-MOD",
            "module_context": "CTX",
        },
        module_name="测试模块",
        map_path=root / "map.md",
        question_path=root / "questions.md",
        resources=resources,
        rsus=[current, support],
        rsu_by_id={current.rsu_id: current, support.rsu_id: support},
        questions={},
    )
    return model, contents["SRC-HUGE"], contents["SRC-UNRELATED"]


class InputDependencyScopeTests(unittest.TestCase):
    def test_card_provenance_is_hashed_but_not_copied_as_semantic_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, huge_body, unrelated_body = create_model(Path(temp), "DC-001")

            bundle = common.build_bundle(model, model.rsus[0])

            self.assertEqual(
                [item.resource_id for item in bundle.dynamic_materials],
                ["DC-001"],
            )
            self.assertEqual(
                [item.resource_id for item in bundle.evidence_materials],
                ["SRC-HUGE"],
            )
            self.assertEqual(
                [item.rsu_id for item in bundle.supporting_rsus],
                ["RSU-002"],
            )
            self.assertNotIn("SRC-HUGE", bundle.allowed_context_ids)
            self.assertNotIn("SRC-UNRELATED", bundle.allowed_context_ids)
            self.assertNotIn(huge_body, bundle.rendered)
            self.assertNotIn(unrelated_body, bundle.rendered)
            self.assertIn(common.sha256_text(huge_body), bundle.rendered)
            self.assertIn("evidence-reference（正文不自动展开）", bundle.rendered)

    def test_supporting_rsu_does_not_inherit_its_dynamic_dependencies(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, _, unrelated_body = create_model(Path(temp), "DC-001")

            bundle = common.build_bundle(model, model.rsus[0])

            self.assertNotIn(
                "SRC-UNRELATED",
                [item.resource_id for item in bundle.dynamic_materials],
            )
            self.assertNotIn(
                "SRC-UNRELATED",
                [item.resource_id for item in bundle.evidence_materials],
            )
            self.assertNotIn(unrelated_body, bundle.rendered)

    def test_explicit_current_rsu_resource_is_materialized_in_full(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, huge_body, _ = create_model(Path(temp), "DC-001、SRC-HUGE")

            bundle = common.build_bundle(model, model.rsus[0])

            self.assertEqual(
                [item.resource_id for item in bundle.dynamic_materials],
                ["DC-001", "SRC-HUGE"],
            )
            self.assertEqual(bundle.evidence_materials, [])
            self.assertIn("SRC-HUGE", bundle.allowed_context_ids)
            self.assertIn(huge_body, bundle.rendered)

    def test_session_delta_omits_fixed_bodies_but_keeps_current_dynamic_input(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, huge_body, _ = create_model(Path(temp), "DC-001、SRC-HUGE")

            bundle = common.build_bundle(model, model.rsus[0])

            self.assertNotIn("全局上下文", bundle.session_rendered)
            self.assertNotIn("模块需求原文", bundle.session_rendered)
            self.assertNotIn("模块 Context Pack", bundle.session_rendered)
            self.assertIn(huge_body, bundle.session_rendered)
            self.assertIn("RSU-001 原文内容", bundle.session_rendered)
            self.assertIn(bundle.input_sha256, bundle.session_rendered)
            self.assertIn(
                bundle.session_source_fingerprint_sha256,
                bundle.session_rendered,
            )

    def test_session_source_fingerprint_changes_only_with_fixed_anchor(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, _, _ = create_model(Path(temp), "DC-001")
            before = common.build_bundle(model, model.rsus[0])

            model.resources["SRC-HUGE"].path.write_text(
                "changed evidence",
                encoding="utf-8",
            )
            evidence_changed = common.build_bundle(model, model.rsus[0])
            self.assertEqual(
                before.session_source_fingerprint_sha256,
                evidence_changed.session_source_fingerprint_sha256,
            )
            self.assertNotEqual(
                before.session_input_sha256,
                evidence_changed.session_input_sha256,
            )

            model.resources["SRC-GLOBAL"].path.write_text(
                "changed fixed context",
                encoding="utf-8",
            )
            fixed_changed = common.build_bundle(model, model.rsus[0])
            self.assertNotEqual(
                evidence_changed.session_source_fingerprint_sha256,
                fixed_changed.session_source_fingerprint_sha256,
            )

    def test_evidence_content_change_invalidates_the_input_hash(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, _, _ = create_model(Path(temp), "DC-001")
            before = common.build_bundle(model, model.rsus[0])

            model.resources["SRC-HUGE"].path.write_text(
                "changed evidence",
                encoding="utf-8",
            )
            after = common.build_bundle(model, model.rsus[0])

            self.assertNotEqual(before.input_sha256, after.input_sha256)

    def test_fixed_source_change_invalidates_foundation_plan_and_batches(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model, _, _ = create_model(root, "DC-001")
            output = root / "test-points"
            output.mkdir()
            state, bundles = common.reconcile_state(model, output, None)
            old_fingerprint = state["session_source_fingerprint_sha256"]
            state["foundation"] = {
                "status": "validated",
                "thread_id": "foundation-thread",
                "source_fingerprint_sha256": old_fingerprint,
            }
            state["planning"] = {
                "status": "validated",
                "source_sha256": "old-plan-source",
            }
            state["batches"] = [{"batch_id": "BATCH-001", "status": "pending"}]
            for record in state["rsus"]:
                record["batch_id"] = "BATCH-001"
                record["context_signature"] = "old-context"

            model.resources["SRC-GLOBAL"].path.write_text(
                "changed fixed context",
                encoding="utf-8",
            )
            reconciled, changed_bundles = common.reconcile_state(model, output, state)

            self.assertNotEqual(
                old_fingerprint,
                reconciled["session_source_fingerprint_sha256"],
            )
            self.assertEqual(reconciled["foundation"]["status"], "pending")
            self.assertIsNone(reconciled["foundation"]["thread_id"])
            self.assertEqual(reconciled["planning"]["status"], "pending")
            self.assertEqual(reconciled["batches"], [])
            self.assertTrue(
                all(item["batch_id"] is None for item in reconciled["rsus"])
            )
            self.assertTrue(
                all(item["context_signature"] is None for item in reconciled["rsus"])
            )
            self.assertNotEqual(
                bundles["RSU-001"].session_source_fingerprint_sha256,
                changed_bundles["RSU-001"].session_source_fingerprint_sha256,
            )


if __name__ == "__main__":
    unittest.main()
