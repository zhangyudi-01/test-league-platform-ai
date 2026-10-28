#!/usr/bin/env python3
"""Contracts for module-level RSU complexity planning and batching."""

from __future__ import annotations

import json
import re
from collections import OrderedDict
from pathlib import Path
from typing import Any

from common import InputBundle, ModuleModel, WorkflowError, clean_cell, sha256_text

PLAN_SCHEMA_VERSION = "rsu-test-point-generation/plan-v1"
PLAN_FILE = "generation-plan.json"
PLAN_INPUT_FILE = "planning-input.md"
PLAN_STATUSES = {"draft", "validated"}
RSU_MODES = {"simple", "complex"}
RSU_ID_RE = re.compile(r"RSU-\d{3}")
BATCH_ID_RE = re.compile(r"BATCH-\d{3}")
TARGET_BATCH_MIN = 4
TARGET_BATCH_MAX = 6
HARD_BATCH_MAX = 10


def plan_path(output_dir: Path) -> Path:
    return output_dir / PLAN_FILE


def planning_input_path(output_dir: Path) -> Path:
    return output_dir / PLAN_INPUT_FILE


def _resource_kind(resource_id: str) -> str:
    match = re.match(r"[A-Z]+", resource_id)
    return match.group(0) if match else "OTHER"


