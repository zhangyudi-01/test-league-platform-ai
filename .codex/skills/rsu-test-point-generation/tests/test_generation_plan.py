from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import common  # noqa: E402
import generation_plan  # noqa: E402


def make_model(root: Path, count: int) -> common.ModuleModel:
    rsus = [
        common.RequirementUnit(
            f"RSU-{index:03d}",
            (f"RSU-{index:03d}", "无", f"规则{index}", "SRC", "L1", "无", "无", "已确认"),
            index,
            index,
        )
        for index in range(1, count + 1)
    ]
    return common.ModuleModel(
        root,
        root,
        None,
        None,
        {},
        {},
        "模块",
        root / "map.md",
        root / "questions.md",
        {},
        rsus,
        {item.rsu_id: item for item in rsus},
        {},
    )


def make_bundles(model: common.ModuleModel, signatures: list[str] | None = None):
    result = {}
    for index, rsu in enumerate(model.rsus):
        kind = signatures[index] if signatures else "shared"
        dynamic = [common.Material(f"{kind}-001", model.module_dir / "ctx.md", "dynamic", kind)]
        result[rsu.rsu_id] = common.InputBundle(
            rsu,
            f"input-{rsu.rsu_id}",
            [],
            [rsu.rsu_id],
            [],
            [],
            [],
            [],
            dynamic,
            [],
            [],
            [],
            "full",
            "delta",
            f"delta-{rsu.rsu_id}",
            "fixed-source",
        )
    return result


def validated_plan(model, bundles, modes: list[str], batches: list[str]):
    value = generation_plan.empty_plan(model, bundles, "planning-hash")
    value["status"] = "validated"
    for item, mode, batch_id in zip(value["rsus"], modes, batches):
        item["mode"] = mode
        item["batch_id"] = batch_id
        item["rationale"] = "语义风险评估"
    return value


class GenerationPlanTests(unittest.TestCase):
    def test_accepts_simple_compatible_batch_and_complex_singleton(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model = make_model(Path(temp), 6)
            bundles = make_bundles(model)
            plan = validated_plan(
                model,
                bundles,
                ["simple"] * 5 + ["complex"],
                ["BATCH-001"] * 5 + ["BATCH-002"],
            )

            _, batches = generation_plan.validate_plan(plan, model, bundles, "planning-hash")

            self.assertEqual([len(item["rsu_ids"]) for item in batches], [5, 1])
            self.assertEqual(batches[1]["mode"], "complex")

    def test_rejects_missing_duplicate_unknown_and_non_map_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model = make_model(Path(temp), 2)
            bundles = make_bundles(model)
            plan = validated_plan(model, bundles, ["simple", "simple"], ["BATCH-001"] * 2)
            for rows in (
                plan["rsus"][:1],
                [plan["rsus"][0], plan["rsus"][0]],
                [plan["rsus"][0], {**plan["rsus"][1], "rsu_id": "RSU-999"}],
                list(reversed(plan["rsus"])),
            ):
                invalid = {**plan, "rsus": copy.deepcopy(rows)}
                with self.assertRaisesRegex(common.WorkflowError, "exactly once in map order"):
                    generation_plan.validate_plan(invalid, model, bundles, "planning-hash")

    def test_rejects_complex_multi_member_simple_over_ten_and_incompatible_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            model = make_model(root, 11)
            bundles = make_bundles(model)
            complex_plan = validated_plan(
                model, bundles, ["complex", "complex"] + ["simple"] * 9,
                ["BATCH-001", "BATCH-001"] + ["BATCH-002"] * 9,
            )
            with self.assertRaisesRegex(common.WorkflowError, "complex mode must contain exactly one"):
                generation_plan.validate_plan(complex_plan, model, bundles, "planning-hash")

            oversized = validated_plan(model, bundles, ["simple"] * 11, ["BATCH-001"] * 11)
            with self.assertRaisesRegex(common.WorkflowError, "at most 10"):
                generation_plan.validate_plan(oversized, model, bundles, "planning-hash")

            model2 = make_model(root, 2)
            bundles2 = make_bundles(model2, ["FC", "DC"])
            mixed = validated_plan(model2, bundles2, ["simple", "simple"], ["BATCH-001"] * 2)
            with self.assertRaisesRegex(common.WorkflowError, "incompatible context signatures"):
                generation_plan.validate_plan(mixed, model2, bundles2, "planning-hash")

    def test_planning_hash_and_context_signature_are_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model = make_model(Path(temp), 1)
            bundles = make_bundles(model)
            plan = validated_plan(model, bundles, ["simple"], ["BATCH-001"])
            stale = copy.deepcopy(plan)
            stale["planning_input_sha256"] = "stale"
            with self.assertRaisesRegex(common.WorkflowError, "planning-input"):
                generation_plan.validate_plan(stale, model, bundles, "planning-hash")
            stale = copy.deepcopy(plan)
            stale["rsus"][0]["context_signature"] = "stale"
            with self.assertRaisesRegex(common.WorkflowError, "context_signature"):
                generation_plan.validate_plan(stale, model, bundles, "planning-hash")


if __name__ == "__main__":
    unittest.main()
