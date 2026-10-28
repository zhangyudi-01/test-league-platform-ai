#!/usr/bin/env python3
"""Pure candidate-document validation shared by single-RSU and batch flows."""

from __future__ import annotations

from pathlib import Path

from common import (
    WorkflowError,
    clean_cell,
    column_value,
    infer_required_data_closures,
    parse_candidate_document,
    parse_context_refs,
    parse_data_closure_refs,
    parse_ref_ids,
    read_text,
    requires_data_closure,
    sha256_text,
)


def _require_nonempty(cells: list[str], row_number: int, headers: tuple[str, ...]) -> None:
    for index, cell in enumerate(cells, start=1):
        if not cell.strip() and headers[index - 1] != "备注":
            raise WorkflowError(f"candidate row {row_number} has an empty cell at column {index}")


def _require_source_part_traceability(text: str, label: str, parent_present: bool) -> None:
    normalized = clean_cell(text)
    if "原文内容" not in normalized:
        raise WorkflowError(f"{label} must explicitly record 原文内容 review")
    if parent_present and "父级条件" not in normalized:
        raise WorkflowError(f"{label} must explicitly record 父级条件 review")


def validate_candidate_document(
    model,
    bundle,
    input_file: Path,
    candidate_file: Path,
    *,
    allowed_rsu_ids: set[str] | None = None,
    allowed_q_ids: set[str] | None = None,
    allowed_context_ids: set[str] | None = None,
    required_context_ids: set[str] | None = None,
    allowed_data_closure_ids: set[str] | None = None,
):
    if not input_file.is_file() or sha256_text(read_text(input_file)) != sha256_text(bundle.rendered):
        raise WorkflowError(f"materialized input is missing or changed: {input_file}")
    if not candidate_file.is_file():
        raise WorkflowError(f"candidate file does not exist: {candidate_file}")
    document = parse_candidate_document(candidate_file, model.data_closure_enabled)
    rsu_id = bundle.rsu.rsu_id
    if document.rsu_id != rsu_id:
        raise WorkflowError(f"candidate metadata RSU-ID must be {rsu_id}, found {document.rsu_id}")
    if document.input_sha256 != bundle.input_sha256:
        raise WorkflowError("candidate input SHA-256 does not match current materialized input")
    if document.result not in {"candidates", "zero-candidate"}:
        raise WorkflowError("生成结果 must be candidates or zero-candidate")
    if document.result == "candidates" and not document.rows:
        raise WorkflowError("生成结果 is candidates but the candidate table is empty")
    if document.result == "zero-candidate":
        if document.rows:
            raise WorkflowError("zero-candidate output must have an empty candidate table")
        if not document.zero_reason or document.zero_reason in {"无", "不适用"} or len(document.zero_reason) < 12:
            raise WorkflowError("zero-candidate requires a concrete rationale of at least 12 characters")

    parent_present = clean_cell(bundle.rsu.cells[1]) != "无"
    if document.result == "zero-candidate":
        _require_source_part_traceability(document.zero_reason, "zero-candidate rationale", parent_present)

    # Single-RSU generation is validated against its materialized InputBundle.
    # Adaptive complex generation may deliberately join several RSUs in one
    # bounded Scope; the caller can then supply that Scope's exact authorization
    # sets. These are replacements, not unions with module-wide data, so a
    # complex candidate still cannot escape its fork packet.
    allowed_rsus = set(bundle.allowed_rsu_ids) if allowed_rsu_ids is None else set(allowed_rsu_ids)
    allowed_qs = set(bundle.allowed_q_ids) if allowed_q_ids is None else set(allowed_q_ids)
    allowed_context = (
        set(bundle.allowed_context_ids)
        if allowed_context_ids is None else set(allowed_context_ids)
    )
    required_context = (
        set(bundle.required_context_ids)
        if required_context_ids is None else set(required_context_ids)
    )
    allowed_data_closures = (
        set(model.data_closure_ids)
        if allowed_data_closure_ids is None else set(allowed_data_closure_ids)
    )
    title_warnings: list[str] = []
    for number, cells in enumerate(document.rows, start=1):
        _require_nonempty(cells, number, document.headers)
        expected_id = f"CAND-{rsu_id}-{number:03d}"
        candidate_id = clean_cell(column_value(document.headers, cells, "候选 ID"))
        if candidate_id != expected_id:
            raise WorkflowError(f"candidate row {number} must use ID {expected_id}, found {candidate_id}")
        primary = clean_cell(column_value(document.headers, cells, "Primary RSU"))
        if primary != rsu_id:
            raise WorkflowError(f"{candidate_id} Primary RSU must be {rsu_id}")
        source_rsus = set(parse_ref_ids(column_value(document.headers, cells, "Source RSUs"), "RSU"))
        if rsu_id not in source_rsus:
            raise WorkflowError(f"{candidate_id} Source RSUs must include {rsu_id}")
        if unknown_rsus := source_rsus - allowed_rsus:
            raise WorkflowError(f"{candidate_id} references RSUs not materialized in input: {sorted(unknown_rsus)}")
        q_refs = set(parse_ref_ids(column_value(document.headers, cells, "Question Refs"), "Q"))
        if unknown_qs := q_refs - allowed_qs:
            raise WorkflowError(f"{candidate_id} references questions not materialized in input: {sorted(unknown_qs)}")
        context_refs = set(
            parse_context_refs(column_value(document.headers, cells, "Context Refs"), iter(model.resources))
        )
        if missing_required := required_context - context_refs:
            raise WorkflowError(f"{candidate_id} is missing required Context Refs: {sorted(missing_required)}")
        if unknown_context := context_refs - allowed_context:
            raise WorkflowError(f"{candidate_id} references context not materialized in input: {sorted(unknown_context)}")
        if model.data_closure_enabled:
            raw_dc_refs = clean_cell(column_value(document.headers, cells, "Data Closure Refs"))
            dc_refs = set(parse_data_closure_refs(raw_dc_refs))
            if raw_dc_refs != "无" and not dc_refs:
                raise WorkflowError(f"{candidate_id} has malformed Data Closure Refs")
            if unknown_dc := dc_refs - set(model.data_closure_ids):
                raise WorkflowError(f"{candidate_id} references undefined data closures: {sorted(unknown_dc)}")
            if unavailable_dc := dc_refs - allowed_data_closures:
                raise WorkflowError(f"{candidate_id} references data closures not materialized in input: {sorted(unavailable_dc)}")
            if missing_dc_context := dc_refs - context_refs:
                raise WorkflowError(
                    f"{candidate_id} Data Closure Refs must also appear in Context Refs: {sorted(missing_dc_context)}"
                )
            business_columns = ("测试维度", "测试点", "可观察结果") if "可观察结果" in document.headers else ("测试项", "测试点", "备注")
            observable = "\n".join(column_value(document.headers, cells, name) for name in business_columns)
            if requires_data_closure(observable):
                dc_materials = [
                    material for material in [*bundle.fixed_materials, *bundle.dynamic_materials]
                    if material.resource_id.startswith("DC-")
                ]
                inferred_dc = infer_required_data_closures(observable, dc_materials)
                if dc_materials and not dc_refs:
                    raise WorkflowError(f"{candidate_id} has explicit data assertions but Data Closure Refs is empty")
                if missing_inferred := inferred_dc - dc_refs:
                    raise WorkflowError(
                        f"{candidate_id} has explicit data assertions but is missing inferred Data Closure Refs: "
                        f"{sorted(missing_inferred)}"
                    )
        _require_source_part_traceability(
            column_value(document.headers, cells, "推导依据"),
            f"{candidate_id} 推导依据",
            parent_present,
        )
    return document, title_warnings
