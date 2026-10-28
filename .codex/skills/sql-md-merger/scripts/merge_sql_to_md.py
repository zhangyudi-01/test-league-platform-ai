#!/usr/bin/env python3
"""Merge all SQL assets of a module into one Markdown document.

Input contract
--------------
The source is a module's `test-cases-history-20261015/sql/` directory produced by
tp-test-case-generation:

    sql-manifest.json        REQUIRED: asset registry (sql-assets-v1)
    SQL-<ID>.sql             SQL asset files, one statement per file
    validation.json          ignored by this conversion (validation evidence)

Output
------
A single Markdown document, by default `<sql-dir>/../模块测试用例SQL汇总.md`
(i.e. `test-cases-history-20261015/模块测试用例SQL汇总.md`):

    # <模块名> 测试用例 SQL 汇总

    > 说明行 …

    ## 索引

    | 序号 | SQL 标题 | SQL-ID | 来源文件 | 类型 | 用途 |

    ## <序号>. <中文标题>

    - 来源文件：`SQL-XXX.sql`
    - SQL-ID：`SQL-XXX`
    - 类型 / 数据闭包 / 参数 等元数据行（按 manifest 内容，有则写）

    ```sql
    <file content verbatim>
    ```

Rules
-----
- Only SELECT assets are included by default (查询 SQL); use --include-all to
  also emit INSERT/UPDATE/DELETE assets.
- The Chinese title is derived in this priority order:
  1. manifest `title_cn` field (optional, manual override),
  2. the SQL file's first `-- title:` comment line,
  3. the manifest `purpose` text (trimmed to the first sentence/clause),
  4. fallback: the SQL-ID itself.
- SQL file content is embedded verbatim; nothing is rewritten, reordered or
  reformatted.
- Output path defaults beside the sql dir; existing output is NEVER silently
  overwritten when --force is absent.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# sql-assets-v1 (or later) manifest schema prefix
SCHEMA_PREFIX = "tp-test-case-generation/sql-assets"

TITLE_KEY = "title_cn"
TITLE_COMMENT_RE = re.compile(r"^\s*--\s*title\s*[：:]\s*(.+?)\s*$", re.IGNORECASE)
# cut the derived title at the first hard sentence/clause boundary
TITLE_CUT_RE = re.compile(r"[。；;，,]")
MAX_TITLE_LEN = 60


def load_manifest(sql_dir: Path) -> dict:
    manifest_path = sql_dir / "sql-manifest.json"
    if not manifest_path.is_file():
        sys.exit(f"[ERROR] sql-manifest.json not found in {sql_dir}")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        sys.exit(f"[ERROR] cannot parse {manifest_path}: {exc}")
    if not str(manifest.get("schema_version", "")).startswith("tp-test-case-generation/sql-assets"):
        # tolerate exact-prefix mismatch but warn
        print(f"[WARN] unexpected schema_version: {manifest.get('schema_version')!r}")
    return manifest


def derive_title(asset: dict, sql_path: Path) -> str:
    """Chinese title priority: manifest title_cn > file '-- title:' > purpose > SQL-ID."""
    manual = str(asset.get(TITLE_KEY, "") or "").strip()
    if manual:
        return manual
    if sql_path.is_file():
        for line in sql_path.read_text(encoding="utf-8-sig").splitlines():
            match = TITLE_COMMENT_RE.match(line)
            if match:
                return match.group(1).strip()
    purpose = str(asset.get("purpose", "") or "").strip()
    if purpose:
        cut = TITLE_CUT_RE.split(purpose, maxsplit=1)[0].strip()
        title = cut if cut else purpose
        return title[:MAX_TITLE_LEN]
    return str(asset.get("sql_id", sql_path.stem))


def format_params(params: dict) -> str | None:
    if not params:
        return None
    parts = []
    for name, meta in params.items():
        if isinstance(meta, dict):
            desc = str(meta.get("description", "")).strip()
            example = str(meta.get("example", "")).strip()
            segment = f"`:{name}`"
            if desc:
                segment += f"（{desc}"
                if example:
                    segment += f"，示例 {example}"
                segment += "）"
        else:
            segment = f"`:{name}`"
        parts.append(segment)
    return "；".join(parts)


def build_document(module_name: str, entries: list[dict], note: str) -> str:
    lines: list[str] = []
    lines.append(f"# {module_name} 测试用例 SQL 汇总")
    lines.append("")
    if note:
        lines.append(f"> {note}")
        lines.append("")
    lines.append("## 索引")
    lines.append("")
    lines.append("| 序号 | SQL 标题 | SQL-ID | 来源文件 | 类型 | 用途 |")
    lines.append("| --- | --- | --- | --- | --- | --- |")
    for idx, entry in enumerate(entries, start=1):
        purpose = entry["purpose"].replace("|", "\\|")
        lines.append(
            f"| {idx} | {entry['title']} | `{entry['sql_id']}` | "
            f"`{entry['file']}` | {entry['stmt_type']} | {purpose} |"
        )
    lines.append("")
    for idx, entry in enumerate(entries, start=1):
        lines.append(f"## {idx}. {entry['title']}")
        lines.append("")
        lines.append(f"- 来源文件：`{entry['file']}`")
        lines.append(f"- SQL-ID：`{entry['sql_id']}`")
        if entry["stmt_type"]:
            lines.append(f"- 语句类型：{entry['stmt_type']}")
        if entry["dc_refs"]:
            lines.append(f"- 数据闭包：{'、'.join(entry['dc_refs'])}")
        params_text = format_params(entry["params"])
        if params_text:
            lines.append(f"- 参数：{params_text}")
        if entry["purpose"]:
            lines.append(f"- 用途：{entry['purpose']}")
        lines.append("")
        lines.append("```sql")
        lines.append(entry["sql_text"].rstrip("\n"))
        lines.append("```")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Merge module SQL assets into one Markdown document."
    )
    parser.add_argument("sql_dir", help="module test-cases-history-20261015/sql directory containing sql-manifest.json")
    parser.add_argument(
        "-o", "--output",
        help="output .md path (default: <sql_dir>/../模块测试用例SQL汇总.md)",
    )
    parser.add_argument("--module-name", help="module display name used in the title (default: inferred from path)")
    parser.add_argument(
        "--include-all",
        action="store_true",
        help="include INSERT/UPDATE/DELETE assets too (default: SELECT only)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="overwrite an existing output file (default: refuse and exit)",
    )
    args = parser.parse_args()

    sql_dir = Path(args.sql_dir).resolve()
    if not sql_dir.is_dir():
        sys.exit(f"[ERROR] sql dir not found: {sql_dir}")

    manifest = load_manifest(sql_dir)
    assets = manifest.get("assets") or []
    if not assets:
        sys.exit(f"[ERROR] sql-manifest.json contains no assets")

    module_name = args.module_name or infer_module_name(sql_dir)

    entries = []
    skipped = []
    for asset in assets:
        stmt_type = str(asset.get("statement_type", "")).upper()
        if stmt_type and stmt_type != "SELECT" and not args.include_all:
            skipped.append(asset.get("sql_id", "?"))
            continue
        file_name = str(asset.get("file", "")).strip()
        sql_path = sql_dir / file_name
        if not file_name or not sql_path.is_file():
            sys.exit(f"[ERROR] SQL file listed in manifest not found: {file_name}")
        sql_text = sql_path.read_text(encoding="utf-8-sig")
        entries.append(
            {
                "sql_id": str(asset.get("sql_id", sql_path.stem)),
                "file": file_name,
                "title": derive_title(asset, sql_path),
                "purpose": str(asset.get("purpose", "") or "").strip(),
                "stmt_type": stmt_type,
                "dc_refs": [str(x) for x in (asset.get("data_closure_refs") or [])],
                "params": asset.get("parameters") or {},
                "sql_text": sql_text,
            }
        )

    if not entries:
        sys.exit("[ERROR] no SELECT assets found (use --include-all to include write statements)")

    output = Path(args.output).resolve() if args.output else sql_dir.parent / "模块测试用例SQL汇总.md"
    if output.exists() and not args.force:
        sys.exit(f"[ERROR] output already exists, refusing to overwrite (use --force or another -o): {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    note = (
        f"共收录 {len(entries)} 条查询 SQL，来源于 `{sql_dir.name}/sql-manifest.json`；"
        "SQL 正文逐字取自对应 .sql 文件，未做任何改写。"
    )
    if skipped:
        note += f"已跳过非 SELECT 资产：{'、'.join(skipped)}。"

    document = build_document(module_name, entries, note)
    output.write_text(document, encoding="utf-8", newline="\n")

    print(f"Created {output}")
    print(f"Module: {module_name} | SQL entries: {len(entries)} | skipped: {len(skipped)}")
    for idx, entry in enumerate(entries, start=1):
        print(f"  {idx}. {entry['title']}  <- {entry['file']}")
    return 0


def infer_module_name(sql_dir: Path) -> str:
    """<module-root>/test-cases-history-20261015/sql -> take the module dir name, strip the ID prefix."""
    module_dir = sql_dir.parent.parent
    raw = module_dir.name
    match = re.match(r"^MOD-\d+(?:-\d+)*[-_]\s*(.+)$", raw)
    return match.group(1).strip() if match else raw


if __name__ == "__main__":
    raise SystemExit(main())
