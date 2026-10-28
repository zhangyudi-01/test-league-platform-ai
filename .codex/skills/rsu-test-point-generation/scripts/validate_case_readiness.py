#!/usr/bin/env python3
"""Validate the test-case readiness handoff and its TP/question coverage."""

from __future__ import annotations

import argparse
import re

from common import (
    CASE_INPUT_QUESTION_HEADERS,
    CLOSED_CASE_INPUT_HEADERS,
    TP_READINESS_HEADERS,
    UNRESOLVED_RE,
    WorkflowError,
    add_layout_arguments,
    atomic_write_json,
    clean_cell,
    column_value,
    default_output_dir,
    extract_tables,
    find_tables,
    load_state,
    parse_final_document,
    parse_data_closure_refs,
    parse_metadata_table,
    parse_module,
    parse_tp_ids,
    read_text,
    reconcile_state,
    resolve_module_layout,
    run_preanalysis_validation,
    sha256_file,
    sha256_text,
    state_lock,
    state_path,
    tp_readiness_headers,
    utc_now,
)


QUESTION_TYPES = {
    "test-data",
    "environment",
    "configuration",
    "observability",
    "upstream-requirement",
    "data-contract",
}
TP_STATUSES = {"ready", "blocked-input", "upstream-gap"}
QUESTION_STATUSES = {"pending", "answered"}
RESULTS = {"ready", "blocked-input", "upstream-gap"}
UNANSWERED_PLACEHOLDERS = {
    "未提供",
    "尚未提供",
    "暂未提供",
    "待提供",
    "待补充",
    "待回填",
    "未回填",
    "pending",
    "not provided",
    "not available",
    "n/a",
}


def require_nonempty(cells: list[str], label: str) -> None:
    for index, cell in enumerate(cells, start=1):
        if not cell.strip():
            raise WorkflowError(f"{label} has an empty cell at column {index}")


def parse_ciq_ids(text: str) -> list[str]:
    result: list[str] = []
    for item in re.findall(r"CIQ-\d{3}", text):
        if item not in result:
            result.append(item)
    return result


