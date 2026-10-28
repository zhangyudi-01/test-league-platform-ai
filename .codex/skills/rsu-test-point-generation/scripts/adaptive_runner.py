#!/usr/bin/env python3
"""Module-level baseline runner for adaptive RSU test-point generation.

The module baseline is intentionally small: deterministic input preparation,
one bounded Codex turn, deterministic validation, and optional local forks.
The older foundation/batch implementation remains available as a compatibility
route in ``run_generation.py``.
"""

from __future__ import annotations

import inspect
import json
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from candidate_validation import validate_candidate_document
from adaptive_worker import (
    DEFAULT_PACKET_BUDGET_BYTES,
    compile_baseline_worker_packet,
    compile_complex_generation_packet,
    detect_complex_generation_scopes,
    load_semantic_result,
    merge_complex_generation_result,
    normalize_complex_scope_dispositions,
    required_context_dispositions,
    render_candidate_artifacts,
    render_final_artifacts,
    semantic_baseline_json_schema,
    validate_semantic_baseline_result,
    validate_complex_generation_result,
    worker_prompt,
    write_worker_schemas,
)
from common import (
    RSU_HEADERS,
    WorkflowError,
    atomic_write_json,
    atomic_write_text,
    build_bundle,
    display_path,
    ensure_adaptive_state,
    load_state,
    parse_module,
    reconcile_state,
    record_paths,
    resolve_module_layout,
    run_preanalysis_validation,
    sha256_file,
    sha256_text,
    state_lock,
    state_path,
    utc_now,
)


BASELINE_RESULT_SCHEMA = "rsu-test-point-generation/baseline-v1"


def _layout_args(config: Any) -> list[str]:
    result = [str(config.module_dir)]
    if config.manifest is not None:
        result += ["--manifest", str(config.manifest)]
    if config.preanalysis_dir is not None:
        result += ["--preanalysis-dir", str(config.preanalysis_dir)]
    if config.output_dir is not None:
        result += ["--output-dir", str(config.output_dir)]
    return result


def _now_run_dir(config: Any, output_dir: Path) -> Path:
    root = config.logs_dir or output_dir / "runner-logs"
    run_dir = root / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8])
    run_dir.mkdir(parents=True, exist_ok=False)
    return run_dir


def _path_key(path: Path) -> str:
    """Return a stable path identity that also deduplicates Windows aliases."""

    return str(path.resolve()).casefold()


