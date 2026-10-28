from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import common  # noqa: E402
from validate_rsu_test_points import require_source_part_traceability  # noqa: E402


def requirement_unit(rsu_id: str, parent: str, source: str, order: int) -> common.RequirementUnit:
    return common.RequirementUnit(
        rsu_id,
        (rsu_id, parent, source, "SRC-MOD", "业务规则", "无", "无", "captured"),
        order + 10,
        order,
    )


class ParentSourceCoverageTests(unittest.TestCase):
    def test_behavioral_parent_is_linked_to_the_rsu_that_exposes_it(self) -> None:
        parent = "校验通过后，系统生成计奖审核任务，并进入任务详情页。"
        parent_rsu = requirement_unit("RSU-001", "无", parent, 1)
        child_rsu = requirement_unit("RSU-002", parent, "顶部展示奖期编号。", 2)
        model = SimpleNamespace(rsus=[parent_rsu, child_rsu])
        self.assertEqual(common.parent_behavior_source_ids(model, child_rsu), ["RSU-001"])

    def test_pure_condition_needs_no_behavior_source_rsu(self) -> None:
        child_rsu = requirement_unit("RSU-001", "校验通过后", "顶部展示奖期编号。", 1)
        model = SimpleNamespace(rsus=[child_rsu])
        self.assertEqual(common.parent_behavior_source_ids(model, child_rsu), [])
        self.assertFalse(common.parent_has_observable_behavior("进入任务详情页后"))
        self.assertFalse(common.parent_has_observable_behavior("任务状态为待核查时"))
        self.assertTrue(common.parent_has_observable_behavior("系统进入任务详情页。"))

    def test_candidate_basis_requires_both_source_parts_when_parent_exists(self) -> None:
        require_source_part_traceability(
            "父级条件：校验通过后；原文内容：顶部展示奖期编号。",
            "candidate",
            True,
        )
        with self.assertRaisesRegex(common.WorkflowError, "父级条件"):
            require_source_part_traceability("原文内容：顶部展示奖期编号。", "candidate", True)
        with self.assertRaisesRegex(common.WorkflowError, "原文内容"):
            require_source_part_traceability("父级条件：校验通过后。", "candidate", True)

    def test_upstream_validation_excludes_nested_generation_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module_dir = Path(temp)
            output_dir = module_dir / "test-points"
            manifest = module_dir / "preanalysis-manifest.json"
            validator = module_dir / "validate_preanalysis.py"
            layout = SimpleNamespace(
                preanalysis_dir=module_dir,
                manifest_path=manifest,
                default_output_dir=output_dir,
            )
            completed = SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

            with (
                patch.object(common, "find_preanalysis_validator", return_value=validator),
                patch.object(common.subprocess, "run", return_value=completed) as mocked,
            ):
                common.run_preanalysis_validation(layout, output_dir)

            command = mocked.call_args.args[0]
            self.assertIn("--exclude-root", command)
            self.assertEqual(command[command.index("--exclude-root") + 1], str(output_dir.resolve()))

    def test_upstream_validation_does_not_exclude_sibling_generation_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            module_dir = Path(temp) / "module"
            preanalysis_dir = module_dir / "preanalysis"
            output_dir = module_dir / "test-points"
            layout = SimpleNamespace(
                preanalysis_dir=preanalysis_dir,
                manifest_path=preanalysis_dir / "preanalysis-manifest.json",
                default_output_dir=output_dir,
            )
            completed = SimpleNamespace(returncode=0, stdout="ok\n", stderr="")

            with (
                patch.object(
                    common,
                    "find_preanalysis_validator",
                    return_value=preanalysis_dir / "validate_preanalysis.py",
                ),
                patch.object(common.subprocess, "run", return_value=completed) as mocked,
            ):
                common.run_preanalysis_validation(layout, output_dir)

            self.assertNotIn("--exclude-root", mocked.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
