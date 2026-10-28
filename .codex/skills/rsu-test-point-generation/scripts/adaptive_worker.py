"""Self-contained semantic workers and deterministic adaptive artifact rendering."""

from __future__ import annotations

from collections import defaultdict
import json
from pathlib import Path
from typing import Any, Iterable

from adaptive_validation import complexity_risk_signals
from common import (
    CANDIDATE_DISPOSITION_HEADERS,
    RSU_COVERAGE_HEADERS,
    WorkflowError,
    atomic_write_json,
    atomic_write_text,
    build_bundle,
    candidate_headers,
    clean_cell,
    context_resource_index_template,
    escape_markdown_table_cell,
    final_headers,
    markdown_table,
    sha256_file,
    sha256_text,
)


SEMANTIC_BASELINE_SCHEMA = "rsu-test-point-generation/semantic-baseline-v5"
COMPLEX_GENERATION_SCHEMA = "rsu-test-point-generation/complex-generation-v5"
WORKER_PACKET_VERSION = "rsu-test-point-generation/worker-packet-v3"
DEFAULT_PACKET_BUDGET_BYTES = 1_000_000

SEMANTIC_ROW_PROPERTIES: dict[str, Any] = {
    "key": {"type": "string", "minLength": 1},
    "primary_rsu": {"type": "string", "pattern": "^RSU-[0-9]{3}$"},
    "source_rsus": {
        "type": "array", "minItems": 1, "uniqueItems": True,
        "items": {"type": "string", "pattern": "^RSU-[0-9]{3}$"},
    },
    "test_item": {"type": "string", "minLength": 1},
    "test_point": {"type": "string", "minLength": 1},
    "remarks": {"type": "string"},
    "question_refs": {
        "type": "array", "uniqueItems": True,
        "items": {"type": "string", "pattern": "^Q-[0-9]{3}$"},
    },
    "context_refs": {
        "type": "array", "minItems": 1, "uniqueItems": True,
        "items": {"type": "string", "minLength": 1},
    },
    "data_closure_refs": {
        "type": "array", "uniqueItems": True,
        "items": {"type": "string", "pattern": "^DC-[0-9]{3}$"},
    },
}


def semantic_baseline_json_schema() -> dict[str, Any]:
    candidate = {
        "type": "object",
        "additionalProperties": False,
        "required": list(SEMANTIC_ROW_PROPERTIES) + ["derivation"],
        "properties": {**SEMANTIC_ROW_PROPERTIES, "derivation": {"type": "string", "minLength": 1}},
    }
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "additionalProperties": False,
        "required": [
            "schema", "packet_sha256", "rsus", "candidates",
            "complex_scopes", "context_dispositions",
        ],
        "properties": {
            "schema": {"type": "string", "const": SEMANTIC_BASELINE_SCHEMA},
            "packet_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "rsus": {
                "type": "array", "minItems": 1,
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": ["rsu_id", "status", "candidate_keys", "reason"],
                    "properties": {
                        "rsu_id": {"type": "string", "pattern": "^RSU-[0-9]{3}$"},
                        "status": {
                            "type": "string",
                            "enum": ["generated", "zero-test-points", "needs-fork", "blocked"],
                        },
                        "candidate_keys": {
                            "type": "array", "uniqueItems": True,
                            "items": {"type": "string", "minLength": 1},
                        },
                        "reason": {"type": "string"},
                    },
                },
            },
            "candidates": {"type": "array", "items": candidate},
            "complex_scopes": {
                "type": "array",
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": [
                        "scope_key", "rsu_ids", "context_refs", "question_refs",
                        "data_closure_refs", "risk_signals", "reason",
                    ],
                    "properties": {
                        "scope_key": {"type": "string", "minLength": 1},
                        "rsu_ids": {
                            "type": "array", "minItems": 1, "uniqueItems": True,
                            "items": {"type": "string", "pattern": "^RSU-[0-9]{3}$"},
                        },
                        "context_refs": {
                            "type": "array", "uniqueItems": True,
                            "items": {"type": "string", "minLength": 1},
                        },
                        "question_refs": {
                            "type": "array", "uniqueItems": True,
                            "items": {"type": "string", "pattern": "^Q-[0-9]{3}$"},
                        },
                        "data_closure_refs": {
                            "type": "array", "uniqueItems": True,
                            "items": {"type": "string", "pattern": "^DC-[0-9]{3}$"},
                        },
                        "risk_signals": {
                            "type": "array", "uniqueItems": True,
                            "items": {"type": "string", "minLength": 1},
                        },
                        "reason": {"type": "string", "minLength": 1},
                    },
                },
            },
            "context_dispositions": {
                "type": "array",
                "items": {
                    "type": "object", "additionalProperties": False,
                    "required": [
                        "resource_type", "resource_id", "rsu_ids", "candidate_keys",
                        "disposition", "reason",
                    ],
                    "properties": {
                        "resource_type": {
                            "type": "string", "enum": ["context", "question", "data-closure"],
                        },
                        "resource_id": {"type": "string", "minLength": 1},
                        "rsu_ids": {
                            "type": "array", "uniqueItems": True,
                            "items": {"type": "string", "pattern": "^RSU-[0-9]{3}$"},
                        },
                        "candidate_keys": {
                            "type": "array", "uniqueItems": True,
                            "items": {"type": "string", "minLength": 1},
                        },
                        "disposition": {
                            "type": "string",
                            "enum": ["generated", "absorbed", "needs-fork", "excluded"],
                        },
                        "reason": {"type": "string", "minLength": 1},
                    },
                },
            },
        },
    }


def complex_generation_json_schema() -> dict[str, Any]:
    baseline = semantic_baseline_json_schema()
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object", "additionalProperties": False,
        "required": [
            "schema", "packet_sha256", "scope_id", "status", "rsus",
            "candidates", "reason",
        ],
        "properties": {
            "schema": {"type": "string", "const": COMPLEX_GENERATION_SCHEMA},
            "packet_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
            "scope_id": {"type": "string", "minLength": 1},
            "status": {"type": "string", "const": "resolved"},
            "rsus": baseline["properties"]["rsus"],
            "candidates": baseline["properties"]["candidates"],
            "reason": {"type": "string", "minLength": 1},
        },
    }


def write_worker_schemas(output_dir: Path) -> tuple[Path, Path]:
    schema_dir = output_dir / "worker-schemas"
    schema_dir.mkdir(parents=True, exist_ok=True)
    baseline = schema_dir / "semantic-baseline-v5.schema.json"
    complex_generation = schema_dir / "complex-generation-v5.schema.json"
    atomic_write_json(baseline, semantic_baseline_json_schema())
    atomic_write_json(complex_generation, complex_generation_json_schema())
    return baseline, complex_generation