def _render_baseline_input(
    model: Any,
    state: dict,
    output_dir: Path,
    bundles: dict[str, Any],
) -> str:
    """Render the module input from the union of materialized RSU dependencies.

    The preanalysis map can register large evidence documents that only a focused
    FC/DC card cites for provenance. Those files belong in the source index, but
    copying every registered resource body into the baseline defeats dependency
    scoping and duplicates the same module artifacts under several aliases.
    """

    del state  # Kept in the signature for compatibility with existing callers.

    body_groups: dict[str, dict[str, Any]] = {}
    question_rows: dict[str, Any] = {}
    evidence_keys: set[str] = set()
    for bundle in bundles.values():
        for material in [*bundle.fixed_materials, *bundle.dynamic_materials]:
            key = _path_key(material.path)
            group = body_groups.setdefault(
                key,
                {
                    "path": material.path,
                    "content": material.content,
                    "resource_ids": [],
                    "roles": [],
                },
            )
            if material.resource_id not in group["resource_ids"]:
                group["resource_ids"].append(material.resource_id)
            if material.role not in group["roles"]:
                group["roles"].append(material.role)
        for question in bundle.questions:
            question_rows.setdefault(question.q_id, question)
        for evidence in bundle.evidence_materials:
            evidence_keys.add(_path_key(evidence.path))

    source_groups: dict[str, dict[str, Any]] = {}

    def register_source(
        path: Path,
        *,
        artifact_label: str | None = None,
        resource_id: str | None = None,
        purpose: str | None = None,
    ) -> None:
        if not path.is_file():
            return
        key = _path_key(path)
        group = source_groups.setdefault(
            key,
            {
                "path": path,
                "artifact_labels": [],
                "resource_ids": [],
                "purposes": [],
            },
        )
        if artifact_label and artifact_label not in group["artifact_labels"]:
            group["artifact_labels"].append(artifact_label)
        if resource_id and resource_id not in group["resource_ids"]:
            group["resource_ids"].append(resource_id)
        if purpose and purpose not in group["purposes"]:
            group["purposes"].append(purpose)

    for label, path in sorted(model.artifact_paths.items()):
        register_source(path, artifact_label=label)
    if model.manifest_path is not None:
        register_source(model.manifest_path, artifact_label="preanalysis-manifest")
    for resource_id, resource in sorted(model.resources.items()):
        register_source(
            resource.path,
            resource_id=resource_id,
            purpose=resource.purpose,
        )

    sections: list[str] = [
        "# 模块级测试点基线输入",
        "",
        f"- 模块：`{model.module_name}`",
        f"- 模块目录：`{model.module_dir}`",
        f"- RSU 数量：{len(model.rsus)}",
        "- 本输入是唯一事实源；不得读取 runner-logs、其他模块或旧会话历史。",
        "- 测试点数量不是目标；一个测试点可以覆盖多个 RSU，一个 RSU 也可以零候选。",
        "- 正文仅展开全部 RSU 实际物化依赖的并集；其他已登记来源只保留定位、用途和指纹。",
        "",
    ]

    sections.extend([
        "## 来源与依赖索引",
        "",
        "| 文件 | Artifact 别名 | Resource ID | 用途 | 正文处理 | SHA-256 |",
        "|---|---|---|---|---|---|",
    ])
    for key, group in sorted(
        source_groups.items(),
        key=lambda item: display_path(item[1]["path"], model.module_dir).casefold(),
    ):
        path = group["path"]
        handling = "已物化一次" if key in body_groups else (
            "证据索引，不展开" if key in evidence_keys else "登记来源，不展开"
        )
        cells = [
            f"`{display_path(path, model.module_dir)}`",
            "、".join(group["artifact_labels"]) or "无",
            "、".join(group["resource_ids"]) or "无",
            "；".join(group["purposes"]) or "无",
            handling,
            f"`{sha256_file(path)}`",
        ]
        sections.append("| " + " | ".join(cell.replace("|", "\\|") for cell in cells) + " |")

    sections.extend(["", "## 已物化依赖正文（按文件去重）", ""])
    for _, group in sorted(
        body_groups.items(),
        key=lambda item: (
            0 if "fixed" in item[1]["roles"] else 1,
            ",".join(item[1]["resource_ids"]),
        ),
    ):
        content = group["content"]
        aliases = "、".join(group["resource_ids"])
        sections.extend([
            f"### {aliases}",
            f"- 角色：{'、'.join(group['roles'])}",
            f"- SHA-256：`{sha256_text(content)}`",
            "",
            content.rstrip(),
            "",
        ])

    sections.extend(["## 相关问题（仅 RSU 实际引用）", ""])
    if question_rows:
        for q_id, question in sorted(question_rows.items()):
            headers = [str(cell).replace("|", "\\|") for cell in question.headers]
            cells = [str(cell).replace("\n", "<br>").replace("|", "\\|") for cell in question.cells]
            sections.extend([
                f"### {q_id}",
                "",
                "| " + " | ".join(headers) + " |",
                "|" + "|".join("---" for _ in headers) + "|",
                "| " + " | ".join(cells) + " |",
                "",
            ])
    else:
        sections.extend(["无", ""])

    sections.extend([
        "## RSU 清单",
        "",
        "| " + " | ".join(RSU_HEADERS) + " |",
        "|" + "|".join("---" for _ in RSU_HEADERS) + "|",
    ])
    for rsu in model.rsus:
        cells = [str(cell).replace("\n", "<br>").replace("|", "\\|") for cell in rsu.cells]
        sections.append("| " + " | ".join(cells) + " |")
    sections.extend([
        "",
        "## 语义输出边界",
        "",
        "- 子 Worker 只返回结构化语义，不读取或写入任何文件。",
        "- 候选编号、TP 编号、Markdown、覆盖矩阵和状态均由父 Runner 确定性生成。",
    ])
    return "\n".join(sections).rstrip() + "\n"


def prepare_baseline_input(config: Any, output_dir: Path) -> tuple[Path, dict, Any, str]:
    layout = resolve_module_layout(config.module_dir, config.preanalysis_dir, config.manifest)
    run_preanalysis_validation(layout, output_dir)
    model = parse_module(layout)
    with state_lock(output_dir):
        state = load_state(output_dir, layout)
        if state is None:
            raise WorkflowError("generation state does not exist; run init_generation.py first")
        state, bundles = reconcile_state(model, output_dir, state)
        ensure_adaptive_state(state)
        for rsu_id, bundle in bundles.items():
            input_path, _ = record_paths(output_dir, rsu_id)
            input_path.parent.mkdir(parents=True, exist_ok=True)
            if not input_path.is_file() or sha256_text(input_path.read_text(encoding="utf-8")) != sha256_text(bundle.rendered):
                atomic_write_text(input_path, bundle.rendered)
        text = _render_baseline_input(model, state, output_dir, bundles)
        input_path = output_dir / "baseline-input.md"
        input_hash = sha256_text(text)
        previous = state.get("baseline", {})
        if previous.get("input_sha256") != input_hash or not input_path.is_file():
            atomic_write_text(input_path, text)
            state["baseline"] = {
                **previous,
                "status": "prepared",
                "input_file": "baseline-input.md",
                "input_sha256": input_hash,
                "result_file": "baseline-result.json",
                "result_sha256": None,
                "validated_at": None,
            }
        state["architecture"] = "module-baseline"
        state["session_source_fingerprint_sha256"] = input_hash
        state["updated_at"] = utc_now()
        atomic_write_json(state_path(output_dir), state)
    return input_path, state, model, input_hash


