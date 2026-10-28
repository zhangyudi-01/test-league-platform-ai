from __future__ import annotations

import json
import re
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

from sql_assets import (  # noqa: E402
    SqlAssetError,
    _prepared_statement,
    find_database_config,
    load_database_config,
    load_registry,
    relevant_assets_index_text,
    relevant_assets_manifest,
    registry_manifest,
    require_current_validation,
    sha256_file,
    validate_assets,
)
from common import (  # noqa: E402
    WorkflowError,
    _require_case_execution_quality,
    _require_data_execution_rows,
    _require_multi_case_justifications,
    parse_case_variables,
    parse_case_document,
)
from validate_module_test_cases import _validate_final_sql  # noqa: E402
from sql_convergence import analyze_convergence, render_report, write_convergence_report  # noqa: E402


def write_assets(root: Path, assets: list[dict]) -> Path:
    sql_dir = root / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema_version": "tp-test-case-generation/sql-assets-v1",
        "assets": assets,
    }
    (sql_dir / "sql-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False), encoding="utf-8"
    )
    for asset in assets:
        (sql_dir / asset["file"]).write_text(asset["sql"], encoding="utf-8")
    return root


def write_asset(
    root: Path,
    *,
    sql: str,
    statement_type: str = "SELECT",
    parameters=None,
    sql_id: str = "SQL-001",
    data_closure_refs=None,
) -> Path:
    return write_assets(
        root,
        [
            {
                "sql_id": sql_id,
                "file": f"{sql_id}.sql",
                "statement_type": statement_type,
                "purpose": "test asset",
                "data_closure_refs": data_closure_refs or ["DC-001"],
                "parameters": parameters or {},
                "sql": sql,
            }
        ],
    )


class FakeCursor:
    def __init__(self) -> None:
        self.calls: list[tuple[str, object]] = []

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def execute(self, statement, values=None):
        self.calls.append((statement, values))

    def fetchone(self):
        return ("8.0-test",)

    def fetchall(self):
        return []


class FakeConnection:
    def __init__(self) -> None:
        self.cursor_instance = FakeCursor()
        self.rollback_count = 0
        self.close_count = 0

    def cursor(self):
        return self.cursor_instance

    def rollback(self):
        self.rollback_count += 1

    def close(self):
        self.close_count += 1


class FailingCursor(FakeCursor):
    def execute(self, statement, values=None):
        self.calls.append((statement, values))
        if statement.startswith("EXPLAIN "):
            raise RuntimeError("invalid column")


class FailingConnection(FakeConnection):
    def __init__(self) -> None:
        super().__init__()
        self.cursor_instance = FailingCursor()


def format_case(precondition: str, expected: str) -> list[str]:
    step_count = len(re.split(r"<br\s*/?>", expected, flags=re.IGNORECASE))
    steps = "<br>".join(
        f"{index}. 点击页面中的目标控件 {index}。" for index in range(1, step_count + 1)
    )
    return [
        "TC-001", "当前迭代", "测试项", "测试点", "无",
        precondition,
        steps,
        "无",
        expected,
        "未执行", "未执行", "未执行",
    ]


class CaseExecutionFormatTests(unittest.TestCase):
    def test_accepts_scenario_specific_precondition_categories(self) -> None:
        case = format_case(
            "页面状态：<br>已打开文件核查页面。<br>页面已完成列表加载。<br>"
            "Mock配置：<br>IN17返回校验一致结果。<br>"
            "操作准备：<br>选中一条可重新推送的文件。",
            "1. 第一项结果可观察。<br>2. 第二项结果可观察。",
        )

        _require_case_execution_quality("TC-001", case, set(), {})


