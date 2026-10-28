#!/usr/bin/env python3
"""Safely reopen one validated RSU after a semantic finalization review."""

from __future__ import annotations

import argparse
import copy
from pathlib import Path

from common import (
    WorkflowError,
    add_layout_arguments,
    atomic_write_json,
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


def not_ready_finalization() -> dict:
    return {
        "status": "not-ready",
        "input_sha256": None,
        "input_document_sha256": None,
        "validated_at": None,
        "module_test_points_sha256": None,
        "coverage_matrix_sha256": None,
    }


def not_ready_case_readiness() -> dict:
    return {
        "status": "not-ready",
        "result": None,
        "input_sha256": None,
        "input_document_sha256": None,
        "validated_at": None,
        "output_sha256": None,
    }


def reopen_validated_rsu(
    state: dict,
    rsu_id: str,
    reason: str,
    reopened_at: str,
) -> dict:
    """Return a reopened state without mutating the caller's state object."""

    normalized_reason = " ".join(reason.split())
    if not normalized_reason:
        raise WorkflowError("reopen reason must not be empty")

    updated = copy.deepcopy(state)
    records = updated.get("rsus")
    if not isinstance(records, list):
        raise WorkflowError("generation state rsus must be a list")

    matches = [index for index, item in enumerate(records) if item.get("rsu_id") == rsu_id]
    if not matches:
        raise WorkflowError(f"RSU does not exist in generation state: {rsu_id}")
    if len(matches) != 1:
        raise WorkflowError(f"generation state contains duplicate RSU: {rsu_id}")

    target = records[matches[0]]
    status = target.get("generation_status")
    if status != "validated":
        raise WorkflowError(
            f"RSU can only be reopened from validated; {rsu_id} is {status or 'missing-status'}"
        )

    history = updated.setdefault("reopen_history", [])
    if not isinstance(history, list):
        raise WorkflowError("generation state reopen_history must be a list")

    previous_rsu_state = copy.deepcopy(target)
    target_batch_id = target.get("batch_id")
    previous_batch_state = None
    if target_batch_id:
        matches = [
            item for item in updated.get("batches", [])
            if item.get("batch_id") == target_batch_id
        ]
        if len(matches) > 1:
            raise WorkflowError(f"generation state contains duplicate batch: {target_batch_id}")
        if matches:
            batch = matches[0]
            previous_batch_state = copy.deepcopy(batch)
            batch.update(
                {
                    "status": "pending",
                    "active_rsu_ids": [],
                    "input_file": None,
                    "input_sha256": None,
                    "prepared_at": None,
                    "validated_at": None,
                    "last_error": None,
                }
            )
    previous_finalization = copy.deepcopy(updated.get("finalization", {}))
    previous_case_readiness = copy.deepcopy(updated.get("case_readiness", {}))

    target["generation_status"] = "stale"
    target["output_sha256"] = None
    target["candidate_count"] = None
    target["validated_at"] = None
    target["blockers"] = []
    updated["finalization"] = not_ready_finalization()
    updated["case_readiness"] = not_ready_case_readiness()
    history.append(
        {
            "rsu_id": rsu_id,
            "reason": normalized_reason,
            "reopened_at": reopened_at,
            "previous_rsu_state": previous_rsu_state,
            "previous_batch_state": previous_batch_state,
            "previous_finalization": previous_finalization,
            "previous_case_readiness": previous_case_readiness,
        }
    )
    updated["updated_at"] = reopened_at
    return updated


def ensure_runner_not_active(output_dir: Path) -> None:
    runner_lock = output_dir / ".generation-runner.lock"
    if runner_lock.exists():
        raise WorkflowError(
            f"cannot reopen an RSU while a generation runner lock exists: {runner_lock}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Safely reopen one validated RSU for semantic regeneration."
    )
    add_layout_arguments(parser)
    parser.add_argument("rsu_id", help="Validated RSU-ID to reopen, for example RSU-008.")
    parser.add_argument(
        "--reason",
        required=True,
        help="Human-readable semantic reason recorded in generation-state.json.",
    )
    args = parser.parse_args()

    try:
        layout = resolve_module_layout(args.module_dir, args.preanalysis_dir, args.manifest)
        output_dir = default_output_dir(layout, args.output_dir)
        ensure_runner_not_active(output_dir)
        run_preanalysis_validation(layout, output_dir)
        with state_lock(output_dir):
            ensure_runner_not_active(output_dir)
            state = load_state(output_dir, layout)
            if state is None:
                raise WorkflowError(
                    "generation state does not exist; run init_generation.py before reopening an RSU"
                )
            model = parse_module(layout)
            state, _ = reconcile_state(model, output_dir, state)
            reopened_at = utc_now()
            updated = reopen_validated_rsu(
                state,
                args.rsu_id.strip(),
                args.reason,
                reopened_at,
            )
            atomic_write_json(state_path(output_dir), updated)

        print(f"STATE_FILE={state_path(output_dir)}")
        print(f"REOPENED_RSU={args.rsu_id.strip()}")
        print("PREVIOUS_STATUS=validated")
        print("STATUS=stale")
        print("NEXT_ACTION=run prepare_next_batch.py with the same layout arguments")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