def _invoke(invoke_fn: Callable[..., Any], config: Any, run_dir: Path, prompt: str) -> Any:
    signature = inspect.signature(invoke_fn)
    try:
        signature.bind(config, run_dir, 1, "baseline", prompt, None, None)
    except TypeError:
        return invoke_fn(config, run_dir, 1, "baseline", prompt, None)
    return invoke_fn(config, run_dir, 1, "baseline", prompt, None, None)


def _invoke_worker(
    invoke_fn: Callable[..., Any],
    config: Any,
    run_dir: Path,
    turn_number: int,
    phase: str,
    prompt: str,
    scope_id: str | None,
    *,
    fork_from: str | None = None,
    output_schema: Path | None = None,
) -> Any:
    """Invoke an injected worker while retaining compatibility with narrow fakes."""

    signature = inspect.signature(invoke_fn)
    accepts_kwargs = any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD
        for parameter in signature.parameters.values()
    )
    kwargs: dict[str, Any] = {}
    if accepts_kwargs or "fork_from" in signature.parameters:
        kwargs["fork_from"] = fork_from
    if accepts_kwargs or "output_schema" in signature.parameters:
        kwargs["output_schema"] = output_schema
    if accepts_kwargs or "session" in signature.parameters:
        from run_generation import CodexSession
        kwargs["session"] = CodexSession("isolated")
    return invoke_fn(config, run_dir, turn_number, phase, prompt, scope_id, **kwargs)


def _complex_scope_authorizations(
    scopes: list[dict[str, Any]], fixed_resource_ids: tuple[str, ...]
) -> dict[str, dict[str, set[str]]]:
    """Map each complex RSU to the exact authorization carried by its Scope."""

    authorizations: dict[str, dict[str, set[str]]] = {}
    for scope in scopes:
        data_closure_refs = set(scope.get("data_closure_refs", []))
        authorization = {
            "allowed_rsu_ids": set(scope.get("rsu_ids", [])),
            "allowed_q_ids": set(scope.get("question_refs", [])),
            # Candidate documents must repeat every DC ID in context_refs.
            # Scope routing keeps DC IDs in a separate field, therefore the
            # publication authorization must explicitly union both fields.
            "allowed_context_ids": (
                set(fixed_resource_ids)
                | set(scope.get("context_refs", []))
                | data_closure_refs
            ),
            "required_context_ids": set(fixed_resource_ids),
            "allowed_data_closure_ids": data_closure_refs,
        }
        for rsu_id in scope.get("rsu_ids", []):
            if rsu_id in authorizations:
                raise WorkflowError(f"complex RSU is assigned to multiple scopes: {rsu_id}")
            authorizations[rsu_id] = authorization
    return authorizations


def _bundle_authorizations(model: Any) -> dict[str, dict[str, set[str]]]:
    """Build the exact semantic authorization carried by each RSU input bundle."""

    data_closure_ids = set(model.data_closure_ids)
    result: dict[str, dict[str, set[str]]] = {}
    for rsu in model.rsus:
        bundle = build_bundle(model, rsu)
        allowed_context_ids = set(bundle.allowed_context_ids)
        result[rsu.rsu_id] = {
            "allowed_rsu_ids": set(bundle.allowed_rsu_ids),
            "allowed_q_ids": set(bundle.allowed_q_ids),
            "allowed_context_ids": allowed_context_ids,
            "required_context_ids": set(bundle.required_context_ids),
            "allowed_data_closure_ids": allowed_context_ids & data_closure_ids,
        }
    return result


