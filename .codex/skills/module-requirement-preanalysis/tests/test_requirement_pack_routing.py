from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
SKILL_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPT_DIR))

import scaffold_preanalysis as scaffold  # noqa: E402
import validate_preanalysis as validator  # noqa: E402


def write_global_context(root: Path) -> Path:
    context_dir = root / "00-global"
    context_dir.mkdir(parents=True, exist_ok=True)
    context = context_dir / "00-project-context.md"
    context.write_text("# 项目全局上下文\n", encoding="utf-8")
    return context


class RequirementPackRoutingTests(unittest.TestCase):
    def run_scaffold(self, module_root: Path, *extra: str) -> int:
        argv = [
            "scaffold_preanalysis.py",
            str(module_root),
            "--module-name",
            "测试模块",
            *extra,
        ]
        old_argv = sys.argv
        sys.argv = argv
        try:
            return scaffold.main()
        finally:
            sys.argv = old_argv

    def test_module_root_pack_is_referenced_not_copied(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module_root = root / "MOD-01-测试"
            module_root.mkdir()
            (module_root / "00-module-requirement-pack.md").write_text(
                "# 模块需求\n规则一：生成报表。\n", encoding="utf-8"
            )
            write_global_context(root)

            self.assertEqual(self.run_scaffold(module_root), 0)

            manifest = json.loads(
                (module_root / "preanalysis" / "preanalysis-manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                manifest["artifacts"]["module_requirement"],
                "../00-module-requirement-pack.md",
            )
            self.assertFalse(
                (module_root / "preanalysis" / "00-module-requirement-pack.md").exists(),
                "module-root pack must not be duplicated into preanalysis/",
            )
            for name in ("README.md", "01-context-pack.md", "02-sentence-test-point-map.md"):
                text = (module_root / "preanalysis" / name).read_text(encoding="utf-8")
                self.assertIn("../00-module-requirement-pack.md", text)

    def test_identical_duplicate_is_removed_and_conflict_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module_root = root / "MOD-02-测试"
            preanalysis = module_root / "preanalysis"
            preanalysis.mkdir(parents=True)
            pack = module_root / "00-module-requirement-pack.md"
            pack.write_text("# 模块需求\n", encoding="utf-8")
            (preanalysis / "00-module-requirement-pack.md").write_text(
                "# 模块需求\n", encoding="utf-8"
            )
            write_global_context(root)

            # Identical duplicate: scaffold removes it and keeps the module-root pack.
            self.assertEqual(self.run_scaffold(module_root), 0)
            self.assertTrue(pack.is_file())
            self.assertFalse((preanalysis / "00-module-requirement-pack.md").exists())

            # Divergent duplicate: scaffold must refuse.
            (preanalysis / "00-module-requirement-pack.md").write_text(
                "# 模块需求（旧版）\n", encoding="utf-8"
            )
            self.assertEqual(self.run_scaffold(module_root), 2)

    def test_pack_without_module_root_copy_stays_inside_preanalysis(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module_root = root / "MOD-03-测试"
            module_root.mkdir()
            source = root / "requirement.md"
            source.write_text("# 模块需求\n规则二：导出 Excel。\n", encoding="utf-8")
            write_global_context(root)

            self.assertEqual(
                self.run_scaffold(module_root, "--requirement-source", str(source)), 0
            )
            pack = module_root / "preanalysis" / "00-module-requirement-pack.md"
            self.assertTrue(pack.is_file())
            self.assertFalse((module_root / "00-module-requirement-pack.md").exists())

            manifest = json.loads(
                (module_root / "preanalysis" / "preanalysis-manifest.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertEqual(
                manifest["artifacts"]["module_requirement"], "00-module-requirement-pack.md"
            )
            self.assertEqual(
                self.run_scaffold(module_root, "--refresh-manifest"),
                0,
                "re-running scaffold must not demote the pack back outside preanalysis/",
            )
            self.assertTrue(pack.is_file())

    def test_validator_accepts_module_root_pack_and_rejects_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module_root = root / "MOD-04-测试"
            preanalysis = module_root / "preanalysis"
            preanalysis.mkdir(parents=True)
            (module_root / "00-module-requirement-pack.md").write_text(
                "# 模块需求\n", encoding="utf-8"
            )
            write_global_context(root)
            self.run_scaffold(module_root)

            # A fresh skeleton fails validation on analysis placeholders by
            # design; the duplicate check must stay silent for a single pack
            # and must fire once a stale preanalysis/ copy appears.
            baseline_output = self.run_validator(preanalysis)
            self.assertNotIn("duplicate module requirement pack", baseline_output)

            (preanalysis / "00-module-requirement-pack.md").write_text(
                "# 模块需求（旧版）\n", encoding="utf-8"
            )
            duplicate_output = self.run_validator(preanalysis)
            self.assertIn("duplicate module requirement pack", duplicate_output)

    def run_validator(self, preanalysis: Path) -> str:
        import contextlib
        import io

        argv = [
            "validate_preanalysis.py",
            str(preanalysis),
            "--require-canonical-layout",
        ]
        old_argv = sys.argv
        sys.argv = argv
        stdout = io.StringIO()
        try:
            with contextlib.redirect_stdout(stdout):
                validator.main()
        finally:
            sys.argv = old_argv
        return stdout.getvalue()


if __name__ == "__main__":
    unittest.main()
