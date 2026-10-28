#!/usr/bin/env python3
"""Convert module-test-cases-history-20261015.md (module test case Markdown) into the team's standard Excel workbook.

Input contract
--------------
The source Markdown is produced by the module test-case convergence step and has this shape:

    # <module title> - 模块测试用例

    ## 生成元数据            (2-column key/value table, optional)
    ## 模块用例追溯索引       (traceability index table, optional)
    ## 标准测试用例           (REQUIRED: the 12-column standard testcase table)
    ## 模块数据闭包执行计划    (optional execution-plan table)
    ## 覆盖矩阵 / SQL资产 ...  (any other auxiliary tables)

Each `##` section becomes one worksheet named after the section title.
The workbook format follows tests/sample-testcases.xlsx:
  - a 首页 (home) sheet listing every sheet with its row count,
  - per testcase sheet: row1 `时间：xxxx-xx-xx  姓名：xxx`, row2 `执行开始时间`,
    row3 header, data from row4; frozen header, borders, wrap text, auto filter.

Cell cleaning rules (the reason this skill exists)
--------------------------------------------------
1. `<br>`, `<br/>`, `<br />` become real newlines.
2. Inline numbering like `1.xxx2.xxx3.xxx` (written on one line without separators)
   is split into one numbered item per line: `1.xxx\n2.xxx\n3.xxx`.
   Decimal numbers are protected: `1.5`, `0.5`, `$P=1.5`, `迭代2.3` are NOT split points.
3. Markdown backticks and other inline HTML tags are stripped.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Iterable

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

TESTCASE_SHEET_TITLE = "标准测试用例"

# columns that identify "the standard testcase table"
TESTCASE_KEY_COLUMNS = {"测试项", "测试点", "执行步骤", "预期结果"}

# columns that must be cleaned into numbered multi-line text
NUMBERED_COLUMNS = {"前置条件", "执行步骤", "预期结果"}

DEFAULT_SHEET_TITLES = {
    "生成元数据",
    "模块用例追溯索引",
    TESTCASE_SHEET_TITLE,
    "模块数据闭包执行计划",
    "覆盖矩阵",
    "SQL资产",
}

INVALID_SHEET_CHARS = re.compile(r"[\\/*?:\[\]]")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
HTML_TAG_RE = re.compile(r"</?[a-zA-Z][^>]*>")
BACKTICK_RE = re.compile(r"`+")

# a split point: `2.` that starts a new numbered item
# - not preceded by a digit (rules out the `2` in `12.`? no - `12.` IS a valid item number,
#   so instead we require the char before the number to not be a digit-dot pattern),
# - not followed by a digit+dot (rules out `1.5` decimals: `1.5` has digit after the dot,
#   an item would have non-digit content after the dot)
ITEM_START_RE = re.compile(r"(?:(?<=^)|(?<=[\s。；;：:，,）)>★①-]))(\d{1,2})\.(?!\d)")


# ---------------------------------------------------------------------------
# markdown table parsing
# ---------------------------------------------------------------------------

def split_md_row(line: str) -> list[str]:
    """Split a Markdown table row while respecting escaped pipes."""
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]

    cells: list[str] = []
    buf: list[str] = []
    escaped = False
    for ch in text:
        if escaped:
            buf.append(ch)
            escaped = False
        elif ch == "\\":
            escaped = True
        elif ch == "|":
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    if escaped:
        buf.append("\\")
    cells.append("".join(buf).strip())
    return cells


def is_separator_row(line: str) -> bool:
    cells = split_md_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c.strip()) for c in cells)


def safe_sheet_name(name: str, used: set[str]) -> str:
    cleaned = INVALID_SHEET_CHARS.sub("-", name).strip().strip("'") or "Sheet"
    base = cleaned[:31]
    candidate = base
    index = 2
    while candidate in used:
        suffix = f"-{index}"
        candidate = f"{base[:31 - len(suffix)]}{suffix}"
        index += 1
    used.add(candidate)
    return candidate


# ---------------------------------------------------------------------------
# cell cleaning
# ---------------------------------------------------------------------------

def split_inline_numbering(value: str) -> str:
    """Split `1.aaa2.bbb` style inline numbering into one item per line.

    Decimal protection: a `<digits>.` followed immediately by another digit is a
    decimal number (`1.5`), never an item start. Numbers > 2 digits are treated
    as content, not item numbers (test steps rarely exceed 99 steps).
    A valid item start must be at the beginning of the text or follow a natural
    boundary character (。；;：:，,空白 etc.), which keeps `迭代2.3`, `版本1.2`
    intact because `2.` there follows a Chinese character.
    """
    if not value or "\n" in value:
        # already multi-line: caller split the <br> first, leave as is
        return value

    matches = list(ITEM_START_RE.finditer(value))
    if not matches:
        return value

    # only treat as inline numbering when at least two item starts exist
    # (a lone `1.` mid-sentence is more likely prose than a list)
    if len(matches) < 2:
        return value

    parts: list[str] = []
    last = 0
    for m in matches:
        num = m.group(1)
        # keep original char positions: match includes the number and the dot
        start = m.start(1)
        parts.append(value[last:start])
        last = start
    parts.append(value[last:])

    # first chunk is the preamble before item 1; drop it if empty
    chunks = [p for p in parts if p.strip() or p is parts[0]]
    result = []
    preamble = chunks[0]
    if preamble.strip():
        result.append(preamble.strip())
    for chunk in chunks[1:]:
        result.append(chunk.strip())
    return "\n".join(result)


def clean_cell(value: str, numbered: bool = False) -> str:
    """Clean one Markdown cell into Excel text."""
    value = value.replace("&nbsp;", " ")
    value = BR_RE.sub("\n", value)
    value = HTML_TAG_RE.sub("", value)
    value = BACKTICK_RE.sub("", value)
    # collapse 3+ consecutive blank lines introduced by <br> padding
    value = re.sub(r"\n{3,}", "\n\n", value)
    value = value.strip()

    if numbered:
        value = split_inline_numbering(value)

    # normalise full-width spaces used as padding
    value = value.replace("　", " ")
    return value.strip()


# ---------------------------------------------------------------------------
# parsing
# ---------------------------------------------------------------------------

def parse_markdown(path: Path) -> list[tuple[str, list[str], list[list[str]]]]:
    """Return [(section_title, headers, rows), ...] for every table found.

    A table belongs to the most recent `##` heading (falls back to `#`).
    """
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    sections: list[tuple[str, list[str], list[list[str]]]] = []
    current_title = path.stem

    i = 0
    while i < len(lines):
        line = lines[i]
        heading = HEADING_RE.match(line)
        if heading:
            level = len(heading.group(1))
            if level <= 2:
                current_title = heading.group(2).strip()
            i += 1
            continue

        if line.strip().startswith("|") and i + 1 < len(lines) and is_separator_row(lines[i + 1]):
            headers = [clean_cell(h, numbered=False) for h in split_md_row(line)]
            headers = [h for h in headers if h != ""]
            if len(headers) < 2:
                i += 1
                continue

            rows: list[list[str]] = []
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                raw = split_md_row(lines[i])
                if any(cell.strip() for cell in raw):
                    rows.append(raw)
                i += 1

            if rows:
                sections.append((current_title, headers, rows))
            continue

        i += 1

    return sections


def build_row(raw: list[str], headers: list[str]) -> list[str]:
    """Map a raw markdown row onto the header columns and clean each cell."""
    numbered_set = {h for h in headers if h in NUMBERED_COLUMNS}
    result: list[str] = []
    for idx, header in enumerate(headers):
        value = raw[idx] if idx < len(raw) else ""
        result.append(clean_cell(value, numbered=header in numbered_set))
    return result


# ---------------------------------------------------------------------------
# workbook writing (sample-testcases.xlsx format)
# ---------------------------------------------------------------------------

TESTCASE_COLUMN_WIDTHS = {
    "序号": 10,
    "冲刺": 12,
    "测试项": 18,
    "测试点": 32,
    "数据变量": 28,
    "前置条件": 42,
    "执行步骤": 42,
    "备注": 28,
    "预期结果": 42,
    "测试结果1": 10,
    "测试结果2": 10,
    "测试结果3": 10,
}


def style_sheet(ws, header_row: int = 3) -> None:
    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    header_fill = PatternFill("solid", fgColor="D9EAF7")
    header_font = Font(bold=True)

    for row in ws.iter_rows():
        for cell in row:
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    header_cells = ws[header_row]
    for cell in header_cells:
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    ws.freeze_panes = f"A{header_row + 1}"
    ws.auto_filter.ref = f"A{header_row}:{get_column_letter(ws.max_column)}{ws.max_row}"
    ws.row_dimensions[1].height = 24
    ws.row_dimensions[2].height = 24
    ws.row_dimensions[header_row].height = 30


def set_column_widths(ws, headers: list[str]) -> None:
    default_width = 24
    for idx, header in enumerate(headers, start=1):
        width = TESTCASE_COLUMN_WIDTHS.get(header, default_width)
        ws.column_dimensions[get_column_letter(idx)].width = width


def add_home_sheet(wb: Workbook, title: str, sheet_infos: list[tuple[str, int]]) -> None:
    ws = wb.active
    ws.title = "首页"
    ws.merge_cells("A1:F1")
    ws["A1"] = "测试用例"
    ws["A1"].font = Font(size=18, bold=True)
    ws.merge_cells("A2:F2")
    ws["A2"] = f"——{title}"
    ws["A2"].font = Font(size=14, bold=True)
    ws["A4"] = "Sheet"
    ws["B4"] = "用例数/行数"
    row = 5
    for name, count in sheet_infos:
        ws.cell(row=row, column=1, value=name)
        ws.cell(row=row, column=2, value=count)
        row += 1
    for col in range(1, 7):
        ws.column_dimensions[get_column_letter(col)].width = 28
    for row_cells in ws.iter_rows():
        for cell in row_cells:
            cell.alignment = Alignment(vertical="top", wrap_text=True)


def write_testcase_sheet(wb: Workbook, section_name: str, headers: list[str], rows: list[list[str]], used: set[str]):
    ws = wb.create_sheet(safe_sheet_name(section_name, used))
    last_col = len(headers)

    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=min(8, last_col))
    ws.cell(row=1, column=1, value="时间：xxxx-xx-xx  姓名：xxx")
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=min(7, last_col))
    ws.cell(row=2, column=1, value="执行开始时间")

    for col_idx, col_name in enumerate(headers, start=1):
        ws.cell(row=3, column=col_idx, value=col_name)

    for row_idx, row in enumerate(rows, start=4):
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    style_sheet(ws, header_row=3)
    set_column_widths(ws, headers)
    return ws


def write_plain_sheet(wb: Workbook, section_name: str, headers: list[str], rows: list[list[str]], used: set[str]):
    """Auxiliary sheets (traceability, execution plan, ...): plain header + data."""
    ws = wb.create_sheet(safe_sheet_name(section_name, used))
    for col_idx, col_name in enumerate(headers, start=1):
        ws.cell(row=1, column=col_idx, value=col_name)
    for row_idx, row in enumerate(rows, start=2):
        for col_idx, value in enumerate(row, start=1):
            ws.cell(row=row_idx, column=col_idx, value=value)

    thin = Side(style="thin", color="D9D9D9")
    border = Border(left=thin, right=thin, top=thin, bottom=thin)
    for row_cells in ws.iter_rows():
        for cell in row_cells:
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)
    for cell in ws[1]:
        cell.fill = PatternFill("solid", fgColor="D9EAF7")
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"
    set_column_widths(ws, headers)
    return ws


def write_workbook(
    sections: list[tuple[str, list[str], list[list[str]]]],
    output: Path,
    title: str,
) -> None:
    if not sections:
        raise SystemExit("No tables found. The Markdown must contain at least one table with a header row.")

    wb = Workbook()
    used: set[str] = {"首页"}

    prepared: list[tuple[str, list[str], list[list[str]], bool]] = []
    for section_name, headers, raw_rows in sections:
        rows = [build_row(raw, headers) for raw in raw_rows]
        is_testcase = TESTCASE_KEY_COLUMNS.issubset(set(headers))
        prepared.append((section_name, headers, rows, is_testcase))

    add_home_sheet(wb, title, [(name, len(rows)) for name, _headers, rows, _tc in prepared])

    for section_name, headers, rows, is_testcase in prepared:
        if is_testcase:
            write_testcase_sheet(wb, section_name, headers, rows, used)
        else:
            write_plain_sheet(wb, section_name, headers, rows, used)

    output.parent.mkdir(parents=True, exist_ok=True)
    wb.save(output)
    counts = ", ".join(f"{name}={len(rows)}行" for name, _h, rows, _tc in prepared)
    print(f"Created {output}")
    print(f"Sheets: {counts}")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Convert module-test-cases-history-20261015.md to the standard Excel workbook.")
    parser.add_argument("input", type=Path, help="Input module-test-cases-history-20261015.md")
    parser.add_argument("output", type=Path, help="Output .xlsx file")
    parser.add_argument("--title", default=None, help="Workbook title shown on the home sheet (default: first H1)")
    args = parser.parse_args()

    sections = parse_markdown(args.input)
    title = args.title or args.input.stem
    write_workbook(sections, args.output, title)


if __name__ == "__main__":
    main()
