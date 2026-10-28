from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import common  # noqa: E402
from candidate_validation import validate_candidate_document  # noqa: E402


def create_scope(root: Path) -> tuple[common.ModuleModel, common.InputBundle, Path, Path]:
    module_dir = root / "module"
    module_dir.mkdir()
    resources: dict[str, common.Resource] = {}
    for order, resource_id in enumerate(("SRC-GLOBAL", "SRC-MOD", "CTX"), start=1):
        path = module_dir / f"{resource_id}.md"
        path.write_text(resource_id, encoding="utf-8")
        resources[resource_id] = common.Resource(resource_id, path, resource_id, order)
    rsu = common.RequirementUnit(
        "RSU-001",
        ("RSU-001", "无", "非可作废状态不能执行作废", "SRC-MOD", "作废规则", "无", "无", "captured"),
        1,
        1,
    )
    map_path = module_dir / "map.md"
    question_path = module_dir / "questions.md"
    map_path.write_text("map", encoding="utf-8")
    question_path.write_text("questions", encoding="utf-8")
    model = common.ModuleModel(
        module_dir=module_dir,
        preanalysis_dir=module_dir,
        manifest_path=None,
        manifest_sha256=None,
        artifact_paths={},
        resource_roles={
            "global_context": "SRC-GLOBAL",
            "module_requirement": "SRC-MOD",
            "module_context": "CTX",
        },
        module_name="候选质量模块",
        map_path=map_path,
        question_path=question_path,
        resources=resources,
        rsus=[rsu],
        rsu_by_id={"RSU-001": rsu},
        questions={},
    )
    rendered = "authoritative input\n"
    bundle = common.InputBundle(
        rsu=rsu,
        input_sha256="input-business-hash",
        blockers=[],
        allowed_rsu_ids=["RSU-001", "RSU-002"],
        allowed_q_ids=[],
        allowed_context_ids=["SRC-GLOBAL", "SRC-MOD", "CTX"],
        required_context_ids=["SRC-GLOBAL", "SRC-MOD", "CTX"],
        fixed_materials=[],
        dynamic_materials=[],
        evidence_materials=[],
        supporting_rsus=[],
        questions=[],
        rendered=rendered,
        session_rendered="session input\n",
        session_input_sha256="session-hash",
        session_source_fingerprint_sha256="foundation-hash",
    )
    input_file = module_dir / "RSU-001-input.md"
    candidate_file = module_dir / "RSU-001.md"
    input_file.write_text(rendered, encoding="utf-8")
    return model, bundle, input_file, candidate_file


