#!/usr/bin/env python3
"""Validate lossless consolidation of all TP testcase outputs."""
from __future__ import annotations

import argparse
import re
from collections import Counter
from pathlib import Path

from common import (
    CASE_HEADERS,
    CASE_READINESS_PATH,
    COVERAGE_HEADERS,
    FINAL_DATA_EXECUTION_HEADERS,
    FINAL_TRACE_HEADERS,
    ID_RE,
    WorkflowError,
    _resource_ids,
    assert_source_hashes,
    build_finalization_manifest,
    clean_cell,
    context_path,
    ensure_upstream_validation,
    load_final_test_points,
    load_json,
    module_paths,
    parse_case_readiness,
    parse_coverage_matrix,
    parse_module_case_document,
    question_refs_in_cell,
    read_context,
    refs_cell,
    run_preanalysis_validation,
    save_json,
    sha256_file,
    source_case_documents,
    source_hashes,
    sql_refs_in_cell,
    _require_case_execution_quality,
    state_lock,
    state_path,
    utc_now,
)
from sql_assets import (
    SqlAssetError,
    load_registry,
    registry_manifest,
    require_current_validation,
)

SOURCE_TC_RE = re.compile(r"\bTC-TP-\d{3}-\d{3}\b")
FINAL_TC_RE = re.compile(r"\bTC-MOD-\d{3}\b")
GENERIC_REF_RE = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b")


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a lossless module testcase consolidation."
    )
    parser.add_argument("module_dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--preanalysis-dir", type=Path)
    parser.add_argument("--case-output-dir", type=Path)
    parser.add_argument("--db-config", type=Path)
    return parser.parse_args()


def _listed_ids(value: str, pattern: re.Pattern[str], label: str) -> list[str]:
    raw = clean_cell(value)
    if raw in {"", "无"}:
        raise WorkflowError(f"{label} must contain at least one reference")
    result = pattern.findall(raw)
    if not result:
        raise WorkflowError(f"{label} has malformed references: {raw}")
    if len(result) != len(set(result)):
        raise WorkflowError(f"{label} repeats a reference: {raw}")
    return result


def _optional_refs(value: str, pattern: re.Pattern[str], label: str) -> set[str]:
    raw = clean_cell(value)
    if raw == "无":
        return set()
    if not raw:
        raise WorkflowError(f"{label} must use `无` when no reference applies")
    result = set(pattern.findall(raw))
    if not result:
        raise WorkflowError(f"{label} has malformed references: {raw}")
    return result


def _context_refs(model, value: str, label: str) -> set[str]:
    raw = clean_cell(value)
    if raw == "无":
        return set()
    if not raw:
        raise WorkflowError(f"{label} must use `无` when no reference applies")
    known = set(model.resources)
    unknown = set(GENERIC_REF_RE.findall(raw)) - known
    if unknown:
        raise WorkflowError(f"{label} contains unregistered context refs: {sorted(unknown)}")
    result = set(_resource_ids(raw, known))
    if not result:
        raise WorkflowError(f"{label} has malformed context refs: {raw}")
    return result


def _source_trace_information(model, source_documents):
    """Index every validated source case and all of its data-plan evidence."""
    information: dict[str, dict[str, set[str]]] = {}
    expected_data: Counter[tuple[str, ...]] = Counter()
    for source_tc_id, (point, document) in source_documents.items():
        trace_matches = [row for row in document.trace_rows if clean_cell(row[0]) == source_tc_id]
        if len(trace_matches) != 1:
            raise WorkflowError(f"{source_tc_id} cannot be resolved to exactly one source trace row")
        trace = trace_matches[0]
        information[source_tc_id] = {
            "tp": {point.tp_id},
            "rsu": set(refs_cell(trace[3], "RSU")),
            "question": set(question_refs_in_cell(trace[4])),
            "context": _context_refs(model, trace[5], f"{source_tc_id} Context Refs"),
            "dc": set(refs_cell(trace[6], "DC")),
            "dp": set(refs_cell(trace[7], "DP")),
        }
        for data_row in document.data_execution_rows:
            if clean_cell(data_row[0]) != source_tc_id:
                continue
            expected_data[
                (
                    source_tc_id,
                    clean_cell(data_row[1]),
                    clean_cell(data_row[2]),
                    *(clean_cell(value) for value in data_row[3:]),
                )
            ] += 1
    return information, expected_data