GENERATION_POLICY = """You are a constrained test-analysis worker, not an orchestration agent.
You are a senior test engineer performing requirements-based test analysis. Use only the facts in this packet. Do not call tools, read files, inspect repositories, invoke Skills, or run scripts.
Generate every test point supported by the supplied requirements. There is no target count: do not invent points to
increase the count, and do not merge independent requirements merely to reduce it.
The requirement text defines the acceptance boundary. Question answers may interpret or constrain behavior already
described there, but do not independently authorize a new acceptance object, behavior, or test point. If an answer
only settles a data source, fields, formula, SQL/calculation path, or test-data oracle, use it in the matching
requirement point's verification design or SQL artifact; do not create a standalone point. Extend acceptance scope
only when the user explicitly declares a new requirement/acceptance behavior. Context cards and data-closure cards
may clarify the requirement but cannot create commitments. Database table/column names, joins, query paths,
calculation implementation, test-data setup, and other technical provenance are not test points. Never rephrase
implementation detail as business language to evade this boundary.
A candidate represents one independently verifiable requirement behavior or rule. A candidate MUST be independently
triggerable, executable, judgeable, and diagnosable as a defect. Before writing candidates, identify the distinct
testable commitments in each RSU: applicable condition/state, tested object, user operation or system event, expected
business outcome, and pass/fail oracle. Separate candidates may cover different operations, controls, business
outcomes, state transitions, exception handling, boundaries, authorization, audit behavior, concurrency protection,
polling behavior, retry behavior, or other distinct commitments when the source supports them. Status values, return
codes, fields, equivalence classes, boundary values, and UI/API/database/log observations may be split when they
represent different operations, objects, state transitions, business outcomes, exception/recovery paths, or
independently diagnosable defects. They may be combined only when they are equivalent inputs or common evidence for
the same operation, object, lifecycle phase, and expected outcome. Do not hide several independent behaviors in
`test_point`; that field contains one complete, executable verification statement, not a short title.
Write practical test-plan prose using these business fields:
- `test_item`: a concise functional/rule category, e.g. 彩票年选项, 回显-数据源, 重置, 作废入口.
  Do not concatenate a generic testing dimension and a long point title mechanically.
- `test_point`: state the relevant condition and operation/system event when needed, plus the concrete expected
  behavior. A reader must understand what to verify from this field alone, without opening an RSU, a scenario
  matrix, or remarks. Use concise natural language, not detailed test-case steps or redundant assertions.
- `remarks`: optional supplemental qualification or source-change note; use an empty string when unnecessary.
  Never move a required condition, expected result, numeric limit or timeout rule out of `test_point` into remarks.
For example: test_item=彩票年选项; test_point=点击彩票年下拉框，选项仅包含当前年 Y 与上一年 Y-1。
For example: test_item=重置; test_point=点击【重置】，彩票年与任务状态恢复为全部、奖期编号清空，不自动查询。
For example: test_item=作废入口; test_point=待核查任务点击【作废】，打开对应任务的作废弹窗。
Do not write placeholders such as 按来源场景执行, 验证当前 TP 核心操作 or 结果符合需求. Do not add generic
无报错, SQL equality, setup/cleanup or other module behaviors without a requirement-based reason.
Before returning the result, perform an atomicity self-review. If one candidate contains multiple user operations,
controls, lifecycle phases, state transitions, or independent business outcomes, split it. In particular, do not put
checkbox eligibility, select-all scope, action-button availability, and post-action state recalculation in one
candidate merely because they belong to the same page or RSU.
Every candidate must trace to current RSUs and supplied Q/context/data-closure references.
The RSU disposition map and each candidate's `source_rsus` are bidirectionally
consistent: an RSU may list a candidate only when that RSU is present in the
candidate's `source_rsus`; when one candidate covers several RSUs, include every
covered RSU in `source_rsus` and list the exact same candidate key in each of
those RSU dispositions.  Do not attach a cross-cutting candidate (for example,
an authorization or audit-log observation) to an RSU whose source text is not
actually part of that candidate's declared scope.  Never add an RSU merely to
make the map look complete.
For every candidate, `context_refs` MUST include every fixed resource ID listed in
the packet's `Required Context Refs` (normally `SRC-GLOBAL`, `SRC-MOD`, and `CTX`),
even when a fixed resource is only a background authority for the rule.  Add each
other context or data-closure resource actually used; every `data_closure_refs`
entry must also appear in `context_refs`.  Never omit a required fixed ID merely
because the candidate's observable behavior comes from a more specific context card.
Use the exact IDs and spelling supplied by the packet; do not invent aliases.
Account for every non-fixed Context Card, Question and Data Closure Card exactly once in `context_dispositions`.
Do not silently omit authorization, audit-log, concurrency, invalid-state, external-interface, polling, timeout,
retry or locking commitments. Mark each resource as generated/absorbed/needs-fork/excluded with concrete RSUs,
candidate keys and reason. A `needs-fork` resource must be included in the matching complex scope.
For `generated` or `absorbed`, provide at least one existing simple candidate key as evidence.
An index/provenance-only resource without candidate evidence must use `excluded` with a concrete reason;
`excluded` does not exclude the substantive rule carried by its focused card or routed complex scope.
Return only JSON conforming to the supplied output schema. Do not emit Markdown.
"""


DEFAULT_ROUTING_POLICY = """Before generating candidates, classify every RSU and every directly coupled cross-RSU lifecycle as simple or complex.
Generate candidates in the baseline only for simple RSUs. A complex RSU MUST use status `needs-fork`, MUST have
an empty `candidate_keys` list, and MUST belong to exactly one `complex_scopes` entry. Never generate a provisional
candidate for a complex scope. Complex means that correct test semantics require focused reasoning over a state
lifecycle, external submit/poll/timeout/retry flow, concurrency/idempotency/locking, authorization or audit behavior,
or another directly coupled multi-RSU rule. Size alone does not determine complexity.
"""


BASELINE_ONLY_POLICY = """Explicit run mode: the user selected baseline-only generation for this module. Generate every RSU in this
single baseline session regardless of complexity signals. Do not classify or route RSUs into complex scopes. Every
RSU must be `generated` or `zero-test-points`; return no `complex_scopes`, `needs-fork`, or `blocked` dispositions.
This run-specific instruction overrides the default routing policy for this run only.
"""


def structured_risk_facts(model: Any) -> list[dict[str, Any]]:
    facts: list[dict[str, Any]] = []
    for rsu in model.rsus:
        text = " ".join(str(cell) for cell in rsu.cells)
        signals = sorted(complexity_risk_signals(text))
        if signals:
            context_refs = [
                item.strip() for item in str(rsu.cells[5]).replace("、", ",").split(",")
                if item.strip() and item.strip() != "无"
            ]
            facts.append({"rsu_id": rsu.rsu_id, "signals": signals, "context_refs": context_refs})
    return facts


