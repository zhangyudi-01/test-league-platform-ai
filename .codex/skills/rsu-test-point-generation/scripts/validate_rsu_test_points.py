#!/usr/bin/env python3
"""Validate the prepared RSU candidate file and advance one state entry."""

from __future__ import annotations

import argparse
from pathlib import Path

from candidate_validation import (
    _require_source_part_traceability,
    validate_candidate_document,
)
from common import (
    WorkflowError,
    add_layout_arguments,
    atomic_write_json,
    default_output_dir,
    load_state,
    next_record,
    parse_module,
    reconcile_state,
    record_paths,
    resolve_module_layout,
    run_preanalysis_validation,
    sha256_file,
    state_lock,
    state_path,
    utc_now,
)


def require_source_part_traceability(text: str, label: str, parent_present: bool) -> None:
    """Compatibility wrapper for callers of the former single-RSU validator helper."""

    _require_source_part_traceability(text, label, parent_present)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate exactly the currently prepared RSU output.")
    add_layout_arguments(parser)
    parser.add_argument("--candidate-file", type=Path)
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
            state, bundles = reconcile_state(model, output_dir, state)
            record = next_record(state)
            if record is None:
                raise WorkflowError("all RSUs are already validated")
            rsu_id = record["rsu_id"]
            if record["generation_status"] != "prepared":
                details = "; ".join(record.get("blockers", []))
                raise WorkflowError(
                    f"earliest nonvalidated RSU is {rsu_id} with status {record['generation_status']}"
                    + (f": {details}" if details else "")
                )
            bundle = bundles[rsu_id]
            input_file, expected_candidate = record_paths(output_dir, rsu_id)
            candidate_file = args.candidate_file.resolve() if args.candidate_file else expected_candidate
            if candidate_file.resolve() != expected_candidate.resolve():
                raise WorkflowError(f"wrong-order candidate: expected {expected_candidate}, received {candidate_file}")

            document, title_warnings = validate_candidate_document(
                model, bundle, input_file, candidate_file
            )
            record["generation_status"] = "validated"
            record["input_sha256"] = bundle.input_sha256
            record["current_input_sha256"] = bundle.input_sha256
            record["output_sha256"] = sha256_file(candidate_file)
            record["candidate_count"] = len(document.rows)
            record["validated_at"] = utc_now()
            record["blockers"] = []
            state["updated_at"] = utc_now()
            if all(item["generation_status"] == "validated" for item in state["rsus"]):
                state["finalization"] = {
                    "status": "ready",
                    "input_sha256": None,
                    "input_document_sha256": None,
                    "validated_at": None,
                    "module_test_points_sha256": None,
                    "coverage_matrix_sha256": None,
                }
                state["case_readiness"] = {
                    "status": "not-ready",
                    "result": None,
                    "input_sha256": None,
                    "input_document_sha256": None,
                    "validated_at": None,
                    "output_sha256": None,
                }
            atomic_write_json(state_path(output_dir), state)
            upcoming = next_record(state)
        print(f"VALIDATED_RSU={rsu_id}")
        print(f"CANDIDATE_COUNT={len(document.rows)}")
        for warning in title_warnings:
            print(f"WARNING: {warning}")
        print(f"NEXT_RSU={upcoming['rsu_id'] if upcoming else 'NONE'}")
        print("STOP_AFTER_THIS_RSU=true")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
