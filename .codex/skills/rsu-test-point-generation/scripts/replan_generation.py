#!/usr/bin/env python3
"""Convert replan-required RSUs into isolated complex batches and revalidate the plan."""

from __future__ import annotations

import argparse
import json

from common import (
    WorkflowError,
    add_layout_arguments,
    atomic_write_json,
    atomic_write_text,
    default_output_dir,
    load_state,
    parse_module,
    reconcile_state,
    resolve_module_layout,
    run_preanalysis_validation,
    state_lock,
    state_path,
    utc_now,
)
from generation_plan import load_plan, plan_path


def rebuilt_assignments(plan: dict, affected: set[str]) -> list[dict]:
    groups: list[list[dict]] = []
    current: list[dict] = []
    current_key: tuple[str, str, str] | None = None
    for raw in plan["rsus"]:
        item = dict(raw)
        original_batch = str(item["batch_id"])
        if item["rsu_id"] in affected:
            if current:
                groups.append(current)
                current = []
                current_key = None
            item["mode"] = "complex"
            item["rationale"] = f"重新规划为复杂单 RSU：{item['rationale']}"
            groups.append([item])
            continue
        key = (original_batch, item["mode"], item["context_signature"])
        if current and key != current_key:
            groups.append(current)
            current = []
        current.append(item)
        current_key = key
    if current:
        groups.append(current)
    result: list[dict] = []
    for index, group in enumerate(groups, start=1):
        batch_id = f"BATCH-{index:03d}"
        for item in group:
            item["batch_id"] = batch_id
            result.append(item)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Apply a local RSU generation replan.")
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
                raise WorkflowError("generation state does not exist")
            state, _ = reconcile_state(model, output_dir, state)
            affected = {
                item["rsu_id"] for item in state["rsus"]
                if item["generation_status"] == "replan-required"
            }
            if not affected:
                raise WorkflowError("no RSU is marked replan-required")
            plan = load_plan(output_dir)
            plan["rsus"] = rebuilt_assignments(plan, affected)
            plan["status"] = "validated"
            atomic_write_text(
                plan_path(output_dir), json.dumps(plan, ensure_ascii=False, indent=2) + "\n"
            )
            for record in state["rsus"]:
                if record["rsu_id"] in affected:
                    record["generation_status"] = "stale"
                    record["batch_id"] = None
                    record["last_error"] = None
            state["planning"] = {
                **state.get("planning", {}),
                "status": "prepared",
                "output_sha256": None,
                "semantic_sha256": None,
                "validated_at": None,
            }
            state["batches"] = []
            state.setdefault("replan_history", []).append(
                {"rsu_ids": sorted(affected), "replanned_at": utc_now(), "strategy": "complex-isolation"}
            )
            state["updated_at"] = utc_now()
            atomic_write_json(state_path(output_dir), state)
        print("STATUS=prepared")
        print(f"REPLANNED_RSUS={','.join(sorted(affected))}")
        print("NEXT_ACTION=run validate_generation_plan.py")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