def _mark_validated(
    config: Any,
    output_dir: Path,
    model: Any,
    result: dict,
    input_hash: str,
    *,
    complex_scope_authorizations: dict[str, dict[str, set[str]]] | None = None,
) -> dict:
    layout = resolve_module_layout(config.module_dir, config.preanalysis_dir, config.manifest)
    with state_lock(output_dir):
        state = load_state(output_dir, layout)
        if state is None:
            raise WorkflowError("generation state disappeared during baseline run")
        state, bundles = reconcile_state(model, output_dir, state)
        dispositions = {row["rsu_id"]: row for row in result["rsus"]}
        for record in state["rsus"]:
            rsu_id = record["rsu_id"]
            row = dispositions[rsu_id]
            candidate_path = output_dir / "by-rsu" / f"{rsu_id}.md"
            if row["status"] in {"generated", "zero-test-points"}:
                authorization = dict(
                    (complex_scope_authorizations or {}).get(rsu_id, {})
                )
                # Semantic validation carries its own required-context set.
                # Publication keeps the existing per-RSU required inputs and
                # passes only Scope widening fields to candidate validation.
                authorization.pop("required_context_ids", None)
                document, _ = validate_candidate_document(
                    model,
                    bundles[rsu_id],
                    output_dir / "inputs" / f"{rsu_id}-input.md",
                    candidate_path,
                    required_context_ids=set(bundles[rsu_id].required_context_ids),
                    **authorization,
                )
                record.update({
                    "generation_status": "validated",
                    "input_sha256": bundles[rsu_id].input_sha256,
                    "current_input_sha256": bundles[rsu_id].input_sha256,
                    "output_sha256": sha256_file(candidate_path),
                    "candidate_count": len(document.rows),
                    "validated_at": utc_now(),
                    "blockers": [],
                    "adaptive_disposition": row["status"],
                    "adaptive_reason": row.get("reason"),
                })
            else:
                record["generation_status"] = "blocked"
                record["blockers"] = [str(row.get("reason"))]
                record["adaptive_disposition"] = row["status"]
                record["adaptive_reason"] = row.get("reason")
        pending = [item for item in state["rsus"] if item["generation_status"] != "validated"]
        if pending:
            state["baseline"]["status"] = "needs-fork"
            state["adaptive"]["completion"] = {"status": "pending", "reasons": ["one or more RSUs need fork or are blocked"]}
        else:
            state["baseline"]["status"] = "validated"
            state["baseline"]["input_sha256"] = input_hash
            state["baseline"]["result_sha256"] = sha256_file(output_dir / "baseline-result.json")
            state["baseline"]["validated_at"] = utc_now()
            state["finalization"] = {
                "status": "ready", "input_sha256": None, "input_document_sha256": None,
                "validated_at": None, "module_test_points_sha256": None, "coverage_matrix_sha256": None,
            }
            state["adaptive"]["completion"] = {"status": "pending", "reasons": []}
        state["updated_at"] = utc_now()
        atomic_write_json(state_path(output_dir), state)
        return state


def _run_script(config: Any, script_name: str) -> str:
    command = [sys.executable, "-B", str(Path(__file__).with_name(script_name)), *_layout_args(config)]
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace")
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    if result.returncode:
        raise WorkflowError(f"{script_name} failed:\n{output}")
    return output


def _run_optional_readiness(config: Any, output_dir: Path, run_dir: Path, invoke_fn: Callable[..., Any] | None, turn_number: int) -> tuple[str | None, int]:
    _run_script(config, "prepare_case_readiness.py")
    prompt = (
        "只执行测试用例生成就绪性审查。读取 case-readiness-input.md 和 Skill 的 readiness 契约，"
        "只修改 test-case-readiness.md；不得修改测试点、候选、状态或来源，也不得运行准备、校验或 Runner 脚本。"
        "父 Runner 会执行 validate_case_readiness.py。"
    )
    if invoke_fn is None:
        from run_generation import CodexSession, invoke_codex
        result = invoke_codex(config, run_dir, turn_number, "case-readiness", prompt, None, session=CodexSession("isolated"))
    else:
        result = _invoke(invoke_fn, config, run_dir, prompt)
    if getattr(result, "returncode", 1) != 0:
        raise WorkflowError("optional readiness turn failed")
    _run_script(config, "validate_case_readiness.py")
    layout = resolve_module_layout(config.module_dir, config.preanalysis_dir, config.manifest)
    state = load_state(output_dir, layout) or {}
    readiness = state.get("case_readiness", {})
    return readiness.get("result"), 1


def _aggregate_turn_metrics(turns: list[Any]) -> tuple[int | None, dict[str, int]]:
    tool_values = [getattr(turn, "tool_calls", None) for turn in turns]
    tool_calls = None if any(value is None for value in tool_values) else sum(tool_values)
    usage: dict[str, int] = {}
    for turn in turns:
        current = getattr(turn, "usage", {}) or {}
        for key, value in current.items():
            if isinstance(value, int):
                usage[key] = usage.get(key, 0) + value
    return tool_calls, usage


def _merge_adaptive_metrics(
    existing: dict[str, Any] | None,
    invocation: dict[str, Any],
    *,
    reused: bool,
) -> dict[str, Any]:
    """Keep original generation cost while recording zero-call resume checks."""

    if not reused or not existing:
        return invocation
    preserved = dict(existing)
    resume_history = list(preserved.get("resume_history", []))
    resume_history.append(invocation)
    preserved["resume_history"] = resume_history
    preserved["last_resume"] = invocation
    return preserved


