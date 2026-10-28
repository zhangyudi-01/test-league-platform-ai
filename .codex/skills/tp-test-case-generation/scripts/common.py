#!/usr/bin/env python3
"""Shared contracts for TP-to-test-case generation.

The module deliberately loads the sibling RSU skill at runtime.  This keeps
module discovery, manifest parsing, and upstream final-TP validation in one
place while allowing the case skill to work in another project checkout.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sql_assets import (
    SQL_ID_RE,
    SqlAssetError,
    ensure_sql_workspace,
    load_registry,
    relevant_assets_index_text,
    relevant_assets_manifest,
    registry_manifest,
    validate_assets,
)

SKILL_DIR = Path(__file__).resolve().parent.parent
BT = chr(96)


def _load_upstream() -> Any:
    configured = os.environ.get("RSU_TEST_POINT_GENERATION_SCRIPTS")
    candidates = []
    if configured:
        candidates.append(Path(configured).expanduser())
    candidates.extend(
        [
            SKILL_DIR.parent / "rsu-test-point-generation" / "scripts",
            SKILL_DIR.parent.parent / ".agents" / "skills" / "rsu-test-point-generation" / "scripts",
            SKILL_DIR.parent.parent / ".claude" / "skills" / "rsu-test-point-generation" / "scripts",
        ]
    )
    for directory in candidates:
        path = directory.resolve() / "common.py"
        if path.is_file() and path.resolve() != Path(__file__).resolve():
            spec = importlib.util.spec_from_file_location("_tp_upstream_common", path)
            if spec is None or spec.loader is None:
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            return module
    searched = ", ".join(str(item) for item in candidates)
    raise RuntimeError(
        "rsu-test-point-generation/scripts/common.py not found; "
        f"set RSU_TEST_POINT_GENERATION_SCRIPTS. searched: {searched}"
    )


upstream = _load_upstream()
WorkflowError = upstream.WorkflowError

# Re-export the upstream parser primitives used by every script.
read_text = upstream.read_text
atomic_write_text = upstream.atomic_write_text
atomic_write_json = upstream.atomic_write_json
sha256_file = upstream.sha256_file
sha256_text = upstream.sha256_text
utc_now = upstream.utc_now
clean_cell = upstream.clean_cell
extract_tables = upstream.extract_tables
find_tables = upstream.find_tables
markdown_table = upstream.markdown_table
parse_metadata_table = upstream.parse_metadata_table
column_value = upstream.column_value
resolve_module_layout = upstream.resolve_module_layout
parse_module = upstream.parse_module
default_output_dir = upstream.default_output_dir
parse_final_document = upstream.parse_final_document
state_lock = upstream.state_lock


def run_preanalysis_validation(layout: Any, case_output_dir: Path | None = None) -> str:
    """Validate source preanalysis without scanning generated TP/case workspaces."""
    validator = upstream.find_preanalysis_validator()
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, "-B", str(validator), str(layout.preanalysis_dir)]
    if layout.manifest_path is not None:
        command.extend(["--manifest", str(layout.manifest_path)])

    preanalysis_root = layout.preanalysis_dir.resolve()
    # The preanalysis validator must not scan generated test-point or
    # testcase workspaces: their materialized inputs intentionally contain
    # links relative to the module root, not links resolvable from the
    # preanalysis tree. Exclude both roots when they live below it.
    generated_roots = [
        layout.default_output_dir.resolve(),
        (layout.module_dir.resolve() / "test-cases"),
    ]
    if case_output_dir is not None:
        generated_roots.append(case_output_dir.resolve())

    # Flat/legacy module layouts may keep several isolated testcase workspaces
    # beside the active one (for example, performance comparison runs).  The
    # preanalysis validator recursively scans the whole module root, so every
    # genuine testcase workspace for this module must be excluded, not only the
    # currently selected output directory.  Detect workspaces by their state
    # schema and module binding instead of by a fragile directory-name prefix.
    module_root = layout.module_dir.resolve()
    for current_dir, child_dirs, file_names in os.walk(preanalysis_root):
        if "generation-state.json" not in file_names:
            continue
        candidate = Path(current_dir).resolve()
        state_file = candidate / "generation-state.json"
        try:
            payload = json.loads(state_file.read_text(encoding="utf-8-sig"))
            bound_module = Path(str(payload.get("module_dir", ""))).resolve()
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if (
            payload.get("schema_version") in {
                "tp-test-case-generation/v2",
                "tp-test-case-generation/v3",
            }
            and bound_module == module_root
        ):
            generated_roots.append(candidate)
            child_dirs[:] = []
    seen: set[Path] = set()
    for generated_root in generated_roots:
        if generated_root in seen:
            continue
        seen.add(generated_root)
        try:
            generated_root.relative_to(preanalysis_root)
        except ValueError:
            continue
        if generated_root != preanalysis_root:
            command.extend(["--exclude-root", str(generated_root)])

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    output = (result.stdout + result.stderr).strip()
    if result.returncode != 0:
        raise WorkflowError("upstream preanalysis validation failed:\n" + output)
    return output

RESOURCE_HEADERS = upstream.RESOURCE_HEADERS
RSU_HEADERS = upstream.RSU_HEADERS
CASE_INPUT_QUESTION_HEADERS = upstream.CASE_INPUT_QUESTION_HEADERS
TP_READINESS_HEADERS = upstream.tp_readiness_headers

CASE_READINESS_PATH = "test-case-readiness.md"
FINAL_POINTS_NAME = "module-test-points.md"
UPSTREAM_STATE_NAME = "generation-state.json"
CASE_STATE_NAME = "generation-state.json"
CASE_STATE_SCHEMA_VERSION = "tp-test-case-generation/v3"
CASE_INPUT_SCHEMA_VERSION = "tp-test-case-generation/input-v4"
FINALIZATION_SCHEMA_VERSION = "tp-test-case-generation/finalization-v2"

TRACE_HEADERS = (
    "TC-ID", "覆盖场景", "TP-ID", "RSU Refs", "Question Refs",
    "Context Refs", "Data Closure Refs", "Data Profile Refs", "用例设计说明",
)
DATA_EXECUTION_HEADERS = (
    "TC-ID", "DC-ID", "DP-ID", "SQL Refs", "查询/验证入口", "目标数据状态",
    "准备或变更动作", "动态预期推导", "清理/隔离",
)
CASE_HEADERS = (
    "TC-ID", "冲刺", "测试项", "测试点", "数据变量", "前置条件", "执行步骤", "备注",
    "预期结果", "测试结果1", "测试结果2", "测试结果3",
)
# Outputs generated before TP-OPT-018 used a misleading first-column label
# (`序号`) while still storing the required TC-ID values in that column. Keep
# read compatibility for already-validated historical outputs; all new
# templates and prompts use the canonical `TC-ID` header above.
LEGACY_CASE_HEADERS = (
    "序号", "冲刺", "测试项", "测试点", "数据变量", "前置条件", "执行步骤", "备注",
    "预期结果", "测试结果1", "测试结果2", "测试结果3",
)
CONTEXT_HEADERS = (
    "Context Key", "Category", "CIQ Refs", "Value or Entry", "Evidence/Location", "Status",
)

PLACEHOLDER_RE = re.compile(
    r"\{\{[A-Z0-9_]+\}\}|\bTODO\b|\bTBD\b|待填写|未填写|待补充",
    re.IGNORECASE,
)
ID_RE = re.compile(r"\b(?:TP|RSU|Q|CIQ|DC|DP|FC)-\d{3}\b")
SQL_REF_RE = re.compile(r"\bSQL-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
CASE_VARIABLE_RE = re.compile(r"(?<![A-Za-z0-9_])\$([A-Z][A-Z0-9_]*)(?![A-Za-z0-9_])")
CELL_BREAK_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
MID_LINE_SENTENCE_RE = re.compile(r"[。！？]\s*\S")
EXPECTED_ITEM_RE = re.compile(r"^(\d+)[.、]\s*\S")
STEP_ITEM_RE = re.compile(r"^(\d+)[.、]\s*\S")
PRECONDITION_CATEGORY_RE = re.compile(
    r"^(?:\d+[.、]\s*)?[^：:<>{}|]{1,30}[：:]$"
)
SECRET_RE = re.compile(
    r"(?i)(?:password|passwd|token|secret|api[_-]?key|密码|口令|访问密钥)\s*[:=]"
)

FORBIDDEN_CASE_PROSE = (
    "当前TP",
    "当前 TP",
    "来源场景",
    "场景矩阵",
    "数据闭包执行计划",
    "执行计划中的场景条件",
    "执行当前TP的核心操作",
    "执行当前 TP 的核心操作",
    "执行当前测试场景",
    "按场景分别记录",
    "按来源场景分别记录",
    "各来源场景均",
    "具体状态按本用例",
    "根据测试点执行",
    "进行相应操作",
)


@dataclass(frozen=True)
class TestPoint:
    tp_id: str
    cells: tuple[str, ...]
    headers: tuple[str, ...]
    order: int
    primary_rsu: str
    source_rsus: tuple[str, ...]
    question_refs: tuple[str, ...]
    context_refs: tuple[str, ...]
    data_closure_refs: tuple[str, ...]
    text: str


@dataclass(frozen=True)
class CaseReadiness:
    result: str
    tp_status: dict[str, str]
    tp_ciq_refs: dict[str, tuple[str, ...]]
    questions: dict[str, tuple[str, ...]]
    document_sha256: str
    output_sha256: str


@dataclass(frozen=True)
class CaseInput:
    tp: TestPoint
    input_sha256: str
    text: str
    blockers: tuple[str, ...]
    sql_registry: dict[str, Any]
    module_baseline_text: str
    module_baseline_sha256: str
    context_baseline_text: str
    context_baseline_sha256: str
    baseline_signature: str
    delta_text: str
    delta_sha256: str


@dataclass(frozen=True)
class CaseDocument:
    metadata: dict[str, str]
    trace_rows: list[list[str]]
    case_rows: list[list[str]]
    data_execution_rows: list[list[str]]


def _ids(text: str, prefix: str) -> tuple[str, ...]:
    result = []
    for item in re.findall(rf"\b{re.escape(prefix)}-\d{{3}}\b", text or ""):
        if item not in result:
            result.append(item)
    return tuple(result)


def _resource_ids(text: str, known: set[str]) -> tuple[str, ...]:
    if not text or not known:
        return ()
    escaped = "|".join(re.escape(item) for item in sorted(known, key=len, reverse=True))
    pattern = re.compile(rf"(?<![A-Za-z0-9_])(?:{escaped})(?![A-Za-z0-9_])")
    result = []
    for match in pattern.finditer(text):
        item = match.group(0)
        if item not in result:
            result.append(item)
    return tuple(result)

def _cell(row: tuple[str, ...] | list[str], headers: tuple[str, ...], name: str) -> str:
    return clean_cell(column_value(headers, list(row), name))


def module_paths(module_dir: Path, preanalysis_dir: Path | None, manifest: Path | None,
                 case_output_dir: Path | None = None):
    layout = resolve_module_layout(module_dir, preanalysis_dir, manifest)
    model = parse_module(layout)
    upstream_points_dir = default_output_dir(layout, None)
    case_dir = (case_output_dir.resolve() if case_output_dir else module_dir.resolve() / "test-cases")
    return layout, model, upstream_points_dir, case_dir


def load_final_test_points(points_dir: Path, model) -> tuple[list[TestPoint], Path, str]:
    final_path = points_dir / FINAL_POINTS_NAME
    if not final_path.is_file():
        raise WorkflowError(f"validated final test points are missing: {final_path}")
    document = parse_final_document(final_path, model.data_closure_enabled)
    known = set(model.resources)
    points: list[TestPoint] = []
    seen: set[str] = set()
    for order, cells in enumerate(document.rows, start=1):
        tp_id = _cell(cells, document.headers, "TP-ID")
        if not re.fullmatch(r"TP-\d{3}", tp_id):
            raise WorkflowError(f"invalid TP-ID in final test points: {tp_id}")
        if tp_id in seen:
            raise WorkflowError(f"duplicate final TP-ID: {tp_id}")
        seen.add(tp_id)
        source_rsus = _ids(_cell(cells, document.headers, "Source RSUs"), "RSU")
        primary = _cell(cells, document.headers, "Primary RSU")
        if primary not in source_rsus:
            source_rsus = (primary, *source_rsus)
        question_refs = _ids(_cell(cells, document.headers, "Question Refs"), "Q")
        context_refs = _resource_ids(_cell(cells, document.headers, "Context Refs"), known)
        raw_context = _cell(cells, document.headers, "Context Refs")
        if clean_cell(raw_context) != "无" and not context_refs:
            raise WorkflowError(f"{tp_id} has malformed Context Refs")
        data_refs = ()
        if model.data_closure_enabled:
            data_refs = _ids(_cell(cells, document.headers, "Data Closure Refs"), "DC")
            if set(data_refs) - set(context_refs):
                raise WorkflowError(f"{tp_id} Data Closure Refs must also be Context Refs")
        points.append(
            TestPoint(
                tp_id, tuple(cells), tuple(document.headers), order, primary, source_rsus, question_refs,
                context_refs, data_refs, " | ".join(clean_cell(item) for item in cells),
            )
        )
    if not points:
        raise WorkflowError("final test point document contains no TP rows")
    return points, final_path, sha256_file(final_path)


def parse_case_readiness(path: Path, model) -> CaseReadiness:
    if not path.is_file():
        raise WorkflowError(f"test-case-readiness.md is missing: {path}")
    text = read_text(path)
    metadata = parse_metadata_table(text)
    result = clean_cell(metadata.get("审查结果", ""))
    if result not in {"ready", "blocked-input", "upstream-gap"}:
        raise WorkflowError(f"invalid readiness result: {result}")
    tables = extract_tables(text)
    q_tables = find_tables(tables, CASE_INPUT_QUESTION_HEADERS)
    if len(q_tables) != 1:
        raise WorkflowError("test-case-readiness.md must contain exactly one case-input question table")
    questions: dict[str, tuple[str, ...]] = {}
    question_status: dict[str, str] = {}
    for _, cells in q_tables[0].rows:
        qid = clean_cell(cells[0])
        if not re.fullmatch(r"CIQ-\d{3}", qid) or qid in questions:
            raise WorkflowError(f"invalid or duplicate CIQ ID: {qid}")
        questions[qid] = tuple(cells)
        question_status[qid] = clean_cell(cells[6])
    expected = TP_READINESS_HEADERS(model.data_closure_enabled)
    tp_tables = find_tables(tables, expected)
    if len(tp_tables) != 1:
        raise WorkflowError("test-case-readiness.md must contain exactly one TP readiness table")
    tp_status: dict[str, str] = {}
    tp_ciq: dict[str, tuple[str, ...]] = {}
    for _, cells in tp_tables[0].rows:
        tp_id = clean_cell(cells[0])
        if tp_id in tp_status:
            raise WorkflowError(f"duplicate readiness TP-ID: {tp_id}")
        status = clean_cell(cells[1])
        if status not in {"ready", "blocked-input", "upstream-gap"}:
            raise WorkflowError(f"invalid readiness status for {tp_id}: {status}")
        raw = clean_cell(cells[3] if model.data_closure_enabled else cells[2])
        refs = _ids(raw, "CIQ")
        if clean_cell(raw) != "无" and not refs:
            raise WorkflowError(f"{tp_id} has malformed Input Question Refs")
        if set(refs) - set(questions):
            raise WorkflowError(f"{tp_id} references undefined CIQ: {sorted(set(refs) - set(questions))}")
        pending = [item for item in refs if question_status[item] == "pending"]
        if status == "ready" and pending:
            raise WorkflowError(f"{tp_id} is ready but references pending CIQ: {pending}")
        if status == "blocked-input" and not pending:
            raise WorkflowError(f"{tp_id} blocked-input must reference pending CIQ")
        tp_status[tp_id] = status
        tp_ciq[tp_id] = refs
    return CaseReadiness(
        result,
        tp_status,
        tp_ciq,
        questions,
        sha256_text(text),
        sha256_file(path),
    )


def read_context(path: Path) -> tuple[str, str, bool]:
    if not path.is_file():
        raise WorkflowError(f"execution context is missing: {path}")
    text = read_text(path)
    if SECRET_RE.search(text):
        raise WorkflowError("execution-context.md contains a secret-like key/value; keep passwords and tokens out of the artifact")
    tables = find_tables(extract_tables(text), CONTEXT_HEADERS)
    if len(tables) != 1:
        raise WorkflowError("execution-context.md must contain exactly one fixed context table")
    pending = []
    for line, cells in tables[0].rows:
        if len(cells) != len(CONTEXT_HEADERS):
            raise WorkflowError(f"execution context row at line {line} has the wrong column count")
        status = clean_cell(cells[5])
        if status not in {"ready", "not-needed", "pending"}:
            raise WorkflowError(f"invalid execution context status at line {line}: {status}")
        if status == "pending":
            pending.append(clean_cell(cells[0]))
        if status != "pending" and not clean_cell(cells[3]):
            raise WorkflowError(f"execution context value is empty at line {line}")
    return text, sha256_file(path), not pending


def closure_profiles(model, closure_ids: tuple[str, ...]) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for closure_id in closure_ids:
        resource = model.resources.get(closure_id)
        if resource is None:
            raise WorkflowError(f"undefined data closure: {closure_id}")
        profiles = set(re.findall(r"\bDP-\d{3}\b", read_text(resource.path)))
        result[closure_id] = profiles
    return result


def all_profile_owners(model) -> dict[str, set[str]]:
    owners: dict[str, set[str]] = {}
    for closure_id in model.data_closure_ids:
        for profile in closure_profiles(model, (closure_id,))[closure_id]:
            owners.setdefault(profile, set()).add(closure_id)
    return owners


def materialize_case_input(model, readiness: CaseReadiness,
                           context_text: str, context_hash: str, tp: TestPoint,
                           final_points_dir: Path, case_dir: Path) -> CaseInput:
    blockers: list[str] = []
    fixed_ids = list(model.fixed_resource_ids)
    fixed_set = set(fixed_ids)
    resource_ids: list[str] = []
    for item in tp.context_refs:
        if item == "DC-INDEX" and not tp.data_closure_refs:
            continue
        if item in fixed_set:
            continue
        if item not in resource_ids:
            resource_ids.append(item)
    for item in tp.data_closure_refs:
        if item not in resource_ids:
            resource_ids.append(item)
    if model.data_closure_enabled and tp.data_closure_refs and "DC-INDEX" in model.resources:
        if "DC-INDEX" not in resource_ids:
            resource_ids.insert(0, "DC-INDEX")
    materials: list[tuple[str, str]] = []
    for resource_id in resource_ids:
        resource = model.resources.get(resource_id)
        if resource is None:
            blockers.append(f"{tp.tp_id} references undefined resource {resource_id}")
            continue
        try:
            content = read_text(resource.path)
        except Exception as exc:
            blockers.append(str(exc))
            continue
        materials.append((resource_id, content))
    q_refs = tp.question_refs
    q_lines = []
    for qid in q_refs:
        question = model.questions.get(qid)
        if question is None:
            blockers.append(f"{tp.tp_id} references undefined question {qid}")
            continue
        if question.status == "pending":
            blockers.append(f"{tp.tp_id} references unanswered requirement question {qid}")
        q_lines.append(markdown_table(question.headers, [list(question.cells)]))
    ciq_lines = []
    for ciq in readiness.tp_ciq_refs.get(tp.tp_id, ()):
        row = readiness.questions.get(ciq)
        if row is None:
            blockers.append(f"{tp.tp_id} references undefined CIQ {ciq}")
            continue
        if clean_cell(row[6]) != "answered":
            blockers.append(f"{tp.tp_id} references unanswered CIQ {ciq}")
        ciq_lines.append(markdown_table(CASE_INPUT_QUESTION_HEADERS, [list(row)]))
    rsu_rows = []
    for rsu_id in tp.source_rsus:
        rsu = model.rsu_by_id.get(rsu_id)
        if rsu is None:
            blockers.append(f"{tp.tp_id} references undefined RSU {rsu_id}")
        else:
            rsu_rows.append(list(rsu.cells))
    if not rsu_rows:
        blockers.append(f"{tp.tp_id} has no source RSU")
    source_table = markdown_table(RSU_HEADERS, rsu_rows) if rsu_rows else "无"
    materials.sort(key=lambda item: item[0])
    dynamic_source_text = "\n\n".join(
        f"### {resource_id}\n\n- 文件：`{model.resources[resource_id].path.as_posix()}`\n\n"
        f"<!-- BEGIN {resource_id} -->\n{content.rstrip()}\n<!-- END {resource_id} -->"
        for resource_id, content in materials
    ) or "无"

    fixed_anchors = []
    for resource_id in fixed_ids:
        resource = model.resources.get(resource_id)
        if resource is None:
            blockers.append(f"fixed resource is undefined: {resource_id}")
            continue
        try:
            fixed_anchors.append(
                {
                    "id": resource_id,
                    "path": resource.path.as_posix(),
                    "sha256": sha256_file(resource.path),
                }
            )
        except OSError as exc:
            blockers.append(f"cannot hash fixed resource {resource_id}: {exc}")
    fixed_anchor_text = "\n".join(
        f"- `{item['id']}`：`{item['path']}`；SHA-256 `{item['sha256']}`"
        for item in fixed_anchors
    ) or "- 无"

    try:
        sql_registry = relevant_assets_manifest(case_dir, tp.data_closure_refs)
        sql_text = relevant_assets_index_text(case_dir, tp.data_closure_refs)
    except SqlAssetError as exc:
        blockers.append(str(exc))
        sql_registry = {}
        sql_text = "SQL 资产注册表无效，修复后重新准备当前 TP。"
    canonical_context_refs = tuple(sorted(set(tp.context_refs)))
    canonical_data_refs = tuple(sorted(set(tp.data_closure_refs)))
    allowed_context = "、".join(canonical_context_refs) if canonical_context_refs else "无"
    allowed_data = "、".join(canonical_data_refs) if canonical_data_refs else "无"
    input_manifest = {
        "schema_version": CASE_INPUT_SCHEMA_VERSION,
        "tp_id": tp.tp_id,
        "tp_order": tp.order,
        "tp_cells": list(tp.cells),
        "source_rsus": list(tp.source_rsus),
        "question_refs": list(tp.question_refs),
        "context_refs": list(tp.context_refs),
        "data_closure_refs": list(tp.data_closure_refs),
        "fixed_resource_anchors": fixed_anchors,
        "material_resources": [
            {"id": rid, "path": model.resources[rid].path.as_posix(), "sha256": sha256_text(content)}
            for rid, content in materials
        ],
        "context_sha256": context_hash,
        "readiness_document_sha256": readiness.document_sha256,
        "final_test_points_sha256": sha256_file(final_points_dir / FINAL_POINTS_NAME),
        "sql_registry": sql_registry,
    }
    input_hash = sha256_text(json.dumps(input_manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
    module_baseline_text = (
        "# 模块公共基线\n\n"
        "## 基线边界\n\n"
        "- 本文件只包含本模块所有 TP 可共享的执行上下文与固定来源溯源锚点。\n"
        "- 固定来源正文不在这里展开；不得依据路径自行扫描全文补充业务事实。\n"
        "- 本基线不包含任何具体 TP 的测试点、RSU、Q/CIQ、输出或工具调用历史。\n\n"
        "## 固定来源溯源锚点\n\n"
        f"{fixed_anchor_text}\n\n"
        "## 执行上下文\n\n"
        f"{context_text.rstrip()}\n"
    )
    module_baseline_sha256 = sha256_text(module_baseline_text)
    context_baseline_manifest = {
        "schema_version": CASE_INPUT_SCHEMA_VERSION,
        "module_baseline_sha256": module_baseline_sha256,
        "context_refs": list(canonical_context_refs),
        "data_closure_refs": list(canonical_data_refs),
        "material_resources": input_manifest["material_resources"],
        "sql_registry": sql_registry,
    }
    context_baseline_sha256 = sha256_text(
        json.dumps(
            context_baseline_manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    baseline_signature = context_baseline_sha256[:24]
    context_baseline_text = (
        f"# TP 上下文基线：{baseline_signature}\n\n"
        "## 基线元数据\n\n"
        "| 字段 | 值 |\n|---|---|\n"
        f"| 基线签名 | `{baseline_signature}` |\n"
        f"| 上下文基线语义 SHA-256 | `{context_baseline_sha256}` |\n"
        f"| 模块公共基线 SHA-256 | `{module_baseline_sha256}` |\n"
        f"| Context Refs | `{allowed_context}` |\n"
        f"| Data Closure Refs | `{allowed_data}` |\n\n"
        "## 使用边界\n\n"
        "- 本文件只包含共享同一 Context/DC/SQL 组合的 TP 可复用事实。\n"
        "- 后续 TP 分支只能结合自己的增量输入使用这些事实；不得读取兄弟 TP 的输入、输出或聊天历史。\n"
        "- 若增量输入与本基线仍不足以形成可判断预期，必须停止并报告阻断。\n\n"
        "## 动态上下文与数据依赖\n\n"
        f"{dynamic_source_text}\n\n"
        "## 数据闭包使用边界\n\n"
        "- Data Closure Refs 只提供数据事实和准备依据，不代表当前 TP 必须使用 SQL。\n"
        "- 普通页面交互、按钮状态、提示、校验顺序、轮询、重试、并发和勾选行为不得为了引用 DC 而附加 SQL。\n"
        "- 只有模块生成计划已经为当前 TP 分配查询 SQL 时才可引用 SQL；不得在用例生成阶段临时新增。\n\n"
        "## 可复用 SQL 资产\n\n"
        f"{sql_text}\n\n"
        "- SQL 已在批次生成前由模块 SQL 阶段统一规划、生成并校验；当前用例只能引用计划分配的 SQL-ID。\n"
        "- SQL 收敛不以 CASE、别名、展示转换或排版差异判定业务缺陷；这些差异只有在确认查询口径一致时才可合并。\n"
        "- SQL 参数使用 `:参数名`；数据变量列必须为每个参数提供同名映射。步骤只引用 SQL-ID 和文件名，不粘贴 SQL 原文。\n"
        "- 只有用途与当前场景匹配时才读取对应单个 SQL 文件，不得批量展开 SQL 正文。\n"
    )
    delta_text = (
        f"# TP 会话增量输入：{tp.tp_id}\n\n"
        "## 增量元数据\n\n"
        "| 字段 | 值 |\n|---|---|\n"
        f"| TP-ID | `{tp.tp_id}` |\n"
        f"| 完整输入语义 SHA-256 | `{input_hash}` |\n"
        f"| TP 增量语义 SHA-256 | `{{DELTA_SHA256}}` |\n"
        f"| TP 顺序 | `{tp.order}` |\n"
        f"| 模块公共基线 SHA-256 | `{module_baseline_sha256}` |\n"
        f"| 上下文基线签名 | `{baseline_signature}` |\n"
        f"| 上下文基线语义 SHA-256 | `{context_baseline_sha256}` |\n\n"
        "## 生成边界\n\n"
        f"- 当前批次中只为 `{tp.tp_id}` 生成默认 1 条、确有必要时少量拆分的可执行测试用例。\n"
        "- 当前会话已从模块公共基线和上下文基线 fork；不得再次读取完整 Skill、完整 INPUT、固定来源全文、runner 日志或其他 TP 输入输出。\n"
        "- 简单用例只写关键前置、具体动作和对应结果；没有前置填 `无`，不得制造准备动作或准备校验。\n"
        "- 步骤和预期都从 `1.` 连续编号并一一对应；禁止使用“当前 TP 核心操作”“来源场景”“数据闭包执行计划”等内部占位话术。\n"
        "- 不得新增未出现在本增量或继承基线中的 RSU、Q、CIQ、FC、SRC、DC、DP 或 SQL 引用。\n"
        "- 本次只允许写入当前 `by-tp/<TP-ID>.md`；SQL 资产在本阶段只读，不得新增或修改。\n\n"
        "## 当前最终测试点\n\n"
        f"{markdown_table(tp.headers, [list(tp.cells)])}\n\n"
        "## 来源 RSU 原文\n\n"
        f"{source_table}\n\n"
        "## 当前 TP 的需求问题\n\n"
        f"{'\n\n'.join(q_lines) if q_lines else '无'}\n\n"
        "## 当前 TP 的用例输入问题\n\n"
        f"{'\n\n'.join(ciq_lines) if ciq_lines else '无'}\n"
    )
    delta_sha256 = sha256_text(delta_text.replace("{DELTA_SHA256}", ""))
    delta_text = delta_text.replace("{DELTA_SHA256}", delta_sha256)
    text = (
        f"# TP 用例生成输入：{tp.tp_id}\n\n"
        "## 输入元数据\n\n"
        "| 字段 | 值 |\n|---|---|\n"
        f"| TP-ID | `{tp.tp_id}` |\n| 输入 SHA-256 | `{input_hash}` |\n"
        f"| TP 顺序 | `{tp.order}` |\n| 固定来源锚点 | `{', '.join(fixed_ids) or '无'}` |\n"
        f"| 当前 TP Context Refs | `{allowed_context}` |\n| 当前 TP Data Closure Refs | `{allowed_data}` |\n"
        f"| 执行上下文 SHA-256 | `{context_hash}` |\n"
        f"| 就绪性文档 SHA-256 | `{readiness.document_sha256}` |\n\n"
        "## 生成边界\n\n"
        f"- 只为 `{tp.tp_id}` 生成默认 1 条、确有必要时少量拆分的可执行测试用例。\n"
        "- 简单用例只写关键前置、具体动作和对应结果；没有前置填 `无`，不得制造准备动作或准备校验。\n"
        "- 步骤和预期都从 `1.` 连续编号并一一对应；禁止使用“当前 TP 核心操作”“来源场景”“数据闭包执行计划”等内部占位话术。\n"
        "- 本 INPUT 已构成当前 TP 的确定性最小上下文闭包；不得读取 runner 历史日志、其他 TP 输入包或其他 TP 输出作为业务依据。\n"
        "- 不得新增未出现在本输入包的 RSU、Q、CIQ、FC、SRC 或 DC 引用。固定来源只作为路径/哈希溯源锚点，不在常规生成中展开全文。\n"
        "- Data Closure Refs 只提供数据事实和准备依据，不等于必须使用 SQL 或输出数据闭包执行计划。\n"
        "- 本次只允许写入当前 `by-tp/<TP-ID>.md`；SQL 资产在本阶段只读。\n\n"
        "## 当前最终测试点\n\n"
        f"{markdown_table(tp.headers, [list(tp.cells)])}\n\n"
        "## 来源 RSU 原文\n\n"
        f"{source_table}\n\n"
        "## 当前 TP 的需求问题\n\n"
        f"{'\n\n'.join(q_lines) if q_lines else '无'}\n\n"
        "## 当前 TP 的用例输入问题\n\n"
        f"{'\n\n'.join(ciq_lines) if ciq_lines else '无'}\n\n"
        "## 固定来源溯源锚点\n\n"
        f"{fixed_anchor_text}\n\n"
        "这些锚点用于证明输入来源和检测变更，不是本轮的全文阅读清单。当前 TP 所需业务事实必须来自本 INPUT 已物化的 TP、RSU、Q/CIQ、动态资源和执行上下文；若仍缺少可判定事实，应停止并报告阻断，不得回退全文扫描。\n\n"
        "## 当前 TP 动态上下文与数据依赖\n\n"
        f"{dynamic_source_text}\n\n"
        "## 执行上下文\n\n"
        f"{context_text.rstrip()}\n\n"
        "## 数据闭包使用边界\n\n"
        "- Data Closure Refs 是上游事实和数据准备依据，不得自行扩展，也不代表必须写 SQL。\n"
        "- 入库或更新场景在预期中描述应新增或更新的记录内容；本 Skill 不为此自动生成 INSERT/UPDATE/DELETE。\n"
        "\n## 可复用 SQL 资产\n\n"
        f"{sql_text}\n\n"
        "- SQL 已在模块 SQL 阶段统一规划、生成和校验；用例阶段只能引用当前 TP 被分配的 SQL-ID，不得临时新增。\n"
        "- CASE、别名、展示转换、大小写和排版差异不单独构成 Skill 缺陷；是否复用由查询语义和测试目的决定。\n"
        "- SQL 参数使用 `:参数名`；数据变量列必须为每个参数提供同名映射。步骤只引用 SQL-ID 和文件名，不粘贴 SQL 原文。\n"
        "- INPUT 仅提供与当前 DC 匹配的 SQL 元数据索引；只有用途与当前场景匹配时才读取对应单个 SQL 文件。\n"
    )
    return CaseInput(
        tp,
        input_hash,
        text,
        tuple(blockers),
        sql_registry,
        module_baseline_text,
        module_baseline_sha256,
        context_baseline_text,
        context_baseline_sha256,
        baseline_signature,
        delta_text,
        delta_sha256,
    )


def output_paths(case_dir: Path, tp_id: str) -> tuple[Path, Path]:
    return case_dir / "inputs" / f"{tp_id}-input.md", case_dir / "by-tp" / f"{tp_id}.md"


def session_input_paths(case_dir: Path, tp_id: str, signature: str) -> tuple[Path, Path, Path]:
    return (
        case_dir / "baselines" / "module-baseline.md",
        case_dir / "baselines" / "contexts" / f"{signature}-baseline.md",
        case_dir / "inputs" / f"{tp_id}-delta.md",
    )


def context_path(case_dir: Path) -> Path:
    return case_dir / "execution-context.md"


def state_path(case_dir: Path) -> Path:
    return case_dir / CASE_STATE_NAME


def load_json(path: Path) -> dict:
    try:
        value = json.loads(read_text(path))
    except FileNotFoundError as exc:
        raise WorkflowError(f"required state file is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"invalid JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError(f"JSON root must be an object: {path}")
    return value


def save_json(path: Path, value: dict) -> None:
    atomic_write_json(path, value)


def assert_case_state_schema(state: dict) -> None:
    actual = state.get("schema_version")
    if actual != CASE_STATE_SCHEMA_VERSION:
        raise WorkflowError(
            f"unsupported testcase generation state schema {actual}; "
            "rerun init_generation.py --refresh"
        )


def ensure_dirs(case_dir: Path) -> None:
    for name in ("inputs", "by-tp", "by-batch", "history", "final", "sql", "baselines", "baselines/contexts"):
        (case_dir / name).mkdir(parents=True, exist_ok=True)
    ensure_sql_workspace(case_dir)


def require_no_placeholders(text: str, label: str) -> None:
    match = PLACEHOLDER_RE.search(text)
    if match:
        raise WorkflowError(f"{label} contains unresolved placeholder: {match.group(0)}")


def _table_headers_summary(tables: list[Any]) -> str:
    """Return compact observed table headers for deterministic repair feedback."""

    if not tables:
        return "无 Markdown 表格"
    summaries = [" | ".join(table.headers) for table in tables[:8]]
    if len(tables) > 8:
        summaries.append(f"其余 {len(tables) - 8} 个表省略")
    return "；".join(summaries)


def parse_case_document(path: Path, require_data_execution: bool = False) -> CaseDocument:
    text = read_text(path)
    require_no_placeholders(text, str(path))
    metadata = parse_metadata_table(text)
    tables = extract_tables(text)
    trace_tables = find_tables(tables, TRACE_HEADERS)
    canonical_case_tables = find_tables(tables, CASE_HEADERS)
    legacy_case_tables = find_tables(tables, LEGACY_CASE_HEADERS)
    case_tables = canonical_case_tables or legacy_case_tables
    data_tables = find_tables(tables, DATA_EXECUTION_HEADERS)
    if len(trace_tables) != 1:
        expected = " | ".join(TRACE_HEADERS)
        observed = _table_headers_summary(tables)
        raise WorkflowError(
            f"{path} must contain exactly one case trace table; "
            f"expected exact header: {expected}; observed headers: {observed}"
        )
    if len(case_tables) != 1:
        expected = " | ".join(CASE_HEADERS)
        observed = _table_headers_summary(tables)
        raise WorkflowError(
            f"{path} must contain exactly one standard testcase table; "
            f"expected exact header: {expected}; observed headers: {observed}"
        )
    if require_data_execution and len(data_tables) != 1:
        raise WorkflowError(f"{path} must contain exactly one data-closure execution table")
    if not require_data_execution and data_tables:
        raise WorkflowError(f"{path} must not contain a data-closure execution table without Data Closure Refs")
    return CaseDocument(
        metadata,
        [cells for _, cells in trace_tables[0].rows],
        [cells for _, cells in case_tables[0].rows],
        [cells for _, cells in data_tables[0].rows] if data_tables else [],
    )


def id_set(text: str, prefix: str) -> set[str]:
    return set(_ids(text, prefix))


def refs_cell(value: str, prefix: str) -> set[str]:
    raw = clean_cell(value)
    if raw == "无":
        return set()
    return id_set(raw, prefix)


def normalize_ref_cell(value: str, prefix: str) -> str:
    refs = sorted(refs_cell(value, prefix))
    return "、".join(refs) if refs else "无"


def sql_refs_in_cell(value: str) -> set[str]:
    return set(SQL_REF_RE.findall(value or ""))


def sql_registry_digest(case_dir: Path) -> str:
    registry = registry_manifest(case_dir)
    return sha256_text(
        json.dumps(registry, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def parse_case_variables(value: str, label: str) -> dict[str, tuple[str, str]]:
    raw = clean_cell(value)
    if raw == "无":
        return {}
    if not raw:
        raise WorkflowError(f"{label} must use `无` when no data variable applies")
    result: dict[str, tuple[str, str]] = {}
    fields: set[str] = set()
    parts = [item.strip() for item in re.split(r"[；;]", raw) if item.strip()]
    for part in parts:
        matches = CASE_VARIABLE_RE.findall(part)
        if len(matches) != 1:
            raise WorkflowError(
                f"{label} each declaration must contain exactly one data variable such as $A; "
                "separate declarations with semicolons"
            )
        variable = matches[0]
        # The text before the variable is the human-readable field description.
        # Language, case, spacing, punctuation and naming style are intentionally
        # unconstrained; only a non-empty description is required.
        field = CASE_VARIABLE_RE.sub("", part, count=1).split("（", 1)[0].split("(", 1)[0]
        field = re.sub(r"[\s:=：＝]+$", "", field).strip()
        if not field:
            raise WorkflowError(f"{label} variable ${variable} must have a non-empty field description")
        example = ""
        if variable in result:
            raise WorkflowError(f"{label} repeats variable ${variable}")
        field_key = re.sub(r"\s+", " ", field).strip().casefold()
        if field_key in fields:
            raise WorkflowError(f"{label} repeats field {field}")
        fields.add(field_key)
        result[variable] = (field, example.strip())
    return result


def _require_precondition_layout(tc_id: str, precondition: str) -> None:
    if clean_cell(precondition) == "无":
        return
    lines = [clean_cell(item) for item in CELL_BREAK_RE.split(precondition)]
    if not lines or any(not line for line in lines):
        raise WorkflowError(f"{tc_id} 前置条件 contains an empty line")
    generic = {"准备测试数据", "准备相应数据", "按需准备", "数据正确", "准备成功", "同上"}
    current_category: str | None = None
    content_count = 0
    for line in lines:
        if re.match(r"^(?:\d+[.、]\s*)?[^：:<>{}|]{1,30}[：:]\S", line):
            raise WorkflowError(
                f"{tc_id} 前置条件 category name and content must be separated with <br>"
            )
        if PRECONDITION_CATEGORY_RE.fullmatch(line) is not None:
            if current_category is not None and content_count == 0:
                raise WorkflowError(
                    f"{tc_id} 前置条件 category `{current_category}` must contain a concrete description"
                )
            current_category = line
            content_count = 0
            continue
        normalized = re.sub(r"^\d+[.、]\s*", "", line).strip("；;。！？!?,， ")
        if len(normalized) < 2 or normalized in generic:
            raise WorkflowError(
                f"{tc_id} 前置条件 must contain a concrete executable description"
            )
        if MID_LINE_SENTENCE_RE.search(line):
            raise WorkflowError(
                f"{tc_id} 前置条件 contains multiple sentences on one line; "
                "separate completed sentences with <br>"
            )
        content_count += 1
    if current_category is not None and content_count == 0:
        raise WorkflowError(
            f"{tc_id} 前置条件 category `{current_category}` must contain a concrete description"
        )


def _require_numbered_expected_results(tc_id: str, expected: str) -> None:
    lines = [clean_cell(item) for item in CELL_BREAK_RE.split(expected)]
    if not lines or any(not line for line in lines):
        raise WorkflowError(f"{tc_id} 预期结果 contains an empty line")
    numbers: list[int] = []
    for line in lines:
        match = EXPECTED_ITEM_RE.match(line)
        if match is None:
            raise WorkflowError(
                f"{tc_id} 预期结果 each line must start with a numbered item such as `1. `"
            )
        numbers.append(int(match.group(1)))
    expected_numbers = list(range(1, len(lines) + 1))
    if numbers != expected_numbers:
        raise WorkflowError(
            f"{tc_id} 预期结果 numbering must be contiguous from 1; "
            f"expected={expected_numbers}, found={numbers}"
        )


def _require_numbered_steps(tc_id: str, steps: str) -> int:
    lines = [clean_cell(item) for item in CELL_BREAK_RE.split(steps)]
    if not lines or any(not line for line in lines):
        raise WorkflowError(f"{tc_id} 执行步骤 contains an empty line")
    numbers: list[int] = []
    for line in lines:
        match = STEP_ITEM_RE.match(line)
        if match is None:
            raise WorkflowError(
                f"{tc_id} 执行步骤 each line must start with a numbered item such as `1. `"
            )
        numbers.append(int(match.group(1)))
    expected_numbers = list(range(1, len(lines) + 1))
    if numbers != expected_numbers:
        raise WorkflowError(
            f"{tc_id} 执行步骤 numbering must be contiguous from 1; "
            f"expected={expected_numbers}, found={numbers}"
        )
    return len(lines)


def _require_case_execution_quality(
    tc_id: str,
    case: list[str],
    sql_ids: set[str],
    registry,
) -> None:
    variables = parse_case_variables(case[4], f"{tc_id} 数据变量")
    precondition = clean_cell(case[5])
    steps = clean_cell(case[6])
    expected = clean_cell(case[8])
    prose = {"前置条件": precondition, "执行步骤": steps, "预期结果": expected}
    used_by_section = {
        label: set(CASE_VARIABLE_RE.findall(text)) for label, text in prose.items()
    }
    undeclared = set().union(*used_by_section.values()) - set(variables)
    if undeclared:
        raise WorkflowError(f"{tc_id} uses undeclared data variables: {sorted(undeclared)}")
    for variable in variables:
        if variable not in used_by_section["前置条件"] | used_by_section["执行步骤"]:
            raise WorkflowError(
                f"{tc_id} data variable ${variable} must be used in 前置条件 or 执行步骤"
            )
    _require_precondition_layout(tc_id, precondition)
    step_count = _require_numbered_steps(tc_id, steps)
    _require_numbered_expected_results(tc_id, expected)
    expected_count = len(CELL_BREAK_RE.split(expected))
    if step_count != expected_count:
        raise WorkflowError(
            f"{tc_id} 执行步骤 and 预期结果 must correspond one-to-one; "
            f"steps={step_count}, expected={expected_count}"
        )
    combined = f"{precondition}\n{steps}\n{expected}"
    for phrase in FORBIDDEN_CASE_PROSE:
        if phrase in combined:
            raise WorkflowError(
                f"{tc_id} contains non-executable internal placeholder prose: {phrase}"
            )
    if not sql_ids:
        return
    if "一致" not in expected:
        raise WorkflowError(f"{tc_id} SQL-backed expected result must state the comparison as `一致`")
    select_ids = {sql_id for sql_id in sql_ids if registry[sql_id].statement_type == "SELECT"}
    if not select_ids:
        raise WorkflowError(f"{tc_id} must reference at least one SELECT SQL for manual result comparison")
    for sql_id in select_ids:
        filename = registry[sql_id].path.name
        if sql_id not in steps or filename not in steps:
            raise WorkflowError(f"{tc_id} steps must reference {sql_id} and {filename}")
        if sql_id not in expected:
            raise WorkflowError(f"{tc_id} expected result must reference {sql_id}")
    for sql_id in sql_ids:
        asset = registry[sql_id]
        if asset.statement_type != "SELECT" and (
            sql_id not in precondition or asset.path.name not in precondition
        ):
            raise WorkflowError(
                f"{tc_id} must reference preparation SQL {sql_id} and {asset.path.name} in 前置条件"
            )
        for parameter in asset.parameters:
            if parameter.name not in variables:
                raise WorkflowError(
                    f"{tc_id} SQL parameter :{parameter.name} lacks same-name data variable ${parameter.name}"
                )
            binding = f":{parameter.name}=${parameter.name}"
            target = steps if asset.statement_type == "SELECT" else precondition
            if binding not in target:
                raise WorkflowError(f"{tc_id} must state SQL binding `{binding}`")
            # manifest example is used solely to bind an executable value for SQL EXPLAIN.
            # A test case's example describes its own isolated scenario and can legitimately
            # differ, especially when a shared case reads the same entity through multiple
            # SQL assets whose EXPLAIN examples were established by earlier TPs.


def _require_data_execution_rows(model, trace_data: dict[str, tuple[set[str], set[str]]],
                                 rows: list[list[str]], registry) -> dict[str, set[str]]:
    profile_owners = all_profile_owners(model)
    seen: set[tuple[str, str, str]] = set()
    covered_by_tc: dict[str, set[tuple[str, str]]] = {}
    sql_by_tc: dict[str, set[str]] = {}
    for row in rows:
        if len(row) != len(DATA_EXECUTION_HEADERS):
            raise WorkflowError("data-closure execution row has the wrong column count")
        tc_id = clean_cell(row[0])
        dc_id = clean_cell(row[1])
        dp_id = clean_cell(row[2])
        key = (tc_id, dc_id, dp_id)
        if key in seen:
            raise WorkflowError(f"duplicate data-closure execution row: {key}")
        seen.add(key)
        if tc_id not in trace_data:
            raise WorkflowError(f"data-closure execution row references unknown TC-ID: {tc_id}")
        trace_dcs, trace_dps = trace_data[tc_id]
        if dc_id not in trace_dcs:
            raise WorkflowError(f"{tc_id} data execution DC-ID is outside its trace: {dc_id}")
        if dp_id not in trace_dps:
            raise WorkflowError(f"{tc_id} data execution DP-ID is outside its trace: {dp_id}")
        if dc_id not in profile_owners.get(dp_id, set()):
            raise WorkflowError(f"{tc_id} data execution DP-ID {dp_id} is not owned by {dc_id}")
        sql_ids = sql_refs_in_cell(row[3])
        if not sql_ids:
            raise WorkflowError(f"{tc_id} data-closure execution row must reference reusable SQL assets")
        unknown_sql = sql_ids - set(registry)
        if unknown_sql:
            raise WorkflowError(f"{tc_id} references unknown SQL assets: {sorted(unknown_sql)}")
        if not any(registry[sql_id].statement_type == "SELECT" for sql_id in sql_ids):
            raise WorkflowError(f"{tc_id} data execution must include a SELECT SQL for result comparison")
        for sql_id in sql_ids:
            if dc_id not in registry[sql_id].data_closure_refs:
                raise WorkflowError(f"{tc_id} SQL asset {sql_id} is not registered for {dc_id}")
        for index, cell in enumerate(row[4:], start=5):
            value = clean_cell(cell)
            if not value or value == "无":
                raise WorkflowError(
                    f"{tc_id} data-closure execution row has no executable value at column {index}"
                )
        query_entry = clean_cell(row[4])
        preparation = clean_cell(row[6])
        dynamic_expected = clean_cell(row[7])
        for sql_id in sql_ids:
            asset = registry[sql_id]
            target = query_entry if asset.statement_type == "SELECT" else preparation
            if sql_id not in target or asset.path.name not in target:
                role = "查询/验证入口" if asset.statement_type == "SELECT" else "准备或变更动作"
                raise WorkflowError(
                    f"{tc_id} {role} must reference {sql_id} and {asset.path.name}"
                )
            if asset.statement_type == "SELECT" and sql_id not in dynamic_expected:
                raise WorkflowError(f"{tc_id} dynamic expected must reference SELECT asset {sql_id}")
        covered_by_tc.setdefault(tc_id, set()).add((dc_id, dp_id))
        sql_by_tc.setdefault(tc_id, set()).update(sql_ids)
    for tc_id, (dcs, dps) in trace_data.items():
        pairs = covered_by_tc.get(tc_id, set())
        for dc_id in dcs:
            if not any(pair[0] == dc_id for pair in pairs):
                raise WorkflowError(f"{tc_id} lacks an execution plan for data closure {dc_id}")
        for dp_id in dps:
            if not any(pair[1] == dp_id for pair in pairs):
                raise WorkflowError(f"{tc_id} lacks an execution plan for data profile {dp_id}")
    return sql_by_tc


MULTI_CASE_JUSTIFICATION_FIELDS = (
    "独立业务风险",
    "不可合并前置或操作",
    "独立可判断预期",
    "独立回归价值",
)


def _require_multi_case_justifications(trace_rows: list[list[str]]) -> None:
    """Require auditable reasons only when one TP is expanded into multiple cases."""
    if len(trace_rows) <= 1:
        return
    for trace in trace_rows:
        tc_id = clean_cell(trace[0]) if trace else "unknown TC"
        explanation = clean_cell(trace[8]) if len(trace) > 8 else ""
        missing: list[str] = []
        for field in MULTI_CASE_JUSTIFICATION_FIELDS:
            match = re.search(
                rf"(?:^|[；;])\s*{re.escape(field)}\s*=\s*([^；;]+)",
                explanation,
            )
            if not match or clean_cell(match.group(1)) in {"", "无", "不适用", "N/A", "n/a"}:
                missing.append(field)
        if missing:
            required = "；".join(f"{field}=..." for field in MULTI_CASE_JUSTIFICATION_FIELDS)
            raise WorkflowError(
                f"{tc_id} belongs to a multi-case TP and must justify every split with "
                f"'{required}'; missing or empty: {missing}"
            )


def validate_case_rows(model, tp: TestPoint, input_hash: str, path: Path,
                       ciq_refs: tuple[str, ...] = (), db_config_path: Path | None = None,
                       planned_sql_refs: tuple[str, ...] | None = None,
                       validate_sql_now: bool = True):
    """Validate one TP's complete, traceable test-case expansion.

    The case author may choose a subset of source questions and dynamic resources
    per scenario, but every row must prove that the fixed global/module/logic
    context was carried into that generation. Database facts are deliberately
    closed: a case cannot cite a profile without its owning closure, and a case
    can only use SQL assigned by the validated module plan.
    """
    document = parse_case_document(path, False)
    metadata = document.metadata
    trace_rows = document.trace_rows
    case_rows = document.case_rows
    if metadata.get("TP-ID") != tp.tp_id:
        raise WorkflowError(f"{path} metadata TP-ID does not match {tp.tp_id}")
    if metadata.get("输入 SHA-256") != input_hash:
        raise WorkflowError(f"{path} uses stale input SHA-256")
    if metadata.get("生成结果") != "validated":
        raise WorkflowError(f"{path} metadata 生成结果 must be validated")
    if not trace_rows or not case_rows or len(trace_rows) != len(case_rows):
        raise WorkflowError(f"{path} trace rows and testcase rows must be non-empty and have equal counts")

    required_fixed = {"SRC-GLOBAL", "SRC-MOD", "CTX"}
    if not required_fixed <= set(model.resources):
        missing = sorted(required_fixed - set(model.resources))
        raise WorkflowError(f"upstream module resources are missing required fixed context: {missing}")

    allowed_rsus = set(tp.source_rsus)
    allowed_questions = set(tp.question_refs) | set(ciq_refs)
    allowed_context = allowed_context_ids(model, tp)
    allowed_dc = set(tp.data_closure_refs)
    profile_owners = all_profile_owners(model) if model.data_closure_enabled else {}
    expected_prefix = f"TC-TP-{tp.tp_id[-3:]}-"
    used_dc: set[str] = set()
    trace_data: dict[str, tuple[set[str], set[str]]] = {}

    cases_by_id: dict[str, list[str]] = {}
    for position, (trace, case) in enumerate(zip(trace_rows, case_rows), start=1):
        if len(trace) != len(TRACE_HEADERS):
            raise WorkflowError(f"trace row {position} has the wrong column count")
        if len(case) != len(CASE_HEADERS):
            raise WorkflowError(f"standard testcase row {position} has the wrong column count")
        tc_id = clean_cell(trace[0])
        expected_tc_id = f"{expected_prefix}{position:03d}"
        if tc_id != expected_tc_id:
            raise WorkflowError(f"expected contiguous TC-ID {expected_tc_id}, found {tc_id or 'empty'}")
        if clean_cell(trace[1]) in {"", "无"}:
            raise WorkflowError(f"{tc_id} must state a concrete 覆盖场景")
        if clean_cell(trace[2]) != tp.tp_id:
            raise WorkflowError(f"{tc_id} trace TP-ID must be {tp.tp_id}")
        if clean_cell(trace[8]) in {"", "无"}:
            raise WorkflowError(f"{tc_id} must state a concrete 用例设计说明")
        if clean_cell(case[0]) != tc_id:
            raise WorkflowError(f"standard testcase row must start with {tc_id}")
        cases_by_id[tc_id] = case

        rsus = _strict_refs(trace[3], refs_cell(trace[3], "RSU"), f"{tc_id} RSU Refs")
        questions = _strict_refs(trace[4], question_refs_in_cell(trace[4]), f"{tc_id} Question Refs")
        contexts = _strict_refs(
            trace[5], _resource_ids(trace[5], set(model.resources)), f"{tc_id} Context Refs"
        )
        dcs = _strict_refs(trace[6], refs_cell(trace[6], "DC"), f"{tc_id} Data Closure Refs")
        dps = _strict_refs(trace[7], refs_cell(trace[7], "DP"), f"{tc_id} Data Profile Refs")

        if not rsus or not rsus <= allowed_rsus:
            raise WorkflowError(f"{tc_id} has RSU refs outside current TP")
        if questions - allowed_questions:
            raise WorkflowError(
                f"{tc_id} has Question Refs outside current TP: {sorted(questions - allowed_questions)}"
            )
        if contexts - allowed_context:
            raise WorkflowError(
                f"{tc_id} has Context Refs outside current TP: {sorted(contexts - allowed_context)}"
            )
        if not required_fixed <= contexts:
            missing = sorted(required_fixed - contexts)
            raise WorkflowError(f"{tc_id} must retain fixed context refs: {missing}")
        if dcs - allowed_dc:
            raise WorkflowError(
                f"{tc_id} has Data Closure Refs outside current TP: {sorted(dcs - allowed_dc)}"
            )
        if not model.data_closure_enabled:
            if dcs or dps:
                raise WorkflowError(f"{tc_id} must not invent database refs for a module without data closures")
        else:
            if dps and not dcs:
                raise WorkflowError(f"{tc_id} cannot cite Data Profile Refs without Data Closure Refs")
            if any(dc not in contexts for dc in dcs):
                raise WorkflowError(f"{tc_id} Data Closure Refs must also be Context Refs")
            for dp in dps:
                if dp not in profile_owners or not (profile_owners[dp] & dcs):
                    raise WorkflowError(f"{tc_id} Data Profile {dp} is not owned by its DC refs")

        if dcs:
            trace_data[tc_id] = (dcs, dps)
        used_dc.update(dcs)
        for index, cell in enumerate(case[1:], start=2):
            if not clean_cell(cell):
                raise WorkflowError(f"{tc_id} has an empty testcase cell at column {index}")

    _require_multi_case_justifications(trace_rows)

    if used_dc != allowed_dc:
        raise WorkflowError(
            f"case DC coverage must equal TP DC refs; expected={sorted(allowed_dc)}, found={sorted(used_dc)}"
        )
    actual_sql_by_tc = {
        tc_id: sql_refs_in_cell("\n".join((case[5], case[6], case[8])))
        for tc_id, case in cases_by_id.items()
    }
    actual_sql_refs = set().union(*actual_sql_by_tc.values()) if actual_sql_by_tc else set()
    expected_sql_refs = set(planned_sql_refs or ())
    if actual_sql_refs != expected_sql_refs:
        raise WorkflowError(
            f"{tp.tp_id} SQL refs must exactly match the validated module plan; "
            f"expected={sorted(expected_sql_refs)}, found={sorted(actual_sql_refs)}"
        )
    if actual_sql_refs:
        try:
            registry = load_registry(path.parent.parent)
        except SqlAssetError as exc:
            raise WorkflowError(str(exc)) from exc
        unknown_sql = actual_sql_refs - set(registry)
        if unknown_sql:
            raise WorkflowError(f"{tp.tp_id} references unknown SQL assets: {sorted(unknown_sql)}")
        for tc_id, sql_ids in actual_sql_by_tc.items():
            _require_case_execution_quality(tc_id, cases_by_id[tc_id], sql_ids, registry)
        report = None
        if validate_sql_now:
            try:
                report = validate_assets(
                    path.parent.parent,
                    model.module_dir,
                    db_config_path=db_config_path,
                    required_sql_ids=sorted(actual_sql_refs),
                )
            except SqlAssetError as exc:
                raise WorkflowError(str(exc)) from exc
        return len(trace_rows), sha256_file(path), report
    for tc_id, case in cases_by_id.items():
        _require_case_execution_quality(tc_id, case, set(), {})
    return len(trace_rows), sha256_file(path), None


def current_record(state: dict, tp_id: str) -> dict:
    for item in state.get("tps", []):
        if item.get("tp_id") == tp_id:
            return item
    raise WorkflowError(f"unknown TP-ID in generation state: {tp_id}")


def next_pending(state: dict) -> dict | None:
    return next((item for item in state.get("tps", []) if item.get("status") != "validated"), None)


FINAL_TRACE_HEADERS = (
    "Final TC-ID", "Source TC-IDs", "TP Refs", "RSU Refs", "Question Refs",
    "Context Refs", "Data Closure Refs", "Data Profile Refs", "归并说明",
)
FINAL_DATA_EXECUTION_HEADERS = (
    "Final TC-ID", "Source TC-IDs", "DC-ID", "DP-ID", "SQL Refs", "查询/验证入口", "目标数据状态",
    "准备或变更动作", "动态预期推导", "清理/隔离",
)
COVERAGE_HEADERS = ("TP-ID", "Final TC Refs", "状态", "说明")


def load_template(name: str, values: dict[str, str]) -> str:
    """Render a template stored with this skill, not its upstream sibling."""
    path = SKILL_DIR / "assets" / "templates" / name
    if not path.is_file():
        raise WorkflowError(f"skill template is missing: {path}")
    text = read_text(path)
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    return text


def data_execution_section(final: bool = False) -> str:
    headers = FINAL_DATA_EXECUTION_HEADERS if final else DATA_EXECUTION_HEADERS
    heading = "## 模块数据闭包执行计划" if final else "## 数据闭包执行计划"
    return f"{heading}\n\n{markdown_table(headers, [])}"


def case_document_template(tp_id: str, input_sha256: str, has_data_closure: bool) -> str:
    return load_template(
        "tp-test-cases.md.tmpl",
        {
            "TP_ID": tp_id,
            "INPUT_SHA256": input_sha256,
            "DATA_EXECUTION_SECTION": "",
        },
    )


def module_case_document_template(module_name: str, input_sha256: str, has_data_closure: bool) -> str:
    return load_template(
        "module-test-cases.md.tmpl",
        {
            "MODULE_NAME": module_name,
            "FINAL_INPUT_SHA256": input_sha256,
            "DATA_EXECUTION_SECTION": "",
        },
    )


def coverage_matrix_template(module_name: str, points: list[TestPoint]) -> str:
    rows = "\n".join(
        f"| {point.tp_id} | 待填写 | 待填写 | 待填写 |" for point in points
    )
    return load_template(
        "coverage-matrix.md.tmpl",
        {"MODULE_NAME": module_name, "COVERAGE_ROWS": rows},
    )


def render_execution_context(module_name: str, readiness: CaseReadiness) -> str:
    rows: list[str] = []
    for ciq_id, cells in readiness.questions.items():
        source_status = clean_cell(cells[6])
        if source_status == "answered":
            value, status = clean_cell(cells[5]), "ready"
        elif source_status == "not-needed":
            value, status = "无", "not-needed"
        else:
            value, status = "请填写安全的环境别名、样本定位方法或资料入口", "pending"
        rows.append(
            "| {key} | {category} | {ref} | {value} | {evidence} | {status} |".format(
                key=ciq_id,
                category=clean_cell(cells[1]),
                ref=ciq_id,
                value=value,
                evidence=clean_cell(cells[4]),
                status=status,
            )
        )
    if not rows:
        rows.append("| EC-001 | module | 无 | 本模块无额外执行上下文 | 上游就绪性审查 | not-needed |")
    return load_template(
        "execution-context.md.tmpl",
        {"MODULE_NAME": module_name, "CONTEXT_ROWS": "\n".join(rows)},
    )


def allowed_context_ids(model, tp: TestPoint) -> set[str]:
    allowed = set(model.fixed_resource_ids) | set(tp.context_refs) | set(tp.data_closure_refs)
    if tp.data_closure_refs and "DC-INDEX" in model.resources:
        allowed.add("DC-INDEX")
    return allowed


def question_refs_in_cell(value: str) -> set[str]:
    return set(re.findall(r"\b(?:Q|CIQ)-\d{3}\b", value or ""))


def _strict_refs(value: str, refs: Iterable[str], label: str) -> set[str]:
    parsed = set(refs)
    raw = clean_cell(value)
    if not raw:
        raise WorkflowError(f"{label} must use `无` when no reference applies")
    if raw == "无":
        return set()
    if not parsed:
        raise WorkflowError(f"{label} has malformed references: {raw}")
    return parsed


def source_hashes(model, final_hash: str, readiness_hash: str, context_hash: str) -> dict[str, str | None]:
    return {
        "manifest_sha256": model.manifest_sha256,
        "module_test_points_sha256": final_hash,
        "case_readiness_sha256": readiness_hash,
        "execution_context_sha256": context_hash,
    }


def assert_source_hashes(state: dict, current: dict[str, str | None]) -> None:
    assert_case_state_schema(state)
    if state.get("source_hashes") != current:
        raise WorkflowError("upstream artifact or execution context changed; rerun init_generation.py --refresh")


def ensure_upstream_validation(points_dir: Path, final_hash: str, readiness_hash: str) -> dict:
    upstream_state = load_json(points_dir / UPSTREAM_STATE_NAME)
    finalization = upstream_state.get("finalization", {})
    readiness = upstream_state.get("case_readiness", {})
    if finalization.get("status") != "validated":
        raise WorkflowError("upstream module test points are not validated")
    if finalization.get("module_test_points_sha256") != final_hash:
        raise WorkflowError("module-test-points.md changed after upstream validation")
    if readiness.get("status") != "validated":
        raise WorkflowError("upstream case readiness is not validated")
    if readiness.get("output_sha256") != readiness_hash:
        raise WorkflowError("test-case-readiness.md changed after upstream validation")
    return upstream_state


def _archive_paths(case_dir: Path, paths: list[Path], reason: str) -> Path | None:
    """Move generated artifacts aside without touching execution context or history."""
    existing = [path for path in paths if path.exists()]
    if not existing:
        return None
    marker = sha256_text(reason)[:12]
    stamp = utc_now().replace(":", "").replace("+", "_").replace("-", "")
    destination = case_dir / "history" / f"{stamp}-{marker}"
    destination.mkdir(parents=True, exist_ok=False)
    for path in existing:
        shutil.move(str(path), str(destination / path.name))
    ensure_dirs(case_dir)
    return destination


def archive_generated_artifacts(case_dir: Path, reason: str) -> Path | None:
    """Archive all generated work while preserving manual execution context."""
    return _archive_paths(
        case_dir,
        [
            case_dir / "inputs",
            case_dir / "session-inputs",
            case_dir / "baselines",
            case_dir / "by-tp",
            case_dir / "by-batch",
            case_dir / "sql",
            case_dir / "planning-input.md",
            case_dir / "generation-plan.json",
            case_dir / "sql-generation-input.md",
            case_dir / "finalization-input.md",
            case_dir / "module-test-cases.md",
            case_dir / "coverage-matrix.md",
        ],
        reason,
    )


def archive_finalization_artifacts(case_dir: Path, reason: str) -> Path | None:
    """Archive only module-consolidation artifacts after source TP cases change."""
    return _archive_paths(
        case_dir,
        [
            case_dir / "finalization-input.md",
            case_dir / "module-test-cases.md",
            case_dir / "coverage-matrix.md",
        ],
        reason,
    )


def parse_module_case_document(path: Path, require_data_execution: bool) -> CaseDocument:
    text = read_text(path)
    require_no_placeholders(text, str(path))
    metadata = parse_metadata_table(text)
    tables = extract_tables(text)
    trace_tables = find_tables(tables, FINAL_TRACE_HEADERS)
    canonical_case_tables = find_tables(tables, CASE_HEADERS)
    legacy_case_tables = find_tables(tables, LEGACY_CASE_HEADERS)
    case_tables = canonical_case_tables or legacy_case_tables
    data_tables = find_tables(tables, FINAL_DATA_EXECUTION_HEADERS)
    if len(trace_tables) != 1:
        raise WorkflowError(f"{path} must contain exactly one module trace table")
    if len(case_tables) != 1:
        raise WorkflowError(f"{path} must contain exactly one standard testcase table")
    if require_data_execution and len(data_tables) != 1:
        raise WorkflowError(f"{path} must contain exactly one module data-closure execution table")
    if not require_data_execution and data_tables:
        raise WorkflowError(f"{path} must not contain a module data-closure execution table")
    return CaseDocument(
        metadata,
        [cells for _, cells in trace_tables[0].rows],
        [cells for _, cells in case_tables[0].rows],
        [cells for _, cells in data_tables[0].rows] if data_tables else [],
    )


def parse_coverage_matrix(path: Path) -> list[list[str]]:
    text = read_text(path)
    require_no_placeholders(text, str(path))
    tables = find_tables(extract_tables(text), COVERAGE_HEADERS)
    if len(tables) != 1:
        raise WorkflowError(f"{path} must contain exactly one coverage matrix")
    return [cells for _, cells in tables[0].rows]


def source_case_documents(case_dir: Path, points: list[TestPoint], state: dict) -> dict[str, tuple[TestPoint, CaseDocument]]:
    result: dict[str, tuple[TestPoint, CaseDocument]] = {}
    try:
        registry = load_registry(case_dir)
    except SqlAssetError as exc:
        raise WorkflowError(str(exc)) from exc
    for point in points:
        record = current_record(state, point.tp_id)
        if record.get("status") != "validated":
            raise WorkflowError(f"{point.tp_id} is not validated")
        _, path = output_paths(case_dir, point.tp_id)
        if not path.is_file():
            raise WorkflowError(f"validated TP output is missing: {path}")
        if record.get("output_sha256") != sha256_file(path):
            raise WorkflowError(f"{point.tp_id} output changed after validation; refresh the workspace")
        document = parse_case_document(path, False)
        if document.metadata.get("生成结果") != "validated":
            raise WorkflowError(f"{point.tp_id} output is no longer marked validated")
        document_sql_refs = sorted(
            {
                sql_id
                for case_row in document.case_rows
                for sql_id in sql_refs_in_cell("\n".join((case_row[5], case_row[6], case_row[8])))
            }
        )
        if sorted(record.get("sql_refs", [])) != document_sql_refs:
            raise WorkflowError(
                f"{point.tp_id} SQL refs no longer match its validated state; "
                "rerun init_generation.py --refresh"
            )
        changed = [sql_id for sql_id in document_sql_refs if sql_id not in registry]
        if changed:
            raise WorkflowError(
                f"{point.tp_id} referenced SQL assets changed after validation: {sorted(changed)}; "
                "rerun init_generation.py --refresh"
            )
        for row in document.trace_rows:
            tc_id = clean_cell(row[0])
            if tc_id in result:
                raise WorkflowError(f"duplicate source TC-ID across TP outputs: {tc_id}")
            result[tc_id] = (point, document)
    return result

def build_finalization_manifest(case_dir: Path, points: list[TestPoint], state: dict) -> tuple[dict, str]:
    """Return the deterministic source contract for module-case consolidation.

    The manifest deliberately pins the current upstream hashes together with each
    validated TP output. It is the only digest accepted by module finalization,
    so an edited source case cannot silently survive module consolidation and validation.
    """
    source_case_documents(case_dir, points, state)
    entries: list[dict] = []
    for point in points:
        record = current_record(state, point.tp_id)
        _, output = output_paths(case_dir, point.tp_id)
        document = parse_case_document(output, False)
        source_ids = [clean_cell(row[0]) for row in document.trace_rows]
        if record.get("case_count") != len(source_ids):
            raise WorkflowError(
                f"{point.tp_id} case count in generation state does not match its testcase output"
            )
        entries.append(
            {
                "tp_id": point.tp_id,
                "order": point.order,
                "input_sha256": record.get("input_sha256"),
                "output_file": output.relative_to(case_dir).as_posix(),
                "output_sha256": record.get("output_sha256"),
                "case_count": len(source_ids),
                "source_tc_ids": source_ids,
                "sql_refs": sorted(record.get("sql_refs", [])),
            }
        )
    try:
        sql_registry = registry_manifest(case_dir)
    except SqlAssetError as exc:
        raise WorkflowError(str(exc)) from exc
    manifest = {
        "schema_version": FINALIZATION_SCHEMA_VERSION,
        "source_hashes": state.get("source_hashes"),
        "tps": entries,
        "sql_registry": sql_registry,
    }
    digest = sha256_text(
        json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )
    return manifest, digest
