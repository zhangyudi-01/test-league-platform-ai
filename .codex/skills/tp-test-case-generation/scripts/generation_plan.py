#!/usr/bin/env python3
"""Module-level testcase generation and SQL planning contracts."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from common import WorkflowError, clean_cell, sha256_file, sha256_text

PLAN_SCHEMA_VERSION = "tp-test-case-generation/plan-v2"
PLAN_FILE = "generation-plan.json"
PLAN_INPUT_FILE = "planning-input.md"
SQL_INPUT_FILE = "sql-generation-input.md"
PLAN_STATUS = {"draft", "validated"}
BATCH_MODES = {"simple", "query-display", "complex"}
SQL_PURPOSE_TYPES = {
    "page-filter-result",
    "page-summary-field",
    "page-list-column",
    "page-aggregate",
    "explicit-db-consistency",
}
TP_ID_RE = re.compile(r"TP-\d{3}")
BATCH_ID_RE = re.compile(r"BATCH-\d{3}")
SQL_ID_RE = re.compile(r"SQL-[A-Z0-9]+(?:-[A-Z0-9]+)*")


def plan_path(case_dir: Path) -> Path:
    return case_dir / PLAN_FILE


def planning_input_path(case_dir: Path) -> Path:
    return case_dir / PLAN_INPUT_FILE


def sql_input_path(case_dir: Path) -> Path:
    return case_dir / SQL_INPUT_FILE


def plan_source_hash(source_hashes: dict[str, Any]) -> str:
    return sha256_text(
        json.dumps(source_hashes, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def empty_plan(module_name: str, source_sha256: str) -> dict[str, Any]:
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "module_name": module_name,
        "source_sha256": source_sha256,
        "status": "draft",
        "sql_assets": [],
        "batches": [],
    }


def load_plan(case_dir: Path) -> dict[str, Any]:
    path = plan_path(case_dir)
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"generation plan is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"invalid generation plan JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError("generation plan root must be an object")
    return value


def _string_list(value: Any, label: str, pattern: re.Pattern[str] | None = None) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise WorkflowError(f"{label} must be a string array")
    result = [item.strip() for item in value]
    if any(not item for item in result):
        raise WorkflowError(f"{label} contains an empty value")
    if len(result) != len(set(result)):
        raise WorkflowError(f"{label} contains duplicates")
    if pattern is not None and any(pattern.fullmatch(item) is None for item in result):
        raise WorkflowError(f"{label} contains an invalid identifier")
    return result


def validate_plan(
    plan: dict[str, Any],
    *,
    module_name: str,
    source_sha256: str,
    points: list[Any],
    known_dc_ids: set[str],
) -> dict[str, Any]:
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise WorkflowError(f"generation plan schema_version must be {PLAN_SCHEMA_VERSION}")
    if plan.get("module_name") != module_name:
        raise WorkflowError("generation plan module_name does not match the current module")
    if plan.get("source_sha256") != source_sha256:
        raise WorkflowError("generation plan source SHA-256 is stale")
    if plan.get("status") not in PLAN_STATUS:
        raise WorkflowError("generation plan status must be draft or validated")
    if plan.get("status") != "validated":
        raise WorkflowError("generation plan status must be validated before it can be accepted")

    expected_tps = [point.tp_id for point in points]
    expected_set = set(expected_tps)
    raw_sql = plan.get("sql_assets")
    raw_batches = plan.get("batches")
    if not isinstance(raw_sql, list) or not isinstance(raw_batches, list):
        raise WorkflowError("generation plan sql_assets and batches must be arrays")

    sql_assets: list[dict[str, Any]] = []
    sql_ids: set[str] = set()
    sql_by_tp: dict[str, set[str]] = {tp_id: set() for tp_id in expected_tps}
    for index, raw in enumerate(raw_sql, start=1):
        if not isinstance(raw, dict):
            raise WorkflowError(f"sql_assets[{index}] must be an object")
        sql_id = str(raw.get("sql_id", "")).strip()
        if SQL_ID_RE.fullmatch(sql_id) is None or sql_id in sql_ids:
            raise WorkflowError(f"sql_assets[{index}] has invalid or duplicate sql_id: {sql_id}")
        purpose_type = str(raw.get("purpose_type", "")).strip()
        if purpose_type not in SQL_PURPOSE_TYPES:
            raise WorkflowError(
                f"{sql_id} purpose_type must be one of {sorted(SQL_PURPOSE_TYPES)}"
            )
        purpose = clean_cell(str(raw.get("purpose", "")))
        rationale = clean_cell(str(raw.get("rationale", "")))
        functional_module = clean_cell(str(raw.get("functional_module", "")))
        if len(functional_module) < 2:
            raise WorkflowError(
                f"{sql_id} functional_module must name the page feature area served by this SQL"
            )
        if len(purpose) < 4 or len(rationale) < 6:
            raise WorkflowError(f"{sql_id} must state a concrete purpose and SQL necessity rationale")
        tp_refs = _string_list(raw.get("tp_refs"), f"{sql_id} tp_refs", TP_ID_RE)
        if not tp_refs or not set(tp_refs) <= expected_set:
            raise WorkflowError(f"{sql_id} tp_refs must be non-empty and belong to this module")
        dc_refs = _string_list(raw.get("data_closure_refs", []), f"{sql_id} data_closure_refs")
        if not set(dc_refs) <= known_dc_ids:
            raise WorkflowError(f"{sql_id} contains unknown Data Closure Refs")
        if str(raw.get("statement_type", "SELECT")).upper() != "SELECT":
            raise WorkflowError(
                f"{sql_id} must be SELECT; this Skill describes writes in expected records instead of generating DML"
            )
        for tp_id in tp_refs:
            sql_by_tp[tp_id].add(sql_id)
        sql_ids.add(sql_id)
        sql_assets.append(
            {
                "sql_id": sql_id,
                "statement_type": "SELECT",
                "purpose_type": purpose_type,
                "functional_module": functional_module,
                "purpose": purpose,
                "rationale": rationale,
                "tp_refs": tp_refs,
                "data_closure_refs": dc_refs,
            }
        )

    batches: list[dict[str, Any]] = []
    seen_tps: list[str] = []
    seen_batch_ids: set[str] = set()
    for index, raw in enumerate(raw_batches, start=1):
        if not isinstance(raw, dict):
            raise WorkflowError(f"batches[{index}] must be an object")
        batch_id = str(raw.get("batch_id", "")).strip()
        expected_batch_id = f"BATCH-{index:03d}"
        if batch_id != expected_batch_id or batch_id in seen_batch_ids:
            raise WorkflowError(f"batch IDs must be contiguous; expected {expected_batch_id}")
        mode = str(raw.get("mode", "")).strip()
        if mode not in BATCH_MODES:
            raise WorkflowError(f"{batch_id} mode must be one of {sorted(BATCH_MODES)}")
        tp_ids = _string_list(raw.get("tp_ids"), f"{batch_id} tp_ids", TP_ID_RE)
        if not tp_ids or not set(tp_ids) <= expected_set:
            raise WorkflowError(f"{batch_id} tp_ids must belong to this module")
        if mode == "complex" and len(tp_ids) != 1:
            raise WorkflowError(f"{batch_id} complex mode must contain exactly one TP")
        if mode != "complex" and len(tp_ids) > 10:
            raise WorkflowError(f"{batch_id} may contain at most 10 TPs")
        if tp_ids != sorted(tp_ids, key=expected_tps.index):
            raise WorkflowError(f"{batch_id} TP order must follow the final test-point order")
        rationale = clean_cell(str(raw.get("rationale", "")))
        if len(rationale) < 4:
            raise WorkflowError(f"{batch_id} must state a concrete batching rationale")
        batch_sql = _string_list(raw.get("sql_refs", []), f"{batch_id} sql_refs", SQL_ID_RE)
        expected_sql = sorted({sql_id for tp_id in tp_ids for sql_id in sql_by_tp[tp_id]})
        if sorted(batch_sql) != expected_sql:
            raise WorkflowError(
                f"{batch_id} sql_refs must equal the SQL assigned to its TPs; "
                f"expected={expected_sql}, found={sorted(batch_sql)}"
            )
        seen_tps.extend(tp_ids)
        seen_batch_ids.add(batch_id)
        batches.append(
            {
                "batch_id": batch_id,
                "mode": mode,
                "tp_ids": tp_ids,
                "sql_refs": batch_sql,
                "rationale": rationale,
            }
        )

    if seen_tps != expected_tps:
        missing = [tp for tp in expected_tps if tp not in seen_tps]
        duplicates = sorted({tp for tp in seen_tps if seen_tps.count(tp) > 1})
        raise WorkflowError(
            "generation plan must assign every TP exactly once in final order; "
            f"missing={missing}, duplicates={duplicates}"
        )
    return {
        **plan,
        "sql_assets": sql_assets,
        "batches": batches,
        "sql_by_tp": {tp_id: sorted(sql_by_tp[tp_id]) for tp_id in expected_tps},
    }


def plan_digest(plan: dict[str, Any]) -> str:
    return sha256_text(json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")))

