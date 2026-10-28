#!/usr/bin/env python3
"""Prepare a self-contained test-case readiness review after TP finalization."""

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
    clean_cell,
    collect_module_stage_sources,
    column_value,
    default_output_dir,
    display_path,
    load_state,
    load_template,
    parse_final_document,
    parse_module,
    read_text,
    reconcile_state,
    resolve_module_layout,
    run_preanalysis_validation,
    sha256_file,
    sha256_text,
    state_lock,
    state_path,
    utc_now,
)


READINESS_RULES = SKILL_DIR / "references" / "case-readiness-rules.md"
OUTPUT_CONTRACT = SKILL_DIR / "references" / "output-contract.md"
DATA_CLOSURE_READINESS_RULES = (
    SKILL_DIR / "references" / "data-closure-readiness-rules.md"
)
DATA_CLOSURE_OUTPUT_CONTRACT = (
    SKILL_DIR / "references" / "data-closure-output-contract.md"
)


def archive_existing(output_dir: Path, path: Path, old_hash: str | None) -> None:
    if not path.is_file():
        return
    history = output_dir / "history"
    history.mkdir(parents=True, exist_ok=True)
    suffix = (old_hash or sha256_file(path))[:12]
    target = history / f"case-readiness-{suffix}-{path.name}"
    counter = 1
    while target.exists():
        target = history / f"case-readiness-{suffix}-{counter}-{path.name}"
        counter += 1
    os.replace(path, target)


def render_material_section(resource_id: str, path: Path, content: str, module_dir: Path) -> str:
    return (
        f"## {resource_id}\n\n"
        f"- 文件：{BT}{display_path(path, module_dir)}{BT}\n"
        f"- SHA-256：{BT}{sha256_text(content)}{BT}\n\n"
        f"<!-- BEGIN {resource_id} -->\n{content.rstrip()}\n<!-- END {resource_id} -->"
    )


