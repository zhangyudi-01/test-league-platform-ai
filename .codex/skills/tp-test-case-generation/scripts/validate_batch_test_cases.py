#!/usr/bin/env python3
"""Atomically validate every TP output in one prepared generation batch."""
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
    output_paths,
    parse_case_readiness,
    read_context,
    run_preanalysis_validation,
    save_json,
    sha256_file,
    source_hashes,
    state_lock,
    state_path,
    utc_now,
    validate_case_rows,
)
from sql_assets import SqlAssetError, require_current_validation


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one prepared testcase batch.")
    parser.add_argument("module_dir", type=Path)
    parser.add_argument("batch_id")
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--preanalysis-dir", type=Path)
    parser.add_argument("--case-output-dir", type=Path)
    parser.add_argument("--db-config", type=Path)
    args = parser.parse_args()
    try:
        layout, model, points_dir, case_dir = module_paths(
            args.module_dir, args.preanalysis_dir, args.manifest, args.case_output_dir
        )
        run_preanalysis_validation(layout, case_dir)
        points, _, final_hash = load_final_test_points(points_dir, model)
        point_by_id = {point.tp_id: point for point in points}
        readiness_path = points_dir / CASE_READINESS_PATH
        readiness = parse_case_readiness(readiness_path, model)
        readiness_hash = sha256_file(readiness_path)
        ensure_upstream_validation(points_dir, final_hash, readiness_hash)
        _, context_hash, context_ready = read_context(context_path(case_dir))
        if not context_ready:
            raise WorkflowError("execution-context.md contains pending entries")
        current_hashes = source_hashes(model, final_hash, readiness_hash, context_hash)
        with state_lock(case_dir):
            state = load_json(state_path(case_dir))
            assert_source_hashes(state, current_hashes)
            batch = next(
                (item for item in state.get("batches", []) if item.get("batch_id") == args.batch_id),
                None,
            )
            if batch is None or batch.get("status") != "prepared":
                raise WorkflowError(f"{args.batch_id} is not the prepared batch")
            records = {item["tp_id"]: item for item in state["tps"]}
            required_sql = sorted(
                {
                    sql_id
                    for tp_id in batch["tp_ids"]
                    for sql_id in records[tp_id].get("planned_sql_refs", [])
                }
            )
            if required_sql:
                try:
                    require_current_validation(
                        case_dir,
                        required_sql,
                        module_dir=model.module_dir,
                        db_config_path=args.db_config,
                    )
                except SqlAssetError as exc:
                    raise WorkflowError(str(exc)) from exc
            results = {}
            for tp_id in batch["tp_ids"]:
                record = records[tp_id]
                point = point_by_id[tp_id]
                input_path, output_path = output_paths(case_dir, tp_id)
                if record.get("input_document_sha256") != sha256_file(input_path):
                    raise WorkflowError(f"{tp_id} input changed after batch preparation")
                results[tp_id] = validate_case_rows(
                    model,
                    point,
                    record["input_sha256"],
                    output_path,
                    ciq_refs=readiness.tp_ciq_refs.get(tp_id, ()),
                    db_config_path=args.db_config,
                    planned_sql_refs=tuple(record.get("planned_sql_refs", [])),
                    validate_sql_now=False,
                )
            total = 0
            for tp_id, (count, digest, sql_report) in results.items():
                total += count
                records[tp_id].update(
                    {
                        "status": "validated",
                        "case_count": count,
                        "output_sha256": digest,
                        "validated_at": utc_now(),
                        "sql_refs": list(records[tp_id].get("planned_sql_refs", [])),
                    }
                )
            batch.update(
                {
                    "status": "validated",
                    "case_count": total,
                    "validated_at": utc_now(),
                }
            )
            state["updated_at"] = utc_now()
            save_json(state_path(case_dir), state)
        print("STATUS=validated")
        print(f"BATCH_ID={args.batch_id}")
        print(f"TP_COUNT={len(batch['tp_ids'])}")
        print(f"CASE_COUNT={total}")
        return 0
    except (WorkflowError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