def _prepare_worker_contract(
    config: Any,
    output_dir: Path,
    model: Any,
    business_input_path: Path,
    business_input_sha256: str,
) -> tuple[Path, Path, str, dict[str, str], list[dict[str, Any]]]:
    baseline_schema_path, complex_schema_path = write_worker_schemas(output_dir)
    schema = semantic_baseline_json_schema()
    try:
        packet, fingerprints, risks = compile_baseline_worker_packet(
            model,
            business_input_path.read_text(encoding="utf-8-sig"),
            business_input_sha256,
            sha256_file(baseline_schema_path),
            schema,
            packet_budget_bytes=getattr(
                config, "worker_packet_budget_bytes", DEFAULT_PACKET_BUDGET_BYTES
            ),
            baseline_only=getattr(config, "baseline_only", False),
        )
    except WorkflowError as exc:
        layout = resolve_module_layout(config.module_dir, config.preanalysis_dir, config.manifest)
        with state_lock(output_dir):
            state = load_state(output_dir, layout) or {}
            baseline = state.setdefault("baseline", {})
            baseline.update({
                "status": "context-pressure",
                "business_input_sha256": business_input_sha256,
                "context_pressure": str(exc),
            })
            state["updated_at"] = utc_now()
            atomic_write_json(state_path(output_dir), state)
        raise
    packet_path = output_dir / "baseline-worker-packet.md"
    atomic_write_text(packet_path, packet)
    layout = resolve_module_layout(config.module_dir, config.preanalysis_dir, config.manifest)
    with state_lock(output_dir):
        state = load_state(output_dir, layout) or {}
        baseline = state.setdefault("baseline", {})
        previous_contract = {
            key: baseline.get(key) for key in fingerprints
        }
        if previous_contract != fingerprints:
            baseline["status"] = "prepared"
            baseline["semantic_result_sha256"] = None
            baseline["validated_at"] = None
        baseline.update(fingerprints)
        baseline.update({
            "business_input_sha256": business_input_sha256,
            "packet_file": packet_path.name,
            "packet_bytes": len(packet.encode("utf-8")),
            "semantic_result_file": "worker-results/baseline.json",
            "context_pressure": None,
        })
        state["updated_at"] = utc_now()
        atomic_write_json(state_path(output_dir), state)
    return baseline_schema_path, complex_schema_path, packet, fingerprints, risks


def _legacy_baseline_manifest(
    semantic: dict[str, Any], assigned: dict[str, Any], business_input_sha256: str
) -> dict[str, Any]:
    candidate_ids = assigned["candidate_id_by_key"]
    return {
        "schema": BASELINE_RESULT_SCHEMA,
        "input_sha256": business_input_sha256,
        "rsus": [
            {
                "rsu_id": row["rsu_id"],
                "status": row["status"],
                "candidate_ids": [candidate_ids[key] for key in row["candidate_keys"]],
                "reason": row["reason"],
            }
            for row in semantic["rsus"]
        ],
    }


def _load_worker_message(turn: Any) -> dict[str, Any]:
    path = getattr(turn, "last_message", None)
    if not isinstance(path, Path):
        if isinstance(path, str):
            path = Path(path)
        else:
            raise WorkflowError("semantic worker did not expose its final response file")
    return load_semantic_result(path)


def _load_reusable_baseline(
    semantic_path: Path,
    baseline_state: dict[str, Any],
    fingerprints: dict[str, str],
    model: Any,
    authorizations: dict[str, dict[str, set[str]]],
    *,
    baseline_only: bool = False,
) -> dict[str, Any] | None:
    """Load only a hash-matched result that passes baseline-only authorization."""

    if not (
        baseline_state.get("status") == "validated"
        and baseline_state.get("packet_sha256") == fingerprints["packet_sha256"]
        and semantic_path.is_file()
        and baseline_state.get("semantic_result_sha256") == sha256_file(semantic_path)
    ):
        return None
    try:
        semantic = load_semantic_result(semantic_path)
        validate_semantic_baseline_result(
            semantic,
            model,
            fingerprints["packet_sha256"],
            require_pre_generation_routing=not baseline_only,
            baseline_only=baseline_only,
            rsu_authorizations=authorizations,
        )
    except (OSError, ValueError, WorkflowError):
        # Older runners could persist merged fork candidates as the baseline.
        return None
    return semantic


def _baseline_validation_repair_prompt(
    semantic: dict[str, Any],
    error: Exception,
    model: Any,
    packet_sha256: str,
    *,
    baseline_only: bool = False,
) -> str:
    """Build a bounded zero-tool repair request for a baseline contract error."""

    routing_instruction = (
        "Keep every RSU in this baseline run: all dispositions must be generated or zero-test-points, "
        "with no complex scopes and no needs-fork/blocked dispositions. Do not create fork routes. "
        if baseline_only
        else "Preserve the existing RSU classification, complex-scope routing, candidates, and the parent-maintained "
        "compatibility final_intents mapping unless a change is strictly required by the validation error. "
    )
    return (
        "Repair the previous semantic baseline JSON so it passes the deterministic parent validation. "
        "Return the complete corrected JSON only. Do not use tools or read any path. "
        + routing_instruction
        + f"packet_sha256 must remain {packet_sha256}.\n\n"
        "Validation error:\n"
        f"{error}\n\n"
        "The context_dispositions identities must equal this exact ledger:\n"
        + json.dumps(required_context_dispositions(model), ensure_ascii=False, indent=2)
        + "\n\nPrevious JSON to repair:\n"
        + json.dumps(semantic, ensure_ascii=False, indent=2)
    )


