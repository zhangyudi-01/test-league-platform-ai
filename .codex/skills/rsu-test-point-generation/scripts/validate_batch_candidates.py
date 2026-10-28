#!/usr/bin/env python3
"""Parent-side validation and atomic state commit for one RSU batch."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from candidate_validation import validate_candidate_document
from common import (
    WorkflowError,
    add_layout_arguments,
    atomic_write_json,
    atomic_write_text,
    archive_candidate,
    default_output_dir,
    load_state,
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

BATCH_RESULT_SCHEMA = "rsu-test-point-generation/batch-result-v1"


def load_batch_result(path: Path, batch: dict) -> list[dict]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"batch result is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"invalid batch result JSON: {path}: {exc}") from exc
    if not isinstance(value, dict) or value.get("schema_version") != BATCH_RESULT_SCHEMA:
        raise WorkflowError("batch result has an invalid schema_version")
    if value.get("batch_id") != batch["batch_id"]:
        raise WorkflowError("batch result batch_id does not match scheduler state")
    aggregate_status = value.get("status")
    if aggregate_status not in {"draft", "partial", "complete", "replan-required"}:
        raise WorkflowError(
            "batch result status must be draft, partial, complete or replan-required"
        )
    rows = value.get("rsus")
    if not isinstance(rows, list) or not all(isinstance(item, dict) for item in rows):
        raise WorkflowError("batch result rsus must be an object array")
    expected = list(batch.get("active_rsu_ids") or batch["rsu_ids"])
    found = [str(item.get("rsu_id", "")).strip() for item in rows]
    if found != expected:
        raise WorkflowError(f"batch result RSU order mismatch: expected={expected}, found={found}")
    allowed = {"draft", "complete", "replan-required", "failed"}
    for item in rows:
        status = item.get("status")
        reason = " ".join(str(item.get("reason", "")).split())
        if status not in allowed:
            raise WorkflowError(f"{item.get('rsu_id')} has invalid batch result status: {status}")
        if status in {"failed", "replan-required"} and len(reason) < 8:
            raise WorkflowError(f"{item.get('rsu_id')} {status} needs a concrete reason")
    has_replan = any(item["status"] == "replan-required" for item in rows)
    if aggregate_status == "replan-required" and not has_replan:
        raise WorkflowError("batch result aggregate status conflicts with per-RSU statuses")
    if aggregate_status == "complete" and has_replan:
        raise WorkflowError("batch result aggregate status conflicts with per-RSU statuses")
    if aggregate_status == "complete" and any(item["status"] != "complete" for item in rows):
        raise WorkflowError("complete batch result contains a non-complete RSU")
    terminal_count = sum(item["status"] != "draft" for item in rows)
    unfinished_count = sum(item["status"] in {"draft", "failed"} for item in rows)
    if aggregate_status == "partial" and (terminal_count == 0 or unfinished_count == 0):
        raise WorkflowError("partial batch result must contain progress and unfinished RSUs")
    if aggregate_status == "draft" and terminal_count == 0:
        raise WorkflowError("draft batch result contains no recoverable progress")
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate and commit one prepared RSU batch.")
    add_layout_arguments(parser)
    parser.add_argument("batch_id")
    args = parser.parse_args()
    try:
        layout = resolve_module_layout(args.module_dir, args.preanalysis_dir, args.manifest)
        output_dir = default_output_dir(layout, args.output_dir)
        run_preanalysis_validation(layout, output_dir)
        replan = False
        total = 0
        warnings: list[str] = []
        with state_lock(output_dir):
            model = parse_module(layout)
            state = load_state(output_dir, layout)
            if state is None:
                raise WorkflowError("generation state does not exist")
            state, bundles = reconcile_state(model, output_dir, state)
            batch = next(
                (item for item in state.get("batches", []) if item.get("batch_id") == args.batch_id),
                None,
            )
            if batch is None or batch.get("status") not in {"prepared", "running"}:
                raise WorkflowError(f"{args.batch_id} is not a prepared or running batch")
            result_file = output_dir / str(batch.get("result_file", ""))
            rows = load_batch_result(result_file, batch)
            records = {item["rsu_id"]: item for item in state["rsus"]}
            validated: dict[str, tuple[object, list[str], Path]] = {}
            for result in rows:
                rsu_id = result["rsu_id"]
                if result["status"] != "complete":
                    continue
                input_file, candidate_file = record_paths(output_dir, rsu_id)
                staged_value = records[rsu_id].get("staged_candidate_file")
                if not isinstance(staged_value, str) or not staged_value:
                    raise WorkflowError(f"{rsu_id} has no staged candidate file")
                staged_candidate = output_dir / staged_value
                document, item_warnings = validate_candidate_document(
                    model, bundles[rsu_id], input_file, staged_candidate
                )
                validated[rsu_id] = (document, item_warnings, staged_candidate)

            for result in rows:
                rsu_id = result["rsu_id"]
                record = records[rsu_id]
                if result["status"] == "replan-required":
                    replan = True
                    record["generation_status"] = "replan-required"
                    record["last_error"] = " ".join(str(result.get("reason", "")).split())
                    record["output_sha256"] = None
                    record["candidate_count"] = None
                    record["validated_at"] = None
                    continue
                if result["status"] in {"draft", "failed"}:
                    record["generation_status"] = "prepared"
                    record["last_error"] = (
                        " ".join(str(result.get("reason", "")).split())
                        if result["status"] == "failed" else None
                    )
                    record["output_sha256"] = None
                    record["candidate_count"] = None
                    record["validated_at"] = None
                    continue
                document, item_warnings, staged_candidate = validated[rsu_id]
                _, candidate_file = record_paths(output_dir, rsu_id)
                if candidate_file.is_file():
                    archive_candidate(output_dir, candidate_file, rsu_id, record.get("output_sha256"))
                atomic_write_text(candidate_file, staged_candidate.read_text(encoding="utf-8-sig"))
                digest = sha256_file(candidate_file)
                record.update(
                    {
                        "generation_status": "validated",
                        "input_sha256": bundles[rsu_id].input_sha256,
                        "current_input_sha256": bundles[rsu_id].input_sha256,
                        "output_sha256": digest,
                        "candidate_count": len(document.rows),
                        "validated_at": utc_now(),
                        "blockers": [],
                        "last_error": None,
                        "staged_candidate_file": None,
                    }
                )
                total += len(document.rows)
                warnings.extend(item_warnings)
            unfinished = [
                item["rsu_id"] for item in rows if item["status"] in {"draft", "failed"}
            ]
            if replan:
                batch_status = "replan-required"
            elif unfinished:
                batch_status = "prepared"
            else:
                batch_status = "validated"
            validated_total = sum(
                int(records[rsu_id].get("candidate_count") or 0)
                for rsu_id in batch["rsu_ids"]
                if records[rsu_id].get("generation_status") == "validated"
            )
            batch.update(
                {
                    "status": batch_status,
                    "validated_at": utc_now() if batch_status == "validated" else None,
                    "candidate_count": validated_total,
                    "last_error": (
                        "; ".join(
                            str(records[item["rsu_id"]].get("last_error") or "")
                            for item in rows
                            if item["status"] in {"replan-required", "failed"}
                        )
                        if replan or unfinished else None
                    ),
                    "runner_pid": None,
                    "runner_run_id": None,
                    "started_at": None,
                }
            )
            all_validated = all(item["generation_status"] == "validated" for item in state["rsus"])
            state["finalization"] = {
                "status": "ready" if all_validated else "not-ready",
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
        status = "replan-required" if replan else ("partial" if unfinished else "validated")
        print(f"STATUS={status}")
        print(f"BATCH_ID={args.batch_id}")
        print(f"VALIDATED_RSU_COUNT={len(validated)}")
        print(f"CANDIDATE_COUNT={total}")
        if unfinished:
            print(f"RETRY_RSU_IDS={','.join(unfinished)}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        return 2 if replan else (3 if unfinished else 0)
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
