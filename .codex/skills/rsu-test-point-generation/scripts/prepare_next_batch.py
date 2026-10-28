#!/usr/bin/env python3
"""Materialize one planned RSU batch without advancing shared validation state."""

from __future__ import annotations

import argparse
import json

from common import (
    WorkflowError,
    add_layout_arguments,
    archive_candidate,
    atomic_write_json,
    atomic_write_text,
    default_output_dir,
    display_path,
    ensure_output_scaffold,
    load_state,
    load_template,
    parse_module,
    read_text,
    reconcile_state,
    record_paths,
    resolve_module_layout,
    run_preanalysis_validation,
    session_input_path,
    sha256_file,
    sha256_text,
    state_lock,
    state_path,
    utc_now,
)


def _select_batch(state: dict, batch_id: str | None) -> dict | None:
    batches = state.get("batches", [])
    if batch_id:
        return next((item for item in batches if item.get("batch_id") == batch_id), None)
    return next((item for item in batches if item.get("status") not in {"validated"}), None)


def _write_or_verify(path, text: str, label: str) -> None:
    if path.is_file() and sha256_text(read_text(path)) != sha256_text(text):
        raise WorkflowError(f"{label} conflicts with deterministic prepared content: {path}")
    if not path.exists():
        atomic_write_text(path, text)


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare one planned RSU generation batch.")
    add_layout_arguments(parser)
    parser.add_argument("--batch-id")
    args = parser.parse_args()
    try:
        layout = resolve_module_layout(args.module_dir, args.preanalysis_dir, args.manifest)
        output_dir = default_output_dir(layout, args.output_dir)
        run_preanalysis_validation(layout, output_dir)
        with state_lock(output_dir):
            model = parse_module(layout)
            ensure_output_scaffold(model, output_dir)
            state = load_state(output_dir, layout)
            if state is None:
                raise WorkflowError("generation state does not exist")
            state, bundles = reconcile_state(model, output_dir, state)
            if state.get("planning", {}).get("status") != "validated":
                raise WorkflowError("generation plan is not validated")
            batch = _select_batch(state, args.batch_id)
            if batch is None:
                if args.batch_id:
                    raise WorkflowError(f"unknown batch: {args.batch_id}")
                print("STATUS=all-batches-validated")
                return 0
            if batch.get("status") == "validated":
                print("STATUS=validated")
                print(f"BATCH_ID={batch['batch_id']}")
                return 0
            if batch.get("status") == "replan-required":
                raise WorkflowError(f"{batch['batch_id']} requires replanning before preparation")
            records = {item["rsu_id"]: item for item in state["rsus"]}
            previous_active_rsus = list(batch.get("active_rsu_ids") or [])
            manifest_lines = [
                f"# {batch['batch_id']} RSU 测试点候选生成输入",
                "",
                f"- 模式：`{batch['mode']}`",
                f"- RSU：`{', '.join(batch['rsu_ids'])}`",
                f"- Context Signature：`{batch['context_signature']}`",
                "",
                "## 执行边界",
                "",
                "- 一次处理本批列出的全部 RSU；每个 RSU 只写自己的 by-rsu 文件。",
                "- generation-state.json、generation-plan.json、最终模块文件和其他批次文件只读。",
                "- 你是高级测试工程师。完整生成来源支持的测试点；不设目标数量，不为凑数拆分，也不为减少数量合并。",
                "- 一个候选必须能够独立触发、独立执行、独立判定并独立定位缺陷；不同操作、控件/对象、业务结果、状态迁移、异常处理或边界约束应分别形成候选。",
                "- 状态、错误码、字段、等价类、边界值以及页面/接口/数据库/日志观察层，若代表不同操作、对象、状态迁移、结果或可定位缺陷就拆分；只有同一操作、对象、生命周期阶段和预期结果下的等价输入或共同证据才合并。",
                "- 生成前后进行原子性自审；不得把复选框可选性、全选范围、操作按钮可用性和操作后的状态重算写在同一个候选中。",
                "- 使用测试项、测试点、备注：测试项简洁分类，测试点包含必要条件/操作和明确预期，备注可为空且不能隐藏关键断言。只合并三列均完全重复的候选。若上下文不足，写 replan-required，不得猜测或遗漏。",
                "",
                "## RSU 输入与授权输出",
                "",
                "| RSU-ID | 完整 INPUT | Delta | OUTPUT | 动态依赖 |",
                "|---|---|---|---|---|",
            ]
            active_rsus: list[str] = []
            for rsu_id in batch["rsu_ids"]:
                record = records[rsu_id]
                if record["generation_status"] == "validated":
                    continue
                if record["generation_status"] == "blocked":
                    raise WorkflowError(f"{rsu_id} is blocked: {'; '.join(record.get('blockers', []))}")
                bundle = bundles[rsu_id]
                input_file, candidate_file = record_paths(output_dir, rsu_id)
                delta_file = session_input_path(output_dir, rsu_id)
                atomic_write_text(input_file, bundle.rendered)
                atomic_write_text(delta_file, bundle.session_rendered)
                staged_candidate = output_dir / "batches" / batch["batch_id"] / "by-rsu" / f"{rsu_id}.md"
                if not staged_candidate.exists():
                    atomic_write_text(
                        staged_candidate,
                        load_template(
                            "rsu-candidates-data-closure.md.tmpl"
                            if model.data_closure_enabled else "rsu-candidates.md.tmpl",
                            {"RSU_ID": rsu_id, "INPUT_SHA256": bundle.input_sha256},
                        ),
                    )
                record.update(
                    {
                        "generation_status": "prepared",
                        "input_sha256": bundle.input_sha256,
                        "current_input_sha256": bundle.input_sha256,
                        "output_sha256": None,
                        "candidate_count": None,
                        "validated_at": None,
                        "blockers": [],
                        "staged_candidate_file": display_path(staged_candidate, output_dir),
                    }
                )
                active_rsus.append(rsu_id)
                dynamic = [item.resource_id for item in bundle.dynamic_materials]
                manifest_lines.append(
                    f"| {rsu_id} | `{display_path(input_file, output_dir)}` | "
                    f"`{display_path(delta_file, output_dir)}` | `{display_path(staged_candidate, output_dir)}` | "
                    f"{', '.join(dynamic) or '无'} |"
                )
            if not active_rsus:
                batch["status"] = "validated"
                batch["validated_at"] = batch.get("validated_at") or utc_now()
                atomic_write_json(state_path(output_dir), state)
                print("STATUS=validated")
                print(f"BATCH_ID={batch['batch_id']}")
                return 0
            batch_input = output_dir / "batches" / f"{batch['batch_id']}-input.md"
            manifest_lines.extend(
                [
                    "",
                    "## 批次结果",
                    "",
                    f"完成后填写 `batch-results/{batch['batch_id']}/result.json`。正常完成填 complete；"
                    "只有确有复杂时序、冲突依赖或语义宽度不足以在本批可靠处理时才填 replan-required，并写具体理由。",
                ]
            )
            batch_text = "\n".join(manifest_lines) + "\n"
            if previous_active_rsus != active_rsus:
                atomic_write_text(batch_input, batch_text)
            else:
                _write_or_verify(batch_input, batch_text, batch["batch_id"])
            result_file = output_dir / "batch-results" / batch["batch_id"] / "result.json"
            rsu_results = ",\n    ".join(
                json.dumps(
                    {"rsu_id": rsu_id, "status": "draft", "reason": ""},
                    ensure_ascii=False,
                    indent=2,
                ).replace("\n", "\n    ")
                for rsu_id in active_rsus
            )
            result_text = load_template(
                "batch-result.json.tmpl",
                {"BATCH_ID": batch["batch_id"], "RSU_RESULTS": rsu_results},
            )
            if previous_active_rsus != active_rsus or not result_file.exists():
                atomic_write_text(result_file, result_text)
            batch.update(
                {
                    "status": "prepared",
                    "active_rsu_ids": active_rsus,
                    "input_file": display_path(batch_input, output_dir),
                    "input_sha256": sha256_file(batch_input),
                    "result_file": display_path(result_file, output_dir),
                    "prepared_at": batch.get("prepared_at") or utc_now(),
                    "last_error": None,
                }
            )
            state["updated_at"] = utc_now()
            atomic_write_json(state_path(output_dir), state)
        print("STATUS=prepared")
        print(f"BATCH_ID={batch['batch_id']}")
        print(f"BATCH_MODE={batch['mode']}")
        print(f"RSU_IDS={','.join(active_rsus)}")
        print(f"BATCH_INPUT={batch_input}")
        print(f"BATCH_RESULT={result_file}")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