def context_signature(bundle: InputBundle) -> str:
    """Return a stable compatibility signature without baking in card identity."""

    payload = {
        "fixed": bundle.session_source_fingerprint_sha256,
        "dynamic_kinds": sorted({_resource_kind(item.resource_id) for item in bundle.dynamic_materials}),
        "evidence_kinds": sorted({_resource_kind(item.resource_id) for item in bundle.evidence_materials}),
        "has_questions": bool(bundle.questions),
        "has_supporting_rsus": bool(bundle.supporting_rsus),
        "required_context_kinds": sorted({_resource_kind(item) for item in bundle.required_context_ids}),
    }
    return sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def plan_source_hash(model: ModuleModel, bundles: dict[str, InputBundle]) -> str:
    payload = {
        "manifest_sha256": model.manifest_sha256,
        "fixed_source_fingerprint_sha256": (
            next(iter(bundles.values())).session_source_fingerprint_sha256 if bundles else None
        ),
        "rsus": [
            {
                "rsu_id": rsu.rsu_id,
                "input_sha256": bundles[rsu.rsu_id].input_sha256,
                "context_signature": context_signature(bundles[rsu.rsu_id]),
            }
            for rsu in model.rsus
        ],
    }
    return sha256_text(json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")))


def empty_plan(
    model: ModuleModel,
    bundles: dict[str, InputBundle],
    planning_input_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": PLAN_SCHEMA_VERSION,
        "module_name": model.module_name,
        "source_sha256": plan_source_hash(model, bundles),
        "planning_input_sha256": planning_input_sha256,
        "status": "draft",
        "rsus": [
            {
                "rsu_id": rsu.rsu_id,
                "mode": "unclassified",
                "context_signature": context_signature(bundles[rsu.rsu_id]),
                "batch_id": "",
                "rationale": "",
            }
            for rsu in model.rsus
        ],
    }


def load_plan(output_dir: Path) -> dict[str, Any]:
    path = plan_path(output_dir)
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise WorkflowError(f"generation plan is missing: {path}") from exc
    except json.JSONDecodeError as exc:
        raise WorkflowError(f"invalid generation plan JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise WorkflowError("generation plan root must be an object")
    return value


def validate_plan(
    plan: dict[str, Any],
    model: ModuleModel,
    bundles: dict[str, InputBundle],
    planning_input_sha256: str,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if plan.get("schema_version") != PLAN_SCHEMA_VERSION:
        raise WorkflowError(f"generation plan schema_version must be {PLAN_SCHEMA_VERSION}")
    if plan.get("module_name") != model.module_name:
        raise WorkflowError("generation plan module_name does not match the current module")
    source_sha256 = plan_source_hash(model, bundles)
    if plan.get("source_sha256") != source_sha256:
        raise WorkflowError("generation plan source SHA-256 is stale")
    if plan.get("planning_input_sha256") != planning_input_sha256:
        raise WorkflowError("generation plan planning-input SHA-256 is stale")
    if plan.get("status") not in PLAN_STATUSES or plan.get("status") != "validated":
        raise WorkflowError("generation plan status must be validated")
    raw_rsus = plan.get("rsus")
    if not isinstance(raw_rsus, list):
        raise WorkflowError("generation plan rsus must be an array")
    expected_ids = [item.rsu_id for item in model.rsus]
    found_ids = [item.get("rsu_id") for item in raw_rsus if isinstance(item, dict)]
    if found_ids != expected_ids:
        missing = [item for item in expected_ids if item not in found_ids]
        duplicates = sorted({item for item in found_ids if found_ids.count(item) > 1})
        unknown = [item for item in found_ids if item not in expected_ids]
        raise WorkflowError(
            "generation plan must list every RSU exactly once in map order; "
            f"missing={missing}, duplicates={duplicates}, unknown={unknown}"
        )

    normalized: list[dict[str, str]] = []
    grouped: OrderedDict[str, list[dict[str, str]]] = OrderedDict()
    for index, raw in enumerate(raw_rsus, start=1):
        if not isinstance(raw, dict):
            raise WorkflowError(f"generation plan rsus[{index}] must be an object")
        rsu_id = str(raw.get("rsu_id", "")).strip()
        mode = str(raw.get("mode", "")).strip()
        batch_id = str(raw.get("batch_id", "")).strip()
        signature = str(raw.get("context_signature", "")).strip()
        rationale = clean_cell(str(raw.get("rationale", "")))
        if RSU_ID_RE.fullmatch(rsu_id) is None or mode not in RSU_MODES:
            raise WorkflowError(f"{rsu_id or f'rsus[{index}]'} has invalid mode or identifier")
        if BATCH_ID_RE.fullmatch(batch_id) is None:
            raise WorkflowError(f"{rsu_id} has invalid batch_id: {batch_id}")
        expected_signature = context_signature(bundles[rsu_id])
        if signature != expected_signature:
            raise WorkflowError(f"{rsu_id} context_signature does not match deterministic dependencies")
        if len(rationale) < 4:
            raise WorkflowError(f"{rsu_id} must state a concrete classification rationale")
        item = {
            "rsu_id": rsu_id,
            "mode": mode,
            "context_signature": signature,
            "batch_id": batch_id,
            "rationale": rationale,
        }
        normalized.append(item)
        grouped.setdefault(batch_id, []).append(item)

    expected_batch_ids = [f"BATCH-{index:03d}" for index in range(1, len(grouped) + 1)]
    if list(grouped) != expected_batch_ids:
        raise WorkflowError(
            f"batch IDs must be contiguous in first-appearance order: expected={expected_batch_ids}"
        )
    batches: list[dict[str, Any]] = []
    for batch_id, members in grouped.items():
        modes = {item["mode"] for item in members}
        signatures = {item["context_signature"] for item in members}
        if len(modes) != 1:
            raise WorkflowError(f"{batch_id} mixes simple and complex RSUs")
        mode = next(iter(modes))
        if mode == "complex" and len(members) != 1:
            raise WorkflowError(f"{batch_id} complex mode must contain exactly one RSU")
        if mode == "simple" and len(members) > HARD_BATCH_MAX:
            raise WorkflowError(f"{batch_id} may contain at most {HARD_BATCH_MAX} simple RSUs")
        if mode == "simple" and len(signatures) != 1:
            raise WorkflowError(f"{batch_id} contains incompatible context signatures")
        batches.append(
            {
                "batch_id": batch_id,
                "mode": mode,
                "context_signature": next(iter(signatures)),
                "rsu_ids": [item["rsu_id"] for item in members],
                "rationale": "；".join(item["rationale"] for item in members),
            }
        )
    return {**plan, "rsus": normalized}, batches


def plan_digest(plan: dict[str, Any]) -> str:
    return sha256_text(json.dumps(plan, ensure_ascii=False, sort_keys=True, separators=(",", ":")))