def current_source_fingerprints(model: Any) -> dict[str, str]:
    result: dict[str, str] = {}
    for label, path in sorted(model.artifact_paths.items()):
        if path.is_file():
            result[f"artifact:{label}"] = sha256_file(path)
    if model.manifest_path is not None and model.manifest_path.is_file():
        result["manifest"] = sha256_file(model.manifest_path)
    for resource_id, resource in sorted(model.resources.items()):
        if resource.path.is_file():
            result[f"resource:{resource_id}"] = sha256_file(resource.path)
    return result


def required_context_dispositions(model: Any) -> list[dict[str, str]]:
    """Return the exact non-fixed resource ledger required from the baseline.

    JSON Schema can constrain the shape of each disposition, but it cannot
    express the runtime resource IDs discovered from the module manifest. The
    parent therefore materializes the exact set in the worker packet instead
    of asking the model to reconstruct it from several indexes.
    """

    fixed_context = set(model.fixed_resource_ids)
    data_closures = set(model.data_closure_ids)
    rows = [
        {
            "resource_type": "data-closure" if resource_id in data_closures else "context",
            "resource_id": resource_id,
        }
        for resource_id in sorted(set(model.resources) - fixed_context)
    ]
    rows.extend(
        {"resource_type": "question", "resource_id": question_id}
        for question_id in sorted(model.questions)
    )
    return rows


