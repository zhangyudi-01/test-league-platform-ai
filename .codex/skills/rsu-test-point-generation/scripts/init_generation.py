#!/usr/bin/env python3
"""Initialize or reconcile deterministic RSU generation state."""

from __future__ import annotations

import argparse

from common import (
    WorkflowError, add_layout_arguments, atomic_write_json, default_output_dir,
    ensure_output_scaffold, load_state, next_record, parse_module,
    reconcile_state, resolve_module_layout, run_preanalysis_validation, state_lock,
    state_path,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize sequential RSU test-point generation.")
    add_layout_arguments(parser)
    args = parser.parse_args()
    try:
        layout = resolve_module_layout(args.module_dir, args.preanalysis_dir, args.manifest)
        output_dir = default_output_dir(layout, args.output_dir)
        validation = run_preanalysis_validation(layout, output_dir)
        with state_lock(output_dir):
            model = parse_module(layout)
            ensure_output_scaffold(model, output_dir)
            state = load_state(output_dir, layout)
            state, _ = reconcile_state(model, output_dir, state)
            atomic_write_json(state_path(output_dir), state)
        counts: dict[str, int] = {}
        for item in state["rsus"]:
            status = item["generation_status"]
            counts[status] = counts.get(status, 0) + 1
        upcoming = next_record(state)
        print(validation.splitlines()[-1] if validation else "Upstream validation passed")
        print(f"PREANALYSIS_DIR={layout.preanalysis_dir}")
        print(f"MANIFEST={layout.manifest_path or 'LEGACY'}")
        print(f"STATE_FILE={state_path(output_dir)}")
        print("STATUS_COUNTS=" + ",".join(f"{key}:{counts[key]}" for key in sorted(counts)))
        print(f"NEXT_RSU={upcoming['rsu_id'] if upcoming else 'NONE'}")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
