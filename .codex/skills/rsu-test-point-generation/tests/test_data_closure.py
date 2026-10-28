from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import common  # noqa: E402


class DataClosureHeuristicTests(unittest.TestCase):
    def test_only_explicit_persistence_or_schema_observations_require_data_closure(self) -> None:
        self.assertTrue(common.requires_data_closure("数据库新增 task_record 记录"))
        self.assertTrue(common.requires_data_closure("核对 SQL 查询返回的 task_id 字段"))
        self.assertFalse(common.requires_data_closure("页面显示任务编号并提示操作成功"))

    def test_unique_schema_identifier_infers_its_materialized_data_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            materials = [
                common.Material(
                    "DC-001",
                    root / "dc-001.md",
                    "data-closure",
                    "表 task_record，字段 task_id、status",
                ),
                common.Material(
                    "DC-002",
                    root / "dc-002.md",
                    "data-closure",
                    "表 audit_record，字段 audit_id",
                ),
            ]
            self.assertEqual(
                common.infer_required_data_closures(
                    "查询 task_id 与 status，核对数据库记录",
                    materials,
                ),
                {"DC-001"},
            )

    def test_ambiguous_identifier_is_not_guessed(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            materials = [
                common.Material("DC-001", root / "one.md", "data-closure", "字段 task_id"),
                common.Material("DC-002", root / "two.md", "data-closure", "字段 task_id"),
            ]
            self.assertEqual(
                common.infer_required_data_closures("核对 task_id 数据库记录", materials),
                set(),
            )


if __name__ == "__main__":
    unittest.main()
