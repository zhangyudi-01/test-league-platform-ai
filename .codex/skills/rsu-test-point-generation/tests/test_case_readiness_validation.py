from __future__ import annotations

import sys
import unittest
from pathlib import Path


SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import validate_case_readiness as readiness
from common import SKILL_DIR


class CaseReadinessPlaceholderTests(unittest.TestCase):
    def test_pending_accepts_semantically_unanswered_placeholders(self) -> None:
        for value in (
            "未提供",
            "待回填",
            "尚未提供",
            "PENDING",
            "Not Provided",
            "not available",
            "N/A",
        ):
            with self.subTest(value=value):
                self.assertTrue(readiness.is_unanswered_placeholder(value))

    def test_pending_rejects_concrete_answers(self) -> None:
        for value in ("账号 test_no_void 已准备", "status_code=3", "见 config.txt"):
            with self.subTest(value=value):
                self.assertFalse(readiness.is_unanswered_placeholder(value))


class CaseReadinessContractTests(unittest.TestCase):
    def test_environment_availability_is_not_a_design_readiness_gate(self) -> None:
        rules = (SKILL_DIR / "references" / "case-readiness-rules.md").read_text(
            encoding="utf-8"
        )
        data_rules = (
            SKILL_DIR / "references" / "data-closure-readiness-rules.md"
        ).read_text(encoding="utf-8")
        output_contract = (SKILL_DIR / "references" / "output-contract.md").read_text(
            encoding="utf-8"
        )

        self.assertIn("不要求 readiness 阶段预先证明其已开通或实际可用", rules)
        self.assertNotIn("必须确认对应访问条件可用", rules)
        self.assertIn("readiness 不要求预先确认其已开通或实际可用", data_rules)
        self.assertIn("准备/断言/安全恢复方案本身无法确定时才阻断", output_contract)


if __name__ == "__main__":
    unittest.main()
