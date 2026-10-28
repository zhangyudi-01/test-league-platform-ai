#!/usr/bin/env python3
"""Validate the module generation plan and install its batches in scheduler state."""
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
    parse_case_readiness,
    read_context,
    run_preanalysis_validation,
    save_json,
    sha256_file,
    source_hashes,
    state_lock,
    state_path,
    utc_now,
)
from generation_plan import load_plan, plan_digest, plan_source_hash, validate_plan


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate module testcase generation plan.")
    parser.add_argument("module_dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--preanalysis-dir", type=Path)
    parser.add_argument("--case-output-dir", type=Path)
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
        _, context_hash, context_ready = read_context(context_path(case_dir))
        if not context_ready:
            raise WorkflowError("execution-context.md contains pending entries")
        current_hashes = source_hashes(model, final_hash, readiness_hash, context_hash)
        with state_lock(case_dir):
            state = load_json(state_path(case_dir))
            assert_source_hashes(state, current_hashes)
            validated = validate_plan(
                load_plan(case_dir),
                module_name=model.module_name,
                source_sha256=plan_source_hash(current_hashes),
                points=points,
                known_dc_ids=set(getattr(model, "data_closure_ids", ())),
            )
            digest = plan_digest(validated)
            if state.get("planning", {}).get("status") == "validated":
                if state.get("planning", {}).get("semantic_sha256") != digest:
                    raise WorkflowError("validated generation plan changed; refresh before replanning")
                print("STATUS=validated")
                print(f"BATCH_COUNT={len(validated['batches'])}")
                print(f"SQL_COUNT={len(validated['sql_assets'])}")
                return 0
            if any(item.get("status") != "pending" for item in state.get("tps", [])):
                raise WorkflowError("cannot install a new generation plan after testcase work started")
            state["planning"] = {
                **state.get("planning", {}),
                "status": "validated",
                "output_sha256": sha256_file(case_dir / "generation-plan.json"),
                "semantic_sha256": digest,
                "validated_at": utc_now(),
            }
            state["sql_planning"] = {"status": "pending"}
            state["batches"] = [
                {**batch, "status": "pending", "prepared_at": None, "validated_at": None}
                for batch in validated["batches"]
            ]
            sql_by_tp = validated["sql_by_tp"]
            for record in state["tps"]:
                record["planned_sql_refs"] = sql_by_tp[record["tp_id"]]
            state["finalization"] = {"status": "not-ready"}
            state["updated_at"] = utc_now()
            save_json(state_path(case_dir), state)
        print("STATUS=validated")
        print(f"BATCH_COUNT={len(validated['batches'])}")
        print(f"SQL_COUNT={len(validated['sql_assets'])}")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
