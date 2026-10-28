#!/usr/bin/env python3
"""Materialize the earliest nonvalidated RSU and only that RSU."""

from __future__ import annotations

import argparse

from common import (
    WorkflowError, add_layout_arguments, archive_candidate, atomic_write_json,
    atomic_write_text, default_output_dir, ensure_output_scaffold, load_state,
    load_template, next_record, parse_module, reconcile_state, record_paths,
    resolve_module_layout, run_preanalysis_validation, session_input_path,
    state_lock, state_path,
)


def ensure_session_input(bundle, path) -> None:
    """Create or verify the deterministic module-session delta for one RSU."""

    if path.is_file():
        if path.read_text(encoding="utf-8") != bundle.session_rendered:
            raise WorkflowError(
                f"{bundle.rsu.rsu_id} module-session delta changed after preparation; "
                "remove only the conflicting derived delta and rerun preparation"
            )
        return
    atomic_write_text(path, bundle.session_rendered)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare exactly the next RSU input package.")
    add_layout_arguments(parser)
    args = parser.parse_args()
    try:
        layout = resolve_module_layout(args.module_dir, args.preanalysis_dir, args.manifest)
        output_dir = default_output_dir(layout, args.output_dir)
        run_preanalysis_validation(layout, output_dir)
        with state_lock(output_dir):
            model = parse_module(layout)
            ensure_output_scaffold(model, output_dir)
            state = load_state(output_dir, layout)
            state, bundles = reconcile_state(model, output_dir, state)
            record = next_record(state)
            if record is None:
                atomic_write_json(state_path(output_dir), state)
                print("ALL_RSUS_VALIDATED=true")
                print("NEXT_ACTION=run prepare_finalization.py in a fresh invocation")
                return 0
            rsu_id = record["rsu_id"]
            bundle = bundles[rsu_id]
            if record["generation_status"] == "blocked":
                atomic_write_json(state_path(output_dir), state)
                print(f"RSU_ID={rsu_id}")
                for blocker in record["blockers"]:
                    print(f"BLOCKER={blocker}")
                return 1
            input_file, candidate_file = record_paths(output_dir, rsu_id)
            runner_session_input = session_input_path(output_dir, rsu_id)
            if record["generation_status"] == "prepared":
                ensure_session_input(bundle, runner_session_input)
                atomic_write_json(state_path(output_dir), state)
                print(f"RSU_ID={rsu_id}")
                print(f"INPUT_FILE={input_file}")
                print(f"SESSION_INPUT={runner_session_input}")
                print(f"SESSION_INPUT_SHA256={bundle.session_input_sha256}")
                print(
                    "SESSION_SOURCE_FINGERPRINT_SHA256="
                    f"{bundle.session_source_fingerprint_sha256}"
                )
                print(f"CANDIDATE_FILE={candidate_file}")
                print("STATUS=prepared")
                return 0
            if record["generation_status"] == "stale":
                archived = archive_candidate(output_dir, candidate_file, rsu_id, record.get("input_sha256"))
                if archived:
                    print(f"ARCHIVED_CANDIDATE={archived}")
            atomic_write_text(input_file, bundle.rendered)
            atomic_write_text(runner_session_input, bundle.session_rendered)
            atomic_write_text(
                candidate_file,
                load_template(
                    "rsu-candidates-data-closure.md.tmpl"
                    if model.data_closure_enabled
                    else "rsu-candidates.md.tmpl",
                    {"RSU_ID": rsu_id, "INPUT_SHA256": bundle.input_sha256},
                ),
            )
            record["generation_status"] = "prepared"
            record["input_sha256"] = bundle.input_sha256
            record["current_input_sha256"] = bundle.input_sha256
            record["output_sha256"] = None
            record["candidate_count"] = None
            record["validated_at"] = None
            record["blockers"] = []
            atomic_write_json(state_path(output_dir), state)
        print(f"RSU_ID={rsu_id}")
        print(f"INPUT_SHA256={bundle.input_sha256}")
        print(f"INPUT_FILE={input_file}")
        print(f"SESSION_INPUT={runner_session_input}")
        print(f"SESSION_INPUT_SHA256={bundle.session_input_sha256}")
        print(
            "SESSION_SOURCE_FINGERPRINT_SHA256="
            f"{bundle.session_source_fingerprint_sha256}"
        )
        print(f"CANDIDATE_FILE={candidate_file}")
        print("STATUS=prepared")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