def _assert_current_readiness(points, readiness, context_ready: bool) -> None:
    expected = [point.tp_id for point in points]
    if list(readiness.tp_status) != expected:
        raise WorkflowError("readiness TP rows must exactly match final TP order")
    if readiness.result != "ready" or any(readiness.tp_status[tp_id] != "ready" for tp_id in expected):
        raise WorkflowError("all TP case-readiness rows must be ready before final validation")
    if not context_ready:
        raise WorkflowError("execution-context.md contains pending entries")


def _validate_final_document(model, points, source_documents, module_path: Path):
    document = parse_module_case_document(module_path, False)
    if document.metadata.get("生成结果") != "validated":
        raise WorkflowError("module-test-cases.md metadata 生成结果 must be validated")
    if not document.trace_rows or not document.case_rows:
        raise WorkflowError("module-test-cases.md must contain at least one final testcase")
    if len(document.trace_rows) != len(document.case_rows):
        raise WorkflowError("module trace rows and standard testcase rows must have equal counts")

    source_info, expected_data = _source_trace_information(model, source_documents)
    source_case_rows = {}
    for source_tc_id, (_, source_document) in source_documents.items():
        matches = [row for row in source_document.case_rows if clean_cell(row[0]) == source_tc_id]
        if len(matches) != 1:
            raise WorkflowError(f"{source_tc_id} cannot resolve to one source testcase row")
        source_case_rows[source_tc_id] = matches[0]
    all_source_ids = set(source_info)
    covered_sources: set[str] = set()
    trace_sources: dict[str, set[str]] = {}
    final_by_tp: dict[str, set[str]] = {point.tp_id: set() for point in points}

    for position, (trace, case) in enumerate(zip(document.trace_rows, document.case_rows), start=1):
        if len(trace) != len(FINAL_TRACE_HEADERS):
            raise WorkflowError(f"final trace row {position} has the wrong column count")
        if len(case) != len(CASE_HEADERS):
            raise WorkflowError(f"final testcase row {position} has the wrong column count")
        final_tc_id = clean_cell(trace[0])
        expected_final_id = f"TC-MOD-{position:03d}"
        if final_tc_id != expected_final_id:
            raise WorkflowError(
                f"expected contiguous Final TC-ID {expected_final_id}, found {final_tc_id or 'empty'}"
            )
        if clean_cell(case[0]) != final_tc_id:
            raise WorkflowError(f"standard testcase row {position} must start with {final_tc_id}")
        for column, value in enumerate(case[1:], start=2):
            if not clean_cell(value):
                raise WorkflowError(f"{final_tc_id} has an empty standard testcase cell at column {column}")
        if clean_cell(trace[8]) in {"", "无"}:
            raise WorkflowError(f"{final_tc_id} must state a concrete 归并说明")

        source_ids = _listed_ids(trace[1], SOURCE_TC_RE, f"{final_tc_id} Source TC-IDs")
        if len(source_ids) != 1:
            raise WorkflowError(
                f"{final_tc_id} must deterministically collect exactly one source testcase"
            )
        source_set = set(source_ids)
        unknown_sources = source_set - all_source_ids
        if unknown_sources:
            raise WorkflowError(f"{final_tc_id} references unknown source TCs: {sorted(unknown_sources)}")
        duplicate_sources = source_set & covered_sources
        if duplicate_sources:
            raise WorkflowError(
                f"source TCs appear in more than one final row: {sorted(duplicate_sources)}"
            )
        covered_sources.update(source_set)
        trace_sources[final_tc_id] = source_set
        source_case = source_case_rows[source_ids[0]]
        if [clean_cell(value) for value in case[1:]] != [
            clean_cell(value) for value in source_case[1:]
        ]:
            raise WorkflowError(
                f"{final_tc_id} standard testcase body differs from source {source_ids[0]}"
            )

        expected_tp = set().union(*(source_info[item]["tp"] for item in source_set))
        expected_rsu = set().union(*(source_info[item]["rsu"] for item in source_set))
        expected_questions = set().union(*(source_info[item]["question"] for item in source_set))
        expected_context = set().union(*(source_info[item]["context"] for item in source_set))
        expected_dc = set().union(*(source_info[item]["dc"] for item in source_set))
        expected_dp = set().union(*(source_info[item]["dp"] for item in source_set))

        actual_tp = _optional_refs(trace[2], re.compile(r"\bTP-\d{3}\b"), f"{final_tc_id} TP Refs")
        actual_rsu = _optional_refs(trace[3], re.compile(r"\bRSU-\d{3}\b"), f"{final_tc_id} RSU Refs")
        actual_questions = _optional_refs(
            trace[4], re.compile(r"\b(?:Q|CIQ)-\d{3}\b"), f"{final_tc_id} Question Refs"
        )
        actual_context = _context_refs(model, trace[5], f"{final_tc_id} Context Refs")
        actual_dc = _optional_refs(trace[6], re.compile(r"\bDC-\d{3}\b"), f"{final_tc_id} Data Closure Refs")
        actual_dp = _optional_refs(trace[7], re.compile(r"\bDP-\d{3}\b"), f"{final_tc_id} Data Profile Refs")

        actual_sets = {
            "TP Refs": actual_tp,
            "RSU Refs": actual_rsu,
            "Question Refs": actual_questions,
            "Context Refs": actual_context,
            "Data Closure Refs": actual_dc,
            "Data Profile Refs": actual_dp,
        }
        expected_sets = {
            "TP Refs": expected_tp,
            "RSU Refs": expected_rsu,
            "Question Refs": expected_questions,
            "Context Refs": expected_context,
            "Data Closure Refs": expected_dc,
            "Data Profile Refs": expected_dp,
        }
        for label, actual in actual_sets.items():
            if actual != expected_sets[label]:
                raise WorkflowError(
                    f"{final_tc_id} {label} must equal its source union; "
                    f"expected={sorted(expected_sets[label])}, found={sorted(actual)}"
                )
        for tp_id in actual_tp:
            final_by_tp[tp_id].add(final_tc_id)

    if covered_sources != all_source_ids:
        raise WorkflowError(
            f"finalization lost source TCs: {sorted(all_source_ids - covered_sources)}"
        )

    if document.data_execution_rows:
        raise WorkflowError("non-database module must not contain final data-closure execution rows")

    return document, final_by_tp


