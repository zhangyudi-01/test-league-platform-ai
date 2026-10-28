#!/usr/bin/env python3
"""Prepare a fresh, module-wide semantic finalization pass."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from common import (
    BT,
    SKILL_DIR,
    WorkflowError,
    add_layout_arguments,
    atomic_write_json,
    atomic_write_text,
    collect_module_stage_sources,
    context_resource_index_template,
    default_output_dir,
    display_path,
    final_headers,
    load_state,
    parse_candidate_document,
    parse_module,
    read_text,
    reconcile_state,
    record_paths,
    resolve_module_layout,
    run_preanalysis_validation,
    sha256_file,
    sha256_text,
    state_lock,
    state_path,
    utc_now,
)


FINALIZATION_RULES = SKILL_DIR / "references" / "finalization-rules.md"
DATA_CLOSURE_FINALIZATION_RULES = (
    SKILL_DIR / "references" / "data-closure-finalization-rules.md"
)
DATA_CLOSURE_OUTPUT_CONTRACT = (
    SKILL_DIR / "references" / "data-closure-output-contract.md"
)


def archive_existing(output_dir: Path, path: Path, old_hash: str | None) -> None:
    """Move a superseded finalization artifact to history without overwriting it."""
    if not path.is_file():
        return
    history = output_dir / "history"
    history.mkdir(parents=True, exist_ok=True)
    suffix = (old_hash or sha256_file(path))[:12]
    target = history / f"finalization-{suffix}-{path.name}"
    counter = 1
    while target.exists():
        target = history / f"finalization-{suffix}-{counter}-{path.name}"
        counter += 1
    os.replace(path, target)


def render_material_section(resource_id: str, path: Path, content: str, module_dir: Path) -> str:
    return (
        f"## {resource_id}\n\n"
        f"- 文件：{BT}{display_path(path, module_dir)}{BT}\n"
        f"- SHA-256：{BT}{sha256_text(content)}{BT}\n\n"
        f"<!-- BEGIN {resource_id} -->\n{content.rstrip()}\n<!-- END {resource_id} -->"
    )


def render_session_source_index(
    sources: list[tuple[str, Path, str]],
    model,
) -> str:
    fixed_ids = set(model.fixed_resource_ids)
    lines = [
        "| Resource ID | 文件 | SHA-256 | Foundation 已加载 |",
        "|---|---|---|---|",
    ]
    for resource_id, path, content in sources:
        inherited = "是" if resource_id in fixed_ids else "否"
        lines.append(
            f"| {resource_id} | {BT}{display_path(path, model.module_dir)}{BT} | "
            f"{BT}{sha256_text(content)}{BT} | {inherited} |"
        )
    return "\n".join(lines)


def build_finalization_session_input(
    final_hash: str,
    candidate_sections: list[str],
    sources: list[tuple[str, Path, str]],
    model,
    finalization_rules: str,
    output_contract: str,
) -> str:
    fixed_ids = set(model.fixed_resource_ids)
    dynamic_sections = [
        render_material_section(resource_id, path, content, model.module_dir)
        for resource_id, path, content in sources
        if resource_id not in fixed_ids
    ]
    return (
        "# 模块测试点汇总与发布会话输入\n\n"
        "本文件仅供从当前模块 Foundation 独立 fork 的 finalization 阶段使用。"
        "Foundation 已加载的固定需求和契约不重复正文；下表路径与 SHA-256、当前候选和动态来源才是事实源。"
        "若 Foundation 身份或任一锚点不一致，停止并改读 `finalization-input.md`。\n\n"
        f"- 最终输入 SHA-256：{BT}{final_hash}{BT}\n"
        f"- 汇总规则 SHA-256：{BT}{sha256_text(finalization_rules)}{BT}\n"
        f"- 输出契约 SHA-256：{BT}{sha256_text(output_contract)}{BT}\n\n"
        "## 来源锚点\n\n"
        + render_session_source_index(sources, model)
        + "\n\n## 全部候选\n\n"
        + "\n\n".join(candidate_sections)
        + "\n\n## 当前阶段动态来源\n\n"
        + ("\n\n".join(dynamic_sections) or "无")
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare module-wide test-point finalization.")
    add_layout_arguments(parser)
    args = parser.parse_args()

    try:
        layout = resolve_module_layout(args.module_dir, args.preanalysis_dir, args.manifest)
        module_dir = layout.module_dir
        output_dir = default_output_dir(layout, args.output_dir)
        run_preanalysis_validation(layout, output_dir)
        with state_lock(output_dir):
            model = parse_module(layout)
            state = load_state(output_dir, layout)
            if state is None:
                raise WorkflowError("generation state does not exist; run init_generation.py first")
            state, _ = reconcile_state(model, output_dir, state)
            incomplete = next(
                (item for item in state["rsus"] if item["generation_status"] != "validated"),
                None,
            )
            if incomplete:
                raise WorkflowError(
                    "cannot finalize before all RSUs are validated; "
                    f"earliest is {incomplete['rsu_id']} ({incomplete['generation_status']})"
                )

            candidate_sections: list[str] = []
            candidate_manifest: list[dict[str, object]] = []
            candidate_rows: list[tuple[str, str]] = []
            rsu_counts: dict[str, int] = {}
            zero_reasons: dict[str, str] = {}
            for record in state["rsus"]:
                rsu_id = record["rsu_id"]
                _, candidate_file = record_paths(output_dir, rsu_id)
                if not candidate_file.is_file():
                    raise WorkflowError(f"validated RSU is missing its candidate file: {candidate_file}")
                document = parse_candidate_document(candidate_file, model.data_closure_enabled)
                content = read_text(candidate_file)
                rsu_counts[rsu_id] = len(document.rows)
                zero_reasons[rsu_id] = document.zero_reason
                candidate_manifest.append(
                    {
                        "rsu_id": rsu_id,
                        "input_sha256": document.input_sha256,
                        "candidate_sha256": sha256_text(content),
                        "candidate_count": len(document.rows),
                    }
                )
                candidate_sections.append(
                    f"## {rsu_id}\n\n"
                    f"- 文件：{BT}{display_path(candidate_file, output_dir)}{BT}\n\n"
                    f"<!-- BEGIN {rsu_id} CANDIDATES -->\n{content.rstrip()}\n"
                    f"<!-- END {rsu_id} CANDIDATES -->"
                )
                for cells in document.rows:
                    candidate_rows.append((cells[0].strip().strip(BT), rsu_id))

            sources = collect_module_stage_sources(model, state)
            source_manifest = [
                {
                    "resource_id": resource_id,
                    "path": display_path(path, module_dir),
                    "sha256": sha256_text(content),
                }
                for resource_id, path, content in sources
            ]
            source_sections = [
                render_material_section(resource_id, path, content, module_dir)
                for resource_id, path, content in sources
            ]

            finalization_rules = read_text(FINALIZATION_RULES)
            output_contract = read_text(SKILL_DIR / "references" / "output-contract.md")
            if model.data_closure_enabled:
                finalization_rules += "\n\n" + read_text(DATA_CLOSURE_FINALIZATION_RULES)
                output_contract += "\n\n" + read_text(DATA_CLOSURE_OUTPUT_CONTRACT)
            manifest = {
                "schema_version": 1,
                "candidates": candidate_manifest,
                "sources": source_manifest,
                "finalization_rules_sha256": sha256_text(finalization_rules),
                "output_contract_sha256": sha256_text(output_contract),
            }
            final_hash = sha256_text(
                json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            )

            finalization_input = output_dir / "finalization-input.md"
            finalization_session_input = output_dir / "finalization-session-input.md"
            final_points = output_dir / "module-test-points.md"
            coverage = output_dir / "coverage-matrix.md"
            input_text = (
                "# 模块测试点汇总与发布输入\n\n"
                "## 任务\n\n"
                "对全部逐 RSU 候选做精确重复检查、跨 RSU 归属核对、覆盖检查和稳定 TP-ID 分配。"
                "不得生成测试用例、详细前置条件或执行步骤。\n\n"
                f"- 最终输入 SHA-256：{BT}{final_hash}{BT}\n\n"
                "## 汇总规则\n\n"
                + finalization_rules.rstrip()
                + "\n\n## 输出契约\n\n"
                + output_contract.rstrip()
                + "\n\n## 全部候选\n\n"
                + "\n\n".join(candidate_sections)
                + "\n\n## 模块来源与上下文\n\n"
                + "\n\n".join(source_sections)
                + "\n"
            )
            input_document_sha256 = sha256_text(input_text)
            session_input_text = build_finalization_session_input(
                final_hash,
                candidate_sections,
                sources,
                model,
                finalization_rules,
                output_contract,
            )
            session_input_document_sha256 = sha256_text(session_input_text)
            previous = state.get("finalization", {})
            outputs_exist = all(path.is_file() for path in (finalization_input, final_points, coverage))
            same_prepared_input = (
                previous.get("input_sha256") == final_hash
                and previous.get("input_document_sha256") == input_document_sha256
                and finalization_input.is_file()
                and sha256_text(read_text(finalization_input)) == input_document_sha256
                and finalization_session_input.is_file()
                and sha256_text(read_text(finalization_session_input)) == session_input_document_sha256
            )
            if previous.get("status") == "prepared" and same_prepared_input and outputs_exist:
                atomic_write_json(state_path(output_dir), state)
                print(f"FINALIZATION_INPUT={finalization_input}")
                print(f"MODULE_TEST_POINTS={final_points}")
                print(f"COVERAGE_MATRIX={coverage}")
                print("STATUS=prepared")
                return 0
            if (
                previous.get("status") == "validated"
                and same_prepared_input
                and outputs_exist
                and previous.get("module_test_points_sha256") == sha256_file(final_points)
                and previous.get("coverage_matrix_sha256") == sha256_file(coverage)
            ):
                atomic_write_json(state_path(output_dir), state)
                print(f"FINALIZATION_INPUT={finalization_input}")
                print(f"MODULE_TEST_POINTS={final_points}")
                print(f"COVERAGE_MATRIX={coverage}")
                print("STATUS=validated")
                return 0

            archive_hash = previous.get("input_sha256")
            for path in (finalization_input, finalization_session_input, final_points, coverage):
                archive_existing(output_dir, path, archive_hash)

            atomic_write_text(finalization_input, input_text)
            atomic_write_text(finalization_session_input, session_input_text)
            output_headers = final_headers(model.data_closure_enabled)
            atomic_write_text(
                final_points,
                "# 模块最终测试点\n\n"
                "## 生成元数据\n\n"
                "| 字段 | 值 |\n"
                "|---|---|\n"
                f"| 最终输入 SHA-256 | {BT}{final_hash}{BT} |\n"
                f"| 生成结果 | {BT}待填写{BT} |\n\n"
                + context_resource_index_template(model, output_dir)
                + "\n\n"
                + "## 最终测试点\n\n"
                + "你是高级测试工程师。每个测试点表达一个可独立触发、执行、判定并定位缺陷的需求行为或规则；使用测试项、测试点、备注：测试项简洁分类，测试点直接包含必要条件/操作和明确预期，备注可为空且不能隐藏关键断言。"
                + "不得按目标数量增删测试点；仅当测试项、完整测试点和备注均完全重复时才合并。"
                + "若原候选已经复合多个独立行为，回退对应 RSU 重新生成。\n\n"
                + "| " + " | ".join(output_headers) + " |\n"
                + "|" + "|".join("---" for _ in output_headers) + "|\n",
            )

            coverage_lines = [
                "# 测试点覆盖矩阵",
                "",
                "## RSU 覆盖",
                "",
                "| RSU-ID | 候选数 | Final TP Refs | 处理结果 | 说明 |",
                "|---|---|---|---|---|",
            ]
            for record in state["rsus"]:
                rsu_id = record["rsu_id"]
                count = rsu_counts[rsu_id]
                if count == 0:
                    reason = zero_reasons[rsu_id] or "该 RSU 已在逐 RSU 阶段确认无独立测试点候选。"
                    coverage_lines.append(f"| {rsu_id} | 0 | 待填写 | 待填写 | {reason} |")
                else:
                    coverage_lines.append(f"| {rsu_id} | {count} | 待填写 | 待填写 | 待填写 |")
            coverage_lines.extend(
                [
                    "",
                    "## 候选归并",
                    "",
                    "| Candidate ID | Source RSU | 处理结果 | Final TP Refs | 说明 |",
                    "|---|---|---|---|---|",
                ]
            )
            for candidate_id, rsu_id in candidate_rows:
                coverage_lines.append(f"| {candidate_id} | {rsu_id} | 待填写 | 待填写 | 待填写 |")
            atomic_write_text(coverage, "\n".join(coverage_lines))

            state["finalization"] = {
                "status": "prepared",
                "input_sha256": final_hash,
                "input_document_sha256": input_document_sha256,
                "session_input_document_sha256": session_input_document_sha256,
                "validated_at": None,
                "module_test_points_sha256": None,
                "coverage_matrix_sha256": None,
            }
            state["case_readiness"] = {
                "status": "not-ready",
                "result": None,
                "input_sha256": None,
                "input_document_sha256": None,
                "validated_at": None,
                "output_sha256": None,
            }
            state["updated_at"] = utc_now()
            atomic_write_json(state_path(output_dir), state)

        print(f"FINALIZATION_SHA256={final_hash}")
        print(f"FINALIZATION_INPUT={finalization_input}")
        print(f"MODULE_TEST_POINTS={final_points}")
        print(f"COVERAGE_MATRIX={coverage}")
        print("STATUS=prepared")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
