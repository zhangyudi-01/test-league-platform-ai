"""Business-column migration across Worker, Markdown and downstream loaders."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from test_adaptive_worker import FakeRsu, baseline_result, candidate, make_model
from adaptive_worker import (
    COMPLEX_GENERATION_SCHEMA,
    GENERATION_POLICY,
    SEMANTIC_BASELINE_SCHEMA,
    build_deterministic_final_intents,
    compile_baseline_worker_packet,
    complex_generation_json_schema,
    render_candidate_artifacts,
    render_final_artifacts,
    semantic_baseline_json_schema,
    validate_semantic_baseline_result,
    write_worker_schemas,
)
from candidate_validation import _require_nonempty
from common import (
    CANDIDATE_HEADERS,
    FINAL_HEADERS,
    LEGACY_CANDIDATE_HEADERS,
    LEGACY_FINAL_HEADERS,
    WorkflowError,
    candidate_headers,
    final_headers,
    markdown_table,
    parse_candidate_document,
    parse_final_document,
    sha256_text,
)
from validate_module_test_points import require_nonempty


SKILL_DIR = Path(__file__).resolve().parents[1]
FULL_POINT = "点击【重置】，彩票年与任务状态恢复为全部、奖期编号清空，不自动查询。"


class BusinessColumnsTests(unittest.TestCase):
    def model_and_result(self, root):
        rsus = [FakeRsu("RSU-001", "查询", "重置恢复默认值", "SRC-MOD", 1)]
        model = make_model(root, rsus)
        row = candidate("c1", "RSU-001", FULL_POINT)
        row["test_item"] = "重置"
        return model, baseline_result(rsus, [row], "b" * 64)

    def render(self, root, *, data_closure=False):
        model, result = self.model_and_result(root)
        validate_semantic_baseline_result(result, model, "b" * 64)
        model.data_closure_enabled = data_closure
        assigned = render_candidate_artifacts(
            result, model,
            {"rsus": [{"rsu_id": "RSU-001", "current_input_sha256": "c" * 64}]},
            root,
        )
        render_final_artifacts(result, model, root, "d" * 64, assigned)
        return model, result

    def test_runtime_schemas_require_new_fields_and_allow_empty_remarks(self):
        for schema, version in (
            (semantic_baseline_json_schema(), SEMANTIC_BASELINE_SCHEMA),
            (complex_generation_json_schema(), COMPLEX_GENERATION_SCHEMA),
        ):
            with self.subTest(version=version):
                self.assertEqual(schema["properties"]["schema"]["const"], version)
                row_schema = schema["properties"]["candidates"]["items"]
                for field in ("test_item", "test_point", "remarks"):
                    self.assertIn(field, row_schema["required"])
                self.assertFalse(row_schema["additionalProperties"])
                self.assertNotIn("minLength", row_schema["properties"]["remarks"])
                for old_field in ("dimension", "title", "observable_results"):
                    self.assertNotIn(old_field, row_schema["properties"])

    def test_packaged_schema_markers_match_generated_schema_versions(self):
        with tempfile.TemporaryDirectory() as temp:
            paths = write_worker_schemas(Path(temp))
            for path in paths:
                marker = json.loads((SKILL_DIR / "assets" / "schemas" / path.name).read_text(encoding="utf-8"))
                generated = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(marker["schema"], generated["properties"]["schema"]["const"])

    def test_worker_packet_receives_actual_business_policy_and_schema(self):
        with tempfile.TemporaryDirectory() as temp:
            model, _ = self.model_and_result(Path(temp))
            business = "原文：重置恢复默认值且不自动查询。"
            packet, _, _ = compile_baseline_worker_packet(
                model, business, sha256_text(business), "a" * 64,
                semantic_baseline_json_schema(),
            )
            self.assertIn(GENERATION_POLICY.strip(), packet)
            self.assertIn('"test_item"', packet)
            self.assertIn('"test_point"', packet)
            self.assertIn('"remarks"', packet)

    def test_semantic_validator_accepts_empty_remarks(self):
        with tempfile.TemporaryDirectory() as temp:
            model, result = self.model_and_result(Path(temp))
            validated = validate_semantic_baseline_result(result, model, "b" * 64)
            self.assertEqual(validated["candidates"][0]["remarks"], "")
            self.assertEqual(validated["final_intents"][0]["test_point"], FULL_POINT)

    def test_semantic_validator_rejects_blank_required_fields_and_nonstring_notes(self):
        for field, value in (("test_item", " "), ("test_point", ""), ("remarks", None)):
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temp:
                model, result = self.model_and_result(Path(temp))
                result["candidates"][0][field] = value
                with self.assertRaises(WorkflowError):
                    validate_semantic_baseline_result(result, model, "b" * 64)

    def test_old_json_result_is_not_reused_as_new_semantics(self):
        with tempfile.TemporaryDirectory() as temp:
            model, result = self.model_and_result(Path(temp))
            row = result["candidates"][0]
            row["dimension"] = row.pop("test_item")
            row["title"] = row.pop("test_point")
            row["observable_results"] = row.pop("remarks")
            with self.assertRaises(WorkflowError):
                validate_semantic_baseline_result(result, model, "b" * 64)
            model, result = self.model_and_result(Path(temp))
            result["schema"] = "rsu-test-point-generation/semantic-baseline-v4"
            with self.assertRaises(WorkflowError):
                validate_semantic_baseline_result(result, model, "b" * 64)

    def test_rendered_markdown_keeps_full_point_and_empty_notes_with_or_without_dc(self):
        for dc in (False, True):
            with self.subTest(data_closure=dc), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.render(root, data_closure=dc)
                cand = parse_candidate_document(root / "by-rsu" / "RSU-001.md", dc)
                final = parse_final_document(root / "module-test-points.md", dc)
                self.assertEqual(cand.headers, candidate_headers(dc))
                self.assertEqual(final.headers, final_headers(dc))
                for document in (cand, final):
                    row = document.rows[0]
                    self.assertEqual(row[3:6], ["重置", FULL_POINT, ""])
                    self.assertIn("SRC-GLOBAL", row[document.headers.index("Context Refs")])
                    if dc:
                        self.assertEqual(row[document.headers.index("Data Closure Refs")], "无")
                _require_nonempty(cand.rows[0], 1, cand.headers)
                require_nonempty(final.rows[0], "TP-001", final.headers)

    def test_cell_validation_only_allows_notes_to_be_empty(self):
        for headers, check in (
            (CANDIDATE_HEADERS, lambda row: _require_nonempty(row, 1, CANDIDATE_HEADERS)),
            (FINAL_HEADERS, lambda row: require_nonempty(row, "TP-001", FINAL_HEADERS)),
        ):
            row = ["value"] * len(headers)
            row[headers.index("备注")] = ""
            check(row)
            for field in ("测试项", "测试点", "Context Refs"):
                with self.subTest(headers=headers, field=field):
                    invalid = row.copy()
                    invalid[headers.index(field)] = ""
                    with self.assertRaises(WorkflowError):
                        check(invalid)

    def test_legacy_markdown_readers_preserve_actual_headers_and_observable_results(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.render(root)
            for path, parser, old_headers in (
                (root / "by-rsu" / "RSU-001.md", parse_candidate_document, LEGACY_CANDIDATE_HEADERS),
                (root / "module-test-points.md", parse_final_document, LEGACY_FINAL_HEADERS),
            ):
                document = parser(path)
                row = document.rows[0].copy()
                row[3:6] = ["查询条件", "重置恢复默认值", FULL_POINT]
                text = path.read_text(encoding="utf-8")
                text = text.replace(markdown_table(document.headers, document.rows), markdown_table(old_headers, [row]))
                path.write_text(text, encoding="utf-8")
                legacy = parser(path)
                self.assertEqual(legacy.headers, old_headers)
                self.assertEqual(legacy.rows[0][5], FULL_POINT)

    def test_mixed_or_duplicate_business_tables_are_rejected(self):
        for duplicate in (False, True):
            with self.subTest(duplicate=duplicate), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                self.render(root)
                for path, parser, old_headers in (
                    (root / "by-rsu" / "RSU-001.md", parse_candidate_document, LEGACY_CANDIDATE_HEADERS),
                    (root / "module-test-points.md", parse_final_document, LEGACY_FINAL_HEADERS),
                ):
                    document = parser(path)
                    headers = document.headers if duplicate else old_headers
                    text = path.read_text(encoding="utf-8") + "\n" + markdown_table(headers, document.rows)
                    path.write_text(text, encoding="utf-8")
                    with self.assertRaises(WorkflowError):
                        parser(path)

    def test_exact_dedup_preserves_sources_but_not_different_notes_or_rules(self):
        first = candidate("c1", "RSU-001", FULL_POINT)
        duplicate = candidate("c2", "RSU-002", FULL_POINT + " ")
        noted = candidate("c3", "RSU-001", FULL_POINT)
        noted["remarks"] = "原型与需求正文不一致，以已确认正文为准。"
        different = candidate("c4", "RSU-001", "点击【查询】，按当前条件刷新列表。")
        intents = build_deterministic_final_intents([first, duplicate, noted, different])
        self.assertEqual([row["source_candidate_keys"] for row in intents], [["c1", "c2"], ["c3"], ["c4"]])
        self.assertEqual(intents[0]["test_point"], FULL_POINT)
        self.assertEqual(intents[1]["remarks"], noted["remarks"])

    def test_downstream_test_case_loader_preserves_new_business_columns(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            self.render(root)
            downstream_scripts = SKILL_DIR.parent / "tp-test-case-generation" / "scripts"
            code = (
                "import json,sys; from pathlib import Path; from types import SimpleNamespace; "
                "sys.path.insert(0,sys.argv[1]); from common import load_final_test_points; "
                "model=SimpleNamespace(data_closure_enabled=False,resources=dict.fromkeys(['SRC-GLOBAL','SRC-MOD','CTX'])); "
                "points,_,_=load_final_test_points(Path(sys.argv[2]),model); "
                "print(json.dumps({'headers':points[0].headers,'cells':points[0].cells},ensure_ascii=True))"
            )
            result = subprocess.run(
                [sys.executable, "-c", code, str(downstream_scripts), str(root)],
                capture_output=True, text=True, encoding="utf-8", check=True,
            )
            loaded = json.loads(result.stdout)
            self.assertEqual(loaded["headers"], list(FINAL_HEADERS))
            self.assertEqual(loaded["cells"][3:6], ["重置", FULL_POINT, ""])


if __name__ == "__main__":
    unittest.main()
