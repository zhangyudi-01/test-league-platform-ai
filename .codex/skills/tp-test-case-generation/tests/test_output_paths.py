from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import common
import run_generation


class OutputPathTests(unittest.TestCase):
    def test_real_templates_are_loadable(self):
        tp = common.case_document_template("TP-001", "a" * 64, False)
        module = common.module_case_document_template("模块", "b" * 64, False)
        self.assertIn("TP-001", tp)
        self.assertIn("a" * 64, tp)
        self.assertIn("模块", module)
        self.assertIn("b" * 64, module)
        self.assertNotIn("{{", tp + module)

    def test_default_output_is_active_directory(self):
        module = Path("module").resolve()
        with patch.object(common, "resolve_module_layout", return_value=object()), \
             patch.object(common, "parse_module", return_value=object()), \
             patch.object(common, "default_output_dir", return_value=module / "test-points"):
            self.assertEqual(common.module_paths(module, None, None)[3], module / "test-cases")
        config = SimpleNamespace(module_dir=module, case_output_dir=None)
        self.assertEqual(run_generation.resolved_case_output_dir(config), module / "test-cases")
        config.case_output_dir = module / "isolated"
        self.assertEqual(run_generation.resolved_case_output_dir(config), config.case_output_dir)


if __name__ == "__main__":
    unittest.main()
