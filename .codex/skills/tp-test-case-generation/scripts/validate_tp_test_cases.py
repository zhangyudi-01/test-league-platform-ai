#!/usr/bin/env python3
"""Validate one prepared TP testcase document and advance one state record."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    CASE_READINESS_PATH,
    WorkflowError,
    assert_source_hashes,
    context_path,
    ensure_upstream_validation,
    load_final_test_points,
    load_json,
    module_paths,
    next_pending,
    output_paths,
    parse_case_readiness,
    read_context,
    run_preanalysis_validation,
    save_json,
    sha256_file,
    sql_registry_digest,
    source_hashes,
    state_lock,
    state_path,
    utc_now,
    validate_case_rows,
)


def select_validation_record(state: dict, tp_id: str, revalidate: bool) -> dict:
    """Select the only state record that this invocation may update."""
    if revalidate:
        record = next((item for item in state.get("tps", []) if item.get("tp_id") == tp_id), None)
        if record is None:
            raise WorkflowError(f"unknown TP-ID: {tp_id}")
        if record.get("status") != "validated":
            raise WorkflowError(f"{tp_id} is not already validated")
        return record

    expected = next_pending(state)
    if expected is None:
        raise WorkflowError("all TPs are already validated")
    if expected.get("tp_id") != tp_id:
        raise WorkflowError(
            f"only next TP {expected.get('tp_id')} can be validated; received {tp_id}"
        )
    if expected.get("status") != "prepared":
        raise WorkflowError(f"{tp_id} has not been prepared")
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate testcase output for exactly one TP.")
    parser.add_argument("module_dir", type=Path)
    parser.add_argument("tp_id", help="Prepared TP-ID to validate.")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--preanalysis-dir", type=Path)
    parser.add_argument("--case-output-dir", type=Path)
    parser.add_argument("--db-config", type=Path)
    parser.add_argument(
        "--revalidate",
        action="store_true",
        help=(
            "Revalidate an already validated TP after an output-only correction. "
            "Upstream sources and the prepared input must remain unchanged."
        ),
    )
    args = parser.parse_args()
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
        if readiness.result != "ready" or any(
            readiness.tp_status.get(point.tp_id) != "ready" for point in points
        ):
            raise WorkflowError("all TP case-readiness rows must be ready before testcase validation")
        _, context_hash, context_ready = read_context(context_path(case_dir))
        if not context_ready:
            raise WorkflowError("execution-context.md contains pending entries")
        current_hashes = source_hashes(model, final_hash, readiness_hash, context_hash)

        with state_lock(case_dir):
            state = load_json(state_path(case_dir))
            assert_source_hashes(state, current_hashes)
            expected = select_validation_record(state, args.tp_id, args.revalidate)
            point = next((item for item in points if item.tp_id == args.tp_id), None)
            if point is None:
                raise WorkflowError(f"unknown TP-ID: {args.tp_id}")
            input_path, output_path = output_paths(case_dir, args.tp_id)
            if not input_path.is_file() or not output_path.is_file():
                raise WorkflowError(f"{args.tp_id} prepared input or testcase output is missing")
            if expected.get("input_document_sha256") != sha256_file(input_path):
                raise WorkflowError(f"{args.tp_id} input document changed after preparation; refresh the workspace")
            if not expected.get("input_sha256"):
                raise WorkflowError(f"{args.tp_id} has no input manifest hash in generation state")

            count, digest, sql_report = validate_case_rows(
                model,
                point,
                expected["input_sha256"],
                output_path,
                ciq_refs=readiness.tp_ciq_refs.get(point.tp_id, ()),
                db_config_path=args.db_config,
                planned_sql_refs=tuple(expected.get("planned_sql_refs", [])),
            )
            expected.update(
                {
                    "status": "validated",
                    "case_count": count,
                    "output_sha256": digest,
                    "validated_at": utc_now(),
                    "blockers": [],
                    "sql_refs": [item["sql_id"] for item in (sql_report or {}).get("assets", [])],
                    "sql_validation_report_sha256": sha256_file(case_dir / "sql" / "validation.json")
                    if sql_report is not None
                    else None,
                    "sql_asset_hashes": {
                        item["sql_id"]: item["sha256"]
                        for item in (sql_report or {}).get("assets", [])
                    },
                    "sql_registry_sha256": sql_registry_digest(case_dir)
                    if sql_report is not None
                    else None,
                }
            )
            if args.revalidate and state.get("finalization", {}).get("status") != "not-ready":
                state["finalization"] = {"status": "not-ready"}
            state["updated_at"] = utc_now()
            save_json(state_path(case_dir), state)
        print("STATUS=revalidated" if args.revalidate else "STATUS=validated")
        print(f"TP_ID={args.tp_id}")
        print(f"CASE_COUNT={count}")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