def _validate_final_sql(case_dir, model, points, document, trace_sources, source_documents, db_config):
    """Validate final SQL references and re-run database EXPLAIN for them."""
    try:
        registry = load_registry(case_dir)
    except SqlAssetError as exc:
        raise WorkflowError(str(exc)) from exc

    final_cases = {clean_cell(row[0]): row for row in document.case_rows}
    final_sql_by_tc: dict[str, set[str]] = {}
    source_sql_by_tc: dict[str, set[str]] = {}
    for source_tc_id, (_, source_document) in source_documents.items():
        if hasattr(source_document, "case_rows"):
            source_case = next(
                row for row in source_document.case_rows if clean_cell(row[0]) == source_tc_id
            )
            source_sql_by_tc[source_tc_id] = sql_refs_in_cell(
                "\n".join((source_case[5], source_case[6], source_case[8]))
            )
        else:
            source_sql_by_tc[source_tc_id] = {
                sql_id
                for data_row in source_document.data_execution_rows
                if clean_cell(data_row[0]) == source_tc_id
                for sql_id in sql_refs_in_cell(data_row[3])
            }
    for final_id, case in final_cases.items():
        final_sql_by_tc[final_id] = (
            sql_refs_in_cell("\n".join((case[5], case[6], case[8])))
            if len(case) > 8
            else set()
        )
    # Read compatibility for already validated v2 finalization fixtures.
    for data_row in getattr(document, "data_execution_rows", []):
        final_id = clean_cell(data_row[0])
        sql_ids = sql_refs_in_cell(data_row[4])
        final_sql_by_tc.setdefault(final_id, set()).update(sql_ids)
        dc_id = clean_cell(data_row[2])
        for sql_id in sql_ids:
            asset = registry.get(sql_id)
            if asset is None:
                raise WorkflowError(f"{final_id} references unknown SQL asset: {sql_id}")
            if dc_id not in asset.data_closure_refs:
                raise WorkflowError(
                    f"{final_id} SQL asset {sql_id} is not registered for data closure {dc_id}"
                )

    required: set[str] = set()
    for final_id, source_ids in trace_sources.items():
        actual = final_sql_by_tc.get(final_id, set())
        expected = set().union(*(source_sql_by_tc.get(source_id, set()) for source_id in source_ids))
        if actual != expected:
            raise WorkflowError(
                f"{final_id} SQL refs must equal its source union; "
                f"expected={sorted(expected)}, found={sorted(actual)}"
            )
        if actual:
            _require_case_execution_quality(final_id, final_cases[final_id], actual, registry)
            required.update(actual)
        elif expected:
            raise WorkflowError(f"{final_id} lost source SQL refs")
    if not required:
        return None
    try:
        return require_current_validation(
            case_dir,
            sorted(required),
            module_dir=model.module_dir,
            db_config_path=db_config,
        )
    except SqlAssetError as exc:
        raise WorkflowError(str(exc)) from exc