class SqlConvergenceTests(unittest.TestCase):
    def test_reports_exact_duplicates_and_references(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_assets(
                root,
                [
                    {
                        "sql_id": "SQL-A",
                        "file": "SQL-A.sql",
                        "statement_type": "SELECT",
                        "purpose": "same query",
                        "data_closure_refs": ["DC-001"],
                        "parameters": {},
                        "sql": "-- comment\nSELECT id FROM task WHERE status_code = 1;\n",
                    },
                    {
                        "sql_id": "SQL-B",
                        "file": "SQL-B.sql",
                        "statement_type": "SELECT",
                        "purpose": "same query",
                        "data_closure_refs": ["DC-001"],
                        "parameters": {},
                        "sql": " select  id  from TASK where status_code = 1 ",
                    },
                ],
            )
            (root / "by-tp").mkdir()
            (root / "by-tp" / "TP-001.md").write_text(
                "步骤引用 SQL-B / SQL-B.sql", encoding="utf-8"
            )
            (root / "inputs").mkdir()
            (root / "inputs" / "TP-001-input.md").write_text(
                "动态索引也包含 SQL-B", encoding="utf-8"
            )

            analysis = analyze_convergence(root)
            self.assertEqual(analysis["exact_duplicate_groups"][0]["sql_ids"], ["SQL-A", "SQL-B"])
            self.assertEqual(
                analysis["exact_duplicate_groups"][0]["references"]["SQL-B"],
                ["by-tp/TP-001.md"],
            )
            report = render_report(root, analysis)
            self.assertIn("必须复用/合并", report)
            self.assertIn("SQL-B", report)

    def test_reports_where_variants_but_does_not_call_them_exact(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_assets(
                root,
                [
                    {
                        "sql_id": "SQL-A",
                        "file": "SQL-A.sql",
                        "statement_type": "SELECT",
                        "purpose": "status one",
                        "data_closure_refs": ["DC-001"],
                        "parameters": {},
                        "sql": "SELECT id FROM task WHERE status_code = 1 ORDER BY id",
                    },
                    {
                        "sql_id": "SQL-B",
                        "file": "SQL-B.sql",
                        "statement_type": "SELECT",
                        "purpose": "status two",
                        "data_closure_refs": ["DC-001"],
                        "parameters": {},
                        "sql": "SELECT id FROM task WHERE status_code = 2 ORDER BY id",
                    },
                ],
            )
            analysis = analyze_convergence(root)
            self.assertEqual(analysis["exact_duplicate_groups"], [])
            self.assertEqual(
                analysis["where_variant_groups"][0]["sql_ids"], ["SQL-A", "SQL-B"]
            )
            self.assertIn("建议人工评估参数化", render_report(root, analysis))

    def test_quoted_value_difference_is_not_an_exact_duplicate(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_assets(
                root,
                [
                    {
                        "sql_id": "SQL-A",
                        "file": "SQL-A.sql",
                        "statement_type": "SELECT",
                        "purpose": "quoted A",
                        "data_closure_refs": ["DC-001"],
                        "parameters": {},
                        "sql": "SELECT CASE WHEN id = 1 THEN 'A' END AS label FROM task",
                    },
                    {
                        "sql_id": "SQL-B",
                        "file": "SQL-B.sql",
                        "statement_type": "SELECT",
                        "purpose": "quoted a",
                        "data_closure_refs": ["DC-001"],
                        "parameters": {},
                        "sql": "SELECT CASE WHEN id = 1 THEN 'a' END AS label FROM task",
                    },
                ],
            )
            analysis = analyze_convergence(root)
            self.assertEqual(analysis["exact_duplicate_groups"], [])

    def test_writes_empty_report_when_no_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(root, sql="SELECT 1", parameters={})
            report_path = write_convergence_report(root)
            self.assertTrue(report_path.is_file())
            self.assertIn("## 完全重复资产", report_path.read_text(encoding="utf-8"))
            self.assertIn("未发现。", report_path.read_text(encoding="utf-8"))


class MultiCaseJustificationTests(unittest.TestCase):
    @staticmethod
    def trace(tc_id: str, explanation: str) -> list[str]:
        return [tc_id, "场景", "TP-001", "RSU-001", "无", "SRC-GLOBAL、SRC-MOD、CTX", "无", "无", explanation]

    def test_single_case_does_not_require_fixed_justification_fields(self) -> None:
        _require_multi_case_justifications([
            self.trace("TC-TP-001-001", "覆盖当前测试点的完整业务规则。")
        ])

    def test_multiple_cases_accept_four_non_empty_justification_fields(self) -> None:
        explanation = (
            "独立业务风险=权限绕过；"
            "不可合并前置或操作=需要无权限账号直接调用接口；"
            "独立可判断预期=服务端拒绝且数据不变；"
            "独立回归价值=后端鉴权可单独回归"
        )
        _require_multi_case_justifications([
            self.trace("TC-TP-001-001", explanation),
            self.trace("TC-TP-001-002", explanation),
        ])

    def test_multiple_cases_reject_missing_field(self) -> None:
        explanation = (
            "独立业务风险=风险A；不可合并前置或操作=操作A；"
            "独立可判断预期=结果A"
        )
        with self.assertRaisesRegex(WorkflowError, "独立回归价值"):
            _require_multi_case_justifications([
                self.trace("TC-TP-001-001", explanation),
                self.trace("TC-TP-001-002", explanation),
            ])

    def test_multiple_cases_reject_empty_or_not_applicable_value(self) -> None:
        explanation = (
            "独立业务风险=风险A；不可合并前置或操作=无；"
            "独立可判断预期=结果A；独立回归价值=价值A"
        )
        with self.assertRaisesRegex(WorkflowError, "不可合并前置或操作"):
            _require_multi_case_justifications([
                self.trace("TC-TP-001-001", explanation),
                self.trace("TC-TP-001-002", explanation),
            ])

    def test_accepts_one_meaningful_precondition_category(self) -> None:
        case = format_case(
            "用户状态：<br>用户已登录并进入目标模块。",
            "1. 结果可观察。",
        )

        _require_case_execution_quality("TC-001", case, set(), {})


class CaseVariableParsingTests(unittest.TestCase):
    def test_accepts_underscore_parameter_names(self) -> None:
        variables = parse_case_variables("报告年:$REPORT_YEAR；报告月:$REPORT_MONTH", "数据变量")
        self.assertEqual(set(variables), {"REPORT_YEAR", "REPORT_MONTH"})

    def test_accepts_descriptive_field_names_without_language_or_case_constraints(self) -> None:
        value = (
            "文件:$A（示例：一个状态为推送失败的文件）；"
            "FileID:$B；"
            "selected FILE = $C；"
            "文件状态（待推送）：$D"
        )

        variables = parse_case_variables(value, "数据变量")

        self.assertEqual(variables["A"], ("文件", ""))
        self.assertEqual(variables["B"], ("FileID", ""))
        self.assertEqual(variables["C"], ("selected FILE", ""))
        self.assertEqual(variables["D"], ("文件状态", ""))

    def test_accepts_multiple_declarations_separated_by_chinese_or_english_semicolons(self) -> None:
        variables = parse_case_variables("文件A:$A; 文件B:$B", "数据变量")

        self.assertEqual(set(variables), {"A", "B"})

    def test_rejects_empty_field_description(self) -> None:
        with self.assertRaisesRegex(WorkflowError, "non-empty field description"):
            parse_case_variables(":$A", "数据变量")

    def test_rejects_declaration_without_a_single_variable(self) -> None:
        with self.assertRaisesRegex(WorkflowError, "exactly one data variable"):
            parse_case_variables("文件编号", "数据变量")

        with self.assertRaisesRegex(WorkflowError, "exactly one data variable"):
            parse_case_variables("文件:$A,$B", "数据变量")

    def test_rejects_duplicate_variables_and_duplicate_field_descriptions(self) -> None:
        with self.assertRaisesRegex(WorkflowError, r"repeats variable \$A"):
            parse_case_variables("文件A:$A；文件B:$A", "数据变量")

        with self.assertRaisesRegex(WorkflowError, "repeats field"):
            parse_case_variables("File ID:$A； file   id:$B", "数据变量")

class CaseDocumentDiagnosticsTests(unittest.TestCase):
    def test_trace_table_error_reports_expected_and_observed_headers(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "TP-001.md"
            path.write_text(
                "# TP-001 - 测试用例\n\n"
                "## 生成元数据\n\n"
                "| 字段 | 值 |\n|---|---|\n| TP-ID | `TP-001` |\n| 输入 SHA-256 | `hash` |\n| 生成结果 | validated |\n\n"
                "## 自定义追溯\n\n"
                "| TC-ID | TP-ID |\n|---|---|\n| TC-001 | TP-001 |\n",
                encoding="utf-8",
            )

            with self.assertRaises(WorkflowError) as context:
                parse_case_document(path)
            message = str(context.exception)
            self.assertIn(
                "expected exact header: TC-ID | 覆盖场景 | TP-ID | RSU Refs",
                message,
            )
            self.assertIn("observed headers: 字段 | 值；TC-ID | TP-ID", message)

    def test_accepts_numbered_precondition_category_and_content(self) -> None:
        case = format_case(
            "1. 环境配置：<br>1. 已配置可访问的第三方存证服务。<br>2. 轮询参数已生效。",
            "1. 结果可观察。",
        )

        _require_case_execution_quality("TC-001", case, set(), {})

    def test_accepts_simple_precondition_without_category(self) -> None:
        case = format_case(
            "用户已登录并进入目标模块。",
            "1. 结果可观察。",
        )

        _require_case_execution_quality("TC-001", case, set(), {})

    def test_rejects_precondition_category_without_line_break(self) -> None:
        case = format_case(
            "页面状态：已打开文件核查页面。",
            "1. 结果可观察。",
        )

        with self.assertRaisesRegex(WorkflowError, "separated with <br>"):
            _require_case_execution_quality("TC-001", case, set(), {})

    def test_rejects_precondition_category_without_content(self) -> None:
        case = format_case(
            "页面状态：<br>Mock配置：<br>IN17返回校验一致结果。",
            "1. 结果可观察。",
        )

        with self.assertRaisesRegex(WorkflowError, "must contain a concrete description"):
            _require_case_execution_quality("TC-001", case, set(), {})

    def test_rejects_generic_precondition_content_under_custom_category(self) -> None:
        case = format_case(
            "测试准备：<br>准备测试数据。",
            "1. 结果可观察。",
        )

        with self.assertRaisesRegex(WorkflowError, "must contain a concrete executable description"):
            _require_case_execution_quality("TC-001", case, set(), {})

    def test_rejects_multiple_precondition_sentences_on_one_line(self) -> None:
        case = format_case(
            "任务状态：<br>任务处于进行中。文件处于待推送状态。",
            "1. 结果可观察。",
        )

        with self.assertRaisesRegex(WorkflowError, "multiple sentences on one line"):
            _require_case_execution_quality("TC-001", case, set(), {})

    def test_rejects_expected_result_without_number(self) -> None:
        case = format_case(
            "页面状态：<br>已打开文件核查页面。",
            "结果可观察。",
        )

        with self.assertRaisesRegex(WorkflowError, "each line must start with a numbered item"):
            _require_case_execution_quality("TC-001", case, set(), {})

    def test_rejects_noncontiguous_expected_result_numbers(self) -> None:
        case = format_case(
            "页面状态：<br>已打开文件核查页面。",
            "1. 第一项结果。<br>3. 第三项结果。",
        )

        with self.assertRaisesRegex(WorkflowError, "numbering must be contiguous from 1"):
            _require_case_execution_quality("TC-001", case, set(), {})


class SqlAssetTests(unittest.TestCase):
    def test_relevant_sql_input_is_metadata_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = write_asset(
                Path(temp),
                sql="SELECT 'SQL-BODY-MUST-NOT-BE-EMBEDDED' AS sentinel",
                data_closure_refs=["DC-001"],
            )

            index = relevant_assets_index_text(root, ("DC-001",))
            manifest = relevant_assets_manifest(root, ("DC-001",))

            self.assertIn("SQL-001.sql", index)
            self.assertIn("test asset", index)
            self.assertNotIn("SQL-BODY-MUST-NOT-BE-EMBEDDED", index)
            self.assertEqual([item["sql_id"] for item in manifest["assets"]], ["SQL-001"])

    def test_case_scenario_examples_need_not_equal_shared_sql_explain_examples(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_assets(
                root,
                [
                    {
                        "sql_id": "SQL-ONE",
                        "file": "SQL-ONE.sql",
                        "statement_type": "SELECT",
                        "purpose": "first snapshot",
                        "data_closure_refs": ["DC-001"],
                        "parameters": {
                            "A": {"description": "batch", "example": 30024},
                            "B": {"description": "file", "example": 31024},
                        },
                        "sql": "-- :A batch; :B file\nSELECT 1 WHERE :A = :A AND :B = :B",
                    },
                    {
                        "sql_id": "SQL-TWO",
                        "file": "SQL-TWO.sql",
                        "statement_type": "SELECT",
                        "purpose": "second snapshot",
                        "data_closure_refs": ["DC-001"],
                        "parameters": {
                            "A": {"description": "batch", "example": 30029},
                            "B": {"description": "file", "example": 31029},
                        },
                        "sql": "-- :A batch; :B file\nSELECT 1 WHERE :A = :A AND :B = :B",
                    },
                ],
            )
            case = [
                "TC-001", "当前迭代", "测试项", "测试点",
                "audit_batch_id:$A（示例：30024）；audit_file_id:$B（示例：31024）",
                "数据状态：<br>审核批次 $A 中存在审核文件 $B。<br>"
                "准备动作：<br>使用隔离数据，不做写入。<br>"
                "准备校验：<br>确认 $A 与 $B 唯一对应。",
                "1. 执行 SQL-ONE（SQL-ONE.sql），绑定 :A=$A、:B=$B。<br>2. 执行 SQL-TWO（SQL-TWO.sql），绑定 :A=$A、:B=$B。",
                "无",
                "1. 页面或接口结果与 SQL-ONE 查询结果一致。<br>2. 页面或接口结果与 SQL-TWO 查询结果一致。",
                "未执行", "未执行", "未执行",
            ]

            _require_case_execution_quality(
                "TC-001", case, {"SQL-ONE", "SQL-TWO"}, load_registry(root)
            )

    def test_sql_underscore_parameters_require_same_name_declared_variables(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = write_asset(
                Path(temp),
                sql="-- :REPORT_YEAR report year\nSELECT 1 WHERE :REPORT_YEAR = :REPORT_YEAR",
                parameters={"REPORT_YEAR": {"description": "report year", "example": 2026}},
            )
            case = [
                "TC-001", "当前迭代", "测试项", "测试点", "报告年:$REPORT_YEAR",
                "报告年为 $REPORT_YEAR（2026）。",
                "1. 执行 SQL-001（SQL-001.sql），绑定 :REPORT_YEAR=$REPORT_YEAR。",
                "无", "1. 页面结果与 SQL-001 查询结果一致。",
                "未执行", "未执行", "未执行",
            ]
            registry = load_registry(root)
            _require_case_execution_quality("TC-001", case, {"SQL-001"}, registry)
            case[4] = "报告年:$Y"
            case[5] = "报告年为 $Y（2026）。"
            case[6] = "1. 执行 SQL-001（SQL-001.sql），绑定 :REPORT_YEAR=$Y。"
            with self.assertRaisesRegex(WorkflowError, "lacks same-name data variable"):
                _require_case_execution_quality("TC-001", case, {"SQL-001"}, registry)

    def test_sql_expected_can_be_concise_without_repeating_data_variable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = write_asset(
                Path(temp),
                sql="-- :A entity id\nSELECT 1 WHERE :A = :A",
                parameters={"A": {"description": "entity id", "example": 1001}},
            )
            case = [
                "TC-001", "当前迭代", "测试项", "测试点", "实体 ID:$A",
                "数据状态：<br>已准备实体 $A。",
                "1. 执行 SQL-001（SQL-001.sql），绑定 :A=$A。",
                "无",
                "1. 页面或接口结果与 SQL-001 查询结果一致。",
                "未执行", "未执行", "未执行",
            ]

            _require_case_execution_quality(
                "TC-001", case, {"SQL-001"}, load_registry(root)
            )

    def test_sql_expected_must_name_the_specific_sql_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = write_asset(
                Path(temp),
                sql="-- :A entity id\nSELECT 1 WHERE :A = :A",
                parameters={"A": {"description": "entity id", "example": 1001}},
            )
            case = [
                "TC-001", "当前迭代", "测试项", "测试点", "实体 ID:$A",
                "数据状态：<br>已准备实体 $A。",
                "1. 执行 SQL-001（SQL-001.sql），绑定 :A=$A。",
                "无",
                "1. 页面或接口结果与数据库查询结果一致。",
                "未执行", "未执行", "未执行",
            ]

            with self.assertRaisesRegex(WorkflowError, "expected result must reference SQL-001"):
                _require_case_execution_quality(
                    "TC-001", case, {"SQL-001"}, load_registry(root)
                )

    def test_sql_parameter_binding_is_still_required_in_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = write_asset(
                Path(temp),
                sql="-- :A entity id\nSELECT 1 WHERE :A = :A",
                parameters={"A": {"description": "entity id", "example": 1001}},
            )
            case = [
                "TC-001", "当前迭代", "测试项", "测试点", "实体 ID:$A",
                "数据状态：<br>已准备实体 $A。",
                "1. 执行 SQL-001（SQL-001.sql）查询实体。",
                "无",
                "1. 页面或接口结果与 SQL-001 查询结果一致。",
                "未执行", "未执行", "未执行",
            ]

            with self.assertRaisesRegex(WorkflowError, r"must state SQL binding `:A=\$A`"):
                _require_case_execution_quality(
                    "TC-001", case, {"SQL-001"}, load_registry(root)
                )

    def test_loads_existing_chinese_config_without_exposing_password(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "config.txt"
            path.write_text(
                "服务器地址：127.0.0.1\n端口：3306\n数据库：demo\n用户名：tester\n密码：plain\n",
                encoding="utf-8",
            )
            config = load_database_config(path)
            self.assertEqual(config.host, "127.0.0.1")
            self.assertEqual(config.port, 3306)
            self.assertEqual(config.password, "plain")

    def test_loads_database_toml(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "database.toml"
            path.write_text(
                '[database]\nhost="localhost"\nport=3307\ndatabase="demo"\nuser="u"\npassword="p"\n',
                encoding="utf-8",
            )
            config = load_database_config(path)
            self.assertEqual((config.host, config.port, config.database), ("localhost", 3307, "demo"))

    def test_database_toml_has_priority_over_nearer_legacy_config(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            module = root / "modules" / "task-list"
            module.mkdir(parents=True)
            legacy = module / "config.txt"
            preferred = root / "database.toml"
            legacy.write_text("host=legacy", encoding="utf-8")
            preferred.write_text("[database]", encoding="utf-8")
            self.assertEqual(find_database_config(module), preferred.resolve())

    def test_rejects_multiple_statements(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(root, sql="SELECT 1; SELECT 2;", parameters={})
            with self.assertRaisesRegex(SqlAssetError, "exactly one statement"):
                load_registry(root)

    def test_allows_semicolon_inside_a_sql_literal(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(root, sql="SELECT 'A;B'", parameters={})
            self.assertEqual(load_registry(root)["SQL-001"].statement_type, "SELECT")

    def test_rejects_duplicate_sql_ids_and_bad_file_names(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_assets(
                root,
                [
                    {
                        "sql_id": "SQL-001",
                        "file": "SQL-001.sql",
                        "statement_type": "SELECT",
                        "purpose": "first",
                        "data_closure_refs": ["DC-001"],
                        "parameters": {},
                        "sql": "SELECT 1",
                    },
                    {
                        "sql_id": "SQL-001",
                        "file": "SQL-001.sql",
                        "statement_type": "SELECT",
                        "purpose": "duplicate",
                        "data_closure_refs": ["DC-001"],
                        "parameters": {},
                        "sql": "SELECT 2",
                    },
                ],
            )
            with self.assertRaisesRegex(SqlAssetError, "duplicate SQL-ID"):
                load_registry(root)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(root, sql="SELECT 1", parameters={})
            manifest_path = root / "sql" / "sql-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["assets"][0]["file"] = "other.sql"
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(SqlAssetError, "file must be SQL-001.sql"):
                load_registry(root)

    def test_rejects_unregistered_sql_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(root, sql="SELECT 1", parameters={})
            (root / "sql" / "SQL-002.sql").write_text("SELECT 2", encoding="utf-8")
            with self.assertRaisesRegex(SqlAssetError, "unregistered SQL files"):
                load_registry(root)

    def test_rejects_parameter_without_comment_and_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(
                root,
                sql="SELECT * FROM tasks WHERE draw_no = :A",
                parameters={"A": {"description": "draw", "example": "24011"}},
            )
            with self.assertRaisesRegex(SqlAssetError, "must be explained"):
                load_registry(root)

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(
                root,
                sql="-- :B is not used\nSELECT * FROM tasks WHERE draw_no = :A",
                parameters={"B": {"description": "other", "example": "x"}},
            )
            with self.assertRaisesRegex(SqlAssetError, "parameter mismatch"):
                load_registry(root)

    def test_parameter_replacement_preserves_literal_colons_and_repeated_values(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(
                root,
                sql="-- :A is the draw number\nSELECT ':A', draw_no FROM tasks WHERE draw_no = :A OR draw_no = :A",
                parameters={"A": {"description": "draw", "example": "24011"}},
            )
            asset = load_registry(root)["SQL-001"]
            statement, values = _prepared_statement(asset)
            self.assertIn("':A'", statement)
            self.assertEqual(values, ["24011", "24011"])

    def test_explain_is_used_for_all_supported_write_types(self) -> None:
        for statement_type, sql in (
            ("SELECT", "-- :A is the key\nSELECT * FROM tasks WHERE id = :A"),
            ("INSERT", "-- :A is the key\nINSERT INTO tasks(id) VALUES (:A)"),
            ("UPDATE", "-- :A is the key\nUPDATE tasks SET id = :A WHERE id = :A"),
            ("DELETE", "-- :A is the key\nDELETE FROM tasks WHERE id = :A"),
        ):
            with self.subTest(statement_type=statement_type), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                write_asset(
                    root,
                    sql=sql,
                    statement_type=statement_type,
                    parameters={"A": {"description": "key", "example": 1}},
                )
                config_path = root / "config.txt"
                config_path.write_text(
                    "host=localhost\nport=3306\ndatabase=demo\nuser=u\npassword=p\n",
                    encoding="utf-8",
                )
                connection = FakeConnection()
                report = validate_assets(
                    root,
                    root,
                    db_config_path=config_path,
                    connect_fn=lambda _config: connection,
                )
                self.assertEqual(report["status"], "validated")
                statements = [call[0] for call in connection.cursor_instance.calls]
                self.assertEqual(statements[0], "SELECT VERSION()")
                self.assertTrue(statements[1].startswith("EXPLAIN "))
                self.assertEqual(connection.rollback_count, 1)
                self.assertEqual(connection.close_count, 1)
                report_text = (root / "sql" / "validation.json").read_text(encoding="utf-8")
                self.assertNotIn('"password"', report_text)
                self.assertNotIn('"p"', report_text)

    def test_rollback_and_close_run_when_explain_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(root, sql="SELECT 1", parameters={})
            config_path = root / "database.toml"
            config_path.write_text(
                '[database]\nhost="localhost"\nport=3306\ndatabase="demo"\nuser="u"\npassword="p"\n',
                encoding="utf-8",
            )
            connection = FailingConnection()
            with self.assertRaisesRegex(SqlAssetError, "database SQL validation failed"):
                validate_assets(
                    root,
                    root,
                    db_config_path=config_path,
                    connect_fn=lambda _config: connection,
                )
            self.assertEqual(connection.rollback_count, 1)
            self.assertEqual(connection.close_count, 1)

    def test_later_stages_reuse_only_an_unchanged_sql_validation_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(root, sql="SELECT 1", parameters={})
            config_path = root / "database.toml"
            config_path.write_text(
                '[database]\nhost="localhost"\nport=3306\ndatabase="demo"\nuser="u"\npassword="p"\n',
                encoding="utf-8",
            )
            validate_assets(
                root,
                root,
                db_config_path=config_path,
                connect_fn=lambda _config: FakeConnection(),
            )
            report = require_current_validation(
                root,
                ["SQL-001"],
                module_dir=root,
                db_config_path=config_path,
            )
            self.assertEqual(report["status"], "validated")

            (root / "sql" / "SQL-001.sql").write_text("SELECT 2", encoding="utf-8")
            with self.assertRaisesRegex(SqlAssetError, "changed after"):
                require_current_validation(root, ["SQL-001"])

    def test_same_sql_asset_can_be_reused_by_multiple_data_plans(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(
                root,
                sql="-- :A is the key\nSELECT * FROM tasks WHERE id = :A",
                parameters={"A": {"description": "key", "example": 1}},
            )
            closure_path = root / "DC-001.md"
            closure_path.write_text("DP-001", encoding="utf-8")
            registry = load_registry(root)
            model = SimpleNamespace(
                data_closure_ids=("DC-001",),
                resources={"DC-001": SimpleNamespace(path=closure_path)},
            )
            rows = [
                [
                    tc_id,
                    "DC-001",
                    "DP-001",
                    "SQL-001",
                    "SQL-001 / SQL-001.sql",
                    "state",
                    "只读查询，无写入动作",
                    "SQL-001 result",
                    "cleanup",
                ]
                for tc_id in ("TC-001", "TC-002")
            ]
            result = _require_data_execution_rows(
                model,
                {
                    "TC-001": ({"DC-001"}, {"DP-001"}),
                    "TC-002": ({"DC-001"}, {"DP-001"}),
                },
                rows,
                registry,
            )
            self.assertEqual(result, {"TC-001": {"SQL-001"}, "TC-002": {"SQL-001"}})

    def test_rejects_sql_asset_registered_for_another_data_closure(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(
                root,
                sql="SELECT 1",
                parameters={},
                data_closure_refs=["DC-002"],
            )
            closure_path = root / "DC-001.md"
            closure_path.write_text("DP-001", encoding="utf-8")
            model = SimpleNamespace(
                data_closure_ids=("DC-001",),
                resources={"DC-001": SimpleNamespace(path=closure_path)},
            )
            with self.assertRaisesRegex(WorkflowError, "SQL asset SQL-001 is not registered"):
                _require_data_execution_rows(
                    model,
                    {"TC-001": ({"DC-001"}, {"DP-001"})},
                    [[
                        "TC-001", "DC-001", "DP-001", "SQL-001", "SQL-001 / SQL-001.sql",
                        "state", "无", "SQL-001 result", "cleanup",
                    ]],
                    load_registry(root),
                )

    def test_finalization_rechecks_sql_data_closure_binding(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            write_asset(
                root,
                sql="SELECT 1",
                parameters={},
                data_closure_refs=["DC-002"],
            )
            final_id = "TC-MOD-001"
            source_id = "TC-TP-001-001"
            document = SimpleNamespace(
                case_rows=[[final_id]],
                data_execution_rows=[[
                    final_id,
                    source_id,
                    "DC-001",
                    "DP-001",
                    "SQL-001",
                    "SQL-001 / SQL-001.sql",
                    "state",
                    "read only",
                    "SQL-001 result",
                    "cleanup",
                ]],
            )
            source_document = SimpleNamespace(
                data_execution_rows=[[
                    source_id,
                    "DC-001",
                    "DP-001",
                    "SQL-001",
                    "SQL-001 / SQL-001.sql",
                    "state",
                    "read only",
                    "SQL-001 result",
                    "cleanup",
                ]]
            )
            with self.assertRaisesRegex(WorkflowError, "not registered for data closure DC-001"):
                _validate_final_sql(
                    root,
                    SimpleNamespace(module_dir=root),
                    [SimpleNamespace(data_closure_refs=("DC-001",))],
                    document,
                    {final_id: {source_id}},
                    {source_id: (None, source_document)},
                    None,
                )

if __name__ == "__main__":
    unittest.main()