def is_unanswered_placeholder(text: str) -> bool:
    normalized = re.sub(r"\s+", " ", clean_cell(text)).strip().casefold()
    return normalized in UNANSWERED_PLACEHOLDERS


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate test-case generation readiness review.")
    add_layout_arguments(parser)
    args = parser.parse_args()

    try:
        layout = resolve_module_layout(args.module_dir, args.preanalysis_dir, args.manifest)
        output_dir = default_output_dir(layout, args.output_dir)
        run_preanalysis_validation(layout, output_dir)
        with state_lock(output_dir):
            model = parse_module(layout)
            state = load_state(output_dir, layout)
            if state is None:
                raise WorkflowError("generation state does not exist; run init_generation.py first")
            state, _ = reconcile_state(model, output_dir, state)
            final_state = state.get("finalization", {})
            if final_state.get("status") != "validated":
                raise WorkflowError("module test points are not validated; finish finalization first")

            final_path = output_dir / "module-test-points.md"
            coverage_path = output_dir / "coverage-matrix.md"
            if final_state.get("module_test_points_sha256") != sha256_file(final_path):
                raise WorkflowError("module-test-points.md changed after validation")
            if final_state.get("coverage_matrix_sha256") != sha256_file(coverage_path):
                raise WorkflowError("coverage-matrix.md changed after validation")

            readiness_state = state.get("case_readiness", {})
            if readiness_state.get("status") not in {"prepared", "validated"}:
                raise WorkflowError("case readiness is not prepared; run prepare_case_readiness.py first")
            expected_hash = readiness_state.get("input_sha256")
            expected_document_hash = readiness_state.get("input_document_sha256")
            if not expected_hash or not expected_document_hash:
                raise WorkflowError("case readiness state lacks input hashes; rerun preparation")

            input_path = output_dir / "case-readiness-input.md"
            output_path = output_dir / "test-case-readiness.md"
            if not input_path.is_file() or not output_path.is_file():
                raise WorkflowError("case readiness input or output file is missing")
            input_text = read_text(input_path)
            if sha256_text(input_text) != expected_document_hash:
                raise WorkflowError("case-readiness-input.md changed after preparation")
            if expected_hash not in input_text:
                raise WorkflowError("case-readiness-input.md does not carry the current SHA-256")

            output_text = read_text(output_path)
            if UNRESOLVED_RE.search(output_text):
                raise WorkflowError("test-case-readiness.md contains unresolved placeholders")
            metadata = parse_metadata_table(output_text)
            if metadata.get("就绪输入 SHA-256") != expected_hash:
                raise WorkflowError("test-case-readiness.md uses a stale readiness input SHA-256")
            result = metadata.get("审查结果")
            if result not in RESULTS:
                raise WorkflowError(f"invalid readiness result: {result}")

            tables = extract_tables(output_text)
            closed_tables = find_tables(tables, CLOSED_CASE_INPUT_HEADERS)
            expected_tp_headers = tp_readiness_headers(model.data_closure_enabled)
            tp_tables = find_tables(tables, expected_tp_headers)
            question_tables = find_tables(tables, CASE_INPUT_QUESTION_HEADERS)
            if len(tables) != 4 or len(closed_tables) != 1 or len(tp_tables) != 1 or len(question_tables) != 1:
                raise WorkflowError("test-case-readiness.md must contain exactly the four fixed tables")

            final_doc = parse_final_document(final_path, model.data_closure_enabled)
            final_tp_ids = [
                clean_cell(column_value(final_doc.headers, cells, "TP-ID"))
                for cells in final_doc.rows
            ]
            valid_tps = set(final_tp_ids)
            final_dc_refs = {
                clean_cell(column_value(final_doc.headers, cells, "TP-ID")): set(
                    parse_data_closure_refs(
                        column_value(final_doc.headers, cells, "Data Closure Refs")
                    )
                )
                for cells in final_doc.rows
            } if model.data_closure_enabled else {tp_id: set() for tp_id in final_tp_ids}
            closure_statuses = model.data_closure_statuses

            for line, cells in closed_tables[0].rows:
                require_nonempty(cells, f"closed input line {line}")
                tp_refs = set(parse_tp_ids(cells[3]))
                if not tp_refs:
                    raise WorkflowError(f"closed input line {line} must reference at least one TP")
                if unknown := tp_refs - valid_tps:
                    raise WorkflowError(f"closed input line {line} references undefined TPs: {sorted(unknown)}")

            questions: dict[str, dict[str, object]] = {}
            for number, (line, cells) in enumerate(question_tables[0].rows, start=1):
                require_nonempty(cells, f"case input question line {line}")
                expected_id = f"CIQ-{number:03d}"
                ciq_id = clean_cell(cells[0])
                if ciq_id != expected_id:
                    raise WorkflowError(f"case input question row {number} must use {expected_id}, found {ciq_id}")
                question_type = clean_cell(cells[1])
                if question_type not in QUESTION_TYPES:
                    raise WorkflowError(f"{ciq_id} has invalid type: {question_type}")
                tp_refs = set(parse_tp_ids(cells[2]))
                if not tp_refs:
                    raise WorkflowError(f"{ciq_id} must reference at least one TP")
                if unknown := tp_refs - valid_tps:
                    raise WorkflowError(f"{ciq_id} references undefined TPs: {sorted(unknown)}")
                question = clean_cell(cells[3])
                evidence = clean_cell(cells[4])
                answer = clean_cell(cells[5])
                status = clean_cell(cells[6])
                if status not in QUESTION_STATUSES:
                    raise WorkflowError(f"{ciq_id} has invalid status: {status}")
                if len(question) < 8 or evidence in {"无", "不适用"}:
                    raise WorkflowError(f"{ciq_id} requires a concrete question and existing evidence")
                if status == "pending" and not is_unanswered_placeholder(answer):
                    raise WorkflowError(
                        f"{ciq_id} pending status requires an unanswered placeholder, "
                        f"found: {answer}"
                    )
                if status == "answered" and (
                    is_unanswered_placeholder(answer) or answer in {"无", "不适用"}
                ):
                    raise WorkflowError(f"{ciq_id} answered status requires a concrete answer or resource")
                questions[ciq_id] = {
                    "type": question_type,
                    "tp_refs": tp_refs,
                    "status": status,
                }

            seen_tps: list[str] = []
            referenced_questions: set[str] = set()
            status_by_tp: dict[str, str] = {}
            for line, cells in tp_tables[0].rows:
                require_nonempty(cells, f"TP readiness line {line}")
                tp_id = clean_cell(column_value(expected_tp_headers, cells, "TP-ID"))
                if tp_id not in valid_tps:
                    raise WorkflowError(f"TP readiness references undefined {tp_id}")
                if tp_id in seen_tps:
                    raise WorkflowError(f"duplicate TP readiness row: {tp_id}")
                seen_tps.append(tp_id)
                status = clean_cell(column_value(expected_tp_headers, cells, "用例生成状态"))
                if status not in TP_STATUSES:
                    raise WorkflowError(f"{tp_id} has invalid readiness status: {status}")
                if model.data_closure_enabled:
                    raw_dc_refs = clean_cell(
                        column_value(expected_tp_headers, cells, "Data Closure Refs")
                    )
                    dc_refs = set(parse_data_closure_refs(raw_dc_refs))
                    if raw_dc_refs != "无" and not dc_refs:
                        raise WorkflowError(f"{tp_id} has malformed Data Closure Refs")
                    if dc_refs != final_dc_refs[tp_id]:
                        raise WorkflowError(
                            f"{tp_id} readiness Data Closure Refs must match final TP: "
                            f"expected={sorted(final_dc_refs[tp_id])}, found={sorted(dc_refs)}"
                        )
                    if any(closure_statuses.get(item) == "blocked" for item in dc_refs):
                        raise WorkflowError(f"{tp_id} references a blocked data closure")
                else:
                    dc_refs = set()
                raw_question_refs = column_value(
                    expected_tp_headers, cells, "Input Question Refs"
                )
                refs = set(parse_ciq_ids(raw_question_refs))
                if clean_cell(raw_question_refs) != "无" and not refs:
                    raise WorkflowError(f"{tp_id} has malformed Input Question Refs")
                if unknown := refs - set(questions):
                    raise WorkflowError(f"{tp_id} references undefined CIQs: {sorted(unknown)}")
                pending_refs = {item for item in refs if questions[item]["status"] == "pending"}
                upstream_refs = {
                    item for item in pending_refs if questions[item]["type"] == "upstream-requirement"
                }
                if status == "ready" and pending_refs:
                    raise WorkflowError(f"{tp_id} is ready but still references pending CIQs")
                if status == "blocked-input" and (not pending_refs or upstream_refs):
                    raise WorkflowError(f"{tp_id} blocked-input requires pending non-upstream CIQs only")
                if status == "upstream-gap" and not upstream_refs:
                    raise WorkflowError(f"{tp_id} upstream-gap requires a pending upstream-requirement CIQ")
                if len(clean_cell(column_value(expected_tp_headers, cells, "说明"))) < 8:
                    raise WorkflowError(f"{tp_id} readiness explanation is too vague")
                referenced_questions.update(refs)
                status_by_tp[tp_id] = status

            if seen_tps != final_tp_ids:
                raise WorkflowError(
                    f"TP readiness rows must match final TP order; expected={final_tp_ids}, found={seen_tps}"
                )
            if set(questions) != referenced_questions:
                raise WorkflowError(
                    "case input question coverage mismatch; "
                    f"unreferenced={sorted(set(questions) - referenced_questions)}"
                )

            expected_result = (
                "upstream-gap"
                if "upstream-gap" in status_by_tp.values()
                else "blocked-input"
                if "blocked-input" in status_by_tp.values()
                else "ready"
            )
            if result != expected_result:
                raise WorkflowError(f"readiness result must be {expected_result}, found {result}")
            if result == "ready" and any(item["status"] == "pending" for item in questions.values()):
                raise WorkflowError("ready result cannot contain pending case input questions")

            readiness_state["status"] = "validated"
            readiness_state["result"] = result
            readiness_state["validated_at"] = utc_now()
            readiness_state["output_sha256"] = sha256_file(output_path)
            state["case_readiness"] = readiness_state
            state["updated_at"] = utc_now()
            atomic_write_json(state_path(output_dir), state)

        print(f"CASE_READINESS_RESULT={result}")
        print(f"FINAL_TP_COUNT={len(final_tp_ids)}")
        print(f"CASE_INPUT_QUESTION_COUNT={len(questions)}")
        print("CASE_READINESS_STATUS=validated")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
