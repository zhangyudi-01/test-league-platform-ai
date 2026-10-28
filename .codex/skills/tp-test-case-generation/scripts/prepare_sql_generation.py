#!/usr/bin/env python3
"""Prepare the module-level SQL asset generation stage after plan validation."""
from __future__ import annotations

import argparse
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
from generation_plan import load_plan, sql_input_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Prepare planned module SQL generation.")
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
        if not context_ready:
            raise WorkflowError("execution-context.md contains pending entries")
        current_hashes = source_hashes(model, final_hash, readiness_hash, context_hash)
        with state_lock(case_dir):
            state = load_json(state_path(case_dir))
            assert_source_hashes(state, current_hashes)
            if state.get("planning", {}).get("status") != "validated":
                raise WorkflowError("generation plan must validate before SQL generation")
            if state.get("planning", {}).get("output_sha256") != sha256_file(
                case_dir / "generation-plan.json"
            ):
                raise WorkflowError("generation-plan.json changed after validation")
            plan = load_plan(case_dir)
            sql_assets = plan.get("sql_assets", [])
            if not sql_assets:
                state["sql_planning"] = {
                    "status": "validated",
                    "sql_count": 0,
                    "validated_at": utc_now(),
                }
                state["updated_at"] = utc_now()
                save_json(state_path(case_dir), state)
                print("STATUS=validated")
                print("SQL_COUNT=0")
                return 0
            resource_ids = {"SRC-MOD"}
            for asset in sql_assets:
                resource_ids.update(asset.get("data_closure_refs", []))
                for tp_id in asset.get("tp_refs", []):
                    point = point_by_id.get(tp_id)
                    if point is None:
                        raise WorkflowError(f"planned SQL references unknown TP {tp_id}")
                    resource_ids.update(point.context_refs)
                    resource_ids.update(point.data_closure_refs)
            resource_ids.discard("SRC-GLOBAL")
            sections = []
            for resource_id in sorted(resource_ids):
                resource = model.resources.get(resource_id)
                if resource is None:
                    raise WorkflowError(f"planned SQL references undefined resource {resource_id}")
                sections.append(
                    f"### {resource_id}\n\n- 文件：`{resource.path.as_posix()}`\n\n"
                    f"{read_text(resource.path).rstrip()}"
                )
            input_text = (
                "# 模块查询 SQL 统一生成输入\n\n"
                "## 边界\n\n"
                "- 只生成 generation-plan.json 中列出的 SELECT SQL，不增删 SQL-ID。\n"
                "- SQL 只用于计划声明的页面查询、展示字段、列表、聚合或明确数据库一致性核对。\n"
                "- 按 generation-plan.json 的 functional_module 分组编写；有原型图时对应原型中的实际页面功能区，无原型时对应需求功能模块。\n"
                "- 查询字段、别名及结果顺序应便于与对应功能区逐项对照；不虚构页面区域或业务口径。\n"
                "- 相同功能区/页面数据视图优先参数化复用；不得为每个 TP 或底层表机械拆分 SQL，也不得创建万能 SQL。\n"
                "- 不生成 INSERT、UPDATE 或 DELETE；入库和更新预期由测试用例文字描述。\n"
                "- 每个命名参数必须在 SQL 注释中说明，并在 sql-manifest.json 提供 EXPLAIN 示例值。\n"
                "- 完成后运行 validate_planned_sql.py。\n\n"
                "## 已验证 SQL 计划\n\n"
                f"{read_text(case_dir / 'generation-plan.json').rstrip()}\n\n"
                "## 数据闭包与表结构事实\n\n"
                f"{'\n\n'.join(sections) or '无'}\n\n"
                "## 执行上下文\n\n"
                f"{context_text.rstrip()}\n"
            )
            input_path = sql_input_path(case_dir)
            if input_path.is_file() and input_path.read_text(encoding="utf-8") != input_text:
                raise WorkflowError("sql-generation-input.md conflicts with deterministic input")
            if not input_path.exists():
                atomic_write_text(input_path, input_text)
            sql_state = state.setdefault("sql_planning", {"status": "pending"})
            sql_state.update(
                {
                    "status": "prepared",
                    "input_file": input_path.relative_to(case_dir).as_posix(),
                    "input_sha256": sha256_file(input_path),
                    "sql_count": len(sql_assets),
                    "prepared_at": sql_state.get("prepared_at") or utc_now(),
                }
            )
            state["updated_at"] = utc_now()
            save_json(state_path(case_dir), state)
        print("STATUS=prepared")
        print(f"SQL_INPUT={input_path}")
        print(f"SQL_COUNT={len(sql_assets)}")
        return 0
    except WorkflowError as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
