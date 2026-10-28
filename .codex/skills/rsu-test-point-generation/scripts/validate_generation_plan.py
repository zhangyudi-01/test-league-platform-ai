#!/usr/bin/env python3
"""Validate an AI-authored RSU generation plan and install scheduler batches."""

from __future__ import annotations

import argparse

from common import (
    WorkflowError,
    add_layout_arguments,
    atomic_write_json,
    default_output_dir,
    display_path,
    load_state,
    parse_module,
    reconcile_state,
    resolve_module_layout,
    run_preanalysis_validation,
    sha256_file,
    state_lock,
    state_path,
    utc_now,
)
from generation_plan import (
    load_plan,
    plan_digest,
    plan_path,
    plan_source_hash,
    planning_input_path,
    validate_plan,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate module RSU generation plan.")
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
            state, bundles = reconcile_state(model, output_dir, state)
            planning = state.get("planning", {})
            if planning.get("status") not in {"prepared", "validated"}:
                raise WorkflowError("generation planning is not prepared")
            planning_input_sha256 = sha256_file(planning_input_path(output_dir))
            validated, batches = validate_plan(
                load_plan(output_dir), model, bundles, planning_input_sha256
            )
            digest = plan_digest(validated)
            if planning.get("status") == "validated":
                if planning.get("semantic_sha256") != digest:
                    raise WorkflowError("validated generation plan changed; refresh before replanning")
                print("STATUS=validated")
                print(f"BATCH_COUNT={len(batches)}")
                return 0
            records = {item["rsu_id"]: item for item in state["rsus"]}
            installed = []
            for batch in batches:
                statuses = {records[rsu_id]["generation_status"] for rsu_id in batch["rsu_ids"]}
                status = "validated" if statuses == {"validated"} else "pending"
                installed.append(
                    {
                        **batch,
                        "status": status,
                        "input_file": None,
                        "input_sha256": None,
                        "result_file": f"batch-results/{batch['batch_id']}/result.json",
                        "prepared_at": None,
                        "validated_at": utc_now() if status == "validated" else None,
                        "last_error": None,
                        "replan_count": 0,
                    }
                )
                for rsu_id in batch["rsu_ids"]:
                    records[rsu_id]["batch_id"] = batch["batch_id"]
                    records[rsu_id]["context_signature"] = batch["context_signature"]
            state["planning"] = {
                **planning,
                "status": "validated",
                "source_sha256": plan_source_hash(model, bundles),
                "output_file": display_path(plan_path(output_dir), output_dir),
                "output_sha256": sha256_file(plan_path(output_dir)),
                "semantic_sha256": digest,
                "validated_at": utc_now(),
            }
            state["batches"] = installed
            state["finalization"] = {
                "status": "ready" if all(item["generation_status"] == "validated" for item in state["rsus"]) else "not-ready",
                "input_sha256": None,
                "input_document_sha256": None,
                "validated_at": None,
                "module_test_points_sha256": None,
                "coverage_matrix_sha256": None,
            }
            state["case_readiness"] = {
                "status": "not-ready", "result": None, "input_sha256": None,
                "input_document_sha256": None, "validated_at": None, "output_sha256": None,
            }
            state["updated_at"] = utc_now()
            atomic_write_json(state_path(output_dir), state)
        print("STATUS=validated")
        print(f"BATCH_COUNT={len(batches)}")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
