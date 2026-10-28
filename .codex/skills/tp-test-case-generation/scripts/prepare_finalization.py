#!/usr/bin/env python3
"""Prepare a source-locked module testcase consolidation workspace."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    CASE_HEADERS,
    CASE_READINESS_PATH,
    COVERAGE_HEADERS,
    FINAL_TRACE_HEADERS,
    WorkflowError,
    archive_finalization_artifacts,
    assert_source_hashes,
    atomic_write_text,
    build_finalization_manifest,
    context_path,
    coverage_matrix_template,
    ensure_dirs,
    ensure_upstream_validation,
    load_final_test_points,
    load_json,
    markdown_table,
    module_paths,
    parse_case_readiness,
    read_context,
    read_text,
    run_preanalysis_validation,
    save_json,
    sha256_file,
    source_hashes,
    state_lock,
    state_path,
    utc_now,
    output_paths,
    parse_case_document,
    clean_cell,
)
from sql_assets import SqlAssetError
from sql_convergence import write_convergence_report


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Prepare source-locked input for module testcase consolidation."
    )
    parser.add_argument("module_dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--preanalysis-dir", type=Path)
    parser.add_argument("--case-output-dir", type=Path)
    return parser.parse_args()


def _require_ready(points, readiness, context_ready: bool) -> None:
    expected_ids = [point.tp_id for point in points]
    if list(readiness.tp_status) != expected_ids:
        raise WorkflowError("readiness TP rows must exactly match final TP order")
    if readiness.result != "ready":
        raise WorkflowError("module testcase readiness must be ready before finalization")
    blocked = [tp_id for tp_id in expected_ids if readiness.tp_status[tp_id] != "ready"]
    if blocked:
        raise WorkflowError(f"cannot finalize while TP readiness is incomplete: {', '.join(blocked)}")
    if not context_ready:
        raise WorkflowError("execution-context.md contains pending entries")


def _finalization_input(case_dir: Path, source_manifest: dict, digest: str) -> str:
    rows = [
        f"| {entry['tp_id']} | {entry['case_count']} | `{entry['output_sha256']}` | "
        f"`{', '.join(entry['source_tc_ids'])}` |"
        for entry in source_manifest["tps"]
    ]
    source_sections = []
    for entry in source_manifest["tps"]:
        source_path = case_dir / entry["output_file"]
        source_sections.append(
            f"## {entry['tp_id']}\n\n"
            f"- 来源文件：`{entry['output_file']}`\n"
            f"- 来源 SHA-256：`{entry['output_sha256']}`\n\n"
            f"{read_text(source_path).rstrip()}"
        )
    return (
        "# 模块测试用例归并输入\n\n"
        "## 输入元数据\n\n"
        "| 字段 | 值 |\n|---|---|\n"
        f"| 最终输入 SHA-256 | `{digest}` |\n"
        f"| 来源 TP 数 | `{len(source_manifest['tps'])}` |\n\n"
        "## SQL 资产清单\n\n"
        f"注册表：`sql/sql-manifest.json`；注册表 SHA-256：`{source_manifest['sql_registry']['manifest_sha256']}`\n\n"
        "| SQL-ID | 文件 | 类型 | 用途 | Data Closure Refs | 参数 | SHA-256 |\n"
        "|---|---|---|---|---|---|---|\n"
        + "\n".join(
            f"| {asset['sql_id']} | `{asset['file']}` | {asset['statement_type']} | "
            f"{asset['purpose']} | {', '.join(asset['data_closure_refs'])} | "
            f"{', '.join(asset['parameters']) or '无'} | `{asset['sha256']}` |"
            for asset in source_manifest["sql_registry"]["assets"]
        )
        + "\n\n## 归并边界\n\n"
        "- 仅归并被测对象、前置条件、执行步骤和可判断预期结果实质相同的已验证来源用例。\n"
        "- 每个 `TC-TP-*` 必须在一个且仅一个 `TC-MOD-*` 的 `Source TC-IDs` 中出现。\n"
        "- 每条最终追溯行的 TP/RSU/Q/CIQ/上下文/DC/DP 引用必须等于其来源用例引用的并集。\n"
        "- 数据闭包只作为事实与追溯来源；最终正文保留来源用例已经写明的关键前置、动作、预期和计划 SQL 引用，不额外扩写完整造数链。\n"
        "- 完成 `module-test-cases.md` 和 `coverage-matrix.md` 后运行校验；本文件只读。\n\n"
        "## 锁定来源清单\n\n"
        "| TP-ID | 来源用例数 | 来源输出 SHA-256 | Source TC-IDs |\n"
        "|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n## 已验证来源用例\n\n"
        + "\n\n".join(source_sections)
        + "\n"
    )


def _deterministic_outputs(case_dir: Path, module_name: str, points, digest: str):
    """Preserve validated source case prose byte-for-cell; only IDs and trace shape change."""
    trace_rows = []
    case_rows = []
    coverage: dict[str, list[str]] = {point.tp_id: [] for point in points}
    position = 0
    for point in points:
        _, source_path = output_paths(case_dir, point.tp_id)
        document = parse_case_document(source_path, False)
        if len(document.trace_rows) != len(document.case_rows):
            raise WorkflowError(f"{point.tp_id} source trace/case count differs")
        for trace, case in zip(document.trace_rows, document.case_rows):
            position += 1
            final_id = f"TC-MOD-{position:03d}"
            source_id = clean_cell(trace[0])
            trace_rows.append(
                [
                    final_id,
                    source_id,
                    point.tp_id,
                    trace[3],
                    trace[4],
                    trace[5],
                    trace[6],
                    trace[7],
                    "按已验证来源用例确定性收录，正文未改写",
                ]
            )
            case_rows.append([final_id, *case[1:]])
            coverage[point.tp_id].append(final_id)
    module_text = (
        f"# {module_name} - 模块测试用例\n\n"
        "## 生成元数据\n\n"
        "| 字段 | 值 |\n|---|---|\n"
        f"| 最终输入 SHA-256 | `{digest}` |\n"
        "| 生成结果 | validated |\n\n"
        "## 模块用例追溯索引\n\n"
        f"{markdown_table(FINAL_TRACE_HEADERS, trace_rows)}\n\n"
        "## 标准测试用例\n\n"
        f"{markdown_table(CASE_HEADERS, case_rows)}\n"
    )
    coverage_rows = [
        [point.tp_id, "、".join(coverage[point.tp_id]), "covered", "来源用例已确定性收录"]
        for point in points
    ]
    coverage_text = (
        f"# {module_name} - 测试点覆盖矩阵\n\n"
        f"{markdown_table(COVERAGE_HEADERS, coverage_rows)}\n"
    )
    return module_text, coverage_text


def main() -> int:
    args = arguments()
    try:
        layout, model, points_dir, case_dir = module_paths(
            args.module_dir, args.preanalysis_dir, args.manifest, args.case_output_dir
        )
        run_preanalysis_validation(layout, case_dir)
        points, _, final_hash = load_final_test_points(points_dir, model)
        readiness_path = points_dir / CASE_READINESS_PATH
        readiness = parse_case_readiness(readiness_path, model)
        readiness_hash = sha256_file(readiness_path)
        ensure_upstream_validation(points_dir, final_hash, readiness_hash)
        _, context_hash, context_ready = read_context(context_path(case_dir))
        _require_ready(points, readiness, context_ready)
        current_hashes = source_hashes(model, final_hash, readiness_hash, context_hash)

        with state_lock(case_dir):
            state = load_json(state_path(case_dir))
            assert_source_hashes(state, current_hashes)
            state_ids = [item.get("tp_id") for item in state.get("tps", [])]
            expected_ids = [point.tp_id for point in points]
            if state_ids != expected_ids:
                raise WorkflowError("generation state TP order does not match final test points")
            incomplete = [
                item["tp_id"] for item in state["tps"] if item.get("status") != "validated"
            ]
            if incomplete:
                raise WorkflowError(f"cannot finalize before all TPs validate: {', '.join(incomplete)}")

            source_manifest, digest = build_finalization_manifest(case_dir, points, state)
            try:
                convergence_report = write_convergence_report(case_dir)
            except (OSError, SqlAssetError) as exc:
                raise WorkflowError(f"cannot build SQL convergence report: {exc}") from exc
            input_path = case_dir / "finalization-input.md"
            module_cases_path = case_dir / "module-test-cases.md"
            coverage_path = case_dir / "coverage-matrix.md"
            finalization = state.get("finalization", {})
            all_artifacts_exist = all(
                path.is_file() for path in (input_path, module_cases_path, coverage_path)
            )
            same_input = finalization.get("input_sha256") == digest

            if same_input and all_artifacts_exist:
                if finalization.get("input_document_sha256") != sha256_file(input_path):
                    raise WorkflowError(
                        "finalization-input.md changed after preparation; refresh source TP outputs first"
                    )
                status = finalization.get("status")
                if status == "validated":
                    if finalization.get("module_test_cases_sha256") != sha256_file(module_cases_path):
                        raise WorkflowError("module-test-cases.md changed after final validation")
                    if finalization.get("coverage_matrix_sha256") != sha256_file(coverage_path):
                        raise WorkflowError("coverage-matrix.md changed after final validation")
                    print("STATUS=validated")
                else:
                    print("STATUS=awaiting-validation")
                print(f"FINALIZATION_INPUT={input_path}")
                print(f"MODULE_TEST_CASES={module_cases_path}")
                print(f"COVERAGE_MATRIX={coverage_path}")
                print(f"SQL_CONVERGENCE_REPORT={convergence_report}")
                return 0

            if any(path.exists() for path in (input_path, module_cases_path, coverage_path, case_dir / "final")):
                archive_finalization_artifacts(
                    case_dir,
                    "finalization-input-changed:" + digest,
                )
            ensure_dirs(case_dir)
            atomic_write_text(input_path, _finalization_input(case_dir, source_manifest, digest))
            module_text, coverage_text = _deterministic_outputs(
                case_dir, model.module_name, points, digest
            )
            atomic_write_text(module_cases_path, module_text)
            atomic_write_text(coverage_path, coverage_text)
            state["finalization"] = {
                "status": "prepared",
                "input_sha256": digest,
                "input_document_sha256": sha256_file(input_path),
                "source_manifest": source_manifest,
                "module_test_cases_sha256": None,
                "coverage_matrix_sha256": None,
                "prepared_at": utc_now(),
                "validated_at": None,
            }
            state["updated_at"] = utc_now()
            save_json(state_path(case_dir), state)

        print("STATUS=prepared")
        print(f"FINALIZATION_INPUT={input_path}")
        print(f"MODULE_TEST_CASES={module_cases_path}")
        print(f"COVERAGE_MATRIX={coverage_path}")
        print(f"SQL_CONVERGENCE_REPORT={convergence_report}")
        print("模块文档已按锁定来源确定性生成；下一步运行 validate_module_test_cases.py")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
