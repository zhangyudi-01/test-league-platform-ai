#!/usr/bin/env python3
"""Shared parsing, materialization, state, and validation helpers."""

from __future__ import annotations

import hashlib
import html
import json
import os
import re
import subprocess
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator
from urllib.parse import quote, unquote

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = SKILL_DIR / "assets" / "templates"
BT = chr(96)
TEXT_SUFFIXES = {".md", ".txt", ".rst", ".csv", ".json", ".yaml", ".yml", ".xml", ".html"}
MANIFEST_NAME = "preanalysis-manifest.json"
MANIFEST_SCHEMA = "preanalysis/v1"
ARTIFACT_KEYS = {
    "readme": "README.md",
    "module_requirement": "00-module-requirement-pack.md",
    "context_pack": "01-context-pack.md",
    "rsu_map": "02-sentence-test-point-map.md",
    "clarifications": "03-clarification-questions.md",
    "context_card_index": "context-cards/README.md",
}
RESOURCE_ROLE_KEYS = ("global_context", "module_requirement", "module_context")
LEGACY_RESOURCE_ROLES = {
    "global_context": "SRC-GLOBAL",
    "module_requirement": "SRC-MOD",
    "module_context": "CTX",
}
LEGACY_PREANALYSIS_REQUIRED_FILES = (
    "README.md",
    "00-module-requirement-pack.md",
    "01-context-pack.md",
    "02-sentence-test-point-map.md",
    "03-clarification-questions.md",
    "context-cards/README.md",
)
RSU_HEADERS = (
    "RSU-ID", "父级条件（原文）", "原文内容", "来源", "来源定位", "相关上下文", "相关问题", "状态",
)
RESOURCE_HEADERS = ("资源 ID", "可点击文件", "定位用途")
DATA_CLOSURE_INDEX_HEADERS = (
    "DC-ID", "业务数据闭包", "可点击文件", "状态", "关联 RSU", "来源资源",
)
ANSWERED_Q_HEADERS = ("Q-ID", "关联原文/上下文", "状态", "人工确认结论", "回填结果")
PENDING_Q_HEADERS = ("Q-ID", "关联来源", "状态", "问题", "未确认时的处理")
LEGACY_CANDIDATE_HEADERS = (
    "候选 ID", "Primary RSU", "Source RSUs", "测试维度", "测试点", "可观察结果",
    "Question Refs", "Context Refs", "推导依据",
)
LEGACY_CANDIDATE_DATA_CLOSURE_HEADERS = (
    "候选 ID", "Primary RSU", "Source RSUs", "测试维度", "测试点", "可观察结果",
    "Question Refs", "Context Refs", "Data Closure Refs", "推导依据",
)
LEGACY_FINAL_HEADERS = (
    "TP-ID", "Primary RSU", "Source RSUs", "测试维度", "测试点", "可观察结果",
    "Question Refs", "Context Refs", "Source Candidates", "合并或保留依据",
)
LEGACY_FINAL_DATA_CLOSURE_HEADERS = (
    "TP-ID", "Primary RSU", "Source RSUs", "测试维度", "测试点", "可观察结果",
    "Question Refs", "Context Refs", "Data Closure Refs", "Source Candidates", "合并或保留依据",
)
CANDIDATE_HEADERS = (
    "候选 ID", "Primary RSU", "Source RSUs", "测试项", "测试点", "备注",
    "Question Refs", "Context Refs", "推导依据",
)
CANDIDATE_DATA_CLOSURE_HEADERS = (
    "候选 ID", "Primary RSU", "Source RSUs", "测试项", "测试点", "备注",
    "Question Refs", "Context Refs", "Data Closure Refs", "推导依据",
)
FINAL_HEADERS = (
    "TP-ID", "Primary RSU", "Source RSUs", "测试项", "测试点", "备注",
    "Question Refs", "Context Refs", "Source Candidates", "合并或保留依据",
)
FINAL_DATA_CLOSURE_HEADERS = (
    "TP-ID", "Primary RSU", "Source RSUs", "测试项", "测试点", "备注",
    "Question Refs", "Context Refs", "Data Closure Refs", "Source Candidates", "合并或保留依据",
)
RSU_COVERAGE_HEADERS = ("RSU-ID", "候选数", "Final TP Refs", "处理结果", "说明")
CANDIDATE_DISPOSITION_HEADERS = ("Candidate ID", "Source RSU", "处理结果", "Final TP Refs", "说明")
CLOSED_CASE_INPUT_HEADERS = ("输入主题", "已确认结论", "来源", "关联 TP")
TP_READINESS_HEADERS = ("TP-ID", "用例生成状态", "Input Question Refs", "说明")
TP_READINESS_DATA_CLOSURE_HEADERS = (
    "TP-ID", "用例生成状态", "Data Closure Refs", "Input Question Refs", "说明",
)
CASE_INPUT_QUESTION_HEADERS = (
    "CIQ-ID", "类型", "关联 TP", "待补充问题", "已有依据", "回填答案/资料", "状态",
)
UNRESOLVED_RE = re.compile(r"\{\{[A-Z0-9_]+\}\}|待填写|\bTODO\b|\bTBD\b", re.IGNORECASE)
PARENT_OBSERVABLE_ACTION_RE = re.compile(
    r"(?:生成|创建|新增|删除|作废|更新|修改|保存|提交|写入|发送|推送|上传|下载|导入|导出|"
    r"弹出|打开|关闭|进入|跳转|返回|展示|显示|提示|调用|启动|停止|取消)"
)
PARENT_CONDITION_ONLY_RE = re.compile(
    r"^.{1,120}(?:时|后|前|期间|情况下|条件下)[：，。；]?$"
)
PARENT_STATIC_STATE_ONLY_RE = re.compile(
    r"^(?:当|在)?[^，。；]{0,60}(?:状态|结果)为[^，。；]{1,60}(?:时)?[：，。；]?$"
)
CONTEXT_RESOURCE_INDEX_BEGIN = "<!-- BEGIN AUTO-GENERATED CONTEXT RESOURCE INDEX -->"
CONTEXT_RESOURCE_INDEX_END = "<!-- END AUTO-GENERATED CONTEXT RESOURCE INDEX -->"
DATA_OBSERVATION_RE = re.compile(
    r"(?:数据库|数据表|落库|持久化|事务|回滚|写入|新增记录|更新记录|删除记录|"
    r"SQL|SELECT|INSERT|UPDATE|DELETE|前后快照|孤立记录|半批次|原子性|"
    r"字段(?:值|映射)|\b[a-z][a-z0-9]*(?:_[a-z0-9]+){1,}\b)",
    re.IGNORECASE,
)
DATA_IDENTIFIER_RE = re.compile(r"(?<![A-Za-z0-9_])([A-Za-z][A-Za-z0-9]*(?:_[A-Za-z0-9]+)+)(?![A-Za-z0-9_])")


class WorkflowError(RuntimeError):
    pass


@dataclass(frozen=True)
class Table:
    headers: tuple[str, ...]
    rows: list[tuple[int, list[str]]]
    line: int


@dataclass(frozen=True)
class Resource:
    resource_id: str
    path: Path
    purpose: str
    line: int


@dataclass(frozen=True)
class RequirementUnit:
    rsu_id: str
    cells: tuple[str, ...]
    line: int
    order: int

    @property
    def source_id(self) -> str:
        return clean_cell(self.cells[3])

    @property
    def parent_text(self) -> str:
        return clean_cell(self.cells[1])

    @property
    def source_text(self) -> str:
        return clean_cell(self.cells[2])

    @property
    def source_location(self) -> str:
        return clean_cell(self.cells[4])

    @property
    def related_context(self) -> str:
        return self.cells[5]

    @property
    def related_questions(self) -> str:
        return self.cells[6]

    @property
    def source_status(self) -> str:
        return clean_cell(self.cells[7])


@dataclass(frozen=True)
class Question:
    q_id: str
    headers: tuple[str, ...]
    cells: tuple[str, ...]
    line: int

    @property
    def status(self) -> str:
        return clean_cell(self.cells[2])


@dataclass(frozen=True)
class Material:
    resource_id: str
    path: Path
    role: str
    content: str


@dataclass(frozen=True)
class EvidenceReference:
    resource_id: str
    path: Path
    purpose: str
    sha256: str


@dataclass
class ModuleLayout:
    module_dir: Path
    preanalysis_dir: Path
    manifest_path: Path | None
    artifact_paths: dict[str, Path]
    resource_roles: dict[str, str]
    default_output_dir: Path