def _invoke_semantic_worker(
    config: Any,
    run_dir: Path,
    turn_number: int,
    phase: str,
    prompt: str,
    scope_id: str | None,
    output_schema: Path,
    invoke_fn: Callable[..., Any] | None,
    *,
    fork_from: str | None = None,
) -> Any:
    if invoke_fn is None:
        from run_generation import CodexSession, invoke_codex
        turn = invoke_codex(
            config,
            run_dir,
            turn_number,
            phase,
            prompt,
            scope_id,
            fork_from=fork_from,
            session=CodexSession("isolated"),
            output_schema=output_schema,
        )
    else:
        turn = _invoke_worker(
            invoke_fn,
            config,
            run_dir,
            turn_number,
            phase,
            prompt,
            scope_id,
            fork_from=fork_from,
            output_schema=output_schema,
        )
    if getattr(turn, "returncode", 1) != 0:
        raise WorkflowError(f"{phase} semantic worker failed; inspect the private run log")
    tool_calls = getattr(turn, "tool_calls", None)
    if tool_calls != 0:
        raise WorkflowError(
            f"{phase} semantic worker violated the zero-tool contract: tool_calls={tool_calls!r}"
        )
    return turn


def _run_complex_generations(
    config: Any,
    output_dir: Path,
    model: Any,
    semantic: dict[str, Any],
    scopes: list[dict[str, Any]],
    fingerprints: dict[str, str],
    complex_schema_path: Path,
    run_dir: Path,
    invoke_fn: Callable[..., Any] | None,
    baseline_thread_id: str | None,
    baseline_authorizations: dict[str, dict[str, set[str]]],
    start_turn_number: int = 2,
) -> tuple[dict[str, Any], list[Any]]:
    if not scopes:
        return semantic, []
    layout = resolve_module_layout(config.module_dir, config.preanalysis_dir, config.manifest)
    turns: list[Any] = []
    current = normalize_complex_scope_dispositions(semantic, scopes)
    merged_authorizations = dict(baseline_authorizations)
    for index, scope in enumerate(scopes, start=start_turn_number):
        materialized_context_ids = {
            material.resource_id
            for rsu_id in scope["rsu_ids"]
            for bundle in [build_bundle(model, model.rsu_by_id[rsu_id])]
            for material in [*bundle.fixed_materials, *bundle.dynamic_materials]
        }
        packet, complex_fingerprints = compile_complex_generation_packet(
            model,
            current,
            scope,
            fingerprints,
            packet_budget_bytes=getattr(
                config, "worker_packet_budget_bytes", DEFAULT_PACKET_BUDGET_BYTES
            ),
            materialized_context_ids=materialized_context_ids,
        )
        packet_hash = complex_fingerprints["packet_sha256"]
        packet_path = output_dir / "fork-inputs" / f"{scope['scope_id']}-worker-packet.md"
        result_path = output_dir / "fork-results" / f"{scope['scope_id']}-semantic.json"
        packet_path.parent.mkdir(parents=True, exist_ok=True)
        result_path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(packet_path, packet)
        state = load_state(output_dir, layout) or {}
        existing = next((
            row for row in state.get("adaptive", {}).get("forks", [])
            if row.get("scope_id") == scope["scope_id"]
        ), None)
        reused = bool(
            existing
            and existing.get("status") == "validated"
            and existing.get("packet_sha256") == packet_hash
            and result_path.is_file()
            and existing.get("result_sha256") == sha256_file(result_path)
        )
        if reused:
            complex_result = load_semantic_result(result_path)
            complex_thread_id = existing.get("thread_id")
        else:
            turn = _invoke_semantic_worker(
                config,
                run_dir,
                index,
                "complex-generation",
                worker_prompt(packet, packet_hash, complex_scope=True),
                scope["scope_id"],
                complex_schema_path,
                invoke_fn,
                fork_from=baseline_thread_id,
            )
            complex_result = _load_worker_message(turn)
            complex_thread_id = getattr(turn, "thread_id", None)
            turns.append(turn)
        validate_complex_generation_result(complex_result, model, scope, packet_hash)
        if not reused:
            atomic_write_json(result_path, complex_result)
        current = merge_complex_generation_result(current, scope, complex_result)
        merged_authorizations.update(
            _complex_scope_authorizations([scope], model.fixed_resource_ids)
        )
        validate_semantic_baseline_result(
            current,
            model,
            fingerprints["packet_sha256"],
            require_pre_generation_routing=False,
            rsu_authorizations=merged_authorizations,
        )
        with state_lock(output_dir):
            state = load_state(output_dir, layout) or {}
            adaptive = ensure_adaptive_state(state).setdefault("adaptive", {})
            forks = adaptive.setdefault("forks", [])
            forks[:] = [row for row in forks if row.get("scope_id") != scope["scope_id"]]
            forks.append({
                "scope_id": scope["scope_id"],
                "kind": "complex-generation",
                "routing_phase": "pre-generation",
                "rsu_ids": scope["rsu_ids"],
                "candidate_keys": scope["candidate_keys"],
                "status": "validated",
                "packet_sha256": packet_hash,
                "result_sha256": sha256_file(result_path),
                "thread_id": complex_thread_id,
                "validated_at": utc_now(),
            })
            state["updated_at"] = utc_now()
            atomic_write_json(state_path(output_dir), state)
    return current, turns


