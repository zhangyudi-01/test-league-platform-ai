#!/usr/bin/env python3
"""Detect reusable and duplicated SQL assets without mutating test artifacts.

The report is intentionally advisory.  Exact duplicate SQL is a strong reuse
signal, while a shared SELECT/FROM/ORDER/LIMIT skeleton with different WHERE
clauses is only a candidate: business semantics, index behavior and the
test-point boundary still require a tester's decision.
"""
from __future__ import annotations

import argparse
import os
import re
from collections import defaultdict
from pathlib import Path
from typing import Any

from sql_assets import SqlAsset, SqlAssetError, _scan_sql, load_registry


REPORT_NAME = "sql-convergence-report.md"


def _canonical_sql(sql: str) -> str:
    """Normalize comments, SQL keyword case and whitespace conservatively.

    Case inside quoted strings and identifiers is preserved.  Lower-casing the
    whole statement would incorrectly treat values such as ``'A'`` and
    ``'a'`` as the same query on a case-sensitive collation.
    """
    code, _, _ = _scan_sql(sql)
    normalized: list[str] = []
    quote = ""
    escaped = False
    for char in code:
        if quote:
            normalized.append(char)
            if escaped:
                escaped = False
                continue
            if char == "\\":
                escaped = True
                continue
            if char == quote:
                quote = ""
            continue
        if char in {"'", '"', "`"}:
            quote = char
            normalized.append(char)
        else:
            normalized.append(char.lower())
    code = "".join(normalized).strip().rstrip(";").strip()
    return re.sub(r"\s+", " ", code)


def _where_free_skeleton(sql: str) -> str:
    """Return a conservative query skeleton with WHERE predicates removed.

    This is deliberately not a SQL parser.  It is only used to group review
    candidates, never to rewrite SQL or decide that two assets are equivalent.
    """
    normalized = _canonical_sql(sql)
    match = re.search(r"\bwhere\b", normalized)
    if match is None:
        return normalized
    prefix = normalized[: match.start()].rstrip()
    suffix_match = re.search(r"\b(order by|group by|having|limit|union)\b", normalized[match.end() :])
    if suffix_match is None:
        suffix = ""
    else:
        suffix = normalized[match.end() + suffix_match.start() :].strip()
    return re.sub(r"\s+", " ", f"{prefix} {suffix}").strip()


def _references(case_dir: Path, sql_id: str) -> list[str]:
    references: list[str] = []
    # Generated INPUT/session/log/history files repeat the same SQL index many
    # times and make the report unreadable.  References should describe the
    # authored TP/module assets that a tester may actually need to update.
    derived_dirs = {"inputs", "session-inputs", "runner-logs", "history"}
    for path in sorted(case_dir.rglob("*.md")):
        if path.name == REPORT_NAME:
            continue
        relative = path.relative_to(case_dir)
        if any(part in derived_dirs for part in relative.parts):
            continue
        try:
            text = path.read_text(encoding="utf-8-sig")
        except (OSError, UnicodeError):
            continue
        if sql_id in text:
            references.append(relative.as_posix())
    return references


def analyze_convergence(case_dir: Path) -> dict[str, Any]:
    """Return deterministic exact and structural SQL convergence findings."""
    registry = load_registry(case_dir)
    exact: dict[str, list[SqlAsset]] = defaultdict(list)
    skeletons: dict[str, list[SqlAsset]] = defaultdict(list)
    for asset in registry.values():
        exact[_canonical_sql(asset.sql)].append(asset)
        skeletons[_where_free_skeleton(asset.sql)].append(asset)

    exact_groups = [
        {
            "kind": "exact-duplicate",
            "sql_ids": [asset.sql_id for asset in sorted(group, key=lambda item: item.sql_id)],
            "parameters": [sorted(item.name for item in asset.parameters) for asset in group],
            "data_closure_refs": [list(asset.data_closure_refs) for asset in group],
            "references": {asset.sql_id: _references(case_dir, asset.sql_id) for asset in group},
        }
        for group in sorted(exact.values(), key=lambda items: min(item.sql_id for item in items))
        if len(group) > 1
    ]
    structural_groups = [
        {
            "kind": "where-variant-candidate",
            "sql_ids": [asset.sql_id for asset in sorted(group, key=lambda item: item.sql_id)],
            "parameters": {asset.sql_id: sorted(item.name for item in asset.parameters) for asset in group},
            "data_closure_refs": {asset.sql_id: list(asset.data_closure_refs) for asset in group},
            "references": {asset.sql_id: _references(case_dir, asset.sql_id) for asset in group},
        }
        for group in sorted(skeletons.values(), key=lambda items: min(item.sql_id for item in items))
        if len(group) > 1 and len({_canonical_sql(asset.sql) for asset in group}) > 1
    ]
    return {
        "schema_version": "tp-test-case-generation/sql-convergence-v1",
        "case_dir": str(case_dir.resolve()),
        "asset_count": len(registry),
        "exact_duplicate_groups": exact_groups,
        "where_variant_groups": structural_groups,
    }


