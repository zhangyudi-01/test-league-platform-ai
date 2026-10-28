#!/usr/bin/env python3
"""Materialize all TP inputs and output templates for the next planned batch."""
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
    output_paths,
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
from prepare_next_tp import materialize_session_artifacts, write_or_verify_text


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare the next planned testcase batch.")
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
        point_by_id = {point.tp_id: point for point in points}
        readiness_path = points_dir / CASE_READINESS_PATH
        readiness = parse_case_readiness(readiness_path, model)
        readiness_hash = sha256_file(readiness_path)
        ensure_upstream_validation(points_dir, final_hash, readiness_hash)
        context_text, context_hash, context_ready = read_context(context_path(case_dir))
        if readiness.result != "ready" or not context_ready:
            print("STATUS=blocked-input")
            return 2
        current_hashes = source_hashes(model, final_hash, readiness_hash, context_hash)
        with state_lock(case_dir):
            state = load_json(state_path(case_dir))
            assert_source_hashes(state, current_hashes)
            if state.get("planning", {}).get("status") != "validated":
                raise WorkflowError("generation plan is not validated")
            if state.get("sql_planning", {}).get("status") != "validated":
                raise WorkflowError("planned SQL assets are not validated")
            batch = next(
                (item for item in state.get("batches", []) if item.get("status") != "validated"),
                None,
            )
            if batch is None:
                print("STATUS=all-batches-validated")
                return 0
            earlier = []
            for item in state["batches"]:
                if item["batch_id"] == batch["batch_id"]:
                    break
                earlier.append(item)
            if any(item.get("status") != "validated" for item in earlier):
                raise WorkflowError("a later batch cannot start before earlier batches validate")
            state_by_tp = {item["tp_id"]: item for item in state["tps"]}
            manifest_lines = [
                f"# {batch['batch_id']} 用例生成输入清单",
                "",
                f"- 模式：`{batch['mode']}`",
                f"- TP：`{', '.join(batch['tp_ids'])}`",
                f"- SQL Refs：`{', '.join(batch.get('sql_refs', [])) or '无'}`",
                "",
                "## 执行边界",
                "",
                "- 一次完成本批次列出的全部 TP；逐个 TP 判断所需用例数量，不预设一 TP 一用例。仅当独立业务风险、不可合并前置或操作、独立可判断预期、独立回归价值四项同时成立时拆分，并在每条追溯说明中给出具体依据；否则合并可执行验证。",
                "- 每条用例只覆盖当前 TP 的独有断言，不重复相邻 TP 已覆盖的完整流程。",
                "- 简单前置允许 `无` 或一句关键条件；步骤与预期必须具体、编号并一一对应。",
                "- 禁止在正文写当前 TP、来源场景、场景矩阵、数据闭包执行计划或核心操作等内部占位话术。",
                "- SQL 资产只读，只能引用计划分配给各 TP 的 SQL-ID。",
                "",
                "## TP 输入与输出",
                "",
                "| TP-ID | 完整 INPUT | 模块基线 | 上下文基线 | Delta | OUTPUT | 计划 SQL |",
                "|---|---|---|---|---|---|---|",
            ]
            for tp_id in batch["tp_ids"]:
                point = point_by_id[tp_id]
                record = state_by_tp[tp_id]
                input_path, output_path = output_paths(case_dir, tp_id)
                bundle = materialize_case_input(
                    model, readiness, context_text, context_hash, point, points_dir, case_dir
                )
                if bundle.blockers:
                    raise WorkflowError("; ".join(bundle.blockers))
                session_fields = materialize_session_artifacts(bundle, case_dir)
                write_or_verify_text(input_path, bundle.text, f"{tp_id} input")
                if not output_path.exists():
                    atomic_write_text(output_path, case_document_template(tp_id, bundle.input_sha256, False))
                record.update(
                    {
                        "status": "prepared",
                        "input_sha256": bundle.input_sha256,
                        "input_document_sha256": sha256_file(input_path),
                        "input_file": input_path.relative_to(case_dir).as_posix(),
                        "output_file": output_path.relative_to(case_dir).as_posix(),
                        "prepared_at": record.get("prepared_at") or utc_now(),
                        "blockers": [],
                        **session_fields,
                    }
                )
                planned_sql = record.get("planned_sql_refs", [])
                manifest_lines.append(
                    f"| {tp_id} | `{input_path.relative_to(case_dir).as_posix()}` | "
                    f"`{session_fields['module_baseline_file']}` | "
                    f"`{session_fields['context_baseline_file']}` | "
                    f"`{session_fields['session_input_file']}` | "
                    f"`{output_path.relative_to(case_dir).as_posix()}` | "
                    f"{', '.join(planned_sql) or '无'} |"
                )
            batch_input = case_dir / "inputs" / f"{batch['batch_id']}-input.md"
            input_text = "\n".join(manifest_lines) + "\n"
            write_or_verify_text(batch_input, input_text, f"{batch['batch_id']} input")
            batch.update(
                {
                    "status": "prepared",
                    "input_file": batch_input.relative_to(case_dir).as_posix(),
                    "input_sha256": sha256_file(batch_input),
                    "prepared_at": batch.get("prepared_at") or utc_now(),
                }
            )
            state["updated_at"] = utc_now()
            save_json(state_path(case_dir), state)
        print("STATUS=prepared")
        print(f"BATCH_ID={batch['batch_id']}")
        print(f"BATCH_MODE={batch['mode']}")
        print(f"TP_IDS={','.join(batch['tp_ids'])}")
        print(f"BATCH_INPUT={batch_input}")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