def _prepare_and_render_finalization(
    config: Any,
    output_dir: Path,
    model: Any,
    semantic: dict[str, Any],
    assigned: dict[str, Any],
) -> None:
    """Let the parent prepare the hash, render both formal files, and validate."""

    _run_script(config, "prepare_finalization.py")
    layout = resolve_module_layout(config.module_dir, config.preanalysis_dir, config.manifest)
    state = load_state(output_dir, layout) or {}
    final_hash = state.get("finalization", {}).get("input_sha256")
    if not isinstance(final_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", final_hash):
        raise WorkflowError("parent finalization preparation did not produce a stable input hash")
    render_final_artifacts(semantic, model, output_dir, final_hash, assigned)
    _run_script(config, "validate_module_test_points.py")


def run_adaptive(config: Any, initialize_fn: Callable[[Any], Path], invoke_fn: Callable[..., Any] | None = None) -> Any:
    """Run a zero-tool semantic baseline and parent-owned deterministic publication."""
    from run_generation import PipelineResult, RunnerLock

    started = time.monotonic()
    state_file = initialize_fn(config).resolve()
    state_data = json.loads(state_file.read_text(encoding="utf-8-sig"))
    output_dir = Path(state_data["output_dir"]).resolve()
    run_dir = _now_run_dir(config, output_dir)
    with RunnerLock(output_dir):
        input_path, state, model, input_hash = prepare_baseline_input(config, output_dir)
        (
            baseline_schema_path,
            complex_schema_path,
            packet,
            fingerprints,
            risks,
        ) = _prepare_worker_contract(config, output_dir, model, input_path, input_hash)
        if getattr(config, "dry_run", False):
            layout = resolve_module_layout(config.module_dir, config.preanalysis_dir, config.manifest)
            with state_lock(output_dir):
                state = load_state(output_dir, layout) or {}
                adaptive = ensure_adaptive_state(state).setdefault("adaptive", {})
                adaptive["metrics"] = {
                    "duration_seconds": round(time.monotonic() - started, 3),
                    "dry_run": True,
                    "worker_packet_bytes": len(packet.encode("utf-8")),
                }
                atomic_write_json(state_path(output_dir), state)
            print(f"BASELINE_INPUT={input_path}")
            print(f"WORKER_PACKET={output_dir / 'baseline-worker-packet.md'}")
            print("PIPELINE_STATUS=dry-run")
            return PipelineResult(state_path(output_dir), run_dir, 0, 0, None)

        layout = resolve_module_layout(config.module_dir, config.preanalysis_dir, config.manifest)
        state = load_state(output_dir, layout) or {}
        baseline_state = state.get("baseline", {})
        semantic_path = output_dir / "worker-results" / "baseline.json"
        semantic_path.parent.mkdir(parents=True, exist_ok=True)
        baseline_turns: list[Any] = []
        baseline_authorizations = _bundle_authorizations(model)
        semantic = _load_reusable_baseline(
            semantic_path,
            baseline_state,
            fingerprints,
            model,
            baseline_authorizations,
            baseline_only=getattr(config, "baseline_only", False),
        )
        reuse_baseline = semantic is not None
        if reuse_baseline:
            baseline_thread_id = baseline_state.get("thread_id")
        else:
            baseline_turn = _invoke_semantic_worker(
                config,
                run_dir,
                1,
                "baseline-worker",
                worker_prompt(packet, fingerprints["packet_sha256"]),
                None,
                baseline_schema_path,
                invoke_fn,
            )
            baseline_turns.append(baseline_turn)
            semantic = _load_worker_message(baseline_turn)
            baseline_thread_id = getattr(baseline_turn, "thread_id", None)
        validation_repairs = 0
        while True:
            try:
                validate_semantic_baseline_result(
                    semantic,
                    model,
                    fingerprints["packet_sha256"],
                    require_pre_generation_routing=not getattr(config, "baseline_only", False),
                    baseline_only=getattr(config, "baseline_only", False),
                    rsu_authorizations=baseline_authorizations,
                )
                break
            except WorkflowError as exc:
                if reuse_baseline or validation_repairs >= getattr(config, "max_validation_repairs", 0):
                    raise
                validation_repairs += 1
                print(
                    f"VALIDATION_REPAIR={validation_repairs}/"
                    f"{getattr(config, 'max_validation_repairs', 0)} PHASE=baseline-worker"
                )
                repair_turn = _invoke_semantic_worker(
                    config,
                    run_dir,
                    1 + validation_repairs,
                    "baseline-validation-repair",
                    _baseline_validation_repair_prompt(
                        semantic,
                        exc,
                        model,
                        fingerprints["packet_sha256"],
                        baseline_only=getattr(config, "baseline_only", False),
                    ),
                    None,
                    baseline_schema_path,
                    invoke_fn,
                    fork_from=baseline_thread_id,
                )
                baseline_turns.append(repair_turn)
                semantic = _load_worker_message(repair_turn)
                baseline_thread_id = getattr(repair_turn, "thread_id", None)
        if not reuse_baseline:
            atomic_write_json(semantic_path, semantic)

        scopes = detect_complex_generation_scopes(semantic, model, risks)
        if getattr(config, "baseline_only", False) and scopes:
            raise WorkflowError(
                "baseline-only mode produced complex scopes; refusing to start any fork"
            )
        complex_scope_authorizations = _complex_scope_authorizations(
            scopes, model.fixed_resource_ids
        )
        complex_turns: list[Any] = []
        if scopes:
            semantic, complex_turns = _run_complex_generations(
                config,
                output_dir,
                model,
                semantic,
                scopes,
                fingerprints,
                complex_schema_path,
                run_dir,
                invoke_fn,
                baseline_thread_id,
                baseline_authorizations,
                start_turn_number=2 + validation_repairs,
            )
        unresolved = [
            row["rsu_id"] for row in semantic["rsus"]
            if row["status"] not in {"generated", "zero-test-points"}
        ]
        if unresolved:
            raise WorkflowError(
                f"complex generations left unresolved RSUs: {', '.join(unresolved)}"
            )
        merged_semantic_path = output_dir / "worker-results" / "merged.json"
        atomic_write_json(merged_semantic_path, semantic)

        publish_paths = [
            output_dir / "module-test-points.md",
            output_dir / "coverage-matrix.md",
            output_dir / "baseline-result.json",
            *[output_dir / "by-rsu" / f"{rsu.rsu_id}.md" for rsu in model.rsus],
        ]
        previous_files = {
            path: path.read_bytes() if path.is_file() else None for path in publish_paths
        }
        state_file_path = state_path(output_dir)
        previous_state = state_file_path.read_bytes()
        try:
            current_state = load_state(output_dir, layout) or {}
            assigned = render_candidate_artifacts(
                semantic, model, current_state, output_dir
            )
            legacy = _legacy_baseline_manifest(semantic, assigned, input_hash)
            atomic_write_json(output_dir / "baseline-result.json", legacy)
            _mark_validated(
                config,
                output_dir,
                model,
                legacy,
                input_hash,
                complex_scope_authorizations=complex_scope_authorizations,
            )
            _prepare_and_render_finalization(
                config, output_dir, model, semantic, assigned
            )
        except Exception:
            for path, content in previous_files.items():
                if content is None:
                    if path.exists():
                        path.unlink()
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(content)
            state_file_path.write_bytes(previous_state)
            raise

        with state_lock(output_dir):
            state = load_state(output_dir, layout) or {}
            adaptive = ensure_adaptive_state(state).setdefault("adaptive", {})
            state["baseline"].update({
                **fingerprints,
                "status": "validated",
                "input_sha256": input_hash,
                "business_input_sha256": input_hash,
                "semantic_result_sha256": sha256_file(semantic_path),
                "merged_semantic_result_file": str(merged_semantic_path.relative_to(output_dir)),
                "merged_semantic_result_sha256": sha256_file(merged_semantic_path),
                "thread_id": baseline_thread_id,
                "worker_tool_calls": 0,
                "validated_at": utc_now(),
            })
            adaptive["completion"] = {"status": "complete", "reasons": []}
            generation_turns = baseline_turns + complex_turns
            tool_calls, usage = _aggregate_turn_metrics(generation_turns)
            invocation_metrics = {
                "duration_seconds": round(time.monotonic() - started, 3),
                "baseline_turns": len(baseline_turns),
                "validation_repair_count": validation_repairs,
                "fork_count": len(complex_turns),
                "complex_scope_count": len(scopes),
                "tool_calls": tool_calls,
                "parent_operations": 4,
                "usage": usage,
                "worker_packet_bytes": len(packet.encode("utf-8")),
                "readiness_duration_seconds": None,
            }
            adaptive["metrics"] = _merge_adaptive_metrics(
                adaptive.get("metrics"), invocation_metrics, reused=reuse_baseline
            )
            state["updated_at"] = utc_now()
            atomic_write_json(state_file_path, state)

        readiness_result = None
        readiness_turns = 0
        if getattr(config, "run_readiness", False):
            readiness_result, readiness_turns = _run_optional_readiness(
                config,
                output_dir,
                run_dir,
                invoke_fn,
                2 + len(complex_turns),
            )
        print("BASELINE_STATUS=validated")
        print(f"COMPLEX_GENERATION_SCOPES={len(scopes)}")
        print("TEST_POINT_GENERATION_STATUS=complete")
        print(f"READINESS_STATUS={readiness_result or 'not-run'}")
        print(f"PIPELINE_STATUS={'complete-existing' if reuse_baseline else 'complete'}")
        return PipelineResult(
            state_file_path,
            run_dir,
            len(baseline_turns) + len(complex_turns) + readiness_turns,
            0,
            readiness_result,
        )
