from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import common  # noqa: E402
from prepare_case_readiness import build_case_readiness_session_input  # noqa: E402
from prepare_finalization import build_finalization_session_input  # noqa: E402


def model_for(root: Path) -> common.ModuleModel:
    resources: dict[str, common.Resource] = {}
    roles = {
        "global_context": "SRC-GLOBAL",
        "module_requirement": "SRC-MOD",
        "module_context": "CTX",
    }
    for order, resource_id in enumerate((*roles.values(), "FC-001", "DC-001"), start=1):
        path = root / f"{resource_id}.md"
        path.write_text(f"正文-{resource_id}", encoding="utf-8")
        resources[resource_id] = common.Resource(resource_id, path, f"用途-{resource_id}", order)
    map_path = root / "map.md"
    question_path = root / "questions.md"
    map_path.write_text("RSU-MAP-DYNAMIC", encoding="utf-8")
    question_path.write_text("Q-INDEX-DYNAMIC", encoding="utf-8")
    return common.ModuleModel(
        module_dir=root,
        preanalysis_dir=root,
        manifest_path=None,
        manifest_sha256=None,
        artifact_paths={},
        resource_roles=roles,
        module_name="阶段输入测试",
        map_path=map_path,
        question_path=question_path,
        resources=resources,
        rsus=[],
        rsu_by_id={},
        questions={},
    )


def sources_for(model: common.ModuleModel) -> list[tuple[str, Path, str]]:
    ids = ["RSU-MAP", "Q-INDEX", "SRC-GLOBAL", "SRC-MOD", "CTX", "FC-001", "DC-001"]
    paths = {
        "RSU-MAP": model.map_path,
        "Q-INDEX": model.question_path,
        **{resource_id: resource.path for resource_id, resource in model.resources.items()},
    }
    return [(resource_id, paths[resource_id], paths[resource_id].read_text(encoding="utf-8")) for resource_id in ids]


class StageSessionInputTests(unittest.TestCase):
    def test_finalization_session_input_omits_fixed_bodies_but_keeps_dynamic_sources(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model = model_for(Path(temp))
            sources = sources_for(model)
            text = build_finalization_session_input(
                "final-hash", ["CANDIDATE-BODY"], sources, model, "FINALIZATION-RULES", "OUTPUT-CONTRACT"
            )
            self.assertIn("CANDIDATE-BODY", text)
            self.assertIn("RSU-MAP-DYNAMIC", text)
            self.assertIn("Q-INDEX-DYNAMIC", text)
            self.assertIn("正文-FC-001", text)
            self.assertIn("正文-DC-001", text)
            self.assertNotIn("<!-- BEGIN SRC-GLOBAL -->", text)
            self.assertNotIn("<!-- BEGIN SRC-MOD -->", text)
            self.assertNotIn("<!-- BEGIN CTX -->", text)
            for _, path, content in sources:
                self.assertIn(common.display_path(path, model.module_dir), text)
                self.assertIn(common.sha256_text(content), text)

    def test_readiness_session_input_keeps_final_outputs_and_omits_fixed_bodies(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model = model_for(Path(temp))
            text = build_case_readiness_session_input(
                "readiness-hash", "FINAL-TP-BODY", "COVERAGE-BODY", sources_for(model), model,
                "READINESS-RULES", "OUTPUT-CONTRACT",
            )
            self.assertIn("FINAL-TP-BODY", text)
            self.assertIn("COVERAGE-BODY", text)
            self.assertIn("RSU-MAP-DYNAMIC", text)
            self.assertIn("Q-INDEX-DYNAMIC", text)
            self.assertIn("正文-FC-001", text)
            self.assertNotIn("<!-- BEGIN SRC-GLOBAL -->", text)
            self.assertNotIn("<!-- BEGIN SRC-MOD -->", text)
            self.assertNotIn("<!-- BEGIN CTX -->", text)

    def test_stage_session_hash_changes_when_dynamic_source_changes(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model = model_for(Path(temp))
            before = build_finalization_session_input(
                "final-hash", ["CANDIDATE"], sources_for(model), model, "RULES", "CONTRACT"
            )
            model.resources["FC-001"].path.write_text("正文-FC-001-CHANGED", encoding="utf-8")
            after = build_finalization_session_input(
                "final-hash", ["CANDIDATE"], sources_for(model), model, "RULES", "CONTRACT"
            )
            self.assertNotEqual(common.sha256_text(before), common.sha256_text(after))


if __name__ == "__main__":
    unittest.main()
