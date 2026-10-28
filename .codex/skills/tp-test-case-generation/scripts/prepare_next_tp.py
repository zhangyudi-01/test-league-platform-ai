#!/usr/bin/env python3
"""Materialize exactly one eligible TP input package and stop."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import (
    CASE_READINESS_PATH,
    WorkflowError,
    assert_source_hashes,
    atomic_write_text,
    case_document_template,
    context_path,
    ensure_upstream_validation,
    load_final_test_points,
    load_json,
    materialize_case_input,
    module_paths,
    next_pending,
    output_paths,
    parse_case_readiness,
    read_context,
    run_preanalysis_validation,
    save_json,
    session_input_paths,
    sha256_file,
    source_hashes,
    state_lock,
    state_path,
    utc_now,
)


def write_or_verify_text(path: Path, text: str, label: str) -> None:
    if path.is_file():
        if path.read_text(encoding="utf-8") != text:
            raise WorkflowError(f"{label} conflicts with deterministic materialization: {path}")
        return
    if path.exists():
        raise WorkflowError(f"{label} path is not a file: {path}")
    atomic_write_text(path, text)


def materialize_session_artifacts(bundle, case_dir: Path) -> dict[str, str]:
    module_path, context_path_value, delta_path = session_input_paths(
        case_dir, bundle.tp.tp_id, bundle.baseline_signature
    )
    write_or_verify_text(module_path, bundle.module_baseline_text, "module baseline")
    write_or_verify_text(context_path_value, bundle.context_baseline_text, "context baseline")
    write_or_verify_text(delta_path, bundle.delta_text, "TP delta input")

    manifest_path = case_dir / "baselines" / "baseline-manifest.json"
    manifest = load_json(manifest_path) if manifest_path.is_file() else {
        "schema_version": "tp-test-case-generation/baselines/v1",
        "module_baseline": {},
        "contexts": {},
        "tps": {},
    }
    if manifest.get("schema_version") != "tp-test-case-generation/baselines/v1":
        raise WorkflowError(f"unsupported baseline manifest schema: {manifest_path}")
    module_entry = {
        "file": module_path.relative_to(case_dir).as_posix(),
        "sha256": sha256_file(module_path),
    }
    existing_module = manifest.get("module_baseline")
    if existing_module and existing_module != module_entry:
        raise WorkflowError("module baseline manifest conflicts with deterministic materialization")
    manifest["module_baseline"] = module_entry
    contexts = manifest.setdefault("contexts", {})
    context_entry = {
        "file": context_path_value.relative_to(case_dir).as_posix(),
        "sha256": sha256_file(context_path_value),
        "semantic_sha256": bundle.context_baseline_sha256,
    }
    if bundle.baseline_signature in contexts and contexts[bundle.baseline_signature] != context_entry:
        raise WorkflowError(
            f"context baseline manifest conflicts for signature {bundle.baseline_signature}"
        )
    contexts[bundle.baseline_signature] = context_entry
    tps = manifest.setdefault("tps", {})
    tp_entry = {
        "baseline_signature": bundle.baseline_signature,
        "delta_file": delta_path.relative_to(case_dir).as_posix(),
        "delta_sha256": sha256_file(delta_path),
        "input_sha256": bundle.input_sha256,
    }
    if bundle.tp.tp_id in tps and tps[bundle.tp.tp_id] != tp_entry:
        raise WorkflowError(f"baseline manifest conflicts for {bundle.tp.tp_id}")
    tps[bundle.tp.tp_id] = tp_entry
    save_json(manifest_path, manifest)
    return {
        "module_baseline_file": module_entry["file"],
        "module_baseline_sha256": module_entry["sha256"],
        "context_baseline_file": context_entry["file"],
        "context_baseline_sha256": context_entry["sha256"],
        "baseline_signature": bundle.baseline_signature,
        "session_input_file": tp_entry["delta_file"],
        "session_input_sha256": tp_entry["delta_sha256"],
    }


def recover_preexisting_preparation(
    pending: dict,
    bundle,
    input_path: Path,
    output_path: Path,
    case_dir: Path,
    session_fields: dict[str, str] | None = None,
) -> bool:
    """Recover a prepared TP whose state was demoted after runner interruption."""

    if not input_path.is_file() or not output_path.is_file():
        return False
    if input_path.read_text(encoding="utf-8") != bundle.text:
        return False
    pending.update(
        {
            "status": "prepared",
            "input_sha256": bundle.input_sha256,
            "input_document_sha256": sha256_file(input_path),
            "input_file": input_path.relative_to(case_dir).as_posix(),
            "output_file": output_path.relative_to(case_dir).as_posix(),
            "output_sha256": None,
            "case_count": None,
            "prepared_at": pending.get("prepared_at") or utc_now(),
            "validated_at": None,
            "sql_refs": [],
            "sql_validation_report_sha256": None,
            "sql_asset_hashes": {},
            "sql_registry_sha256": None,
            "blockers": [],
            **(session_fields or {}),
        }
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare one TP testcase input package.")
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
        if list(readiness.tp_status) != [point.tp_id for point in points]:
            raise WorkflowError("readiness TP rows must exactly match final TP order")

        context_text, context_hash, context_ready = read_context(context_path(case_dir))
        current_hashes = source_hashes(model, final_hash, readiness_hash, context_hash)
        with state_lock(case_dir):
            state = load_json(state_path(case_dir))
            assert_source_hashes(state, current_hashes)
            if state.get("planning", {}).get("status") != "validated":
                raise WorkflowError("generation plan must validate before TP preparation")
            if state.get("sql_planning", {}).get("status") != "validated":
                raise WorkflowError("planned SQL assets must validate before TP preparation")
            pending = next_pending(state)
            if pending is None:
                print("STATUS=all-tps-validated")
                print(f"CASE_OUTPUT_DIR={case_dir}")
                return 0
            tp = next(point for point in points if point.tp_id == pending["tp_id"])
            all_ready = readiness.result == "ready" and all(
                readiness.tp_status[point.tp_id] == "ready" for point in points
            )
            if not all_ready:
                blocked_tps = [
                    point.tp_id for point in points if readiness.tp_status[point.tp_id] != "ready"
                ]
                pending_ciq = sorted(
                    {
                        ciq
                        for blocked_tp in blocked_tps
                        for ciq in readiness.tp_ciq_refs.get(blocked_tp, ())
                    }
                )
                print("STATUS=blocked-input")
                print(f"NEXT_TP={tp.tp_id}")
                print(f"BLOCKED_TPS={', '.join(blocked_tps)}")
                print(f"PENDING_CIQ={', '.join(pending_ciq) or '无'}")
                print("所有 TP 的用例就绪性必须为 ready，才能开始任何正式用例生成")
                return 2
            if not context_ready:
                print("STATUS=blocked-input")
                print(f"NEXT_TP={tp.tp_id}")
                print("执行上下文仍有 pending 项；补齐 execution-context.md 后再执行本命令")
                return 2
            if any(item.get("status") != "validated" for item in state.get("tps", []) if item.get("order", 0) < tp.order):
                raise WorkflowError(f"{tp.tp_id} cannot start before all previous TP records are validated")

            input_path, output_path = output_paths(case_dir, tp.tp_id)
            bundle = materialize_case_input(
                model,
                readiness,
                context_text,
                context_hash,
                tp,
                points_dir,
                case_dir,
            )
            if bundle.blockers:
                raise WorkflowError("; ".join(bundle.blockers))
            session_fields = materialize_session_artifacts(bundle, case_dir)
            if pending.get("status") == "prepared":
                if not input_path.is_file() or not output_path.is_file():
                    raise WorkflowError(
                        f"{tp.tp_id} is marked prepared but its input/output template is missing; refresh the workspace"
                    )
                if pending.get("input_document_sha256") != sha256_file(input_path):
                    raise WorkflowError(
                        f"{tp.tp_id} input document changed after preparation; refresh the workspace"
                    )
                if pending.get("input_sha256") != bundle.input_sha256:
                    raise WorkflowError(
                        f"{tp.tp_id} prepared input no longer matches deterministic materialization; "
                        "refresh the workspace"
                    )
                for key, value in session_fields.items():
                    existing = pending.get(key)
                    if existing not in {None, value}:
                        raise WorkflowError(
                            f"{tp.tp_id} prepared session artifact changed for {key}; refresh the workspace"
                        )
                    pending[key] = value
                state["updated_at"] = utc_now()
                save_json(state_path(case_dir), state)
                print("STATUS=awaiting-validation")
                print(f"TP_ID={tp.tp_id}")
                print(f"INPUT={input_path}")
                print(f"OUTPUT={output_path}")
                print(f"INPUT_SHA256={bundle.input_sha256}")
                print(f"MODULE_BASELINE={case_dir / session_fields['module_baseline_file']}")
                print(f"CONTEXT_BASELINE={case_dir / session_fields['context_baseline_file']}")
                print(f"TP_DELTA={case_dir / session_fields['session_input_file']}")
                print(f"BASELINE_SIGNATURE={session_fields['baseline_signature']}")
                print("当前 TP 已准备；只完成该文档并运行 validate_tp_test_cases.py，不要准备下一个 TP")
                return 0
            if pending.get("status") != "pending":
                raise WorkflowError(f"unexpected TP state for {tp.tp_id}: {pending.get('status')}")
            if input_path.exists() or output_path.exists():
                if recover_preexisting_preparation(
                    pending, bundle, input_path, output_path, case_dir, session_fields
                ):
                    state["updated_at"] = utc_now()
                    save_json(state_path(case_dir), state)
                    print("STATUS=awaiting-validation")
                    print(f"TP_ID={tp.tp_id}")
                    print(f"INPUT={input_path}")
                    print(f"OUTPUT={output_path}")
                    print(f"INPUT_SHA256={bundle.input_sha256}")
                    print(f"MODULE_BASELINE={case_dir / session_fields['module_baseline_file']}")
                    print(f"CONTEXT_BASELINE={case_dir / session_fields['context_baseline_file']}")
                    print(f"TP_DELTA={case_dir / session_fields['session_input_file']}")
                    print(f"BASELINE_SIGNATURE={session_fields['baseline_signature']}")
                    print("RECOVERY=pre-existing deterministic input/output restored to prepared")
                    print("当前 TP 已恢复；只完成该文档并运行 validate_tp_test_cases.py，不要准备下一个 TP")
                    return 0
                raise WorkflowError(
                    f"{tp.tp_id} has conflicting pre-existing generated files; use init_generation.py --refresh instead of overwriting"
                )

            atomic_write_text(input_path, bundle.text)
            atomic_write_text(
                output_path,
                case_document_template(tp.tp_id, bundle.input_sha256, bool(tp.data_closure_refs)),
            )
            pending.update(
                {
                    "status": "prepared",
                    "input_sha256": bundle.input_sha256,
                    "input_document_sha256": sha256_file(input_path),
                    "input_file": input_path.relative_to(case_dir).as_posix(),
                    "output_file": output_path.relative_to(case_dir).as_posix(),
                    "output_sha256": None,
                    "case_count": None,
                    "prepared_at": utc_now(),
                    "validated_at": None,
                    "sql_refs": [],
                    "sql_validation_report_sha256": None,
                    "sql_asset_hashes": {},
                    "sql_registry_sha256": None,
                    "blockers": [],
                    **session_fields,
                }
            )
            state["updated_at"] = utc_now()
            save_json(state_path(case_dir), state)

        print("STATUS=prepared")
        print(f"TP_ID={tp.tp_id}")
        print(f"INPUT={input_path}")
        print(f"OUTPUT={output_path}")
        print(f"INPUT_SHA256={bundle.input_sha256}")
        print(f"MODULE_BASELINE={case_dir / session_fields['module_baseline_file']}")
        print(f"CONTEXT_BASELINE={case_dir / session_fields['context_baseline_file']}")
        print(f"TP_DELTA={case_dir / session_fields['session_input_file']}")
        print(f"BASELINE_SIGNATURE={session_fields['baseline_signature']}")
        print("下一步：只根据该输入包生成该 TP 的 1～N 条用例，写入 OUTPUT 后运行 validate_tp_test_cases.py")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