def _group_lines(group: dict[str, Any], *, exact: bool) -> list[str]:
    lines = [f"### {'必须复用/合并' if exact else '建议人工评估参数化'}：" + "、".join(group["sql_ids"]), ""]
    if exact:
        lines.append("这些 SQL 在去除注释、SQL 关键字大小写和排版差异后执行体相同；应保留一个规范 SQL-ID，其他用例改为引用该 SQL-ID。")
    else:
        lines.append("这些 SQL 共享 SELECT/FROM/排序/分页骨架，但 WHERE 或其他业务表达式存在差异；不得仅凭结构相似自动合并。")
    lines.append("")
    lines.append("| SQL-ID | 参数 | Data Closure Refs | 引用文件 |")
    lines.append("|---|---|---|---|")
    for sql_id in group["sql_ids"]:
        params = (
            group["parameters"][group["sql_ids"].index(sql_id)]
            if exact
            else group["parameters"][sql_id]
        )
        closures = group["data_closure_refs"][group["sql_ids"].index(sql_id)] if exact else group["data_closure_refs"][sql_id]
        refs = group["references"].get(sql_id) or ["无"]
        lines.append(f"| `{sql_id}` | {', '.join(params) or '无'} | {', '.join(closures)} | {', '.join(f'`{item}`' for item in refs)} |")
    lines.append("")
    return lines


def render_report(case_dir: Path, analysis: dict[str, Any]) -> str:
    exact = analysis["exact_duplicate_groups"]
    variants = analysis["where_variant_groups"]
    lines = [
        "# SQL 资产收敛报告",
        "",
        f"- SQL 资产数：`{analysis['asset_count']}`",
        "- 本报告只做确定性比对和候选分组，不自动修改 SQL、manifest 或用例引用。",
        "- `CASE`、别名、展示转换、字符串/标识符大小写和排版差异不会被当作 Skill 缺陷；涉及展示转换时仍由测试人员按业务口径决定是否复用。",
        "",
        "## 收敛规则",
        "",
        "- 完全重复：去除注释、SQL 关键字大小写和空白后执行体相同，标记为必须复用/合并。",
        "- WHERE 变体候选：共享查询骨架但过滤条件或其他表达式不同，只提示评估，不自动合并。",
        "- 业务语义、字段、关联、排序或分页不一致时，保留独立 SQL。",
        "",
        "## 完全重复资产",
        "",
    ]
    if exact:
        for group in exact:
            lines.extend(_group_lines(group, exact=True))
    else:
        lines.append("未发现。")
        lines.append("")
    lines.extend(["## WHERE 变体候选", ""])
    if variants:
        for group in variants:
            lines.extend(_group_lines(group, exact=False))
    else:
        lines.append("未发现。")
        lines.append("")
    lines.extend(
        [
            "## 执行建议",
            "",
            "1. 先为完全重复组选择一个保留的规范 SQL-ID。",
            "2. 在用例生成前，将 generation plan、`sql-manifest.json` 和已有引用统一到规范 SQL-ID。",
            "3. 删除冗余文件后重新运行 `validate_planned_sql.py`；SQL 阶段通过后，批次和最终阶段只复核资产指纹。",
            "4. WHERE 变体仅在参数化后仍保持业务语义、索引和人工执行可读性时合并。",
            "",
        ]
    )
    return "\n".join(lines)


def write_convergence_report(case_dir: Path) -> Path:
    analysis = analyze_convergence(case_dir)
    target = case_dir / "sql" / REPORT_NAME
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(f".{target.name}.{os.getpid()}.tmp")
    temporary.write_text(render_report(case_dir, analysis), encoding="utf-8", newline="\n")
    temporary.replace(target)
    return target


def main() -> int:
    parser = argparse.ArgumentParser(description="Report reusable and duplicate SQL assets.")
    parser.add_argument("case_dir", type=Path, help="module test-cases directory")
    args = parser.parse_args()
    try:
        report = write_convergence_report(args.case_dir.resolve())
    except (OSError, SqlAssetError) as exc:
        print(f"ERROR: {exc}")
        return 1
    print(f"REPORT={report}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
