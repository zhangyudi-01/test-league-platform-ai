#!/usr/bin/env python3
"""Initialize a deterministic, TP-by-TP testcase workspace."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    CASE_READINESS_PATH,
    CASE_STATE_SCHEMA_VERSION,
    WorkflowError,
    archive_generated_artifacts,
    atomic_write_text,
    context_path,
    ensure_dirs,
    ensure_upstream_validation,
    load_final_test_points,
    load_json,
    load_template,
    module_paths,
    parse_case_readiness,
    read_context,
    render_execution_context,
    run_preanalysis_validation,
    save_json,
    sha256_file,
    source_hashes,
    state_lock,
    state_path,
    utc_now,
)


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Initialize deterministic TP testcase generation.")
    parser.add_argument("module_dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--preanalysis-dir", type=Path)
    parser.add_argument("--case-output-dir", type=Path)
    parser.add_argument(
        "--refresh",
        action="store_true",
        help="Archive generated case artifacts and reset deterministic state after input drift.",
    )
    return parser.parse_args()


def _records(points, readiness, existing: dict | None, case_dir: Path, preserve: bool) -> list[dict]:
    previous = {item.get("tp_id"): item for item in (existing or {}).get("tps", [])}
    records: list[dict] = []
    for point in points:
        old = previous.get(point.tp_id, {})
        output = case_dir / "by-tp" / f"{point.tp_id}.md"
        keep_validated = (
            preserve
            and old.get("status") == "validated"
            and output.is_file()
            and old.get("output_sha256") == sha256_file(output)
        )
        keep_prepared = preserve and old.get("status") == "prepared"
        keep_existing = keep_validated or keep_prepared
        records.append(
            {
                "tp_id": point.tp_id,
                "order": point.order,
                "readiness_status": readiness.tp_status[point.tp_id],
                "status": old.get("status") if keep_existing else "pending",
                "input_sha256": old.get("input_sha256") if keep_existing else None,
                "input_document_sha256": old.get("input_document_sha256") if keep_existing else None,
                "input_file": old.get("input_file") if keep_existing else None,
                "module_baseline_file": old.get("module_baseline_file") if keep_existing else None,
                "module_baseline_sha256": old.get("module_baseline_sha256") if keep_existing else None,
                "context_baseline_file": old.get("context_baseline_file") if keep_existing else None,
                "context_baseline_sha256": old.get("context_baseline_sha256") if keep_existing else None,
                "baseline_signature": old.get("baseline_signature") if keep_existing else None,
                "session_input_file": old.get("session_input_file") if keep_existing else None,
                "session_input_sha256": old.get("session_input_sha256") if keep_existing else None,
                "output_file": old.get("output_file") if keep_existing else None,
                "output_sha256": old.get("output_sha256") if keep_validated else None,
                "case_count": old.get("case_count") if keep_validated else None,
                "prepared_at": old.get("prepared_at") if keep_existing else None,
                "validated_at": old.get("validated_at") if keep_validated else None,
                "sql_refs": old.get("sql_refs", []) if keep_validated else [],
                "sql_validation_report_sha256": old.get("sql_validation_report_sha256")
                if keep_validated
                else None,
                "sql_asset_hashes": old.get("sql_asset_hashes", {}) if keep_validated else {},
                "sql_registry_sha256": old.get("sql_registry_sha256") if keep_validated else None,
                "planned_sql_refs": old.get("planned_sql_refs", []) if preserve else [],
                "blockers": list(readiness.tp_ciq_refs.get(point.tp_id, ()))
                if readiness.tp_status[point.tp_id] != "ready"
                else [],
            }
        )
    return records


def _state_incompatible(existing: dict | None) -> bool:
    return existing is not None and (
        existing.get("schema_version") != CASE_STATE_SCHEMA_VERSION
        or not all(key in existing for key in ("planning", "sql_planning", "batches"))
    )


def main() -> int:
    args = arguments()
    try:
        layout, model, points_dir, case_dir = module_paths(
            args.module_dir, args.preanalysis_dir, args.manifest, args.case_output_dir
        )
        run_preanalysis_validation(layout, case_dir)
        points, _, final_hash = load_final_test_points(points_dir, model)
        readiness_path = points_dir / CASE_READINESS_PATH
        readiness = parse_case_readiness(readiness_path, model)
        if list(readiness.tp_status) != [point.tp_id for point in points]:
            raise WorkflowError("readiness TP rows must exactly match final TP order")
        readiness_hash = sha256_file(readiness_path)
        ensure_upstream_validation(points_dir, final_hash, readiness_hash)

        state_file = state_path(case_dir)
        preliminary = load_json(state_file) if state_file.is_file() else None
        if _state_incompatible(preliminary) and not args.refresh:
            raise WorkflowError(
                "testcase output contract changed; rerun init_generation.py --refresh"
            )

        ensure_dirs(case_dir)
        with state_lock(case_dir):
            execution_context = context_path(case_dir)
            if not execution_context.exists():
                atomic_write_text(execution_context, render_execution_context(model.module_name, readiness))
            _, context_hash, context_ready = read_context(execution_context)
            current_hashes = source_hashes(model, final_hash, readiness_hash, context_hash)
            existing = load_json(state_file) if state_file.is_file() else None
            incompatible = _state_incompatible(existing)
            if incompatible and not args.refresh:
                raise WorkflowError(
                    "testcase output contract changed; rerun init_generation.py --refresh"
                )
            drifted = existing is not None and existing.get("source_hashes") != current_hashes
            if drifted and not args.refresh:
                raise WorkflowError(
                    "upstream artifact or execution context changed; rerun init_generation.py --refresh"
                )
            reset = bool(args.refresh or drifted or incompatible)
            if reset:
                archive_generated_artifacts(case_dir, "refresh:" + str(current_hashes))

            records = _records(points, readiness, existing, case_dir, preserve=not reset)
            now = utc_now()
            # Keep optional recovery/compatibility fields only on unchanged sources.
            state = {
                **(existing if existing and not reset else {}),
                "schema_version": CASE_STATE_SCHEMA_VERSION,
                "module_dir": model.module_dir.as_posix(),
                "preanalysis_dir": model.preanalysis_dir.as_posix(),
                "manifest_path": model.manifest_path.as_posix() if model.manifest_path else None,
                "upstream_test_points_dir": points_dir.as_posix(),
                "case_output_dir": case_dir.as_posix(),
                "readiness_result": readiness.result,
                "source_hashes": current_hashes,
                "created_at": (existing or {}).get("created_at", now),
                "updated_at": now,
                "tps": records,
                "planning": (existing or {}).get("planning", {"status": "pending"})
                if not reset
                else {"status": "pending"},
                "sql_planning": (existing or {}).get("sql_planning", {"status": "pending"})
                if not reset
                else {"status": "pending"},
                "batches": (existing or {}).get("batches", []) if not reset else [],
                "finalization": (existing or {}).get("finalization", {"status": "not-ready"})
                if not reset
                else {"status": "not-ready"},
            }
            save_json(state_file, state)
            readme = case_dir / "README.md"
            if not readme.exists():
                atomic_write_text(
                    readme,
                    load_template("README.md.tmpl", {"MODULE_NAME": model.module_name}),
                )

        all_tps_ready = all(readiness.tp_status[point.tp_id] == "ready" for point in points)
        ready = readiness.result == "ready" and all_tps_ready and context_ready
        print(f"CASE_OUTPUT_DIR={case_dir}")
        print(f"READINESS_RESULT={readiness.result}")
        print(f"EXECUTION_CONTEXT={context_path(case_dir)}")
        print("STATUS=initialized" if ready else "STATUS=blocked-input")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
