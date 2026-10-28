#!/usr/bin/env python3
"""Prepare one source-bound module complexity and batch planning input."""

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
    default_output_dir,
    display_path,
    ensure_output_scaffold,
    escape_markdown_table_cell,
    load_state,
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
from generation_plan import (
    context_signature,
    empty_plan,
    plan_path,
    plan_source_hash,
    planning_input_path,
)

PLANNING_RULES = SKILL_DIR / "references" / "planning-rules.md"
FOUNDATION_INPUT_FILE = "foundation-input.md"


def _archive(output_dir: Path, path: Path, source_sha256: str | None) -> None:
    if not path.is_file():
        return
    history = output_dir / "history" / "planning"
    history.mkdir(parents=True, exist_ok=True)
    suffix = (source_sha256 or sha256_file(path))[:12]
    target = history / f"{path.stem}-{suffix}{path.suffix}"
    counter = 1
    while target.exists():
        target = history / f"{path.stem}-{suffix}-{counter}{path.suffix}"
        counter += 1
    os.replace(path, target)


def planning_document(model, bundles, source_sha256: str) -> str:
    lines = [
        "# RSU 模块生成规划输入",
        "",
        "## 任务",
        "",
        "只判断本次测试点生成的运行复杂度并分批；不得生成测试点，不得修改前置分析。",
        f"- 模块：{model.module_name}",
        f"- 规划来源 SHA-256：{BT}{source_sha256}{BT}",
        "",
        "## 规划规则",
        "",
        read_text(PLANNING_RULES).rstrip(),
        "",
        "## RSU 规划矩阵",
        "",
        "| RSU-ID | 父级条件原文 | 原文内容 | 来源 | 动态依赖 | Context Signature |",
        "|---|---|---|---|---|---|",
    ]
    for rsu in model.rsus:
        bundle = bundles[rsu.rsu_id]
        dependencies = [item.resource_id for item in bundle.dynamic_materials]
        dependencies.extend(question.q_id for question in bundle.questions)
        dependencies.extend(item.rsu_id for item in bundle.supporting_rsus)
        lines.append(
            "| "
            + " | ".join(
                (
                    rsu.rsu_id,
                    escape_markdown_table_cell(rsu.parent_text),
                    escape_markdown_table_cell(rsu.source_text),
                    escape_markdown_table_cell(f"{rsu.source_id} {rsu.source_location}"),
                    escape_markdown_table_cell(", ".join(dependencies) or "无"),
                    context_signature(bundle),
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## 输出",
            "",
            f"填写 {BT}generation-plan.json{BT}：",
            "",
            "- 将 status 改为 validated。",
            "- 为每个 RSU 填写 simple 或 complex、连续 batch_id 和具体分类理由。",
            "- 不得修改 rsu_id、context_signature、module_name、source_sha256 或 planning_input_sha256。",
        ]
    )
    return "\n".join(lines) + "\n"


def foundation_document(model, bundles) -> str:
    fixed_materials = next(iter(bundles.values())).fixed_materials if bundles else []
    sections = [
        "# RSU 测试点生成模块基础上下文",
        "",
        f"- 模块：{model.module_name}",
        "- 本文件只包含所有阶段共享且来源指纹稳定的事实与契约。",
        "- 阶段 fork 必须补读自己的 planning、batch、finalization 或 readiness 输入；不得只凭会话记忆写产物。",
        "",
        "## 固定需求来源",
        "",
    ]
    for material in fixed_materials:
        sections.extend(
            [
                f"### {material.resource_id}",
                "",
                f"- 文件：`{display_path(material.path, model.module_dir)}`",
                f"- SHA-256：`{sha256_text(material.content)}`",
                "",
                material.content.rstrip(),
                "",
            ]
        )
    contract_files = [
        PLANNING_RULES,
        SKILL_DIR / "references" / "generation-rules.md",
        SKILL_DIR / "references" / "output-contract.md",
        SKILL_DIR / "references" / "finalization-rules.md",
        SKILL_DIR / "references" / "case-readiness-rules.md",
    ]
    if model.data_closure_enabled:
        contract_files.extend(
            [
                SKILL_DIR / "references" / "data-closure-generation-rules.md",
                SKILL_DIR / "references" / "data-closure-output-contract.md",
                SKILL_DIR / "references" / "data-closure-finalization-rules.md",
                SKILL_DIR / "references" / "data-closure-readiness-rules.md",
            ]
        )
    sections.extend(["## 生成契约", ""])
    for path in contract_files:
        sections.extend([f"### {path.name}", "", read_text(path).rstrip(), ""])
    return "\n".join(sections).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare module RSU generation planning input.")
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
            blocked = [item for item in state["rsus"] if item["generation_status"] == "blocked"]
            if blocked:
                details = "; ".join(
                    f"{item['rsu_id']}: {', '.join(item.get('blockers', []))}" for item in blocked
                )
                raise WorkflowError(f"cannot plan while RSU inputs are blocked: {details}")
            source_sha256 = plan_source_hash(model, bundles)
            source_fingerprint = state.get("session_source_fingerprint_sha256")
            foundation_file = output_dir / FOUNDATION_INPUT_FILE
            foundation_text = foundation_document(model, bundles)
            foundation = state.get("foundation", {})
            foundation_same = (
                foundation.get("source_fingerprint_sha256") == source_fingerprint
                and foundation_file.is_file()
                and sha256_text(read_text(foundation_file)) == sha256_text(foundation_text)
            )
            if not foundation_same:
                atomic_write_text(foundation_file, foundation_text)
                state["foundation"] = {
                    "status": "pending",
                    "thread_id": None,
                    "source_fingerprint_sha256": source_fingerprint,
                    "input_file": display_path(foundation_file, output_dir),
                    "input_sha256": sha256_file(foundation_file),
                    "created_at": None,
                }
            input_file = planning_input_path(output_dir)
            output_file = plan_path(output_dir)
            input_text = planning_document(model, bundles, source_sha256)
            planning_input_sha256 = sha256_text(input_text)
            planning = state.get("planning", {})
            same_source = planning.get("source_sha256") == source_sha256
            same_input = input_file.is_file() and sha256_text(read_text(input_file)) == sha256_text(input_text)
            if planning.get("status") == "validated" and same_source and same_input and output_file.is_file():
                atomic_write_json(state_path(output_dir), state)
                print("STATUS=validated")
            else:
                if not same_source:
                    _archive(output_dir, input_file, planning.get("source_sha256"))
                    _archive(output_dir, output_file, planning.get("source_sha256"))
                if not input_file.exists():
                    atomic_write_text(input_file, input_text)
                elif not same_input:
                    raise WorkflowError("planning-input.md conflicts with deterministic current sources")
                if not output_file.exists():
                    atomic_write_text(
                        output_file,
                        json.dumps(
                            empty_plan(model, bundles, planning_input_sha256),
                            ensure_ascii=False,
                            indent=2,
                        ) + "\n",
                    )
                state["planning"] = {
                    "status": "prepared",
                    "source_sha256": source_sha256,
                    "input_file": display_path(input_file, output_dir),
                    "input_sha256": sha256_file(input_file),
                    "output_file": display_path(output_file, output_dir),
                    "output_sha256": None,
                    "semantic_sha256": None,
                    "prepared_at": planning.get("prepared_at") if same_source else utc_now(),
                    "validated_at": None,
                }
                state["batches"] = []
                for record in state["rsus"]:
                    record["batch_id"] = None
                    record["context_signature"] = context_signature(bundles[record["rsu_id"]])
                state["updated_at"] = utc_now()
                atomic_write_json(state_path(output_dir), state)
                print("STATUS=prepared")
        print(f"PLANNING_INPUT={input_file}")
        print(f"FOUNDATION_INPUT={foundation_file}")
        print(f"GENERATION_PLAN={output_file}")
        print(f"SOURCE_SHA256={source_sha256}")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