def build_case_readiness_session_input(
    readiness_hash: str,
    final_text: str,
    coverage_text: str,
    sources: list[tuple[str, Path, str]],
    model,
    readiness_rules: str,
    output_contract: str,
) -> str:
    fixed_ids = set(model.fixed_resource_ids)
    source_index_lines = [
        "| Resource ID | 文件 | SHA-256 | Foundation 已加载 |",
        "|---|---|---|---|",
    ]
    dynamic_sections: list[str] = []
    for resource_id, path, content in sources:
        inherited = "是" if resource_id in fixed_ids else "否"
        source_index_lines.append(
            f"| {resource_id} | {BT}{display_path(path, model.module_dir)}{BT} | "
            f"{BT}{sha256_text(content)}{BT} | {inherited} |"
        )
        if resource_id not in fixed_ids:
            dynamic_sections.append(
                render_material_section(resource_id, path, content, model.module_dir)
            )
    return (
        "# 测试用例生成就绪性会话输入\n\n"
        "本文件仅供从当前模块 Foundation 独立 fork 的 readiness 阶段使用。"
        "Foundation 已加载的固定需求和契约不重复正文；最终测试点、覆盖矩阵、动态来源及其哈希是事实源。"
        "若 Foundation 身份或任一锚点不一致，停止并改读 `case-readiness-input.md`。\n\n"
        f"- 就绪输入 SHA-256：{BT}{readiness_hash}{BT}\n"
        f"- 就绪性规则 SHA-256：{BT}{sha256_text(readiness_rules)}{BT}\n"
        f"- 输出契约 SHA-256：{BT}{sha256_text(output_contract)}{BT}\n\n"
        "## 来源锚点\n\n"
        + "\n".join(source_index_lines)
        + "\n\n## 模块最终测试点\n\n"
        + final_text.rstrip()
        + "\n\n## 覆盖矩阵\n\n"
        + coverage_text.rstrip()
        + "\n\n## 当前阶段动态来源\n\n"
        + ("\n\n".join(dynamic_sections) or "无")
        + "\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare test-case generation readiness review.")
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
                raise WorkflowError("generation state does not exist; run init_generation.py first")
            state, _ = reconcile_state(model, output_dir, state)

            final_state = state.get("finalization", {})
            if final_state.get("status") != "validated":
                raise WorkflowError("module test points are not validated; finish finalization first")

            finalization_input = output_dir / "finalization-input.md"
            final_points = output_dir / "module-test-points.md"
            coverage = output_dir / "coverage-matrix.md"
            for path in (finalization_input, final_points, coverage):
                if not path.is_file():
                    raise WorkflowError(f"validated finalization artifact is missing: {path}")
            if final_state.get("module_test_points_sha256") != sha256_file(final_points):
                raise WorkflowError("module-test-points.md changed after validation")
            if final_state.get("coverage_matrix_sha256") != sha256_file(coverage):
                raise WorkflowError("coverage-matrix.md changed after validation")

            final_doc = parse_final_document(final_points, model.data_closure_enabled)
            readiness_rules = read_text(READINESS_RULES)
            output_contract = read_text(OUTPUT_CONTRACT)
            if model.data_closure_enabled:
                readiness_rules += "\n\n" + read_text(DATA_CLOSURE_READINESS_RULES)
                output_contract += "\n\n" + read_text(DATA_CLOSURE_OUTPUT_CONTRACT)
            source_input = read_text(finalization_input)
            final_text = read_text(final_points)
            coverage_text = read_text(coverage)
            readiness_manifest = {
                "schema_version": 1,
                "finalization_input_sha256": sha256_text(source_input),
                "module_test_points_sha256": sha256_text(final_text),
                "coverage_matrix_sha256": sha256_text(coverage_text),
                "readiness_rules_sha256": sha256_text(readiness_rules),
                "output_contract_sha256": sha256_text(output_contract),
            }
            readiness_hash = sha256_text(
                json.dumps(readiness_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            )

            readiness_input = output_dir / "case-readiness-input.md"
            readiness_session_input = output_dir / "case-readiness-session-input.md"
            readiness_output = output_dir / "test-case-readiness.md"
            input_text = (
                "# 测试用例生成就绪性审查输入\n\n"
                "## 任务\n\n"
                "逐个最终 TP 审查生成可执行测试用例所需的测试数据、环境、配置和可观察性输入。"
                "以用例设计的最小充分输入为门禁，默认开发与测试并行。"
                "先识别来源或测试点缺口，再尝试来源推导、语义参数化、常规观察方法和执行时绑定；"
                "只有这些方式都不能形成可执行准备或可判定业务结果时才列 pending CIQ。"
                "不得生成测试步骤或正式用例。\n\n"
                f"- 就绪输入 SHA-256：{BT}{readiness_hash}{BT}\n\n"
                "## 就绪性规则\n\n"
                + readiness_rules.rstrip()
                + "\n\n## 输出契约\n\n"
                + output_contract.rstrip()
                + "\n\n## 模块最终测试点\n\n"
                + final_text.rstrip()
                + "\n\n## 覆盖矩阵\n\n"
                + coverage_text.rstrip()
                + "\n\n## 模块测试点汇总来源输入\n\n"
                + source_input.rstrip()
                + "\n"
            )
            input_document_hash = sha256_text(input_text)
            sources = collect_module_stage_sources(model, state)
            session_input_text = build_case_readiness_session_input(
                readiness_hash,
                final_text,
                coverage_text,
                sources,
                model,
                readiness_rules,
                output_contract,
            )
            session_input_document_hash = sha256_text(session_input_text)
            previous = state.get("case_readiness", {})
            same_input = (
                previous.get("input_sha256") == readiness_hash
                and previous.get("input_document_sha256") == input_document_hash
                and readiness_input.is_file()
                and sha256_text(read_text(readiness_input)) == input_document_hash
                and readiness_session_input.is_file()
                and sha256_text(read_text(readiness_session_input)) == session_input_document_hash
            )
            if same_input and readiness_output.is_file():
                if (
                    previous.get("status") == "validated"
                    and previous.get("output_sha256") == sha256_file(readiness_output)
                ):
                    status = "validated"
                else:
                    previous["status"] = "prepared"
                    previous["result"] = None
                    previous["validated_at"] = None
                    previous["output_sha256"] = None
                    state["case_readiness"] = previous
                    state["updated_at"] = utc_now()
                    atomic_write_json(state_path(output_dir), state)
                    status = "prepared"
                print(f"CASE_READINESS_INPUT={readiness_input}")
                print(f"CASE_READINESS_OUTPUT={readiness_output}")
                print(f"STATUS={status}")
                return 0

            old_hash = previous.get("input_sha256")
            archive_existing(output_dir, readiness_input, old_hash)
            archive_existing(output_dir, readiness_session_input, old_hash)
            archive_existing(output_dir, readiness_output, old_hash)
            atomic_write_text(readiness_input, input_text)
            atomic_write_text(readiness_session_input, session_input_text)

            tp_rows = []
            for cells in final_doc.rows:
                tp_id = clean_cell(column_value(final_doc.headers, cells, "TP-ID"))
                if model.data_closure_enabled:
                    dc_refs = clean_cell(
                        column_value(final_doc.headers, cells, "Data Closure Refs")
                    )
                    tp_rows.append(
                        f"| {tp_id} | 待填写 | {dc_refs} | 待填写 | 待填写 |"
                    )
                else:
                    tp_rows.append(f"| {tp_id} | 待填写 | 待填写 | 待填写 |")
            readiness_template = load_template(
                "test-case-readiness-data-closure.md.tmpl"
                if model.data_closure_enabled
                else "test-case-readiness.md.tmpl",
                {
                    "READINESS_SHA256": readiness_hash,
                    "TP_READINESS_ROWS": "\n".join(tp_rows),
                },
            )
            atomic_write_text(readiness_output, readiness_template)
            state["case_readiness"] = {
                "status": "prepared",
                "result": None,
                "input_sha256": readiness_hash,
                "input_document_sha256": input_document_hash,
                "session_input_document_sha256": session_input_document_hash,
                "validated_at": None,
                "output_sha256": None,
            }
            state["updated_at"] = utc_now()
            atomic_write_json(state_path(output_dir), state)

        print(f"CASE_READINESS_SHA256={readiness_hash}")
        print(f"CASE_READINESS_INPUT={readiness_input}")
        print(f"CASE_READINESS_OUTPUT={readiness_output}")
        print("STATUS=prepared")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
