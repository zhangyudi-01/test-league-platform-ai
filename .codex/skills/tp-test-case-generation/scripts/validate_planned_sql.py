#!/usr/bin/env python3
"""Validate that SQL assets exactly implement the validated module plan."""
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
    save_json,
    sha256_file,
    source_hashes,
    state_lock,
    state_path,
    utc_now,
)
from generation_plan import load_plan
from sql_assets import SqlAssetError, load_registry, validate_assets
from sql_convergence import analyze_convergence, write_convergence_report


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate planned module SQL assets.")
    parser.add_argument("module_dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--preanalysis-dir", type=Path)
    parser.add_argument("--case-output-dir", type=Path)
    parser.add_argument("--db-config", type=Path)
    args = parser.parse_args()
    try:
        _, model, points_dir, case_dir = module_paths(
            args.module_dir, args.preanalysis_dir, args.manifest, args.case_output_dir
        )
        _, _, final_hash = load_final_test_points(points_dir, model)
        readiness_path = points_dir / CASE_READINESS_PATH
        readiness_hash = sha256_file(readiness_path)
        ensure_upstream_validation(points_dir, final_hash, readiness_hash)
        parse_case_readiness(readiness_path, model)
        _, context_hash, context_ready = read_context(context_path(case_dir))
        if not context_ready:
            raise WorkflowError("execution-context.md contains pending entries")
        current_hashes = source_hashes(model, final_hash, readiness_hash, context_hash)
        with state_lock(case_dir):
            state = load_json(state_path(case_dir))
            assert_source_hashes(state, current_hashes)
            if state.get("planning", {}).get("status") != "validated":
                raise WorkflowError("generation plan must validate before SQL validation")
            if state.get("planning", {}).get("output_sha256") != sha256_file(
                case_dir / "generation-plan.json"
            ):
                raise WorkflowError("generation-plan.json changed after validation")
            plan = load_plan(case_dir)
            planned = {item["sql_id"]: item for item in plan.get("sql_assets", [])}
            if not planned:
                state["sql_planning"] = {"status": "validated", "sql_count": 0, "validated_at": utc_now()}
                save_json(state_path(case_dir), state)
                print("STATUS=validated")
                print("SQL_COUNT=0")
                return 0
            try:
                registry = load_registry(case_dir)
            except SqlAssetError as exc:
                raise WorkflowError(str(exc)) from exc
            if set(registry) != set(planned):
                raise WorkflowError(
                    "SQL registry must exactly match the validated plan; "
                    f"planned={sorted(planned)}, actual={sorted(registry)}"
                )
            for sql_id, asset in registry.items():
                row = planned[sql_id]
                if asset.statement_type != "SELECT":
                    raise WorkflowError(f"{sql_id} must be SELECT")
                if asset.purpose != row["purpose"]:
                    raise WorkflowError(f"{sql_id} purpose differs from generation plan")
                if set(asset.data_closure_refs) != set(row.get("data_closure_refs", [])):
                    raise WorkflowError(f"{sql_id} Data Closure Refs differ from generation plan")
            convergence = analyze_convergence(case_dir)
            convergence_path = write_convergence_report(case_dir)
            if convergence["exact_duplicate_groups"]:
                duplicate_ids = [
                    ",".join(group["sql_ids"])
                    for group in convergence["exact_duplicate_groups"]
                ]
                raise WorkflowError(
                    "planned SQL contains exact duplicate assets; consolidate the plan and manifest: "
                    + "; ".join(duplicate_ids)
                )
            try:
                report = validate_assets(
                    case_dir,
                    args.module_dir.resolve(),
                    db_config_path=args.db_config,
                    required_sql_ids=sorted(planned),
                )
            except SqlAssetError as exc:
                raise WorkflowError(str(exc)) from exc
            state["sql_planning"] = {
                **state.get("sql_planning", {}),
                "status": "validated",
                "sql_count": len(planned),
                "manifest_sha256": sha256_file(case_dir / "sql" / "sql-manifest.json"),
                "validation_sha256": sha256_file(case_dir / "sql" / "validation.json"),
                "convergence_report_sha256": sha256_file(convergence_path),
                "validated_at": utc_now(),
            }
            state["updated_at"] = utc_now()
            save_json(state_path(case_dir), state)
        print("STATUS=validated")
        print(f"SQL_COUNT={len(report['assets'])}")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