def candidate_document(result: str, rows: list[list[str]], zero_reason: str = "无") -> str:
    headers = common.CANDIDATE_HEADERS
    lines = [
        "# RSU-001 测试点候选",
        "",
        "## 生成元数据",
        "",
        "| 字段 | 值 |",
        "|---|---|",
        "| RSU-ID | `RSU-001` |",
        "| 输入 SHA-256 | `input-business-hash` |",
        f"| 生成结果 | `{result}` |",
        "",
        "## 候选测试点",
        "",
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    lines.extend(["", "## 零候选说明", "", zero_reason, ""])
    return "\n".join(lines)


def valid_row(candidate_id: str = "CAND-RSU-001-001") -> list[str]:
    return [
        candidate_id,
        "RSU-001",
        "RSU-001",
        "业务规则",
        "非可作废状态阻止作废",
        "页面入口、接口响应和数据保持共同证明作废被拦截",
        "无",
        "SRC-GLOBAL、SRC-MOD、CTX",
        "原文内容：非可作废状态不能执行作废。",
    ]


class CandidateQualityTests(unittest.TestCase):
    def test_zero_candidate_with_auditable_reason_is_valid(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, bundle, input_file, candidate_file = create_scope(Path(temp))
            candidate_file.write_text(
                candidate_document(
                    "zero-candidate",
                    [],
                    "原文内容：该句仅定义术语，已由同批主规则完整覆盖，未形成独立可验证行为。",
                ),
                encoding="utf-8",
            )
            document, _ = validate_candidate_document(model, bundle, input_file, candidate_file)
            self.assertEqual(document.result, "zero-candidate")
            self.assertEqual(document.rows, [])

    def test_single_business_risk_accepts_one_candidate_with_multiple_observations(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, bundle, input_file, candidate_file = create_scope(Path(temp))
            candidate_file.write_text(
                candidate_document("candidates", [valid_row()]),
                encoding="utf-8",
            )
            document, _ = validate_candidate_document(model, bundle, input_file, candidate_file)
            self.assertEqual(len(document.rows), 1)
            self.assertIn("页面入口、接口响应和数据保持", document.rows[0][5])

    def test_exact_duplicate_candidate_is_accepted_for_parent_deduplication(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, bundle, input_file, candidate_file = create_scope(Path(temp))
            duplicate = valid_row("CAND-RSU-001-002")
            candidate_file.write_text(
                candidate_document("candidates", [valid_row(), duplicate]),
                encoding="utf-8",
            )
            document, _ = validate_candidate_document(model, bundle, input_file, candidate_file)
            self.assertEqual(len(document.rows), 2)

    def test_candidate_missing_primary_source_coverage_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, bundle, input_file, candidate_file = create_scope(Path(temp))
            row = valid_row()
            row[2] = "RSU-002"
            candidate_file.write_text(candidate_document("candidates", [row]), encoding="utf-8")
            with self.assertRaisesRegex(common.WorkflowError, "Source RSUs must include RSU-001"):
                validate_candidate_document(model, bundle, input_file, candidate_file)

    def test_candidate_missing_required_context_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, bundle, input_file, candidate_file = create_scope(Path(temp))
            row = valid_row()
            row[7] = "SRC-MOD、CTX"
            candidate_file.write_text(candidate_document("candidates", [row]), encoding="utf-8")
            with self.assertRaisesRegex(common.WorkflowError, "missing required Context Refs"):
                validate_candidate_document(model, bundle, input_file, candidate_file)

    def test_complex_scope_override_allows_cross_rsu_question_and_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, bundle, input_file, candidate_file = create_scope(Path(temp))
            context_path = model.module_dir / "FC-009.md"
            context_path.write_text("scope context", encoding="utf-8")
            model.resources["FC-009"] = common.Resource("FC-009", context_path, "scope", 9)
            row = valid_row()
            row[2] = "RSU-001、RSU-002"
            row[6] = "Q-009"
            row[7] = "SRC-GLOBAL、SRC-MOD、CTX、FC-009"
            candidate_file.write_text(candidate_document("candidates", [row]), encoding="utf-8")

            document, _ = validate_candidate_document(
                model,
                bundle,
                input_file,
                candidate_file,
                allowed_rsu_ids={"RSU-001", "RSU-002"},
                allowed_q_ids={"Q-009"},
                allowed_context_ids={"SRC-GLOBAL", "SRC-MOD", "CTX", "FC-009"},
            )

            self.assertEqual(len(document.rows), 1)

    def test_complex_scope_override_rejects_question_outside_scope(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            model, bundle, input_file, candidate_file = create_scope(Path(temp))
            row = valid_row()
            row[6] = "Q-010"
            candidate_file.write_text(candidate_document("candidates", [row]), encoding="utf-8")

            with self.assertRaisesRegex(common.WorkflowError, "questions not materialized"):
                validate_candidate_document(
                    model,
                    bundle,
                    input_file,
                    candidate_file,
                    allowed_rsu_ids={"RSU-001"},
                    allowed_q_ids={"Q-009"},
                    allowed_context_ids={"SRC-GLOBAL", "SRC-MOD", "CTX"},
                )


if __name__ == "__main__":
    unittest.main()
