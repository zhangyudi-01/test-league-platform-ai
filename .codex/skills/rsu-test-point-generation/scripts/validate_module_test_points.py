#!/usr/bin/env python3
"""Validate module-wide semantic finalization and traceability."""

from __future__ import annotations

import argparse

from common import (
    CANDIDATE_DISPOSITION_HEADERS,
    RSU_COVERAGE_HEADERS,
    UNRESOLVED_RE,
    WorkflowError,
    add_layout_arguments,
    atomic_write_json,
    atomic_write_text,
    clean_cell,
    column_value,
    default_output_dir,
    extract_tables,
    find_tables,
    load_state,
    parse_candidate_document,
    parse_candidate_ids,
    parse_context_refs,
    parse_data_closure_refs,
    parse_final_document,
    parse_metadata_table,
    parse_module,
    parse_ref_ids,
    parse_tp_ids,
    read_text,
    reconcile_state,
    record_paths,
    replace_context_resource_index,
    resolve_module_layout,
    run_preanalysis_validation,
    sha256_file,
    sha256_text,
    state_lock,
    state_path,
    utc_now,
)


def require_nonempty(cells: list[str], label: str, headers: tuple[str, ...] = ()) -> None:
    for index, cell in enumerate(cells, start=1):
        if not cell.strip() and (not headers or headers[index - 1] != "备注"):
            raise WorkflowError(f"{label} has an empty cell at column {index}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate final module test points and coverage.")
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
            incomplete = next(
                (item for item in state["rsus"] if item["generation_status"] != "validated"),
                None,
            )
            if incomplete:
                raise WorkflowError(f"RSU generation is incomplete at {incomplete['rsu_id']}")

            final_state = state.get("finalization", {})
            if final_state.get("status") not in {"prepared", "validated"}:
                raise WorkflowError("finalization is not prepared; run prepare_finalization.py first")
            expected_hash = final_state.get("input_sha256")
            expected_document_hash = final_state.get("input_document_sha256")
            if not expected_hash or not expected_document_hash:
                raise WorkflowError("finalization state lacks the materialized input hash; rerun prepare_finalization.py")

            finalization_input = output_dir / "finalization-input.md"
            final_path = output_dir / "module-test-points.md"
            coverage_path = output_dir / "coverage-matrix.md"
            if not all(path.is_file() for path in (finalization_input, final_path, coverage_path)):
                raise WorkflowError("finalization input or output files are missing")
            finalization_input_text = read_text(finalization_input)
            if sha256_text(finalization_input_text) != expected_document_hash:
                raise WorkflowError("finalization-input.md changed after preparation; rerun prepare_finalization.py")
            if expected_hash not in finalization_input_text:
                raise WorkflowError("finalization-input.md does not carry the current finalization SHA-256")

            candidate_details: dict[str, dict[str, object]] = {}
            rsu_candidate_counts: dict[str, int] = {}
            candidate_rank: dict[str, int] = {}
            next_rank = 1
            for record in state["rsus"]:
                rsu_id = record["rsu_id"]
                _, candidate_path = record_paths(output_dir, rsu_id)
                document = parse_candidate_document(candidate_path, model.data_closure_enabled)
                rsu_candidate_counts[rsu_id] = len(document.rows)
                for cells in document.rows:
                    candidate_id = clean_cell(column_value(document.headers, cells, "候选 ID"))
                    if candidate_id in candidate_details:
                        raise WorkflowError(f"duplicate candidate ID across RSUs: {candidate_id}")
                    candidate_details[candidate_id] = {
                        "primary": clean_cell(column_value(document.headers, cells, "Primary RSU")),
                        "source_rsus": set(
                            parse_ref_ids(column_value(document.headers, cells, "Source RSUs"), "RSU")
                        ),
                        "q_refs": set(
                            parse_ref_ids(column_value(document.headers, cells, "Question Refs"), "Q")
                        ),
                        "context_refs": set(
                            parse_context_refs(
                                column_value(document.headers, cells, "Context Refs"),
                                iter(model.resources),
                            )
                        ),
                        "dc_refs": set(
                            parse_data_closure_refs(
                                column_value(document.headers, cells, "Data Closure Refs")
                            )
                        )
                        if model.data_closure_enabled
                        else set(),
                    }
                    candidate_rank[candidate_id] = next_rank
                    next_rank += 1

            final_text = read_text(final_path)
            final_metadata = parse_metadata_table(final_text)
            final_doc = parse_final_document(final_path, model.data_closure_enabled)
            if final_doc.input_sha256 != expected_hash:
                raise WorkflowError("module-test-points.md uses a stale finalization input SHA-256")
            final_result = final_metadata.get("生成结果")
            if final_result not in {"test-points", "zero-test-points"}:
                raise WorkflowError("最终文件的生成结果 must be test-points or zero-test-points")
            if final_doc.rows and final_result != "test-points":
                raise WorkflowError("nonempty final table requires 生成结果=test-points")
            if not final_doc.rows and final_result != "zero-test-points":
                raise WorkflowError("empty final table requires 生成结果=zero-test-points")

            valid_rsus = set(model.rsu_by_id)
            valid_qs = set(model.questions)
            valid_context = set(model.resources)
            fixed_context = set(model.fixed_resource_ids)
            final_ids: list[str] = []
            final_by_id: dict[str, dict[str, set[str]]] = {}
            referenced_context_ids: set[str] = set()
            previous_rank = 0
            for number, cells in enumerate(final_doc.rows, start=1):
                require_nonempty(cells, f"final row {number}", final_doc.headers)
                expected_id = f"TP-{number:03d}"
                tp_id = clean_cell(column_value(final_doc.headers, cells, "TP-ID"))
                if tp_id != expected_id:
                    raise WorkflowError(f"final row {number} must use {expected_id}, found {tp_id}")
                primary = clean_cell(column_value(final_doc.headers, cells, "Primary RSU"))
                source_rsus = set(
                    parse_ref_ids(column_value(final_doc.headers, cells, "Source RSUs"), "RSU")
                )
                q_refs = set(
                    parse_ref_ids(column_value(final_doc.headers, cells, "Question Refs"), "Q")
                )
                context_refs = set(
                    parse_context_refs(
                        column_value(final_doc.headers, cells, "Context Refs"),
                        iter(model.resources),
                    )
                )
                raw_dc_refs = (
                    clean_cell(column_value(final_doc.headers, cells, "Data Closure Refs"))
                    if model.data_closure_enabled
                    else "无"
                )
                dc_refs = (
                    set(parse_data_closure_refs(raw_dc_refs))
                    if model.data_closure_enabled
                    else set()
                )
                if model.data_closure_enabled and raw_dc_refs != "无" and not dc_refs:
                    raise WorkflowError(f"{tp_id} has malformed Data Closure Refs")
                source_candidates = set(
                    parse_candidate_ids(column_value(final_doc.headers, cells, "Source Candidates"))
                )
                if primary not in valid_rsus or primary not in source_rsus:
                    raise WorkflowError(f"{tp_id} has invalid Primary RSU or Source RSUs")
                if unknown := source_rsus - valid_rsus:
                    raise WorkflowError(f"{tp_id} references undefined RSUs: {sorted(unknown)}")
                if unknown := q_refs - valid_qs:
                    raise WorkflowError(f"{tp_id} references undefined questions: {sorted(unknown)}")
                if unknown := context_refs - valid_context:
                    raise WorkflowError(f"{tp_id} references undefined context resources: {sorted(unknown)}")
                if missing := fixed_context - context_refs:
                    raise WorkflowError(f"{tp_id} is missing fixed Context Refs: {sorted(missing)}")
                if unknown := dc_refs - set(model.data_closure_ids):
                    raise WorkflowError(f"{tp_id} references undefined data closures: {sorted(unknown)}")
                if missing := dc_refs - context_refs:
                    raise WorkflowError(
                        f"{tp_id} Data Closure Refs must also appear in Context Refs: {sorted(missing)}"
                    )
                if not source_candidates:
                    raise WorkflowError(f"{tp_id} must reference at least one Source Candidate")
                if unknown := source_candidates - set(candidate_details):
                    raise WorkflowError(f"{tp_id} references undefined candidates: {sorted(unknown)}")

                earliest_rank = min(candidate_rank[candidate_id] for candidate_id in source_candidates)
                if earliest_rank < previous_rank:
                    raise WorkflowError(
                        f"{tp_id} breaks stable TP ordering; its earliest source candidate appears before the previous TP"
                    )
                previous_rank = earliest_rank

                inherited_rsus: set[str] = set()
                inherited_qs: set[str] = set()
                inherited_context: set[str] = set()
                inherited_dc: set[str] = set()
                for candidate_id in source_candidates:
                    detail = candidate_details[candidate_id]
                    inherited_rsus.update(detail["source_rsus"])
                    inherited_qs.update(detail["q_refs"])
                    inherited_context.update(detail["context_refs"])
                    inherited_dc.update(detail["dc_refs"])
                if source_rsus != inherited_rsus:
                    raise WorkflowError(
                        f"{tp_id} Source RSUs must exactly inherit candidates: "
                        f"expected={sorted(inherited_rsus)}, found={sorted(source_rsus)}"
                    )
                if q_refs != inherited_qs:
                    raise WorkflowError(
                        f"{tp_id} Question Refs must exactly inherit candidates: "
                        f"expected={sorted(inherited_qs)}, found={sorted(q_refs)}"
                    )
                if context_refs != inherited_context:
                    raise WorkflowError(
                        f"{tp_id} Context Refs must exactly inherit candidates: "
                        f"expected={sorted(inherited_context)}, found={sorted(context_refs)}"
                    )
                if dc_refs != inherited_dc:
                    raise WorkflowError(
                        f"{tp_id} Data Closure Refs must exactly inherit candidates: "
                        f"expected={sorted(inherited_dc)}, found={sorted(dc_refs)}"
                    )
                final_ids.append(tp_id)
                referenced_context_ids.update(context_refs)
                final_by_id[tp_id] = {
                    "source_rsus": source_rsus,
                    "source_candidates": source_candidates,
                    "dc_refs": dc_refs,
                }

            coverage_text = read_text(coverage_path)
            if UNRESOLVED_RE.search(coverage_text):
                raise WorkflowError("coverage-matrix.md contains unresolved placeholders")
            coverage_tables = extract_tables(coverage_text)
            rsu_tables = find_tables(coverage_tables, RSU_COVERAGE_HEADERS)
            disposition_tables = find_tables(coverage_tables, CANDIDATE_DISPOSITION_HEADERS)
            if len(coverage_tables) != 2 or len(rsu_tables) != 1 or len(disposition_tables) != 1:
                raise WorkflowError("coverage-matrix.md must contain exactly the two fixed tables")

            disposition_seen: dict[str, set[str]] = {}
            for line, cells in disposition_tables[0].rows:
                require_nonempty(cells, f"candidate disposition line {line}")
                candidate_id = clean_cell(cells[0])
                source_rsu = clean_cell(cells[1])
                status = clean_cell(cells[2])
                tp_refs = set(parse_tp_ids(cells[3]))
                explanation = clean_cell(cells[4])
                detail = candidate_details.get(candidate_id)
                if detail is None:
                    raise WorkflowError(f"candidate disposition references undefined {candidate_id}")
                if candidate_id in disposition_seen:
                    raise WorkflowError(f"candidate appears more than once in disposition table: {candidate_id}")
                if source_rsu != detail["primary"]:
                    raise WorkflowError(f"{candidate_id} disposition Source RSU must be {detail['primary']}")
                if status not in {"retained", "merged", "excluded"}:
                    raise WorkflowError(f"{candidate_id} has invalid disposition: {status}")
                if unknown := tp_refs - set(final_ids):
                    raise WorkflowError(f"{candidate_id} disposition references undefined TPs: {sorted(unknown)}")
                actual_refs = {
                    tp_id
                    for tp_id, item in final_by_id.items()
                    if candidate_id in item["source_candidates"]
                }
                if tp_refs != actual_refs:
                    raise WorkflowError(
                        f"{candidate_id} disposition TP refs {sorted(tp_refs)} do not match final usage {sorted(actual_refs)}"
                    )
                if status in {"retained", "merged"} and not tp_refs:
                    raise WorkflowError(f"{candidate_id} {status} disposition requires Final TP Refs")
                if status == "excluded" and tp_refs:
                    raise WorkflowError(f"{candidate_id} excluded disposition must not reference a final TP")
                if status in {"merged", "excluded"} and (explanation in {"无", "不适用"} or len(explanation) < 8):
                    raise WorkflowError(f"{candidate_id} {status} disposition requires a concrete explanation")
                disposition_seen[candidate_id] = tp_refs
            if set(disposition_seen) != set(candidate_details):
                missing = set(candidate_details) - set(disposition_seen)
                extra = set(disposition_seen) - set(candidate_details)
                raise WorkflowError(
                    f"candidate disposition coverage mismatch; missing={sorted(missing)}, extra={sorted(extra)}"
                )

            rsu_seen: set[str] = set()
            for line, cells in rsu_tables[0].rows:
                require_nonempty(cells, f"RSU coverage line {line}")
                rsu_id = clean_cell(cells[0])
                if rsu_id not in valid_rsus:
                    raise WorkflowError(f"RSU coverage references undefined {rsu_id}")
                if rsu_id in rsu_seen:
                    raise WorkflowError(f"duplicate RSU coverage row: {rsu_id}")
                rsu_seen.add(rsu_id)
                try:
                    count = int(clean_cell(cells[1]))
                except ValueError as exc:
                    raise WorkflowError(f"{rsu_id} candidate count is not an integer") from exc
                expected_count = rsu_candidate_counts[rsu_id]
                if count != expected_count:
                    raise WorkflowError(f"{rsu_id} candidate count must be {expected_count}, found {count}")
                tp_refs = set(parse_tp_ids(cells[2]))
                expected_tps = {
                    tp_id
                    for tp_id, item in final_by_id.items()
                    if rsu_id in item["source_rsus"]
                }
                if tp_refs != expected_tps:
                    raise WorkflowError(
                        f"{rsu_id} Final TP Refs must be {sorted(expected_tps)}, found {sorted(tp_refs)}"
                    )
                status = clean_cell(cells[3])
                expected_status = "covered" if expected_tps else ("zero-candidate" if count == 0 else "excluded")
                if status != expected_status:
                    raise WorkflowError(f"{rsu_id} coverage result must be {expected_status}, found {status}")
                explanation = clean_cell(cells[4])
                if status in {"zero-candidate", "excluded"} and (explanation in {"无", "不适用"} or len(explanation) < 8):
                    raise WorkflowError(f"{rsu_id} {status} coverage requires a concrete explanation")
            if rsu_seen != valid_rsus:
                raise WorkflowError(f"RSU coverage mismatch; missing={sorted(valid_rsus - rsu_seen)}")

            rendered_final_text = replace_context_resource_index(
                final_text,
                model,
                iter(referenced_context_ids),
                output_dir,
            )
            if rendered_final_text != final_text:
                atomic_write_text(final_path, rendered_final_text)

            old_final_hashes = (
                final_state.get("module_test_points_sha256"),
                final_state.get("coverage_matrix_sha256"),
            )
            final_state["status"] = "validated"
            final_state["validated_at"] = utc_now()
            final_state["module_test_points_sha256"] = sha256_file(final_path)
            final_state["coverage_matrix_sha256"] = sha256_file(coverage_path)
            state["finalization"] = final_state
            new_final_hashes = (
                final_state["module_test_points_sha256"],
                final_state["coverage_matrix_sha256"],
            )
            if old_final_hashes != new_final_hashes:
                state["case_readiness"] = {"status": "not-ready", "result": None, "input_sha256": None, "input_document_sha256": None, "validated_at": None, "output_sha256": None}
            state["updated_at"] = utc_now()
            atomic_write_json(state_path(output_dir), state)

        print(f"FINAL_TEST_POINT_COUNT={len(final_ids)}")
        print(f"CANDIDATE_COUNT={len(candidate_details)}")
        print("FINALIZATION_STATUS=validated")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
