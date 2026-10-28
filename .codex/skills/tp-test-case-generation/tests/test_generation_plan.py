from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from common import WorkflowError, _require_case_execution_quality  # noqa: E402
from generation_plan import PLAN_SCHEMA_VERSION, validate_plan  # noqa: E402


class GenerationPlanTests(unittest.TestCase):
    def points(self):
        return [SimpleNamespace(tp_id=f"TP-{index:03d}") for index in range(1, 4)]

    def plan(self):
        return {
            "schema_version": PLAN_SCHEMA_VERSION,
            "module_name": "示例模块",
            "source_sha256": "source",
            "status": "validated",
            "sql_assets": [
                {
                    "sql_id": "SQL-LIST",
                    "statement_type": "SELECT",
                    "purpose_type": "page-list-column",
                    "functional_module": "任务列表",
                    "purpose": "查询页面列表展示字段",
                    "rationale": "用于直接核对列表列值与数据库记录",
                    "tp_refs": ["TP-002"],
                    "data_closure_refs": ["DC-001"],
                }
            ],
            "batches": [
                {
                    "batch_id": "BATCH-001",
                    "mode": "simple",
                    "tp_ids": ["TP-001", "TP-002"],
                    "sql_refs": ["SQL-LIST"],
                    "rationale": "同一页面的简单规则和列表核对",
                },
                {
                    "batch_id": "BATCH-002",
                    "mode": "complex",
                    "tp_ids": ["TP-003"],
                    "sql_refs": [],
                    "rationale": "轮询重试组合需要独立处理",
                },
            ],
        }

    def test_complexity_and_sql_need_are_independent(self) -> None:
        result = validate_plan(
            self.plan(),
            module_name="示例模块",
            source_sha256="source",
            points=self.points(),
            known_dc_ids={"DC-001"},
        )
        self.assertEqual(result["sql_by_tp"]["TP-002"], ["SQL-LIST"])
        self.assertEqual(result["sql_by_tp"]["TP-003"], [])

    def test_complex_batch_must_have_one_tp(self) -> None:
        plan = self.plan()
        plan["batches"] = [{
            "batch_id": "BATCH-001",
            "mode": "complex",
            "tp_ids": ["TP-001", "TP-002", "TP-003"],
            "sql_refs": ["SQL-LIST"],
            "rationale": "错误复杂批次",
        }]
        with self.assertRaisesRegex(WorkflowError, "exactly one TP"):
            validate_plan(
                plan,
                module_name="示例模块",
                source_sha256="source",
                points=self.points(),
                known_dc_ids={"DC-001"},
            )

    def test_plan_rejects_dml(self) -> None:
        plan = self.plan()
        plan["sql_assets"][0]["statement_type"] = "UPDATE"
        with self.assertRaisesRegex(WorkflowError, "must be SELECT"):
            validate_plan(
                plan,
                module_name="示例模块",
                source_sha256="source",
                points=self.points(),
                known_dc_ids={"DC-001"},
            )

    def test_sql_requires_functional_module(self) -> None:
        plan = self.plan()
        del plan["sql_assets"][0]["functional_module"]
        with self.assertRaisesRegex(WorkflowError, "functional_module"):
            validate_plan(
                plan,
                module_name="示例模块",
                source_sha256="source",
                points=self.points(),
                known_dc_ids={"DC-001"},
            )

    def test_plan_preserves_sql_functional_module(self) -> None:
        result = validate_plan(
            self.plan(),
            module_name="示例模块",
            source_sha256="source",
            points=self.points(),
            known_dc_ids={"DC-001"},
        )
        self.assertEqual(result["sql_assets"][0]["functional_module"], "任务列表")


class ConciseCaseQualityTests(unittest.TestCase):
    def case(self, precondition: str, steps: str, expected: str):
        return [
            "TC-001", "当前迭代", "窗口", "彩票年选项", "当前年:$Y",
            precondition, steps, "无", expected, "未执行", "未执行", "未执行",
        ]

    def test_accepts_single_concise_precondition(self) -> None:
        _require_case_execution_quality(
            "TC-001",
            self.case(
                "当前年为 $Y（如 2026）",
                "1. 点击彩票年下拉框。<br>2. 依次选择 $Y 和上一年。",
                "1. 下拉框仅包含当前年和上一年。<br>2. 两个年份可以正常切换。",
            ),
            set(),
            {},
        )

    def test_accepts_no_precondition(self) -> None:
        _require_case_execution_quality(
            "TC-001",
            [
                "TC-001", "当前迭代", "窗口", "打开入口", "无", "无",
                "1. 点击【生成任务】。", "无", "1. 打开生成任务窗口。",
                "未执行", "未执行", "未执行",
            ],
            set(),
            {},
        )

    def test_rejects_internal_placeholder_prose(self) -> None:
        with self.assertRaisesRegex(WorkflowError, "internal placeholder"):
            _require_case_execution_quality(
                "TC-001",
                self.case(
                    "当前年为 $Y（如 2026）",
                    "1. 执行当前 TP 的核心操作。",
                    "1. 按来源场景分别记录结果。",
                ),
                set(),
                {},
            )

    def test_rejects_unpaired_steps_and_expected_results(self) -> None:
        with self.assertRaisesRegex(WorkflowError, "one-to-one"):
            _require_case_execution_quality(
                "TC-001",
                self.case(
                    "当前年为 $Y（如 2026）",
                    "1. 点击彩票年下拉框。<br>2. 选择 $Y。",
                    "1. 下拉框正常展开。",
                ),
                set(),
                {},
            )


if __name__ == "__main__":
    unittest.main()
