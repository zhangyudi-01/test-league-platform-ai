from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
TEST_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(TEST_DIR))

from candidate_validation import validate_candidate_document  # noqa: E402
from test_candidate_quality import candidate_document, create_scope, valid_row  # noqa: E402


class TestPointTitleQualityTests(unittest.TestCase):
    def _validate_title(self, title: str, observable: str) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, bundle, input_file, candidate_file = create_scope(Path(temp))
            row = valid_row()
            row[4] = title
            row[5] = observable
            candidate_file.write_text(
                candidate_document("candidates", [row]),
                encoding="utf-8",
            )
            document, _ = validate_candidate_document(model, bundle, input_file, candidate_file)
            self.assertEqual(document.rows[0][4], title)

    def test_long_title_is_not_mechanically_rejected(self) -> None:
        self._validate_title("测" * 80, "需求行为可以被独立观察和判断")

    def test_chinese_english_case_and_punctuation_are_not_format_gates(self) -> None:
        self._validate_title(
            "Retry 后重置轮询计数；compareNote 保持原始中文值。",
            "重试后重新计数，返回值符合需求。",
        )

    def test_title_may_equal_observable_result(self) -> None:
        text = "作废原因长度上限为 200 字符"
        self._validate_title(text, text)


if __name__ == "__main__":
    unittest.main()