@dataclass
class ModuleModel:
    module_dir: Path
    preanalysis_dir: Path
    manifest_path: Path | None
    manifest_sha256: str | None
    artifact_paths: dict[str, Path]
    resource_roles: dict[str, str]
    module_name: str
    map_path: Path
    question_path: Path
    resources: dict[str, Resource]
    rsus: list[RequirementUnit]
    rsu_by_id: dict[str, RequirementUnit]
    questions: dict[str, Question]

    @property
    def fixed_resource_ids(self) -> tuple[str, str, str]:
        return tuple(self.resource_roles[key] for key in RESOURCE_ROLE_KEYS)

    @property
    def data_closure_ids(self) -> tuple[str, ...]:
        return tuple(
            resource_id
            for resource_id in self.resources
            if re.fullmatch(r"DC-\d{3}", resource_id)
        )

    @property
    def data_closure_enabled(self) -> bool:
        return "DC-INDEX" in self.resources or bool(self.data_closure_ids)

    @property
    def data_closure_statuses(self) -> dict[str, str]:
        if not self.data_closure_enabled:
            return {}
        index = self.resources.get("DC-INDEX")
        if index is None or not index.path.is_file():
            raise WorkflowError("data closures are enabled but DC-INDEX is unavailable")
        tables = find_tables(extract_tables(read_text(index.path)), DATA_CLOSURE_INDEX_HEADERS)
        if len(tables) != 1:
            raise WorkflowError("DC-INDEX must contain exactly one fixed closure-index table")
        statuses = {clean_cell(cells[0]): clean_cell(cells[3]) for _, cells in tables[0].rows}
        if set(statuses) != set(self.data_closure_ids):
            raise WorkflowError("DC-INDEX card set does not match map data-closure resources")
        return statuses


@dataclass
class InputBundle:
    rsu: RequirementUnit
    input_sha256: str
    blockers: list[str]
    allowed_rsu_ids: list[str]
    allowed_q_ids: list[str]
    allowed_context_ids: list[str]
    required_context_ids: list[str]
    fixed_materials: list[Material]
    dynamic_materials: list[Material]
    evidence_materials: list[EvidenceReference]
    supporting_rsus: list[RequirementUnit]
    questions: list[Question]
    rendered: str
    session_rendered: str
    session_input_sha256: str
    session_source_fingerprint_sha256: str


@dataclass
class CandidateDocument:
    rsu_id: str
    input_sha256: str
    result: str
    rows: list[list[str]]
    zero_reason: str
    headers: tuple[str, ...]


@dataclass
class FinalDocument:
    input_sha256: str
    rows: list[list[str]]
    headers: tuple[str, ...]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def clean_cell(value: str) -> str:
    return value.strip().strip(BT).strip()


def requires_data_closure(text: str) -> bool:
    """Identify explicit persistence/schema assertions, not generic business data wording."""

    return DATA_OBSERVATION_RE.search(clean_cell(text)) is not None


def infer_required_data_closures(text: str, materials: list[Material]) -> set[str]:
    """Map explicit schema identifiers to the unique materialized DC that defines them."""

    identifiers = {item.lower() for item in DATA_IDENTIFIER_RE.findall(clean_cell(text))}
    required: set[str] = set()
    closure_text = {
        material.resource_id: material.content.lower()
        for material in materials
        if re.fullmatch(r"DC-\d{3}", material.resource_id)
    }
    for identifier in identifiers:
        matches = {
            resource_id
            for resource_id, content in closure_text.items()
            if re.search(rf"(?<![A-Za-z0-9_]){re.escape(identifier)}(?![A-Za-z0-9_])", content)
        }
        if len(matches) == 1:
            required.update(matches)
    return required


def normalize_requirement_text(text: str) -> str:
    value = html.unescape(text).replace("\u00a0", " ")
    value = re.sub(r"!?(?:\[([^\]]+)\])\([^)]*\)", r"\1", value)
    value = re.sub(r"</?[A-Za-z][^>]*>", "", value)
    value = re.sub(r"\\([\\`*_{}\[\]()#+.!|>-])", r"\1", value)
    value = value.replace("~~", "").replace("**", "").replace("*", "").replace(BT, "")
    return re.sub(r"\s+", "", value).strip()


def parent_has_observable_behavior(text: str) -> bool:
    """Detect high-confidence actions/results that cannot be treated as context only."""

    normalized = normalize_requirement_text(text)
    if not normalized or normalized == "无":
        return False
    probe = re.sub(r"【[^】]*】|“[^”]*”|\"[^\"]*\"|'[^']*'", "", normalized)
    if PARENT_CONDITION_ONLY_RE.fullmatch(probe) or PARENT_STATIC_STATE_ONLY_RE.fullmatch(probe):
        return False
    return PARENT_OBSERVABLE_ACTION_RE.search(probe) is not None


def read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8-sig")
    except UnicodeError as exc:
        raise WorkflowError(f"file is not valid UTF-8 text: {path}") from exc
    except OSError as exc:
        raise WorkflowError(f"cannot read file: {path}: {exc}") from exc


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.endswith("\n"):
        normalized += "\n"
    temp = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(normalized)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def atomic_write_json(path: Path, value: dict) -> None:
    atomic_write_text(path, json.dumps(value, ensure_ascii=False, indent=2))


def load_template(name: str, values: dict[str, str]) -> str:
    text = read_text(TEMPLATE_DIR / name)
    for key, value in values.items():
        text = text.replace("{{" + key + "}}", value)
    unresolved = re.findall(r"\{\{[A-Z0-9_]+\}\}", text)
    if unresolved:
        raise WorkflowError(f"template {name} has unresolved placeholders: {', '.join(sorted(set(unresolved)))}")
    return text


def split_table_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    cells: list[str] = []
    buffer: list[str] = []
    escaped = False
    in_code = False
    for char in text:
        if escaped:
            buffer.append(char)
            escaped = False
            continue
        if char == "\\":
            escaped = True
            buffer.append(char)
            continue
        if char == BT:
            in_code = not in_code
            buffer.append(char)
            continue
        if char == "|" and not in_code:
            cells.append("".join(buffer).strip())
            buffer = []
            continue
        buffer.append(char)
    cells.append("".join(buffer).strip())
    return cells


def is_separator_row(cells: list[str]) -> bool:
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def extract_tables(text: str) -> list[Table]:
    lines = text.splitlines()
    tables: list[Table] = []
    index = 0
    while index + 1 < len(lines):
        if not lines[index].lstrip().startswith("|"):
            index += 1
            continue
        headers = split_table_row(lines[index])
        separator = split_table_row(lines[index + 1])
        if len(headers) != len(separator) or not is_separator_row(separator):
            index += 1
            continue
        rows: list[tuple[int, list[str]]] = []
        cursor = index + 2
        while cursor < len(lines) and lines[cursor].lstrip().startswith("|"):
            cells = split_table_row(lines[cursor])
            if len(cells) != len(headers):
                raise WorkflowError(
                    f"malformed Markdown table row at line {cursor + 1}: "
                    f"expected {len(headers)} cells, found {len(cells)}"
                )
            rows.append((cursor + 1, cells))
            cursor += 1
        tables.append(Table(tuple(headers), rows, index + 1))
        index = cursor
    return tables


def find_tables(tables: list[Table], headers: tuple[str, ...]) -> list[Table]:
    return [table for table in tables if table.headers == headers]


def extract_link_target(cell: str) -> str | None:
    match = re.search(r"!?\[[^\]]*\]\(([^)]+)\)", cell)
    if not match:
        return None
    target = match.group(1).strip()
    if target.startswith("<") and target.endswith(">"):
        target = target[1:-1]
    if " " in target and not target.startswith(("http://", "https://")):
        target = target.split(' "', 1)[0]
    return target


def resolve_local_link(source_file: Path, target: str) -> Path | None:
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", target) or target.startswith("#"):
        return None
    target = unquote(target.split("#", 1)[0])
    if not target:
        return None
    return (source_file.parent / Path(target)).resolve()


def ordered_ids(text: str, prefix: str) -> list[str]:
    pattern = re.compile(rf"{re.escape(prefix)}-(\d{{3}})(?:\s*[～~]\s*(?:{re.escape(prefix)}-)?(\d{{3}}))?")
    result: list[str] = []
    for start_text, end_text in pattern.findall(text):
        start = int(start_text)
        end = int(end_text) if end_text else start
        values = [start] if end < start or end - start > 500 else list(range(start, end + 1))
        for value in values:
            item = f"{prefix}-{value:03d}"
            if item not in result:
                result.append(item)
    return result


def ordered_resource_ids(text: str, known_ids: Iterator[str] | None = None) -> list[str]:
    if known_ids is not None:
        matches: list[tuple[int, str]] = []
        for resource_id in set(known_ids):
            match = re.search(
                rf"(?<![A-Z0-9-]){re.escape(resource_id)}(?![A-Z0-9-])",
                text,
            )
            if match:
                matches.append((match.start(), resource_id))
        return [resource_id for _, resource_id in sorted(matches)]
    result: list[str] = []
    for item in re.findall(r"SRC-[A-Z0-9-]+|FC-\d{3}|CTX", text):
        if item not in result:
            result.append(item)
    return result


