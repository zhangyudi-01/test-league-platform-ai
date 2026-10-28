from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import common  # noqa: E402


def create_model(root: Path) -> tuple[common.ModuleModel, Path]:
    module_dir = root / "module"
    output_dir = module_dir / "test-points"
    source_dir = module_dir / "preanalysis"
    source_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    map_path = source_dir / "02-sentence-test-point-map.md"
    map_path.write_text("map", encoding="utf-8")

    resources: dict[str, common.Resource] = {}
    for index, (resource_id, filename, purpose) in enumerate(
        (
            ("SRC-GLOBAL", "global context.md", "项目背景"),
            ("SRC-MOD", "module.md", "模块需求"),
            ("CTX", "context.md", "页面 | 业务边界"),
            ("FC-001", "card.md", "补充上下文"),
        ),
        start=1,
    ):
        path = source_dir / filename
        path.write_text(resource_id, encoding="utf-8")
        resources[resource_id] = common.Resource(resource_id, path, purpose, index)

    model = common.ModuleModel(
        module_dir=module_dir,
        preanalysis_dir=source_dir,
        manifest_path=None,
        manifest_sha256=None,
        artifact_paths={},
        resource_roles={
            "global_context": "SRC-GLOBAL",
            "module_requirement": "SRC-MOD",
            "module_context": "CTX",
        },
        module_name="测试模块",
        map_path=map_path,
        question_path=source_dir / "03-clarification-questions.md",
        resources=resources,
        rsus=[],
        rsu_by_id={},
        questions={},
    )
    return model, output_dir


class ContextResourceIndexTests(unittest.TestCase):
    def test_index_contains_only_final_refs_in_map_order(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, output_dir = create_model(Path(temp))

            rendered = common.render_context_resource_index(
                model,
                iter(("FC-001", "SRC-MOD", "CTX")),
                output_dir,
            )

            self.assertNotIn("SRC-GLOBAL", rendered)
            self.assertLess(rendered.index("SRC-MOD"), rendered.index("CTX"))
            self.assertLess(rendered.index("CTX"), rendered.index("FC-001"))
            self.assertIn("../preanalysis/module.md", rendered)
            self.assertIn("页面 \\| 业务边界", rendered)
            tables = common.find_tables(
                common.extract_tables(rendered),
                common.RESOURCE_HEADERS,
            )
            self.assertEqual(len(tables), 1)
            self.assertEqual(len(tables[0].rows), 3)

    def test_index_uses_clickable_encoded_target_and_readable_path(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, output_dir = create_model(Path(temp))

            rendered = common.render_context_resource_index(
                model,
                iter(("SRC-GLOBAL",)),
                output_dir,
            )

            self.assertIn("[../preanalysis/global context.md]", rendered)
            self.assertIn("(<../preanalysis/global%20context.md>)", rendered)

    def test_template_block_is_replaced_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, output_dir = create_model(Path(temp))
            template = common.context_resource_index_template(model, output_dir)

            once = common.replace_context_resource_index(
                template,
                model,
                iter(("CTX",)),
                output_dir,
            )
            twice = common.replace_context_resource_index(
                once,
                model,
                iter(("CTX",)),
                output_dir,
            )

            self.assertEqual(once, twice)
            self.assertIn("| CTX |", once)
            self.assertNotIn("通过校验后，此处自动生成", once)

    def test_empty_final_result_has_explicit_empty_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, output_dir = create_model(Path(temp))

            rendered = common.render_context_resource_index(
                model,
                iter(()),
                output_dir,
            )

            self.assertEqual(rendered, "最终测试点未引用上下文资源。")

    def test_legacy_document_gets_controlled_block_on_validation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, output_dir = create_model(Path(temp))

            rendered = common.replace_context_resource_index(
                "# 模块最终测试点\n\n## 生成元数据\n\nmetadata\n\n## 最终测试点\n\nfinal table\n",
                model,
                iter(("CTX",)),
                output_dir,
            )

            self.assertIn("## 上下文资源入口", rendered)
            self.assertIn("| CTX |", rendered)
            self.assertLess(rendered.index("## 上下文资源入口"), rendered.index("## 最终测试点"))

    def test_incomplete_controlled_block_requires_repreparation(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, output_dir = create_model(Path(temp))

            with self.assertRaisesRegex(common.WorkflowError, "rerun prepare_finalization"):
                common.replace_context_resource_index(
                    "# 模块最终测试点\n" + common.CONTEXT_RESOURCE_INDEX_BEGIN,
                    model,
                    iter(("CTX",)),
                    output_dir,
                )


if __name__ == "__main__":
    unittest.main()
