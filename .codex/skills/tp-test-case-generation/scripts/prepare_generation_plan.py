#!/usr/bin/env python3
"""Prepare one module-level batching and SQL-needs planning task."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from common import (
    CASE_READINESS_PATH,
    WorkflowError,
    assert_source_hashes,
    atomic_write_text,
    context_path,
    ensure_upstream_validation,
    load_final_test_points,
    load_json,
    module_paths,
    parse_case_readiness,
    read_context,
    read_text,
    run_preanalysis_validation,
    save_json,
    sha256_file,
    source_hashes,
    state_lock,
    state_path,
    utc_now,
)
from generation_plan import empty_plan, plan_source_hash, plan_path, planning_input_path


def arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare module testcase generation planning.")
    parser.add_argument("module_dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--preanalysis-dir", type=Path)
    parser.add_argument("--case-output-dir", type=Path)
    return parser.parse_args()


def _planning_input(model, points, points_path: Path, readiness_path: Path, context_text: str,
                    source_sha256: str) -> str:
    referenced = []
    wanted = {"SRC-MOD", "CTX"}
    for point in points:
        wanted.update(point.context_refs)
        wanted.update(point.data_closure_refs)
    for resource_id in sorted(wanted):
        resource = model.resources.get(resource_id)
        if resource is None or resource_id in {"SRC-GLOBAL"}:
            continue
        try:
            body = read_text(resource.path)
        except OSError as exc:
            raise WorkflowError(f"cannot read planning resource {resource_id}: {exc}") from exc
        referenced.append(
            f"### {resource_id}\n\n- 文件：`{resource.path.as_posix()}`\n\n{body.rstrip()}"
        )
    resources = "\n\n".join(referenced) or "无"
    return (
        "# 模块测试用例生成规划输入\n\n"
        f"- 模块：{model.module_name}\n"
        f"- 来源 SHA-256：`{source_sha256}`\n\n"
        "## 规划目标\n\n"
        "1. 逐 TP 判断复杂度与 SQL 必要性，二者必须独立判断。\n"
        "2. 简单和同页面查询展示 TP 每批 6～10 个为宜；复杂的并发、轮询、短路、重试或多状态组合 TP 单独成批。\n"
        "3. SQL 只用于页面查询结果、顶部/详情字段、列表列、聚合数量或需求明确要求的数据一致性核对。\n"
        "4. 下拉、默认值、输入限制、按钮状态、提示、校验顺序、接口调用、轮询、超时、重试、并发、锁、勾选行为和普通状态流转不得为了写 SQL 而写 SQL。\n"
        "5. 需求含原型图时，先识别图中实际页面功能区，SQL 按功能区组织，并记录每条 SQL 的 functional_module；查询字段/别名及结果顺序应便于与对应区域逐项对照。不得虚构图中没有的区域或据图新增业务口径。\n"
        "6. 无原型图时按需求明确的功能模块组织 SQL；需求和可读原型均无法确定归属时标记待澄清，不猜测。\n"
        "7. 入库或更新场景只在用例预期描述应新增或更新的记录，不规划 INSERT/UPDATE/DELETE。\n"
        "8. 优先按功能模块/页面数据视图设计少量可复用 SELECT；相同查询结构通过参数复用，不为每个 TP 或底层表机械拆分 SQL，也不创建万能 SQL。\n"
        "9. 每个 TP 必须且只能进入一个批次，顺序保持与最终测试点一致。\n\n"
        "## 最终测试点\n\n"
        f"{read_text(points_path).rstrip()}\n\n"
        "## 用例就绪性\n\n"
        f"{read_text(readiness_path).rstrip()}\n\n"
        "## 执行上下文\n\n"
        f"{context_text.rstrip()}\n\n"
        "## 模块需求与动态上下文\n\n"
        f"{resources}\n"
    )


def main() -> int:
    args = arguments()
    try:
        layout, model, points_dir, case_dir = module_paths(
            args.module_dir, args.preanalysis_dir, args.manifest, args.case_output_dir
        )
        run_preanalysis_validation(layout, case_dir)
        points, points_path, final_hash = load_final_test_points(points_dir, model)
        readiness_path = points_dir / CASE_READINESS_PATH
        readiness = parse_case_readiness(readiness_path, model)
        readiness_hash = sha256_file(readiness_path)
        ensure_upstream_validation(points_dir, final_hash, readiness_hash)
        context_text, context_hash, context_ready = read_context(context_path(case_dir))
        if readiness.result != "ready" or any(
            readiness.tp_status.get(point.tp_id) != "ready" for point in points
        ) or not context_ready:
            print("STATUS=blocked-input")
            return 2
        current_hashes = source_hashes(model, final_hash, readiness_hash, context_hash)
        source_sha256 = plan_source_hash(current_hashes)
        with state_lock(case_dir):
            state = load_json(state_path(case_dir))
            assert_source_hashes(state, current_hashes)
            planning = state.setdefault("planning", {"status": "pending"})
            input_path = planning_input_path(case_dir)
            output_path = plan_path(case_dir)
            if planning.get("status") == "validated":
                print("STATUS=validated")
            else:
                input_text = _planning_input(
                    model, points, points_path, readiness_path, context_text, source_sha256
                )
                if input_path.is_file() and input_path.read_text(encoding="utf-8") != input_text:
                    raise WorkflowError("planning-input.md conflicts with deterministic input")
                if not input_path.exists():
                    atomic_write_text(input_path, input_text)
                if not output_path.exists():
                    atomic_write_text(
                        output_path,
                        json.dumps(
                            empty_plan(model.module_name, source_sha256),
                            ensure_ascii=False,
                            indent=2,
                        ) + "\n",
                    )
                planning.update(
                    {
                        "status": "prepared",
                        "input_file": input_path.relative_to(case_dir).as_posix(),
                        "input_sha256": sha256_file(input_path),
                        "output_file": output_path.relative_to(case_dir).as_posix(),
                        "source_sha256": source_sha256,
                        "prepared_at": planning.get("prepared_at") or utc_now(),
                    }
                )
                state["updated_at"] = utc_now()
                save_json(state_path(case_dir), state)
                print("STATUS=prepared")
            print(f"PLANNING_INPUT={input_path}")
            print(f"GENERATION_PLAN={output_path}")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