def _validate_coverage(points, final_by_tp: dict[str, set[str]], coverage_path: Path) -> None:
    rows = parse_coverage_matrix(coverage_path)
    if len(rows) != len(points):
        raise WorkflowError("coverage matrix must contain exactly one row for every final TP")
    for point, row in zip(points, rows):
        if len(row) != len(COVERAGE_HEADERS):
            raise WorkflowError(f"coverage row for {point.tp_id} has the wrong column count")
        if clean_cell(row[0]) != point.tp_id:
            raise WorkflowError("coverage matrix TP order must exactly match final test points")
        actual_final_ids = set(_listed_ids(row[1], FINAL_TC_RE, f"{point.tp_id} Final TC Refs"))
        expected_final_ids = final_by_tp[point.tp_id]
        if actual_final_ids != expected_final_ids:
            raise WorkflowError(
                f"{point.tp_id} coverage refs must equal trace coverage; "
                f"expected={sorted(expected_final_ids)}, found={sorted(actual_final_ids)}"
            )
        if clean_cell(row[2]) != "covered":
            raise WorkflowError(f"{point.tp_id} coverage status must be covered")
        if clean_cell(row[3]) in {"", "无"}:
            raise WorkflowError(f"{point.tp_id} coverage explanation must be concrete")


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
        _assert_current_readiness(points, readiness, context_ready)
        current_hashes = source_hashes(model, final_hash, readiness_hash, context_hash)

        with state_lock(case_dir):
            state = load_json(state_path(case_dir))
            assert_source_hashes(state, current_hashes)
            state_ids = [item.get("tp_id") for item in state.get("tps", [])]
            if state_ids != [point.tp_id for point in points]:
                raise WorkflowError("generation state TP order does not match final test points")
            if any(item.get("status") != "validated" for item in state.get("tps", [])):
                raise WorkflowError("all TP outputs must be validated before module validation")
            source_manifest, digest = build_finalization_manifest(case_dir, points, state)
            finalization = state.get("finalization", {})
            if finalization.get("status") != "prepared":
                raise WorkflowError("module finalization has not been prepared")
            if finalization.get("input_sha256") != digest:
                raise WorkflowError("source TP cases changed after finalization preparation")
            if finalization.get("source_manifest") != source_manifest:
                raise WorkflowError("finalization source manifest changed; prepare finalization again")
            input_path = case_dir / "finalization-input.md"
            module_cases_path = case_dir / "module-test-cases.md"
            coverage_path = case_dir / "coverage-matrix.md"
            if not all(path.is_file() for path in (input_path, module_cases_path, coverage_path)):
                raise WorkflowError("finalization artifacts are incomplete")
            if finalization.get("input_document_sha256") != sha256_file(input_path):
                raise WorkflowError("finalization-input.md changed after preparation")
            source_documents = source_case_documents(case_dir, points, state)
            document, final_by_tp = _validate_final_document(
                model, points, source_documents, module_cases_path
            )
            if document.metadata.get("最终输入 SHA-256") != digest:
                raise WorkflowError("module-test-cases.md uses a stale final input SHA-256")
            _validate_coverage(points, final_by_tp, coverage_path)
            sql_report = _validate_final_sql(
                case_dir,
                model,
                points,
                document,
                {
                    clean_cell(row[0]): set(_listed_ids(row[1], SOURCE_TC_RE, f"{clean_cell(row[0])} Source TC-IDs"))
                    for row in document.trace_rows
                },
                source_documents,
                args.db_config,
            )
            sql_refs = sorted(item["sql_id"] for item in (sql_report or {}).get("assets", []))
            finalization.update(
                {
                    "status": "validated",
                    "module_test_cases_sha256": sha256_file(module_cases_path),
                    "coverage_matrix_sha256": sha256_file(coverage_path),
                    "validated_at": utc_now(),
                    "sql_refs": sql_refs,
                    "sql_registry": registry_manifest(case_dir),
                    "sql_validation_report_sha256": sha256_file(case_dir / "sql" / "validation.json")
                    if sql_report is not None
                    else None,
                }
            )
            state["finalization"] = finalization
            state["updated_at"] = utc_now()
            save_json(state_path(case_dir), state)

        print("STATUS=validated")
        print(f"MODULE_TEST_CASES={module_cases_path}")
        print(f"COVERAGE_MATRIX={coverage_path}")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
