"""Pure deterministic validators for adaptive baseline/fork artifacts."""

from __future__ import annotations

from collections.abc import Iterable
import re
from typing import Any

from common import ADAPTIVE_DISPOSITIONS, WorkflowError


BASELINE_SCHEMA = "rsu-test-point-generation/baseline-v1"
FORK_SCHEMA = "rsu-test-point-generation/fork-v1"


SEMANTIC_RISK_PATTERNS = {
    "external-submit": re.compile(
        r"(?:IN15|第三方|外部(?:系统|接口)|审计接口|(?:批量|重新|首次)推送|submit)", re.IGNORECASE
    ),
    "async-poll": re.compile(
        r"(?:IN17|轮询|定时(?:查询|刷新)|自动查询|异步|poll(?:ing)?)", re.IGNORECASE
    ),
    "timeout-boundary": re.compile(
        r"(?:超时|最大.{0,8}(?:次数|轮次)|查询上限|timeout)", re.IGNORECASE
    ),
    "retry-recovery": re.compile(
        r"(?:重试|重新推送|再次推送|重新查询|补偿|恢复|retry|resend)", re.IGNORECASE
    ),
    "concurrency-idempotency": re.compile(
        r"(?:并发|幂等|重复(?:提交|点击|请求)|竞态|加锁|锁机制|concurren|idempoten)", re.IGNORECASE
    ),
    "state-transition": re.compile(
        r"(?:状态(?:映射|流转|迁移|落态|更新)|终态|中间态|state transition)", re.IGNORECASE
    ),
}


def complexity_risk_signals(text: str) -> set[str]:
    """Return stable pre-generation complexity facts found in requirement text."""

    return {
        name for name, pattern in SEMANTIC_RISK_PATTERNS.items()
        if pattern.search(text or "")
    }


def validate_baseline_manifest(data: Any, expected_rsu_ids: Iterable[str], input_sha256: str) -> dict[str, dict]:
    if not isinstance(data, dict) or data.get("schema") != BASELINE_SCHEMA:
        raise WorkflowError("baseline result has an unsupported schema")
    if data.get("input_sha256") != input_sha256:
        raise WorkflowError("baseline result input SHA-256 does not match baseline input")
    rows = data.get("rsus")
    if not isinstance(rows, list):
        raise WorkflowError("baseline result rsus must be a list")
    expected = list(expected_rsu_ids)
    by_id: dict[str, dict] = {}
    for row in rows:
        if not isinstance(row, dict) or not isinstance(row.get("rsu_id"), str):
            raise WorkflowError("baseline disposition must be an object with rsu_id")
        if row["rsu_id"] in by_id:
            raise WorkflowError(f"duplicate baseline disposition: {row['rsu_id']}")
        status = row.get("status")
        if status not in ADAPTIVE_DISPOSITIONS:
            raise WorkflowError(f"unsupported baseline disposition: {status}")
        candidate_ids = row.get("candidate_ids", [])
        if not isinstance(candidate_ids, list) or not all(isinstance(value, str) and value.strip() for value in candidate_ids):
            raise WorkflowError(f"{row['rsu_id']} candidate_ids must be a string list")
        if status == "generated" and not candidate_ids:
            raise WorkflowError(f"{row['rsu_id']} generated disposition requires candidate_ids")
        if status == "zero-test-points" and candidate_ids:
            raise WorkflowError(f"{row['rsu_id']} zero-test-points disposition must not list candidate_ids")
        if status != "generated" and not str(row.get("reason", "")).strip():
            raise WorkflowError(f"{row['rsu_id']} disposition {status} requires a reason")
        by_id[row["rsu_id"]] = row
    if list(by_id) != expected:
        raise WorkflowError("baseline dispositions must contain every RSU exactly once in map order")
    return by_id


def validate_fork_manifest(data: Any, rsu_id: str, input_sha256: str) -> dict:
    if not isinstance(data, dict) or data.get("schema") != FORK_SCHEMA:
        raise WorkflowError("fork result has an unsupported schema")
    if data.get("rsu_id") != rsu_id:
        raise WorkflowError("fork result targets a different RSU")
    if data.get("input_sha256") != input_sha256:
        raise WorkflowError("fork result input SHA-256 does not match fork input")
    if data.get("status") not in {"generated", "zero-test-points"}:
        raise WorkflowError("fork result must resolve its scope as generated or zero-test-points")
    return data


def duplicate_candidate_ids(rows: Iterable[Iterable[str]], id_index: int = 0) -> set[str]:
    seen: set[str] = set()
    duplicates: set[str] = set()
    for row in rows:
        values = list(row)
        if id_index >= len(values):
            continue
        candidate_id = values[id_index].strip()
        if not candidate_id:
            continue
        if candidate_id in seen:
            duplicates.add(candidate_id)
        seen.add(candidate_id)
    return duplicates


def ensure_scope(value_ids: Iterable[str], authorized_ids: Iterable[str]) -> None:
    unauthorized = set(value_ids) - set(authorized_ids)
    if unauthorized:
        raise WorkflowError(f"fork output is outside authorized scope: {sorted(unauthorized)}")


def merge_dispositions(base: dict[str, dict], fork: dict[str, dict], authorized_ids: Iterable[str]) -> dict[str, dict]:
    """Merge a bounded fork disposition map without silently overwriting conflicts."""
    ensure_scope(fork.keys(), authorized_ids)
    merged = dict(base)
    for rsu_id, row in fork.items():
        if rsu_id in merged and merged[rsu_id].get("status") not in {"needs-fork", "blocked"}:
            if merged[rsu_id] != row:
                raise WorkflowError(f"unresolved disposition conflict for {rsu_id}")
            continue
        merged[rsu_id] = row
    return merged