def compile_baseline_worker_packet(
    model: Any,
    business_input: str,
    business_input_sha256: str,
    schema_sha256: str,
    output_schema: dict[str, Any] | None = None,
    *,
    packet_budget_bytes: int = DEFAULT_PACKET_BUDGET_BYTES,
    baseline_only: bool = False,
) -> tuple[str, dict[str, str], list[dict[str, Any]]]:
    risks = structured_risk_facts(model)
    sources = current_source_fingerprints(model)
    risk_json = json.dumps(risks, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    source_json = json.dumps(sources, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    policy = GENERATION_POLICY + "\n" + (
        BASELINE_ONLY_POLICY if baseline_only else DEFAULT_ROUTING_POLICY
    )
    policy_hash = sha256_text(policy)
    risk_hash = sha256_text(risk_json)
    header = {
        "packet_version": WORKER_PACKET_VERSION,
        "business_input_sha256": business_input_sha256,
        "generation_policy_sha256": policy_hash,
        "output_schema_sha256": schema_sha256,
        "risk_facts_sha256": risk_hash,
        "source_fingerprints_sha256": sha256_text(source_json),
    }
    packet = (
        "# Self-contained RSU baseline worker packet\n\n"
        "## Contract fingerprints\n\n```json\n"
        + json.dumps(header, ensure_ascii=False, indent=2)
        + "\n```\n\n## Worker policy\n\n"
        + policy.strip()
        + "\n\n## Structured risk facts\n\n```json\n"
        + json.dumps(risks, ensure_ascii=False, indent=2)
        + "\n```\n\n## Current source fingerprints\n\n```json\n"
        + json.dumps(sources, ensure_ascii=False, indent=2)
        + "\n```\n\n## Required context disposition ledger\n\n"
        "Return exactly one `context_dispositions` row for every identity below; "
        "do not omit, duplicate, rename, or add an identity.\n\n```json\n"
        + json.dumps(required_context_dispositions(model), ensure_ascii=False, indent=2)
        + "\n```\n\n## Exact semantic output schema\n\n```json\n"
        + json.dumps(output_schema or semantic_baseline_json_schema(), ensure_ascii=False, indent=2)
        + "\n```\n\n## Complete module business input\n\n"
        + business_input.rstrip()
        + "\n"
    )
    packet_bytes = len(packet.encode("utf-8"))
    if packet_budget_bytes > 0 and packet_bytes > packet_budget_bytes:
        raise WorkflowError(
            f"baseline worker packet exceeds configured budget: {packet_bytes} > {packet_budget_bytes} bytes"
        )
    fingerprints = {**header, "packet_sha256": sha256_text(packet)}
    return packet, fingerprints, risks


def compile_complex_generation_packet(
    model: Any,
    baseline_result: dict[str, Any],
    scope: dict[str, Any],
    source_fingerprints: dict[str, str],
    *,
    packet_budget_bytes: int = DEFAULT_PACKET_BUDGET_BYTES,
    materialized_context_ids: set[str] | None = None,
) -> tuple[str, dict[str, str]]:
    """Build a bounded first-generation packet for one pre-routed complex scope."""

    authorized_rsus = set(scope["rsu_ids"])
    dispositions = [
        row for row in baseline_result["rsus"] if row["rsu_id"] in authorized_rsus
    ]
    rsu_facts = [
        {
            "rsu_id": rsu.rsu_id,
            "parent_text": rsu.parent_text,
            "source_text": rsu.source_text,
            "source_location": rsu.source_location,
            "related_context": rsu.related_context,
            "related_questions": rsu.related_questions,
            "source_status": rsu.source_status,
        }
        for rsu in model.rsus if rsu.rsu_id in authorized_rsus
    ]
    requested_context = set(scope.get("context_refs", []))
    requested_questions = set(scope.get("question_refs", []))
    requested_closures = set(scope.get("data_closure_refs", []))
    for rsu in model.rsus:
        if rsu.rsu_id not in authorized_rsus:
            continue
        requested_context.update(
            item for item in model.resources if item in str(rsu.related_context)
        )
        requested_questions.update(
            item for item in model.questions if item in str(rsu.related_questions)
        )
    requested_context.update(requested_closures)
    resources = []
    for resource_id in sorted(requested_context):
        resource = model.resources.get(resource_id)
        if resource is None:
            continue
        resources.append({
            "resource_id": resource_id,
            "purpose": resource.purpose,
            **(
                {"content": resource.path.read_text(encoding="utf-8-sig")}
                if materialized_context_ids is None or resource_id in materialized_context_ids
                else {
                    "role": "provenance-only",
                    "sha256": sha256_file(resource.path),
                    "note": "Source index only; use the supplied focused Context/Data Closure cards, not this evidence as a direct semantic dependency.",
                }
            ),
        })
    questions = []
    for question_id in sorted(requested_questions):
        question = model.questions.get(question_id)
        if question is None:
            continue
        questions.append({
            "question_id": question_id,
            "fields": dict(zip(question.headers, question.cells)),
        })
    payload = {
        "scope": scope,
        "authorized_rsu_facts": rsu_facts,
        "current_dispositions": dispositions,
        "scope_context_resources": resources,
        "scope_questions": questions,
        "source_fingerprints": source_fingerprints,
    }
    schema = complex_generation_json_schema()
    policy = (
        GENERATION_POLICY
        + "\nThis is the FIRST candidate generation for the authorized complex scope, not a review of baseline candidates. "
        "Return complete resolved dispositions and newly generated candidates for that scope. "
        "Do not perform broad semantic merging or calculate final_intents; the parent Runner creates that "
        "compatibility mapping deterministically from candidates. "
        "Use the embedded scope-specific Context/Question/Data Closure bodies. Do not mention or alter unrelated semantics.\n"
    )
    packet = (
        "# Self-contained bounded RSU complex-generation packet\n\n"
        "## Worker policy\n\n" + policy.strip()
        + "\n\n## Exact semantic output schema\n\n```json\n"
        + json.dumps(schema, ensure_ascii=False, indent=2)
        + "\n```\n\n## Authorized semantic facts\n\n```json\n"
        + json.dumps(payload, ensure_ascii=False, indent=2)
        + "\n```\n"
    )
    packet_bytes = len(packet.encode("utf-8"))
    if packet_budget_bytes > 0 and packet_bytes > packet_budget_bytes:
        raise WorkflowError(
            f"complex generation packet exceeds configured budget: {packet_bytes} > {packet_budget_bytes} bytes"
        )
    fingerprints = {
        "packet_version": WORKER_PACKET_VERSION,
        "generation_policy_sha256": sha256_text(policy),
        "output_schema_sha256": sha256_text(
            json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        ),
        "packet_sha256": sha256_text(packet),
    }
    return packet, fingerprints


def worker_prompt(
    packet: str,
    packet_sha256: str,
    *,
    complex_scope: bool = False,
    baseline_only: bool = False,
) -> str:
    if complex_scope:
        task = "Generate test-point semantics for only the authorized complex scope"
    elif baseline_only:
        task = "Generate test-point semantics for all RSUs in this baseline-only run"
    else:
        task = "Route all RSUs before generation, then generate only the simple scopes"
    complex_rules = (
        "\nComplex-generation identity rules: this scope has no baseline candidates. Create stable new candidate keys "
        "for the authorized RSUs only; RSU `candidate_keys` must reference those keys.\n"
        if complex_scope
        else ""
    )
    return (
        f"{task}. Return only schema-constrained JSON. packet_sha256 must be {packet_sha256}.\n"
        "You have all required facts below. Do not use tools or read any path.\n\n"
        "Traceability rule: every candidate `derivation` and every zero-candidate "
        "reason must explicitly include the labels `原文内容：` and, when the "
        "current RSU has a non-empty parent condition, `父级条件：`. Describe the "
        "specific rule/condition used; do not write only an RSU ID or a generic "
        "phrase such as `依据需求`.\n"
        + complex_rules
        + packet
    )


def _unique_records(rows: Iterable[dict[str, Any]], field: str, label: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get(field), str) or not row[field].strip():
            raise WorkflowError(f"{label} requires nonempty {field}")
        key = row[field].strip()
        if key in result:
            raise WorkflowError(f"duplicate {label} {field}: {key}")
        result[key] = row
    return result


def _semantic_duplicate_key(candidate: dict[str, Any]) -> tuple[str, str, str]:
    """Return the deliberately narrow key used for deterministic deduplication."""

    return (
        "".join(clean_cell(str(candidate.get("test_item", ""))).split()),
        "".join(clean_cell(str(candidate.get("test_point", ""))).split()),
        "".join(clean_cell(str(candidate.get("remarks", ""))).split()),
    )


def build_deterministic_final_intents(candidates: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Map candidates to final test points without broad semantic convergence.

    Candidate generation is the semantic step. The parent keeps every candidate
    by default and merges only rows whose item, full point and remarks are exactly
    equal after whitespace normalization. This prevents a later finalization
    pass from collapsing independently verifiable requirement behavior.
    """

    intents: list[dict[str, Any]] = []
    by_duplicate_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for candidate in candidates:
        duplicate_key = _semantic_duplicate_key(candidate)
        existing = by_duplicate_key.get(duplicate_key)
        if existing is not None:
            existing["source_candidate_keys"].append(candidate["key"])
            existing["rationale"] = "测试项、测试点与备注完全重复，由父 Runner 确定性合并。"
            continue
        intent = {
            "key": f"intent:{candidate['key']}",
            "source_candidate_keys": [candidate["key"]],
            "test_item": candidate["test_item"],
            "test_point": candidate["test_point"],
            "remarks": candidate["remarks"],
            "rationale": "保留为独立测试点。",
        }
        by_duplicate_key[duplicate_key] = intent
        intents.append(intent)
    return intents


def _validate_business_fields(candidates: Iterable[dict[str, Any]]) -> None:
    for candidate in candidates:
        for field in ("test_item", "test_point"):
            value = candidate.get(field)
            if not isinstance(value, str) or not clean_cell(value).strip():
                raise WorkflowError(f"candidate {candidate.get('key')} requires nonempty {field}")
        if not isinstance(candidate.get("remarks"), str):
            raise WorkflowError(f"candidate {candidate.get('key')} requires string remarks (may be empty)")


def validate_semantic_baseline_result(
    data: Any,
    model: Any,
    packet_sha256: str,
    *,
    require_pre_generation_routing: bool = True,
    baseline_only: bool = False,
    rsu_authorizations: dict[str, dict[str, set[str]]] | None = None,
) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema") != SEMANTIC_BASELINE_SCHEMA:
        raise WorkflowError("semantic baseline result has an unsupported schema")
    if data.get("packet_sha256") != packet_sha256:
        raise WorkflowError("semantic baseline result packet hash does not match")
    expected_rsus = [rsu.rsu_id for rsu in model.rsus]
    rows = data.get("rsus")
    if not isinstance(rows, list) or [row.get("rsu_id") for row in rows if isinstance(row, dict)] != expected_rsus:
        raise WorkflowError("semantic baseline dispositions must contain every RSU exactly once in map order")
    candidates = _unique_records(data.get("candidates", []), "key", "candidate")
    _validate_business_fields(candidates.values())
    valid_rsus = set(expected_rsus)
    valid_questions = set(model.questions)
    valid_context = set(model.resources)
    fixed_context = set(model.fixed_resource_ids)
    valid_dc = set(model.data_closure_ids)
    status_by_rsu = {row["rsu_id"]: row.get("status") for row in rows}
    if baseline_only and any(
        status not in {"generated", "zero-test-points"}
        for status in status_by_rsu.values()
    ):
        raise WorkflowError("baseline-only mode requires every RSU to be handled in the baseline")
    for fact in structured_risk_facts(model):
        if require_pre_generation_routing and _has_complex_lifecycle(set(fact["signals"])) and status_by_rsu.get(fact["rsu_id"]) not in {"needs-fork", "blocked"}:
            raise WorkflowError(
                f"high-risk lifecycle RSU must be routed before candidate generation: {fact['rsu_id']}"
            )
    for key, row in candidates.items():
        source_rsus = row.get("source_rsus")
        if row.get("primary_rsu") not in valid_rsus or not isinstance(source_rsus, list) or row["primary_rsu"] not in source_rsus:
            raise WorkflowError(f"candidate {key} has invalid primary/source RSUs")
        authorization = (rsu_authorizations or {}).get(row["primary_rsu"])
        authorized_rsus = (
            set(authorization["allowed_rsu_ids"])
            if authorization is not None
            else valid_rsus
        )
        authorized_questions = (
            set(authorization["allowed_q_ids"])
            if authorization is not None
            else valid_questions
        )
        authorized_context = (
            set(authorization["allowed_context_ids"])
            if authorization is not None
            else valid_context
        )
        required_context = (
            set(authorization["required_context_ids"])
            if authorization is not None
            else fixed_context
        )
        authorized_dc = (
            set(authorization["allowed_data_closure_ids"])
            if authorization is not None
            else valid_dc
        )
        if set(source_rsus) - valid_rsus:
            raise WorkflowError(f"candidate {key} references unknown RSUs")
        if set(source_rsus) - authorized_rsus:
            raise WorkflowError(f"candidate {key} references RSUs outside its materialized input")
        if any(status_by_rsu.get(rsu_id) in {"needs-fork", "blocked"} for rsu_id in source_rsus):
            raise WorkflowError(f"baseline candidate {key} references a complex or blocked RSU")
        question_refs = set(row.get("question_refs", []))
        if question_refs - valid_questions:
            raise WorkflowError(f"candidate {key} references unknown questions")
        if question_refs - authorized_questions:
            raise WorkflowError(f"candidate {key} references questions outside its materialized input")
        context = set(row.get("context_refs", []))
        if context - valid_context:
            raise WorkflowError(f"candidate {key} references unknown context")
        if context - authorized_context:
            raise WorkflowError(f"candidate {key} references context outside its materialized input")
        if required_context - context:
            raise WorkflowError(f"candidate {key} has invalid or incomplete context references")
        dc = set(row.get("data_closure_refs", []))
        if dc - valid_dc or dc - authorized_dc or dc - context:
            raise WorkflowError(f"candidate {key} has invalid data closure references")
    disposition_keys: set[str] = set()
    for row in rows:
        status = row.get("status")
        keys = row.get("candidate_keys")
        reason = str(row.get("reason", "")).strip()
        if status not in {"generated", "zero-test-points", "needs-fork", "blocked"} or not isinstance(keys, list):
            raise WorkflowError(f"invalid disposition for {row.get('rsu_id')}")
        if status == "generated" and not keys:
            raise WorkflowError(f"generated disposition requires candidates: {row['rsu_id']}")
        if status != "generated" and not reason:
            raise WorkflowError(f"non-generated disposition requires reason: {row['rsu_id']}")
        if status != "generated" and keys:
            raise WorkflowError(f"non-generated disposition cannot list candidates: {row['rsu_id']}")
        for key in keys:
            if key not in candidates:
                raise WorkflowError(f"disposition references unknown candidate: {key}")
            # A baseline candidate may intentionally cover more than one RSU.
            # Its single primary RSU is the stable owner, while every additional
            # RSU must be declared in source_rsus before it can list the key.
            candidate_source_rsus = set(candidates[key].get("source_rsus", []))
            if row["rsu_id"] not in candidate_source_rsus:
                raise WorkflowError(
                    f"candidate {key} is listed for an RSU outside source_rsus"
                )
            disposition_keys.add(key)
    if disposition_keys != set(candidates):
        raise WorkflowError("semantic baseline candidate/disposition coverage mismatch")
    complex_scopes = data.get("complex_scopes")
    if not isinstance(complex_scopes, list):
        raise WorkflowError("semantic baseline complex_scopes must be a list")
    if baseline_only and complex_scopes:
        raise WorkflowError("baseline-only mode does not allow complex scopes")
    seen_scopes: set[str] = set()
    routed_rsus: list[str] = []
    scope_by_resource: dict[str, set[str]] = defaultdict(set)
    for request in complex_scopes:
        if not isinstance(request, dict) or not str(request.get("scope_key", "")).strip():
            raise WorkflowError("semantic baseline complex scope requires scope_key")
        if request["scope_key"] in seen_scopes:
            raise WorkflowError(f"duplicate complex scope: {request['scope_key']}")
        seen_scopes.add(request["scope_key"])
        scope_rsus = request.get("rsu_ids", [])
        if not scope_rsus or not set(scope_rsus) <= valid_rsus:
            raise WorkflowError(f"complex scope {request['scope_key']} references invalid RSUs")
        if any(status_by_rsu[rsu_id] not in {"needs-fork", "blocked"} for rsu_id in scope_rsus):
            raise WorkflowError(f"complex scope {request['scope_key']} includes a simple RSU")
        routed_rsus.extend(scope_rsus)
        if set(request.get("context_refs", [])) - valid_context:
            raise WorkflowError(f"complex scope {request['scope_key']} references unknown context")
        if set(request.get("question_refs", [])) - valid_questions:
            raise WorkflowError(f"complex scope {request['scope_key']} references unknown questions")
        if set(request.get("data_closure_refs", [])) - valid_dc:
            raise WorkflowError(f"complex scope {request['scope_key']} references unknown data closure")
        for resource_id in (
            list(request.get("context_refs", []))
            + list(request.get("question_refs", []))
            + list(request.get("data_closure_refs", []))
        ):
            scope_by_resource[resource_id].add(request["scope_key"])
    expected_routed = {
        row["rsu_id"] for row in rows if row.get("status") in {"needs-fork", "blocked"}
    }
    if set(routed_rsus) != expected_routed or len(routed_rsus) != len(set(routed_rsus)):
        raise WorkflowError("every complex or blocked RSU must belong to exactly one pre-generation scope")

    context_dispositions = data.get("context_dispositions")
    if not isinstance(context_dispositions, list):
        raise WorkflowError("semantic baseline context_dispositions must be a list")
    expected_resources = {
        ("data-closure" if resource_id in valid_dc else "context", resource_id)
        for resource_id in valid_context - fixed_context
    } | {("question", question_id) for question_id in valid_questions}
    seen_resources: set[tuple[str, str]] = set()
    for disposition in context_dispositions:
        if not isinstance(disposition, dict):
            raise WorkflowError("context disposition must be an object")
        identity = (disposition.get("resource_type"), disposition.get("resource_id"))
        if identity not in expected_resources or identity in seen_resources:
            raise WorkflowError(f"invalid or duplicate context disposition: {identity}")
        seen_resources.add(identity)
        if set(disposition.get("rsu_ids", [])) - valid_rsus:
            raise WorkflowError(f"context disposition {identity[1]} references unknown RSUs")
        candidate_keys = set(disposition.get("candidate_keys", []))
        if candidate_keys - set(candidates):
            raise WorkflowError(f"context disposition {identity[1]} references unknown candidates")
        kind = disposition.get("disposition")
        if baseline_only and kind == "needs-fork":
            raise WorkflowError("baseline-only mode does not allow needs-fork dispositions")
        if kind in {"generated", "absorbed"} and not candidate_keys:
            raise WorkflowError(f"context disposition {identity[1]} requires candidate evidence")
        if kind == "needs-fork" and identity[1] not in scope_by_resource:
            raise WorkflowError(f"context disposition {identity[1]} is not routed to a complex scope")
    if seen_resources != expected_resources:
        missing = sorted(expected_resources - seen_resources)
        raise WorkflowError(f"context disposition coverage is incomplete: {missing}")
    data["final_intents"] = build_deterministic_final_intents(data.get("candidates", []))
    return data


def validate_complex_generation_result(
    data: Any,
    model: Any,
    scope: dict[str, Any],
    packet_sha256: str,
) -> dict[str, Any]:
    if not isinstance(data, dict) or data.get("schema") != COMPLEX_GENERATION_SCHEMA:
        raise WorkflowError("complex generation result has an unsupported schema")
    if data.get("packet_sha256") != packet_sha256:
        raise WorkflowError("complex generation result packet hash does not match")
    if data.get("scope_id") != scope.get("scope_id") or data.get("status") != "resolved":
        raise WorkflowError("complex generation result does not resolve the authorized scope")
    if not str(data.get("reason", "")).strip():
        raise WorkflowError("complex generation result requires a concrete reason")
    authorized_rsus = set(scope["rsu_ids"])
    rows = data.get("rsus")
    if not isinstance(rows, list) or [row.get("rsu_id") for row in rows if isinstance(row, dict)] != scope["rsu_ids"]:
        raise WorkflowError("complex generation dispositions must match authorized RSUs in scope order")
    candidates = _unique_records(data.get("candidates", []), "key", "complex candidate")
    _validate_business_fields(candidates.values())
    # A complex Worker may combine several RSUs, but it is authorized only for
    # the resources compiled into this Scope. Do not silently widen validation
    # to every question or context card in the module.
    valid_questions = set(scope.get("question_refs", []))
    fixed_context = set(model.fixed_resource_ids)
    valid_dc = set(scope.get("data_closure_refs", []))
    # Data Closure cards are referenced twice by contract: once in
    # data_closure_refs and once in context_refs.  A complex Scope stores them
    # in the dedicated data_closure_refs field, so they must also be accepted
    # as materialized context instead of being rejected as an unknown card.
    valid_context = fixed_context | set(scope.get("context_refs", [])) | valid_dc
    for key, row in candidates.items():
        source_rsus = set(row.get("source_rsus", []))
        if row.get("primary_rsu") not in authorized_rsus or not source_rsus or not source_rsus <= authorized_rsus:
            raise WorkflowError(f"complex candidate {key} escapes authorized RSUs")
        if set(row.get("question_refs", [])) - valid_questions:
            raise WorkflowError(f"complex candidate {key} references unknown questions")
        context = set(row.get("context_refs", []))
        if context - valid_context or fixed_context - context:
            raise WorkflowError(f"complex candidate {key} has invalid or incomplete context references")
        dc = set(row.get("data_closure_refs", []))
        if dc - valid_dc or dc - context:
            raise WorkflowError(f"complex candidate {key} has invalid data closure references")
    disposition_keys: set[str] = set()
    for row in rows:
        keys = row.get("candidate_keys")
        if row.get("status") not in {"generated", "zero-test-points"} or not isinstance(keys, list):
            raise WorkflowError(f"complex generation must resolve {row.get('rsu_id')}")
        if row["status"] == "generated" and not keys:
            raise WorkflowError(f"resolved generated disposition requires candidates: {row['rsu_id']}")
        if row["status"] == "zero-test-points" and (keys or not str(row.get("reason", "")).strip()):
            raise WorkflowError(f"resolved zero-test-points disposition is invalid: {row['rsu_id']}")
        for key in keys:
            if key not in candidates or row["rsu_id"] not in set(candidates[key].get("source_rsus", [])):
                raise WorkflowError(f"complex disposition references invalid candidate: {key}")
            disposition_keys.add(key)
    if disposition_keys != set(candidates):
        raise WorkflowError("complex generation candidate/disposition coverage mismatch")
    data["final_intents"] = build_deterministic_final_intents(data.get("candidates", []))
    return data


def merge_complex_generation_result(
    baseline: dict[str, Any], scope: dict[str, Any], complex_result: dict[str, Any]
) -> dict[str, Any]:
    """Merge one validated complex scope's first-generation result."""

    authorized_rsus = set(scope["rsu_ids"])
    preserved_candidates = [
        row for row in baseline["candidates"]
        if row["primary_rsu"] not in authorized_rsus
    ]
    merged_rsus = [
        next((item for item in complex_result["rsus"] if item["rsu_id"] == row["rsu_id"]), row)
        if row["rsu_id"] in authorized_rsus else row
        for row in baseline["rsus"]
    ]
    resource_candidate_keys: dict[str, set[str]] = defaultdict(set)
    for candidate in complex_result["candidates"]:
        for resource_id in (
            list(candidate.get("context_refs", []))
            + list(candidate.get("question_refs", []))
            + list(candidate.get("data_closure_refs", []))
        ):
            resource_candidate_keys[resource_id].add(candidate["key"])
    scoped_resources = (
        set(scope.get("context_refs", []))
        | set(scope.get("question_refs", []))
        | set(scope.get("data_closure_refs", []))
    )
    merged_context_dispositions = []
    for row in baseline.get("context_dispositions", []):
        if row.get("resource_id") in scoped_resources and row.get("disposition") == "needs-fork":
            actual_candidate_keys = sorted(resource_candidate_keys.get(row.get("resource_id"), set()))
            merged_context_dispositions.append({
                **row,
                "candidate_keys": actual_candidate_keys,
                "disposition": "generated" if actual_candidate_keys else "excluded",
                "reason": "complex scope generation resolved this resource",
            })
        else:
            merged_context_dispositions.append(row)
    merged_candidates = preserved_candidates + list(complex_result["candidates"])
    rsu_order = {
        row["rsu_id"]: index for index, row in enumerate(baseline["rsus"])
    }
    candidate_input_order = {
        row["key"]: index for index, row in enumerate(merged_candidates)
    }
    merged_candidates.sort(
        key=lambda row: (
            # Candidate artifacts are published under Primary RSU in map
            # order. Finalization validates TP order against that physical
            # appearance order, not against the earliest secondary Source RSU.
            rsu_order[row["primary_rsu"]],
            candidate_input_order[row["key"]],
        )
    )
    merged_intents = build_deterministic_final_intents(merged_candidates)
    return {
        **baseline,
        "rsus": merged_rsus,
        "candidates": merged_candidates,
        "final_intents": merged_intents,
        "complex_scopes": [
            row for row in baseline.get("complex_scopes", [])
            if not (set(row.get("rsu_ids", [])) & authorized_rsus)
        ],
        "context_dispositions": merged_context_dispositions,
    }


def load_semantic_result(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise WorkflowError(f"cannot read semantic worker result: {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise WorkflowError("semantic worker result must be a JSON object")
    return data


def _join(values: Iterable[str]) -> str:
    items = [str(item).strip() for item in values if str(item).strip()]
    return "、".join(items) if items else "无"


def _cell(value: Any) -> str:
    return escape_markdown_table_cell(str(value).replace("\r", " ").replace("\n", " ").strip())


def assign_semantic_ids(result: dict[str, Any], model: Any) -> dict[str, Any]:
    candidate_id_by_key: dict[str, str] = {}
    counts: dict[str, int] = defaultdict(int)
    candidates_by_key = _unique_records(result["candidates"], "key", "candidate")
    for row in result["candidates"]:
        primary = row["primary_rsu"]
        counts[primary] += 1
        candidate_id_by_key[row["key"]] = f"CAND-{primary}-{counts[primary]:03d}"
    intent_id_by_key = {
        row["key"]: f"TP-{index:03d}" for index, row in enumerate(result["final_intents"], start=1)
    }
    return {
        "candidates_by_key": candidates_by_key,
        "candidate_id_by_key": candidate_id_by_key,
        "intent_id_by_key": intent_id_by_key,
        "rsu_order": [rsu.rsu_id for rsu in model.rsus],
    }


def render_candidate_artifacts(
    result: dict[str, Any], model: Any, state: dict[str, Any], output_dir: Path
) -> dict[str, Any]:
    assigned = assign_semantic_ids(result, model)
    candidate_ids = assigned["candidate_id_by_key"]
    by_primary: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in result["candidates"]:
        by_primary[row["primary_rsu"]].append(row)
    dispositions = {row["rsu_id"]: row for row in result["rsus"]}
    state_by_rsu = {row["rsu_id"]: row for row in state["rsus"]}
    headers = candidate_headers(model.data_closure_enabled)
    legacy_rows: list[dict[str, Any]] = []
    for rsu in model.rsus:
        rsu_id = rsu.rsu_id
        rows: list[list[str]] = []
        for candidate in by_primary.get(rsu_id, []):
            values = [
                candidate_ids[candidate["key"]], candidate["primary_rsu"],
                _join(candidate["source_rsus"]), candidate["test_item"], candidate["test_point"],
                candidate["remarks"], _join(candidate["question_refs"]),
                _join(candidate["context_refs"]),
            ]
            if model.data_closure_enabled:
                values.append(_join(candidate["data_closure_refs"]))
            values.append(candidate["derivation"])
            rows.append([_cell(value) for value in values])
        disposition = dispositions[rsu_id]
        # This is an RSU candidate document, not the module finalization file.
        # An RSU covered only as a secondary source has no primary-owned rows,
        # so its document must use the candidate-contract value zero-candidate.
        result_name = "candidates" if rows else "zero-candidate"
        if rows:
            zero_reason = "不适用：本 RSU 已生成候选。"
        elif disposition["candidate_keys"]:
            covered_ids = [candidate_ids[key] for key in disposition["candidate_keys"]]
            zero_reason = (
                "原文内容：本 RSU 的规则已由关联候选 "
                + _join(covered_ids)
                + " 完整覆盖，本文件不重复建立主归属候选。"
            )
            if clean_cell(rsu.cells[1]) != "无":
                zero_reason += "父级条件：已审查并作为上述关联候选的适用限定一并保留。"
        else:
            zero_reason = disposition["reason"]
        input_hash = state_by_rsu[rsu_id]["current_input_sha256"]
        text = (
            f"# {rsu_id} 候选测试点\n\n## 生成元数据\n\n"
            f"| 字段 | 值 |\n|---|---|\n| RSU-ID | `{rsu_id}` |\n"
            f"| 输入 SHA-256 | `{input_hash}` |\n| 生成结果 | `{result_name}` |\n\n"
            "## 候选测试点\n\n" + markdown_table(headers, rows)
            + "\n\n## 零候选说明\n\n" + zero_reason.strip() + "\n"
        )
        path = output_dir / "by-rsu" / f"{rsu_id}.md"
        path.parent.mkdir(parents=True, exist_ok=True)
        atomic_write_text(path, text)
        legacy_rows.append({
            "rsu_id": rsu_id,
            "status": disposition["status"],
            "candidate_ids": [candidate_ids[key] for key in disposition["candidate_keys"]],
            "reason": disposition["reason"],
        })
    return {**assigned, "legacy_rows": legacy_rows}


def render_final_artifacts(
    result: dict[str, Any], model: Any, output_dir: Path, finalization_sha256: str,
    assigned: dict[str, Any],
) -> None:
    candidates = assigned["candidates_by_key"]
    candidate_ids = assigned["candidate_id_by_key"]
    tp_ids = assigned["intent_id_by_key"]
    final_rows: list[list[str]] = []
    candidate_to_tps: dict[str, list[str]] = defaultdict(list)
    for intent in result["final_intents"]:
        source_keys = intent["source_candidate_keys"]
        source_candidates = [candidates[key] for key in source_keys]
        primary = source_candidates[0]["primary_rsu"]
        source_rsus: list[str] = []
        questions: list[str] = []
        context: list[str] = []
        data_closures: list[str] = []
        for candidate in source_candidates:
            for target, values in (
                (source_rsus, candidate["source_rsus"]),
                (questions, candidate["question_refs"]),
                (context, candidate["context_refs"]),
                (data_closures, candidate["data_closure_refs"]),
            ):
                for value in values:
                    if value not in target:
                        target.append(value)
        values = [
            tp_ids[intent["key"]], primary, _join(source_rsus), intent["test_item"],
            intent["test_point"], intent["remarks"], _join(questions), _join(context),
        ]
        if model.data_closure_enabled:
            values.append(_join(data_closures))
        values.extend([_join(candidate_ids[key] for key in source_keys), intent["rationale"]])
        final_rows.append([_cell(value) for value in values])
        for key in source_keys:
            candidate_to_tps[key].append(tp_ids[intent["key"]])
    result_name = "test-points" if final_rows else "zero-test-points"
    final_text = (
        "# 模块最终测试点\n\n## 生成元数据\n\n| 字段 | 值 |\n|---|---|\n"
        f"| 最终输入 SHA-256 | `{finalization_sha256}` |\n| 生成结果 | `{result_name}` |\n\n"
        + context_resource_index_template(model, output_dir)
        + "\n\n## 最终测试点\n\n"
        + "测试项为功能/规则分类；测试点直接写明验证条件、操作或事件及预期行为；备注仅作可选补充。\n\n"
        + markdown_table(final_headers(model.data_closure_enabled), final_rows)
        + "\n"
    )
    atomic_write_text(output_dir / "module-test-points.md", final_text)

    final_by_rsu: dict[str, list[str]] = defaultdict(list)
    for intent in result["final_intents"]:
        tp_id = tp_ids[intent["key"]]
        for key in intent["source_candidate_keys"]:
            for rsu_id in candidates[key]["source_rsus"]:
                if tp_id not in final_by_rsu[rsu_id]:
                    final_by_rsu[rsu_id].append(tp_id)
    rsu_rows: list[list[str]] = []
    disposition_by_rsu = {row["rsu_id"]: row for row in result["rsus"]}
    for rsu in model.rsus:
        owned = [row for row in result["candidates"] if row["primary_rsu"] == rsu.rsu_id]
        refs = final_by_rsu.get(rsu.rsu_id, [])
        status = "covered" if refs else ("zero-candidate" if not owned else "excluded")
        explanation = (
            "候选已进入最终测试点。" if status == "covered"
            else disposition_by_rsu[rsu.rsu_id]["reason"]
        )
        rsu_rows.append([_cell(rsu.rsu_id), str(len(owned)), _cell(_join(refs)), status, _cell(explanation)])
    candidate_rows: list[list[str]] = []
    for candidate in result["candidates"]:
        refs = candidate_to_tps.get(candidate["key"], [])
        if not refs:
            status = "excluded"
            explanation = "该候选未形成独立最终测试意图。"
        else:
            merged = any(
                len(intent["source_candidate_keys"]) > 1
                for intent in result["final_intents"]
                if candidate["key"] in intent["source_candidate_keys"]
            )
            status = "merged" if merged else "retained"
            explanation = (
                "测试项、测试点与备注完全重复，确定性合并。"
                if merged else "保留为独立最终测试点。"
            )
        candidate_rows.append([
            _cell(candidate_ids[candidate["key"]]), _cell(candidate["primary_rsu"]), status,
            _cell(_join(refs)), _cell(explanation),
        ])
    coverage = (
        "# 测试点覆盖矩阵\n\n## RSU 覆盖\n\n"
        + markdown_table(RSU_COVERAGE_HEADERS, rsu_rows)
        + "\n\n## 候选归并\n\n"
        + markdown_table(CANDIDATE_DISPOSITION_HEADERS, candidate_rows)
        + "\n"
    )
    atomic_write_text(output_dir / "coverage-matrix.md", coverage)


def _has_complex_lifecycle(signals: set[str]) -> bool:
    return (
        "async-poll" in signals
        and bool(signals & {"timeout-boundary", "retry-recovery", "state-transition"})
    ) or (
        "external-submit" in signals
        and bool(signals & {
            "async-poll", "timeout-boundary", "retry-recovery",
            "concurrency-idempotency", "state-transition",
        })
    ) or (
        "retry-recovery" in signals and "concurrency-idempotency" in signals
    )


def detect_complex_generation_scopes(
    result: dict[str, Any], model: Any, risk_facts: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Return Baseline routes with deterministic InputBundle authorization.

    The model decides *which* RSUs form a complex lifecycle.  It does not own
    the dependency allow-list: every routed RSU already has an authoritative
    InputBundle.  Rebuilding the Scope references from those bundles prevents
    both omitted Q/FC/DC dependencies and provenance-only attachments from
    leaking into Fork authorization.
    """

    del risk_facts  # Routing topology is the Baseline decision.
    fixed_context = set(model.fixed_resource_ids)
    data_closure_ids = set(model.data_closure_ids)
    scopes: list[dict[str, Any]] = []
    for index, scope in enumerate(result.get("complex_scopes", []), start=1):
        allowed_context: set[str] = set()
        allowed_questions: set[str] = set()
        allowed_closures: set[str] = set()
        for rsu_id in scope["rsu_ids"]:
            bundle = build_bundle(model, model.rsu_by_id[rsu_id])
            allowed_context.update(bundle.allowed_context_ids)
            allowed_questions.update(bundle.allowed_q_ids)
            allowed_closures.update(
                set(bundle.allowed_context_ids) & data_closure_ids
            )
        # Keep deterministic module order instead of model-produced ordering.
        context_refs = [
            resource_id
            for resource_id in model.resources
            if resource_id in allowed_context
        ]
        for resource_id in model.fixed_resource_ids:
            if resource_id in allowed_context and resource_id not in context_refs:
                context_refs.insert(0, resource_id)
        question_refs = [
            question_id
            for question_id in model.questions
            if question_id in allowed_questions
        ]
        closure_refs = [
            resource_id
            for resource_id in model.resources
            if resource_id in allowed_closures
        ]
        scopes.append({
            "scope_id": f"COMPLEX-{index:03d}",
            "scope_key": scope["scope_key"],
            "rsu_ids": list(scope["rsu_ids"]),
            "candidate_keys": [],
            "context_refs": context_refs,
            "question_refs": question_refs,
            "data_closure_refs": closure_refs,
            "risk_signals": list(scope.get("risk_signals", [])),
            "reason": scope["reason"],
        })
    return scopes


def normalize_complex_scope_dispositions(
    result: dict[str, Any], scopes: list[dict[str, Any]]
) -> dict[str, Any]:
    """Align the Baseline coverage ledger with deterministic Scope authority.

    Baseline decides the complex RSU topology, but its dependency lists are not
    authorization facts. After Scope references are rebuilt from authoritative
    InputBundles, any model-produced needs-fork row outside that rebuilt union
    is provenance-only (or otherwise not materialized for the Fork) and must
    remain in the exact ledger as excluded instead of an unroutable promise.
    """

    routed_resources = {
        resource_id
        for scope in scopes
        for resource_id in (
            list(scope.get("context_refs", []))
            + list(scope.get("question_refs", []))
            + list(scope.get("data_closure_refs", []))
        )
    }
    dispositions: list[dict[str, Any]] = []
    for row in result.get("context_dispositions", []):
        if (
            row.get("disposition") == "needs-fork"
            and row.get("resource_id") not in routed_resources
        ):
            dispositions.append({
                **row,
                "candidate_keys": [],
                "disposition": "excluded",
                "reason": (
                    "父 Runner 根据复杂 Scope 内 RSU 的权威 InputBundle 重建授权后，"
                    "确认该资源仅作来源追溯或未被当前复杂语义物化，不进入 Fork。"
                ),
            })
        else:
            dispositions.append(row)
    return {**result, "context_dispositions": dispositions}