def markdown_table(headers: tuple[str, ...], rows: list[list[str]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "|" + "|".join("---" for _ in headers) + "|"]
    lines.extend("| " + " | ".join(row) + " |" for row in rows)
    return "\n".join(lines)


def candidate_headers(data_closure_enabled: bool) -> tuple[str, ...]:
    return CANDIDATE_DATA_CLOSURE_HEADERS if data_closure_enabled else CANDIDATE_HEADERS


def final_headers(data_closure_enabled: bool) -> tuple[str, ...]:
    return FINAL_DATA_CLOSURE_HEADERS if data_closure_enabled else FINAL_HEADERS


def tp_readiness_headers(data_closure_enabled: bool) -> tuple[str, ...]:
    return (
        TP_READINESS_DATA_CLOSURE_HEADERS
        if data_closure_enabled
        else TP_READINESS_HEADERS
    )


def column_value(headers: tuple[str, ...], cells: list[str], column: str) -> str:
    try:
        return cells[headers.index(column)]
    except (ValueError, IndexError) as exc:
        raise WorkflowError(f"document row is missing required column: {column}") from exc


def missing_preanalysis_files(path: Path) -> list[str]:
    return [name for name in LEGACY_PREANALYSIS_REQUIRED_FILES if not (path / name).is_file()]


def require_exact_keys(value: dict, expected: set[str], label: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        raise WorkflowError(f"{label} keys mismatch; missing={missing}, unknown={unknown}")


def resolve_portable_path(base: Path, raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw.strip():
        raise WorkflowError(f"{label} must be a nonempty relative path")
    if re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:", raw) or Path(raw).is_absolute():
        raise WorkflowError(f"{label} must be relative to the manifest: {raw}")
    return (base / Path(raw)).resolve()


def require_within(path: Path, root: Path, label: str, allow_root: bool = True) -> None:
    try:
        relative = path.relative_to(root)
    except ValueError as exc:
        raise WorkflowError(f"{label} escapes its allowed root: {path} not under {root}") from exc
    if not allow_root and not relative.parts:
        raise WorkflowError(f"{label} cannot be the root itself: {path}")


def load_manifest_layout(
    manifest_path: Path,
    expected_module_dir: Path,
    expected_preanalysis_dir: Path | None = None,
) -> ModuleLayout:
    manifest_path = manifest_path.resolve()
    if not manifest_path.is_file():
        raise WorkflowError(f"preanalysis manifest does not exist: {manifest_path}")
    try:
        data = json.loads(read_text(manifest_path))
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"invalid preanalysis manifest JSON: {manifest_path}: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkflowError("preanalysis manifest root must be a JSON object")
    require_exact_keys(
        data,
        {"schema_version", "module_root", "artifacts", "resource_roles", "output"},
        "manifest",
    )
    if data["schema_version"] != MANIFEST_SCHEMA:
        raise WorkflowError(
            f"unsupported preanalysis manifest schema: {data['schema_version']}; expected {MANIFEST_SCHEMA}"
        )

    preanalysis_dir = manifest_path.parent.resolve()
    module_dir = resolve_portable_path(preanalysis_dir, data["module_root"], "module_root")
    if module_dir != expected_module_dir.resolve():
        raise WorkflowError(
            f"manifest module_root {module_dir} does not match requested module {expected_module_dir.resolve()}"
        )
    if not module_dir.is_dir():
        raise WorkflowError(f"manifest module_root does not exist: {module_dir}")
    require_within(preanalysis_dir, module_dir, "preanalysis directory")
    if expected_preanalysis_dir is not None and preanalysis_dir != expected_preanalysis_dir.resolve():
        raise WorkflowError(
            f"manifest directory {preanalysis_dir} does not match --preanalysis-dir {expected_preanalysis_dir.resolve()}"
        )

    artifacts = data["artifacts"]
    if not isinstance(artifacts, dict):
        raise WorkflowError("manifest artifacts must be a JSON object")
    require_exact_keys(artifacts, set(ARTIFACT_KEYS), "manifest artifacts")
    artifact_paths: dict[str, Path] = {}
    seen_paths: set[Path] = set()
    for logical_key, internal_name in ARTIFACT_KEYS.items():
        resolved = resolve_portable_path(
            preanalysis_dir,
            artifacts[logical_key],
            f"artifacts.{logical_key}",
        )
        require_within(resolved, preanalysis_dir, f"artifacts.{logical_key}")
        if resolved in seen_paths:
            raise WorkflowError(f"multiple manifest artifact roles point to the same file: {resolved}")
        if not resolved.is_file():
            raise WorkflowError(f"configured preanalysis artifact is missing: {logical_key} -> {resolved}")
        seen_paths.add(resolved)
        artifact_paths[internal_name] = resolved

    roles = data["resource_roles"]
    if not isinstance(roles, dict):
        raise WorkflowError("manifest resource_roles must be a JSON object")
    require_exact_keys(roles, set(RESOURCE_ROLE_KEYS), "manifest resource_roles")
    if len(set(roles.values())) != len(RESOURCE_ROLE_KEYS):
        raise WorkflowError("manifest resource_roles values must be unique")
    for role, resource_id in roles.items():
        if not isinstance(resource_id, str) or not re.fullmatch(r"(?:SRC-[A-Z0-9-]+|CTX)", resource_id):
            raise WorkflowError(f"manifest resource_roles.{role} has invalid resource ID: {resource_id}")
    for role in ("global_context", "module_requirement"):
        if not roles[role].startswith("SRC-"):
            raise WorkflowError(f"manifest resource_roles.{role} must use a SRC-* resource ID")

    output = data["output"]
    if not isinstance(output, dict):
        raise WorkflowError("manifest output must be a JSON object")
    require_exact_keys(output, {"test_points_dir"}, "manifest output")
    output_dir = resolve_portable_path(
        preanalysis_dir,
        output["test_points_dir"],
        "output.test_points_dir",
    )
    require_within(output_dir, module_dir, "output.test_points_dir", allow_root=False)
    return ModuleLayout(
        module_dir,
        preanalysis_dir,
        manifest_path,
        artifact_paths,
        dict(roles),
        output_dir,
    )


def legacy_layout(module_dir: Path, preanalysis_dir: Path) -> ModuleLayout:
    artifact_paths = {
        internal_name: (preanalysis_dir / internal_name).resolve()
        for internal_name in ARTIFACT_KEYS.values()
    }
    return ModuleLayout(
        module_dir.resolve(),
        preanalysis_dir.resolve(),
        None,
        artifact_paths,
        dict(LEGACY_RESOURCE_ROLES),
        module_dir.resolve() / "test-points",
    )


def resolve_module_layout(
    module_dir: Path,
    requested_preanalysis_dir: Path | None,
    requested_manifest: Path | None,
) -> ModuleLayout:
    module_dir = module_dir.resolve()
    if not module_dir.is_dir():
        raise WorkflowError(f"module directory does not exist: {module_dir}")

    if requested_manifest is not None:
        return load_manifest_layout(
            requested_manifest,
            module_dir,
            requested_preanalysis_dir,
        )

    if requested_preanalysis_dir is not None:
        preanalysis_dir = requested_preanalysis_dir.resolve()
        if not preanalysis_dir.is_dir():
            raise WorkflowError(f"preanalysis directory does not exist: {preanalysis_dir}")
        manifest_path = preanalysis_dir / MANIFEST_NAME
        if manifest_path.is_file():
            return load_manifest_layout(manifest_path, module_dir, preanalysis_dir)
        missing = missing_preanalysis_files(preanalysis_dir)
        if missing:
            raise WorkflowError(
                f"explicit preanalysis directory is incomplete: {preanalysis_dir}; "
                f"missing: {', '.join(missing)}"
            )
        return legacy_layout(module_dir, preanalysis_dir)

    manifest_candidates = [
        candidate
        for candidate in (
            module_dir / MANIFEST_NAME,
            *(child / MANIFEST_NAME for child in module_dir.iterdir() if child.is_dir()),
        )
        if candidate.is_file()
    ]
    if len(manifest_candidates) == 1:
        return load_manifest_layout(manifest_candidates[0], module_dir)
    if len(manifest_candidates) > 1:
        choices = ", ".join(path.resolve().as_posix() for path in sorted(manifest_candidates))
        raise WorkflowError(
            f"multiple preanalysis manifests were discovered under module: {choices}; "
            "pass --manifest to select one"
        )

    if not missing_preanalysis_files(module_dir):
        return legacy_layout(module_dir, module_dir)

    candidates = sorted(
        (child.resolve() for child in module_dir.iterdir() if child.is_dir() and not missing_preanalysis_files(child)),
        key=lambda path: path.as_posix(),
    )
    if len(candidates) == 1:
        return legacy_layout(module_dir, candidates[0])
    if not candidates:
        required = ", ".join(LEGACY_PREANALYSIS_REQUIRED_FILES)
        raise WorkflowError(
            f"could not discover {MANIFEST_NAME} or a complete legacy preanalysis directory under module: {module_dir}; "
            f"expected these artifacts directly in the module or in exactly one direct child: {required}; "
            "pass --manifest or --preanalysis-dir explicitly when artifacts are stored elsewhere"
        )
    choices = ", ".join(path.as_posix() for path in candidates)
    raise WorkflowError(
        f"multiple preanalysis directories were discovered under module: {choices}; "
        "pass --preanalysis-dir to select one"
    )


def add_layout_arguments(parser) -> None:
    parser.add_argument("module_dir", type=Path, help="Module workspace root.")
    parser.add_argument(
        "--manifest",
        type=Path,
        help="preanalysis/v1 manifest; auto-discovered from the module root when omitted.",
    )
    parser.add_argument(
        "--preanalysis-dir",
        type=Path,
        help="Preanalysis artifact directory; auto-detected from the module root when omitted.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help="Generation output directory; defaults to manifest output.test_points_dir or <module-dir>/test-points for legacy inputs.",
    )


def parse_module(layout: ModuleLayout) -> ModuleModel:
    module_dir = layout.module_dir
    preanalysis_dir = layout.preanalysis_dir
    map_path = layout.artifact_paths["02-sentence-test-point-map.md"]
    q_path = layout.artifact_paths["03-clarification-questions.md"]
    for path in layout.artifact_paths.values():
        if not path.is_file():
            raise WorkflowError(f"required upstream artifact is missing: {path}")

    map_tables = extract_tables(read_text(map_path))
    resource_tables = find_tables(map_tables, RESOURCE_HEADERS)
    if len(resource_tables) != 1:
        raise WorkflowError("map must contain exactly one fixed resource-index table")
    resources: dict[str, Resource] = {}
    for line, cells in resource_tables[0].rows:
        resource_id = clean_cell(cells[0])
        target = extract_link_target(cells[1])
        if not target:
            raise WorkflowError(f"resource {resource_id} has no local Markdown link at map line {line}")
        resolved = resolve_local_link(map_path, target)
        if resolved is None:
            raise WorkflowError(f"resource {resource_id} is not a local file at map line {line}")
        if resource_id in resources:
            raise WorkflowError(f"duplicate resource ID: {resource_id}")
        resources[resource_id] = Resource(resource_id, resolved, clean_cell(cells[2]), line)

    rsus: list[RequirementUnit] = []
    seen_rsus: set[str] = set()
    for table in sorted(find_tables(map_tables, RSU_HEADERS), key=lambda item: item.line):
        for line, cells in table.rows:
            rsu_id = clean_cell(cells[0])
            if not re.fullmatch(r"RSU-\d{3}", rsu_id):
                raise WorkflowError(f"invalid RSU ID at map line {line}: {rsu_id}")
            if rsu_id in seen_rsus:
                raise WorkflowError(f"duplicate RSU ID: {rsu_id}")
            seen_rsus.add(rsu_id)
            rsus.append(RequirementUnit(rsu_id, tuple(cells), line, len(rsus) + 1))
    if not rsus:
        raise WorkflowError("map contains no RSU rows")

    questions: dict[str, Question] = {}
    for table in extract_tables(read_text(q_path)):
        if table.headers not in (ANSWERED_Q_HEADERS, PENDING_Q_HEADERS):
            continue
        for line, cells in table.rows:
            q_id = clean_cell(cells[0])
            if not re.fullmatch(r"Q-\d{3}", q_id):
                raise WorkflowError(f"invalid Q ID at question line {line}: {q_id}")
            if q_id in questions:
                raise WorkflowError(f"duplicate Q ID: {q_id}")
            questions[q_id] = Question(q_id, table.headers, tuple(cells), line)

    title = module_dir.name
    readme = layout.artifact_paths["README.md"]
    if readme.is_file():
        match = re.search(r"(?m)^#\s+(.+?)\s*$", read_text(readme))
        if match:
            title = match.group(1).strip()
    return ModuleModel(
        module_dir,
        preanalysis_dir,
        layout.manifest_path,
        sha256_file(layout.manifest_path) if layout.manifest_path else None,
        dict(layout.artifact_paths),
        dict(layout.resource_roles),
        title,
        map_path,
        q_path,
        resources,
        rsus,
        {item.rsu_id: item for item in rsus},
        questions,
    )


def display_path(path: Path, base: Path) -> str:
    try:
        return path.resolve().relative_to(base.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


def escape_markdown_table_cell(value: str) -> str:
    """Keep generated resource metadata inside one Markdown table cell."""

    return value.replace("\r", " ").replace("\n", "<br>").replace("|", r"\|")


def local_file_link(path: Path, base: Path) -> str:
    """Render a readable, clickable local path for a generated Markdown artifact."""

    try:
        visible = Path(os.path.relpath(path.resolve(), base.resolve())).as_posix()
    except ValueError:
        # Windows cannot express a relative path across drive letters.
        visible = path.resolve().as_posix()
    label = visible.replace("[", r"\[").replace("]", r"\]")
    target = quote(visible, safe="/:._-~()")
    return f"[{label}](<{target}>)"


def context_resource_index_template(model: ModuleModel, output_dir: Path) -> str:
    """Create the controlled section that validation fills from final TP references."""

    map_link = local_file_link(model.map_path, output_dir)
    return (
        "## 上下文资源入口\n\n"
        "> 本节由最终校验根据最终测试点的 `Context Refs` 自动生成，只列实际使用的资源；"
        f"资源定义以 {map_link} 的“引用入口”为唯一权威来源。请勿手工维护标记区。\n\n"
        f"{CONTEXT_RESOURCE_INDEX_BEGIN}\n"
        "最终测试点通过校验后，此处自动生成资源索引。\n"
        f"{CONTEXT_RESOURCE_INDEX_END}"
    )


def render_context_resource_index(
    model: ModuleModel,
    resource_ids: Iterator[str],
    output_dir: Path,
) -> str:
    """Render only resources referenced by final TPs, in upstream map order."""

    referenced = set(resource_ids)
    unknown = referenced - set(model.resources)
    if unknown:
        raise WorkflowError(
            f"cannot render undefined context resources: {sorted(unknown)}"
        )
    rows: list[list[str]] = []
    for resource_id, resource in model.resources.items():
        if resource_id not in referenced:
            continue
        rows.append(
            [
                escape_markdown_table_cell(resource_id),
                local_file_link(resource.path, output_dir),
                escape_markdown_table_cell(resource.purpose),
            ]
        )
    if not rows:
        return "最终测试点未引用上下文资源。"
    return markdown_table(RESOURCE_HEADERS, rows)


def replace_context_resource_index(
    text: str,
    model: ModuleModel,
    resource_ids: Iterator[str],
    output_dir: Path,
) -> str:
    """Replace the single controlled resource-index block deterministically."""

    begin_count = text.count(CONTEXT_RESOURCE_INDEX_BEGIN)
    end_count = text.count(CONTEXT_RESOURCE_INDEX_END)
    if begin_count == 0 and end_count == 0:
        if "## 上下文资源入口" in text:
            raise WorkflowError(
                "module-test-points.md has an unmanaged context resource index section; "
                "rerun prepare_finalization.py"
            )
        anchor = "\n## 最终测试点\n"
        if text.count(anchor) != 1:
            raise WorkflowError(
                "module-test-points.md has no unique final-test-point section for context "
                "resource index migration; rerun prepare_finalization.py"
            )
        text = text.replace(
            anchor,
            "\n" + context_resource_index_template(model, output_dir) + anchor,
            1,
        )
        begin_count = 1
        end_count = 1
    if begin_count != 1 or end_count != 1:
        raise WorkflowError(
            "module-test-points.md has an invalid auto-generated context resource "
            "index block; rerun prepare_finalization.py"
        )
    start = text.index(CONTEXT_RESOURCE_INDEX_BEGIN) + len(CONTEXT_RESOURCE_INDEX_BEGIN)
    end = text.index(CONTEXT_RESOURCE_INDEX_END)
    if end < start:
        raise WorkflowError(
            "module-test-points.md context resource index markers are out of order; "
            "rerun prepare_finalization.py"
        )
    body = render_context_resource_index(model, resource_ids, output_dir)
    return text[:start] + "\n" + body.rstrip() + "\n" + text[end:]


def material_for(model: ModuleModel, resource_id: str, role: str, blockers: list[str]) -> Material | None:
    resource = model.resources.get(resource_id)
    if resource is None:
        blockers.append(f"undefined resource ID: {resource_id}")
        return None
    if not resource.path.is_file():
        blockers.append(f"resource file does not exist: {resource_id} -> {resource.path}")
        return None
    if resource.path.suffix.lower() not in TEXT_SUFFIXES:
        blockers.append(f"resource is not materializable UTF-8 text; create a Context Card first: {resource_id} -> {resource.path}")
        return None
    try:
        content = read_text(resource.path)
    except WorkflowError as exc:
        blockers.append(str(exc))
        return None
    return Material(resource_id, resource.path, role, content)


def evidence_for(
    model: ModuleModel,
    resource_id: str,
    blockers: list[str],
) -> EvidenceReference | None:
    resource = model.resources.get(resource_id)
    if resource is None:
        blockers.append(f"undefined evidence resource ID: {resource_id}")
        return None
    if not resource.path.is_file():
        blockers.append(
            f"evidence resource file does not exist: {resource_id} -> {resource.path}"
        )
        return None
    try:
        digest = sha256_file(resource.path)
    except OSError as exc:
        blockers.append(f"cannot hash evidence resource {resource.path}: {exc}")
        return None
    return EvidenceReference(resource_id, resource.path, resource.purpose, digest)


def parent_behavior_source_ids(model: ModuleModel, rsu: RequirementUnit) -> list[str]:
    """Locate RSUs whose source-content cell exposes the current row's behavioral parent wording."""

    if not parent_has_observable_behavior(rsu.parent_text):
        return []
    parent_text = normalize_requirement_text(rsu.parent_text)
    return [
        item.rsu_id
        for item in model.rsus
        if parent_text in normalize_requirement_text(item.source_text)
    ]

def build_bundle(model: ModuleModel, rsu: RequirementUnit) -> InputBundle:
    blockers: list[str] = []
    if rsu.source_status in {"pending", "pending-context"}:
        blockers.append(f"{rsu.rsu_id} source status is {rsu.source_status}")

    parent_has_behavior = parent_has_observable_behavior(rsu.parent_text)
    parent_source_ids = parent_behavior_source_ids(model, rsu)
    if parent_has_behavior and not parent_source_ids:
        blockers.append(
            f"{rsu.rsu_id} has observable behavior only in 父级条件（原文）; "
            "create an upstream RSU whose 原文内容 contains the complete parent wording, "
            "or merge it into the current composite RSU"
        )

    fixed_ids = list(model.fixed_resource_ids)
    fixed_materials: list[Material] = []
    for resource_id in fixed_ids:
        material = material_for(model, resource_id, "fixed", blockers)
        if material:
            fixed_materials.append(material)

    q_ids = ordered_ids(rsu.related_questions, "Q")
    questions: list[Question] = []
    for q_id in q_ids:
        question = model.questions.get(q_id)
        if question is None:
            blockers.append(f"{rsu.rsu_id} references undefined question {q_id}")
            continue
        questions.append(question)
        if question.status == "pending":
            blockers.append(f"{rsu.rsu_id} depends on unanswered {q_id}")

    # Only resources declared by the current RSU (or its question row) are
    # semantic inputs.  References found inside an FC/DC card are provenance
    # for that already-focused card, not an instruction to recursively copy
    # whole PRDs, schemas, or every other RSU dependency into this bundle.
    direct_dynamic_ids: list[str] = []
    if rsu.source_id not in fixed_ids:
        direct_dynamic_ids.append(rsu.source_id)
    for resource_id in ordered_resource_ids(rsu.related_context, iter(model.resources)):
        if resource_id not in fixed_ids and resource_id not in direct_dynamic_ids:
            direct_dynamic_ids.append(resource_id)

    if model.data_closure_enabled:
        for question in questions:
            for resource_id in ordered_resource_ids(" ".join(question.cells), iter(model.resources)):
                if resource_id not in fixed_ids and resource_id not in direct_dynamic_ids:
                    direct_dynamic_ids.append(resource_id)

    support_ids: list[str] = [
        source_id for source_id in parent_source_ids if source_id != rsu.rsu_id
    ]
    for question in questions:
        for support_id in ordered_ids(" ".join(question.cells), "RSU"):
            if support_id != rsu.rsu_id and support_id not in support_ids:
                support_ids.append(support_id)

    dynamic_materials: list[Material] = []
    for resource_id in direct_dynamic_ids:
        material = material_for(model, resource_id, "dynamic", blockers)
        if material:
            dynamic_materials.append(material)

    evidence_ids: list[str] = []
    for material in dynamic_materials:
        if not material.resource_id.startswith(("FC-", "DC-")):
            continue
        for support_id in ordered_ids(material.content, "RSU"):
            if support_id != rsu.rsu_id and support_id not in support_ids:
                support_ids.append(support_id)
        for evidence_id in ordered_resource_ids(material.content, iter(model.resources)):
            if (
                evidence_id not in fixed_ids
                and evidence_id not in direct_dynamic_ids
                and evidence_id not in evidence_ids
            ):
                evidence_ids.append(evidence_id)

    evidence_materials: list[EvidenceReference] = []
    for resource_id in evidence_ids:
        evidence = evidence_for(model, resource_id, blockers)
        if evidence:
            evidence_materials.append(evidence)

    for support_id in support_ids:
        if support_id not in model.rsu_by_id:
            blockers.append(f"dependency content references undefined {support_id}")

    supporting_rsus = [
        model.rsu_by_id[support_id]
        for support_id in support_ids
        if support_id in model.rsu_by_id
    ]
    allowed_rsu_ids = [rsu.rsu_id] + [item.rsu_id for item in supporting_rsus]
    allowed_context_ids: list[str] = []
    for resource_id in [*fixed_ids, rsu.source_id, *direct_dynamic_ids]:
        if resource_id not in allowed_context_ids:
            allowed_context_ids.append(resource_id)
    required_context_ids: list[str] = []
    for resource_id in [*fixed_ids, rsu.source_id]:
        if resource_id not in required_context_ids:
            required_context_ids.append(resource_id)

    contract_files = [SKILL_DIR / "references" / "generation-rules.md", SKILL_DIR / "references" / "output-contract.md"]
    if model.data_closure_enabled:
        contract_files.extend(
            [
                SKILL_DIR / "references" / "data-closure-generation-rules.md",
                SKILL_DIR / "references" / "data-closure-output-contract.md",
            ]
        )
    contract_hashes = {path.name: sha256_text(read_text(path)) for path in contract_files}
    manifest = {
        "schema_version": 2,
        "rsu": list(rsu.cells),
        "questions": [{"headers": list(item.headers), "cells": list(item.cells)} for item in questions],
        "supporting_rsus": [list(item.cells) for item in supporting_rsus],
        "materials": [
            {
                "resource_id": item.resource_id,
                "role": item.role,
                "path": display_path(item.path, model.module_dir),
                "sha256": sha256_text(item.content),
            }
            for item in [*fixed_materials, *dynamic_materials]
        ]
        + [
            {
                "resource_id": item.resource_id,
                "role": "evidence-reference",
                "path": display_path(item.path, model.module_dir),
                "sha256": item.sha256,
            }
            for item in evidence_materials
        ],
        "allowed_rsu_ids": allowed_rsu_ids,
        "allowed_q_ids": q_ids,
        "allowed_context_ids": allowed_context_ids,
        "required_context_ids": required_context_ids,
        "preanalysis_manifest": {
            "path": display_path(model.manifest_path, model.module_dir) if model.manifest_path else None,
            "sha256": model.manifest_sha256,
            "resource_roles": model.resource_roles,
        },
        "contracts": contract_hashes,
    }
    input_hash = sha256_text(json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

    current_table = markdown_table(RSU_HEADERS, [list(rsu.cells)])
    support_table = markdown_table(RSU_HEADERS, [list(item.cells) for item in supporting_rsus]) if supporting_rsus else "无"
    question_sections: list[str] = []
    for question in questions:
        question_sections.append(f"### {question.q_id}\n\n" + markdown_table(question.headers, [list(question.cells)]))
    question_text = "\n\n".join(question_sections) if question_sections else "无"

    def render_material(item: Material) -> str:
        relative = display_path(item.path, model.module_dir)
        digest = sha256_text(item.content)
        return (
            f"### {item.resource_id}\n\n"
            f"- 文件：{BT}{relative}{BT}\n"
            f"- 角色：{item.role}\n"
            f"- SHA-256：{BT}{digest}{BT}\n\n"
            f"<!-- BEGIN {item.resource_id} -->\n{item.content.rstrip()}\n<!-- END {item.resource_id} -->"
        )

    fixed_text = "\n\n".join(render_material(item) for item in fixed_materials) or "无"
    dynamic_sections = [
        f"### 当前来源定位\n\n- 来源：{BT}{rsu.source_id}{BT}\n- 语义定位：{rsu.source_location}\n"
        + ("- 来源全文已在固定输入中物化。" if rsu.source_id in fixed_ids else "- 来源全文见下方对应动态资源。")
    ]
    dynamic_sections.extend(render_material(item) for item in dynamic_materials)
    dynamic_text = "\n\n".join(dynamic_sections)
    evidence_sections: list[str] = []
    for item in evidence_materials:
        evidence_sections.append(
            f"### {item.resource_id}\n\n"
            f"- 文件：{BT}{display_path(item.path, model.module_dir)}{BT}\n"
            f"- 角色：evidence-reference（正文不自动展开）\n"
            f"- 定位用途：{item.purpose}\n"
            f"- SHA-256：{BT}{item.sha256}{BT}"
        )
    evidence_text = "\n\n".join(evidence_sections) or "无"
    generation_contract = "\n\n".join(read_text(path).rstrip() for path in contract_files)
    rendered = load_template(
        "rsu-input-data-closure.md.tmpl" if model.data_closure_enabled else "rsu-input.md.tmpl",
        {
            "RSU_ID": rsu.rsu_id,
            "INPUT_SHA256": input_hash,
            "CURRENT_SOURCE_ID": rsu.source_id,
            "ALLOWED_RSU_IDS": "、".join(allowed_rsu_ids),
            "ALLOWED_Q_IDS": "、".join(q_ids) if q_ids else "无",
            "ALLOWED_CONTEXT_IDS": "、".join(allowed_context_ids),
            "REQUIRED_CONTEXT_IDS": "、".join(required_context_ids),
            "ALLOWED_DATA_CLOSURE_IDS": "、".join(
                item for item in allowed_context_ids if re.fullmatch(r"DC-\d{3}", item)
            )
            or "无",
            "CURRENT_RSU_TABLE": current_table,
            "SUPPORTING_RSU_TABLE": support_table,
            "QUESTION_TABLES": question_text,
            "FIXED_MATERIALS": fixed_text,
            "DYNAMIC_MATERIALS": dynamic_text,
            "EVIDENCE_MATERIALS": evidence_text,
            "GENERATION_CONTRACT": generation_contract,
        },
    )

    fixed_anchor_text = "\n".join(
        f"- {BT}{item.resource_id}{BT}：{BT}{sha256_text(item.content)}{BT}"
        f"（{BT}{display_path(item.path, model.module_dir)}{BT}）"
        for item in fixed_materials
    ) or "- 无"
    contract_anchor_text = "\n".join(
        f"- {BT}{name}{BT}：{BT}{digest}{BT}"
        for name, digest in sorted(contract_hashes.items())
    ) or "- 无"
    session_source_manifest = {
        "schema_version": "rsu-test-point-generation/session-source-v1",
        "fixed_materials": [
            {
                "resource_id": item.resource_id,
                "path": display_path(item.path, model.module_dir),
                "sha256": sha256_text(item.content),
            }
            for item in fixed_materials
        ],
        "contracts": contract_hashes,
        "preanalysis_manifest_sha256": model.manifest_sha256,
        "resource_roles": model.resource_roles,
    }
    session_source_fingerprint = sha256_text(
        json.dumps(
            session_source_manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    session_manifest = {
        "schema_version": "rsu-test-point-generation/session-input-v1",
        "rsu_id": rsu.rsu_id,
        "full_input_sha256": input_hash,
        "source_fingerprint_sha256": session_source_fingerprint,
        "rsu": list(rsu.cells),
        "questions": [
            {"headers": list(item.headers), "cells": list(item.cells)}
            for item in questions
        ],
        "supporting_rsus": [list(item.cells) for item in supporting_rsus],
        "dynamic_materials": [
            {
                "resource_id": item.resource_id,
                "path": display_path(item.path, model.module_dir),
                "sha256": sha256_text(item.content),
            }
            for item in dynamic_materials
        ],
        "evidence_materials": [
            {
                "resource_id": item.resource_id,
                "path": display_path(item.path, model.module_dir),
                "sha256": item.sha256,
            }
            for item in evidence_materials
        ],
    }
    session_input_hash = sha256_text(
        json.dumps(
            session_manifest,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    )
    session_rendered = (
        f"# RSU Runner 会话增量输入：{rsu.rsu_id}\n\n"
        "## 会话与完整输入锚点\n\n"
        "| 字段 | 值 |\n|---|---|\n"
        f"| Schema | {BT}rsu-test-point-generation/session-input-v1{BT} |\n"
        f"| RSU-ID | {BT}{rsu.rsu_id}{BT} |\n"
        f"| 会话增量输入 SHA-256 | {BT}{session_input_hash}{BT} |\n"
        f"| 完整输入业务 SHA-256 | {BT}{input_hash}{BT} |\n"
        f"| 固定来源指纹 SHA-256 | {BT}{session_source_fingerprint}{BT} |\n\n"
        "本文件供从模块 Foundation 派生的批次 fork 使用；固定资源正文和生成契约已由 Foundation 提供，"
        "当前批次只补读本 RSU 的动态事实。Foundation 身份、固定来源指纹或任一锚点不一致时，"
        "必须停止轻量输入复用并改读完整 INPUT_FILE。\n\n"
        "## 已加载固定资源锚点（本轮不重复正文）\n\n"
        f"{fixed_anchor_text}\n\n"
        "## 已加载生成契约锚点（本轮不重复正文）\n\n"
        f"{contract_anchor_text}\n\n"
        "若无法准确回忆固定需求或契约、发现上下文被摘要/压缩、记忆与锚点冲突，"
        "必须补读完整 INPUT_FILE 的相关章节；仍不确定时完整重读，不能猜测。\n\n"
        "## 本轮允许引用\n\n"
        f"- Source RSUs：{BT}{'、'.join(allowed_rsu_ids)}{BT}\n"
        f"- Question Refs：{BT}{'、'.join(q_ids) if q_ids else '无'}{BT}\n"
        f"- Context Refs：{BT}{'、'.join(allowed_context_ids)}{BT}\n"
        f"- Required Context Refs：{BT}{'、'.join(required_context_ids)}{BT}\n\n"
        "## 当前 RSU 原文映射\n\n"
        f"{current_table}\n\n"
        "## 支持 RSU 原文\n\n"
        f"{support_table}\n\n"
        "## 相关问题\n\n"
        f"{question_text}\n\n"
        "## 当前 RSU 动态上下文与数据依赖\n\n"
        f"{dynamic_text}\n\n"
        "## 追溯证据索引\n\n"
        f"{evidence_text}\n\n"
        "## 生成边界\n\n"
        f"- 本文件只描述 {BT}{rsu.rsu_id}{BT} 的 0～N 个候选边界；批次实际处理范围以 batch manifest 为准。\n"
        "- 当前 RSU、支持 RSU、Q、动态 FC/DC 和证据锚点以本文件为准。\n"
        "- 固定资源正文和生成契约由模块 Foundation 提供；路径、SHA-256 与本轮允许集合仍是事实边界。\n"
        "- 若 Foundation 身份、固定来源指纹或任一锚点不一致，停止本批并改读完整 INPUT。\n"
        "- 只处理 batch manifest 分配的 RSU；完成本批全部授权输出和批次结果后立即停止。\n"
    )
    return InputBundle(
        rsu, input_hash, blockers, allowed_rsu_ids, q_ids, allowed_context_ids,
        required_context_ids, fixed_materials, dynamic_materials, evidence_materials,
        supporting_rsus, questions, rendered, session_rendered, session_input_hash,
        session_source_fingerprint,
    )


def collect_module_stage_sources(
    model: ModuleModel,
    state: dict[str, Any],
) -> list[tuple[str, Path, str]]:
    """Collect module-wide sources once in deterministic finalization order."""

    sources: list[tuple[str, Path, str]] = []
    seen_paths: set[Path] = set()

    def add_source(resource_id: str, path: Path) -> None:
        resolved = path.resolve()
        if resolved in seen_paths:
            return
        if not resolved.is_file():
            raise WorkflowError(f"module stage context resource is missing: {resource_id} -> {resolved}")
        seen_paths.add(resolved)
        sources.append((resource_id, resolved, read_text(resolved)))

    add_source("RSU-MAP", model.map_path)
    add_source("Q-INDEX", model.question_path)

    resource_ids = list(model.fixed_resource_ids)
    for record in state["rsus"]:
        for resource_id in record["allowed_context_ids"]:
            if resource_id not in resource_ids:
                resource_ids.append(resource_id)
    for resource_id in resource_ids:
        resource = model.resources.get(resource_id)
        if resource is None:
            raise WorkflowError(f"undefined module stage context resource: {resource_id}")
        add_source(resource_id, resource.path)
    return sources


def find_preanalysis_validator() -> Path:
    configured = os.environ.get("MODULE_PREANALYSIS_VALIDATOR")
    candidates = [
        Path(configured).expanduser().resolve() if configured else None,
        SKILL_DIR.parent / "module-requirement-preanalysis" / "scripts" / "validate_preanalysis.py",
    ]
    for path in candidates:
        if path is not None and path.is_file():
            return path
    searched = ", ".join(str(path) for path in candidates if path is not None)
    raise WorkflowError(
        "upstream validator not found; install both skills together or set "
        f"MODULE_PREANALYSIS_VALIDATOR. searched: {searched}"
    )


def run_preanalysis_validation(
    layout: ModuleLayout,
    output_dir: Path | None = None,
) -> str:
    validator = find_preanalysis_validator()
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, "-B", str(validator), str(layout.preanalysis_dir)]
    if layout.manifest_path is not None:
        command.extend(["--manifest", str(layout.manifest_path)])
    generated_root = (output_dir or layout.default_output_dir).resolve()
    preanalysis_root = layout.preanalysis_dir.resolve()
    # The module directory may contain generated test-case/test-run artifacts
    # from prior work.  They are not preanalysis inputs and can contain links
    # relative to their historical staging directory; scanning them here would
    # make an otherwise valid module permanently non-runnable.  Keep the
    # canonical preanalysis documents fully validated, but exclude only these
    # generated roots (plus the already-selected output root).
    generated_roots = [
        preanalysis_root / "test-cases-history-20261015",
        preanalysis_root / "test-points",
        *sorted(preanalysis_root.glob("test-run-*")),
    ]
    try:
        generated_root.relative_to(preanalysis_root)
    except ValueError:
        pass
    else:
        if generated_root != preanalysis_root:
            command.extend(["--exclude-root", str(generated_root)])
    for generated_path in generated_roots:
        if not generated_path.is_dir() or generated_path.resolve() == generated_root:
            continue
        command.extend(["--exclude-root", str(generated_path.resolve())])
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


def default_output_dir(layout: ModuleLayout, requested: Path | None) -> Path:
    return requested.resolve() if requested else layout.default_output_dir


@contextmanager
def state_lock(output_dir: Path) -> Iterator[None]:
    output_dir.mkdir(parents=True, exist_ok=True)
    lock_path = output_dir / ".generation.lock"
    try:
        fd = os.open(lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError as exc:
        raise WorkflowError(f"generation is already locked: {lock_path}") from exc
    try:
        os.write(fd, f"pid={os.getpid()} created_at={utc_now()}\n".encode("utf-8"))
        os.close(fd)
        yield
    finally:
        try:
            lock_path.unlink()
        except FileNotFoundError:
            pass


def state_path(output_dir: Path) -> Path:
    return output_dir / "generation-state.json"


ADAPTIVE_DISPOSITIONS = {"generated", "zero-test-points", "needs-fork", "blocked"}


def ensure_adaptive_state(state: dict) -> dict:
    """Add the adaptive runner state domain without discarding legacy fields."""
    state.setdefault("architecture", "module-baseline")
    state.setdefault("baseline", {
        "status": "pending",
        "input_file": "baseline-input.md",
        "input_sha256": None,
        "result_file": "baseline-result.json",
        "result_sha256": None,
        "session_id": None,
        "validated_at": None,
    })
    state.setdefault("adaptive", {
        "forks": [],
        "conflicts": [],
        "completion": {"status": "pending", "reasons": []},
        "metrics": {},
    })
    return state


def load_state(output_dir: Path, layout: ModuleLayout) -> dict | None:
    path = state_path(output_dir)
    if not path.is_file():
        return None
    try:
        state = json.loads(read_text(path))
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"invalid generation state JSON: {path}: {exc}") from exc
    schema_version = state.get("schema_version")
    if schema_version not in {1, 2, 3, 4}:
        raise WorkflowError("unsupported generation state schema")
    if Path(state.get("module_dir", "")).resolve() != layout.module_dir:
        raise WorkflowError("generation state belongs to a different module directory")
    if Path(state.get("output_dir", "")).resolve() != output_dir.resolve():
        raise WorkflowError("generation state belongs to a different output directory")
    if schema_version == 1:
        state["preanalysis_dir"] = layout.preanalysis_dir.as_posix()
    elif Path(state.get("preanalysis_dir", "")).resolve() != layout.preanalysis_dir:
        raise WorkflowError("generation state belongs to a different preanalysis directory")
    current_manifest = layout.manifest_path.as_posix() if layout.manifest_path else None
    if schema_version in {1, 2}:
        state["manifest_path"] = current_manifest
        state["manifest_sha256"] = sha256_file(layout.manifest_path) if layout.manifest_path else None
    else:
        stored_manifest = state.get("manifest_path")
        stored_resolved = Path(stored_manifest).resolve() if stored_manifest else None
        if stored_resolved != layout.manifest_path:
            raise WorkflowError("generation state belongs to a different preanalysis manifest")
    if schema_version < 4:
        migration_dir = output_dir / "history" / "state-migrations"
        migration_dir.mkdir(parents=True, exist_ok=True)
        digest = sha256_file(path)[:12]
        backup = migration_dir / f"generation-state-v{schema_version}-{digest}.json"
        if not backup.exists():
            atomic_write_text(backup, read_text(path))
        report = migration_dir / f"generation-state-v{schema_version}-{digest}-report.json"
        state["schema_version"] = 4
        state["scheduler_schema"] = "rsu-test-point-generation/state-v2"
        state["migrated_from_schema"] = schema_version
        state["migration_backup"] = display_path(backup, output_dir)
        state["migration_report"] = display_path(report, output_dir)
        state["foundation"] = {
            "status": "pending",
            "thread_id": None,
            "source_fingerprint_sha256": None,
            "created_at": None,
        }
        state["planning"] = {
            "status": "pending",
            "source_sha256": None,
            "input_file": None,
            "input_sha256": None,
            "output_file": "generation-plan.json",
            "output_sha256": None,
            "validated_at": None,
        }
        state["batches"] = []
        for record in state.get("rsus", []):
            record.setdefault("batch_id", None)
            record.setdefault("context_signature", None)
        atomic_write_json(report, {
            "from_schema": schema_version,
            "to_schema": 4,
            "backup": display_path(backup, output_dir),
            "unknown_fields_preserved": True,
            "session_id_discarded": bool(state.get("session_id")),
        })
        atomic_write_json(path, state)
    state.setdefault("scheduler_schema", "rsu-test-point-generation/state-v2")
    ensure_adaptive_state(state)
    state.setdefault(
        "foundation",
        {
            "status": "pending",
            "thread_id": None,
            "source_fingerprint_sha256": None,
            "created_at": None,
        },
    )
    state.setdefault(
        "planning",
        {
            "status": "pending",
            "source_sha256": None,
            "input_file": None,
            "input_sha256": None,
            "output_file": "generation-plan.json",
            "output_sha256": None,
            "validated_at": None,
        },
    )
    state.setdefault("batches", [])
    state.setdefault(
        "case_readiness",
        {
            "status": "not-ready",
            "result": None,
            "input_sha256": None,
            "input_document_sha256": None,
            "validated_at": None,
            "output_sha256": None,
        },
    )
    state.setdefault("reopen_history", [])
    return state


def create_state(model: ModuleModel, output_dir: Path) -> dict:
    now = utc_now()
    text = load_template(
        "generation-state.json.tmpl",
        {
            "MODULE_DIR": model.module_dir.as_posix(),
            "PREANALYSIS_DIR": model.preanalysis_dir.as_posix(),
            "MANIFEST_PATH_JSON": json.dumps(
                model.manifest_path.as_posix() if model.manifest_path else None,
                ensure_ascii=False,
            ),
            "MANIFEST_SHA256_JSON": json.dumps(model.manifest_sha256),
            "OUTPUT_DIR": output_dir.resolve().as_posix(),
            "CREATED_AT": now,
            "UPDATED_AT": now,
        },
    )
    state = json.loads(text)
    ensure_adaptive_state(state)
    return state


def record_paths(output_dir: Path, rsu_id: str) -> tuple[Path, Path]:
    return output_dir / "inputs" / f"{rsu_id}-input.md", output_dir / "by-rsu" / f"{rsu_id}.md"


def session_input_path(output_dir: Path, rsu_id: str) -> Path:
    return output_dir / "session-inputs" / f"{rsu_id}-delta.md"

def reconcile_state(model: ModuleModel, output_dir: Path, state: dict | None) -> tuple[dict, dict[str, InputBundle]]:
    state = state or create_state(model, output_dir)
    old_records = {item.get("rsu_id"): item for item in state.get("rsus", [])}
    bundles: dict[str, InputBundle] = {}
    records: list[dict] = []
    for rsu in model.rsus:
        bundle = build_bundle(model, rsu)
        bundles[rsu.rsu_id] = bundle
        old = old_records.get(rsu.rsu_id, {})
        input_file, candidate_file = record_paths(output_dir, rsu.rsu_id)
        old_status = old.get("generation_status")
        if bundle.blockers:
            status = "blocked"
        elif old_status == "validated":
            output_ok = candidate_file.is_file() and old.get("output_sha256") == sha256_file(candidate_file)
            status = "validated" if old.get("input_sha256") == bundle.input_sha256 and output_ok else "stale"
        elif old_status in {"prepared", "running", "failed"}:
            input_ok = input_file.is_file() and sha256_text(read_text(input_file)) == sha256_text(bundle.rendered)
            staged_value = old.get("staged_candidate_file")
            staged_file = output_dir / staged_value if isinstance(staged_value, str) and staged_value else None
            candidate_ok = candidate_file.is_file() or (staged_file is not None and staged_file.is_file())
            status = "prepared" if old.get("input_sha256") == bundle.input_sha256 and input_ok and candidate_ok else "stale"
        elif old_status == "replan-required":
            status = "replan-required" if old.get("current_input_sha256") == bundle.input_sha256 else "stale"
        elif old_status == "stale":
            status = "stale"
        else:
            status = "pending"
        records.append(
            {
                "rsu_id": rsu.rsu_id,
                "order": rsu.order,
                "source_status": rsu.source_status,
                "generation_status": status,
                "input_sha256": old.get("input_sha256"),
                "current_input_sha256": bundle.input_sha256,
                "input_file": display_path(input_file, output_dir),
                "candidate_file": display_path(candidate_file, output_dir),
                "output_sha256": old.get("output_sha256") if status == "validated" else None,
                "candidate_count": old.get("candidate_count") if status == "validated" else None,
                "validated_at": old.get("validated_at") if status == "validated" else None,
                "batch_id": old.get("batch_id"),
                "context_signature": old.get("context_signature"),
                "staged_candidate_file": old.get("staged_candidate_file") if status == "prepared" else None,
                "blockers": bundle.blockers,
                "allowed_rsu_ids": bundle.allowed_rsu_ids,
                "allowed_q_ids": bundle.allowed_q_ids,
                "allowed_context_ids": bundle.allowed_context_ids,
                "required_context_ids": bundle.required_context_ids,
            }
        )
    state["rsus"] = records
    source_fingerprints = {
        bundle.session_source_fingerprint_sha256 for bundle in bundles.values()
    }
    if len(source_fingerprints) > 1:
        raise WorkflowError(
            "RSU module-session fixed source fingerprints are inconsistent"
        )
    current_fingerprint = (
        next(iter(source_fingerprints)) if source_fingerprints else None
    )
    previous_fingerprint = state.get("session_source_fingerprint_sha256")
    state["session_source_fingerprint_sha256"] = current_fingerprint
    foundation = state.setdefault("foundation", {})
    if foundation.get("source_fingerprint_sha256") not in {None, current_fingerprint}:
        foundation.update(
            {
                "status": "pending",
                "thread_id": None,
                "source_fingerprint_sha256": None,
                "created_at": None,
            }
        )
    if previous_fingerprint not in {None, current_fingerprint}:
        state["planning"] = {
            "status": "pending",
            "source_sha256": None,
            "input_file": None,
            "input_sha256": None,
            "output_file": "generation-plan.json",
            "output_sha256": None,
            "validated_at": None,
        }
        state["batches"] = []
        for record in records:
            record["batch_id"] = None
            record["context_signature"] = None
    state["manifest_sha256"] = model.manifest_sha256
    state["updated_at"] = utc_now()
    if not all(item["generation_status"] == "validated" for item in records):
        state["finalization"] = {"status": "not-ready", "input_sha256": None, "input_document_sha256": None, "validated_at": None, "module_test_points_sha256": None, "coverage_matrix_sha256": None}
        state["case_readiness"] = {"status": "not-ready", "result": None, "input_sha256": None, "input_document_sha256": None, "validated_at": None, "output_sha256": None}
    return state, bundles


def next_record(state: dict) -> dict | None:
    return next((item for item in state["rsus"] if item["generation_status"] != "validated"), None)


def archive_candidate(output_dir: Path, candidate_file: Path, rsu_id: str, old_hash: str | None) -> Path | None:
    if not candidate_file.is_file():
        return None
    history = output_dir / "history"
    history.mkdir(parents=True, exist_ok=True)
    suffix = (old_hash or sha256_file(candidate_file))[:12]
    target = history / f"{rsu_id}-{suffix}.md"
    counter = 1
    while target.exists():
        target = history / f"{rsu_id}-{suffix}-{counter}.md"
        counter += 1
    os.replace(candidate_file, target)
    return target


def ensure_output_scaffold(model: ModuleModel, output_dir: Path) -> None:
    for name in ("inputs", "session-inputs", "by-rsu", "batches", "batch-results", "fork-inputs", "fork-results", "history"):
        (output_dir / name).mkdir(parents=True, exist_ok=True)
    readme = output_dir / "README.md"
    if not readme.exists():
        atomic_write_text(
            readme,
            load_template(
                "README.md.tmpl",
                {
                    "MODULE_NAME": model.module_name,
                    "MODULE_DIR": model.module_dir.as_posix(),
                    "PREANALYSIS_DIR": model.preanalysis_dir.as_posix(),
                    "MANIFEST_PATH": display_path(model.manifest_path, model.module_dir)
                    if model.manifest_path
                    else "legacy（无 manifest）",
                },
            ),
        )


def parse_metadata_table(text: str) -> dict[str, str]:
    tables = find_tables(extract_tables(text), ("字段", "值"))
    if len(tables) != 1:
        raise WorkflowError("document must contain exactly one metadata table with header: 字段 | 值")
    result: dict[str, str] = {}
    for line, cells in tables[0].rows:
        key = clean_cell(cells[0])
        if key in result:
            raise WorkflowError(f"duplicate metadata key at line {line}: {key}")
        result[key] = clean_cell(cells[1])
    return result


def extract_section(text: str, heading: str) -> str:
    pattern = re.compile(rf"(?ms)^##\s+{re.escape(heading)}\s*$\n(.*?)(?=^##\s+|\Z)")
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def parse_candidate_document(path: Path, data_closure_enabled: bool = False) -> CandidateDocument:
    text = read_text(path)
    if UNRESOLVED_RE.search(text):
        raise WorkflowError(f"candidate document contains unresolved placeholder: {path}")
    metadata = parse_metadata_table(text)
    for key in ("RSU-ID", "输入 SHA-256", "生成结果"):
        if key not in metadata:
            raise WorkflowError(f"candidate metadata is missing: {key}")
    expected_headers = candidate_headers(data_closure_enabled)
    legacy_headers = LEGACY_CANDIDATE_DATA_CLOSURE_HEADERS if data_closure_enabled else LEGACY_CANDIDATE_HEADERS
    all_tables = extract_tables(text)
    tables = find_tables(all_tables, expected_headers) + find_tables(all_tables, legacy_headers)
    if len(tables) != 1:
        raise WorkflowError("candidate document must contain exactly one fixed candidate table")
    return CandidateDocument(
        metadata["RSU-ID"], metadata["输入 SHA-256"], metadata["生成结果"],
        [cells for _, cells in tables[0].rows], extract_section(text, "零候选说明"),
        tables[0].headers,
    )


def parse_ref_ids(text: str, prefix: str) -> list[str]:
    return ordered_ids(clean_cell(text), prefix)


def parse_context_refs(text: str, known_ids: Iterator[str] | None = None) -> list[str]:
    return ordered_resource_ids(clean_cell(text), known_ids)


def parse_data_closure_refs(text: str) -> list[str]:
    return ordered_ids(clean_cell(text), "DC")


def parse_candidate_ids(text: str) -> list[str]:
    result: list[str] = []
    for item in re.findall(r"CAND-RSU-\d{3}-\d{3}", text):
        if item not in result:
            result.append(item)
    return result


def parse_tp_ids(text: str) -> list[str]:
    result: list[str] = []
    for item in re.findall(r"TP-\d{3}", text):
        if item not in result:
            result.append(item)
    return result


def parse_final_document(path: Path, data_closure_enabled: bool = False) -> FinalDocument:
    text = read_text(path)
    if UNRESOLVED_RE.search(text):
        raise WorkflowError(f"final document contains unresolved placeholder: {path}")
    metadata = parse_metadata_table(text)
    if "最终输入 SHA-256" not in metadata:
        raise WorkflowError("final metadata is missing: 最终输入 SHA-256")
    expected_headers = final_headers(data_closure_enabled)
    legacy_headers = LEGACY_FINAL_DATA_CLOSURE_HEADERS if data_closure_enabled else LEGACY_FINAL_HEADERS
    all_tables = extract_tables(text)
    tables = find_tables(all_tables, expected_headers) + find_tables(all_tables, legacy_headers)
    if len(tables) != 1:
        raise WorkflowError("module-test-points.md must contain exactly one fixed final table")
    return FinalDocument(
        metadata["最终输入 SHA-256"],
        [cells for _, cells in tables[0].rows],
        tables[0].headers,
    )
