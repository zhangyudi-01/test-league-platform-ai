#!/usr/bin/env python3
"""Run the RSU test-point workflow as guarded, one-turn Codex invocations."""

from __future__ import annotations

import argparse
import inspect
import hashlib
import json
import os
import platform
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from contextlib import AbstractContextManager, contextmanager, nullcontext
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterator


SKILL_DIR = Path(__file__).resolve().parents[1]
INIT_SCRIPT = SKILL_DIR / "scripts" / "init_generation.py"
SKILL_FILE = SKILL_DIR / "SKILL.md"
ALLOWED_RSU_STATUSES = {
    "pending", "prepared", "running", "failed", "replan-required",
    "blocked", "validated", "stale",
}
RUNNABLE_RSU_STATUSES = {"pending", "prepared", "failed", "stale"}
ALLOWED_BATCH_STATUSES = {
    "pending", "prepared", "running", "failed", "replan-required", "validated",
}

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ATTENTION = 2
EXIT_INTERRUPTED = 130
SESSION_MODES = {"module-session", "isolated"}
# The old sequential ``legacy-resume`` topology is intentionally no longer a
# selectable runner architecture.  ``isolated`` remains the manual/compatibility
# path and is dispatched below as one full-context RSU turn at a time.
PIPELINE_ARCHITECTURES = {"foundation-fork", "module-baseline"}
DEFAULT_PIPELINE_ARCHITECTURE = "module-baseline"
SESSION_RECOVERY_MODES = {"fresh-session", "isolated", "stop"}
DEFAULT_CONTEXT_REFRESH_INTERVAL = 5
DEFAULT_MAX_TRANSIENT_RETRIES = 6
DEFAULT_RETRY_BASE_DELAY_SECONDS = 15.0
DEFAULT_RETRY_MAX_DELAY_SECONDS = 300.0
DEFAULT_STAGE_TIMEOUT_SECONDS = 3600.0
DEFAULT_STALL_TIMEOUT_SECONDS = 900.0
DEFAULT_HEARTBEAT_INTERVAL_SECONDS = 60.0
DEFAULT_REPEATED_ACTION_LIMIT = 6
DEFAULT_MAX_WATCHDOG_RETRIES = 1
DEFAULT_SESSION_RESET_AFTER = 2
DEFAULT_MAX_VALIDATION_REPAIRS = 2
DEFAULT_GLOBAL_CONCURRENCY = 3
DEFAULT_MODULE_CONCURRENCY = 3
DEFAULT_GLOBAL_WAIT_TIMEOUT_SECONDS = 1800.0
DEFAULT_WORKER_PACKET_BUDGET_BYTES = 1_000_000
WATCHDOG_EXIT_CODE = 124
TRANSIENT_CODEX_FAILURE_RE = re.compile(
    r"(?:"
    r"unexpected\s+status\s+(?:408|425|429|500|502|503|504|520|521|522|524|529)\b|"
    r"\b(?:408|425|429|500|502|503|504|520|521|522|524|529)\s+"
    r"(?:bad\s+request|too\s+many\s+requests|bad\s+gateway|service\s+unavailable|"
    r"gateway\s+timeout|web\s+server\s+is\s+down|connection\s+timed\s+out)\b|"
    r"service\s+unavailable|bad\s+gateway|gateway\s+timeout|too\s+many\s+requests|"
    r"rate\s+limit(?:ed|ing)?|stream\s+disconnected|"
    r"connection\s+(?:reset|refused|closed|aborted)|"
    r"error\s+sending\s+request|failed\s+to\s+connect|provider\s+connection\s+failed|"
    r"(?:dns|name\s+resolution|temporary\s+failure\s+in\s+name\s+resolution|"
    r"getaddrinfo)\s+(?:resolution\s+)?(?:failed|error)|name\s+or\s+service\s+not\s+known|"
    r"(?:tls|ssl)\s+(?:handshake|connection)\s+(?:failed|error|timeout)|"
    r"temporar(?:y|ily)\s+unavailable|request\s+timed\s+out|"
    r"local\s+proxy\s+failed|provider[^\r\n]{0,120}(?:unavailable|circuit\s+open)|"
    r"供应商[^\r\n]{0,24}(?:连接失败|连接超时|不可用|繁忙|超时)|"
    r"(?:连接|访问)(?:供应商|服务)[^\r\n]{0,12}(?:失败|超时)|"
    r"网络(?:连接)?(?:失败|异常|超时)|请求超时|服务暂时不可用|暂时无法连接|"
    r"网关(?:错误|超时)|流(?:式)?中断"
    r")",
    re.IGNORECASE,
)
NONTRANSIENT_PROVIDER_FAILURE_RE = re.compile(
    r"(?:"
    r"用户额度不足|额度不足|余额不足|"
    r"insufficient[_\s-]+quota|billing[_\s-]+hard[_\s-]+limit|"
    r"credit\s+balance[^\r\n]{0,80}(?:too\s+low|insufficient)|"
    r"unexpected\s+status\s+(?:401|402|403)\b|"
    r"\b(?:401|402|403)\s+(?:unauthorized|payment\s+required|forbidden)\b|"
    r"(?:unauthorized|forbidden|invalid\s+(?:api|access)\s+key|"
    r"authentication\s+failed|payment\s+required|account\s+suspended)"
    r")",
    re.IGNORECASE,
)
SESSION_RESUME_FAILURE_RE = re.compile(
    r"(?:(?:session|thread|conversation)[^\r\n]{0,120}"
    r"(?:not\s+found|does\s+not\s+exist|expired|invalid|cannot\s+resume|failed\s+to\s+resume)|"
    r"(?:会话|线程)[^\r\n]{0,80}(?:不存在|过期|无效|无法恢复|恢复失败))",
    re.IGNORECASE,
)
RETRY_AFTER_RE = re.compile(
    r"retry[\s_-]*after(?:[\s_-]*seconds)?\s*['\"]?\s*[:=]\s*['\"]?"
    r"(?P<seconds>\d+(?:\.\d+)?)\s*(?:s|sec|seconds)?\b",
    re.IGNORECASE,
)
REPAIRABLE_VALIDATION_RE = re.compile(
    r"(?:\bERROR:\s*|validation\s+failed|校验失败).{0,1000}"
    r"(?:must\b|mismatch|missing|undefined|unresolved|malformed|stale|"
    r"does\s+not|changed\s+after|fixed\s+table|empty\s+cell|"
    r"candidate\s+count|TP\s+refs?|coverage|SHA-256|placeholder|"
    r"缺少|不匹配|未定义|格式|引用|表格|占位符|哈希)",
    re.IGNORECASE | re.DOTALL,
)
NONREPAIRABLE_VALIDATION_RE = re.compile(
    r"(?:blocked-input|upstream-gap|unanswered|pending-context|"
    r"requires?\s+(?:human|follow-up)|业务歧义|待确认|上游缺口|未回答)",
    re.IGNORECASE,
)


def configure_process_stdio() -> None:
    """Keep Windows console output from crashing on model/provider messages."""

    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except (OSError, ValueError):
            # Embedded hosts may expose a stream that cannot be reconfigured.
            continue


class RunnerError(RuntimeError):
    """The runner or Codex process failed unexpectedly."""


class AttentionRequired(RuntimeError):
    """The workflow stopped intentionally for human inspection or input."""


@dataclass(frozen=True)
class RunnerConfig:
    module_dir: Path
    manifest: Path | None
    preanalysis_dir: Path | None
    output_dir: Path | None
    workdir: Path
    logs_dir: Path | None
    codex_bin: str
    model: str | None
    profile: str | None
    sandbox: str
    max_rsu_turns: int | None
    max_transient_retries: int = DEFAULT_MAX_TRANSIENT_RETRIES
    retry_base_delay_seconds: float = DEFAULT_RETRY_BASE_DELAY_SECONDS
    retry_max_delay_seconds: float = DEFAULT_RETRY_MAX_DELAY_SECONDS
    session_mode: str = "module-session"
    context_refresh_interval: int = DEFAULT_CONTEXT_REFRESH_INTERVAL
    stage_timeout_seconds: float = DEFAULT_STAGE_TIMEOUT_SECONDS
    stall_timeout_seconds: float = DEFAULT_STALL_TIMEOUT_SECONDS
    heartbeat_interval_seconds: float = DEFAULT_HEARTBEAT_INTERVAL_SECONDS
    repeated_action_limit: int = DEFAULT_REPEATED_ACTION_LIMIT
    max_watchdog_retries: int = DEFAULT_MAX_WATCHDOG_RETRIES
    session_reset_after: int = DEFAULT_SESSION_RESET_AFTER
    session_recovery: str = "fresh-session"
    max_validation_repairs: int = DEFAULT_MAX_VALIDATION_REPAIRS
    global_concurrency: int = DEFAULT_GLOBAL_CONCURRENCY
    module_concurrency: int = DEFAULT_MODULE_CONCURRENCY
    global_lock_dir: Path | None = None
    global_wait_timeout_seconds: float = DEFAULT_GLOBAL_WAIT_TIMEOUT_SECONDS
    # Programmatic callers retain the compatibility topology unless they opt
    # into the adaptive architecture explicitly; the CLI default is adaptive.
    pipeline_architecture: str = "foundation-fork"
    baseline_only: bool = False
    dry_run: bool = False
    run_readiness: bool = False
    worker_packet_budget_bytes: int = DEFAULT_WORKER_PACKET_BUDGET_BYTES


@dataclass
class CodexSession:
    mode: str
    thread_id: str | None = None
    validated_rsus: int = 0
    consecutive_failures: int = 0
    recovery_count: int = 0
    force_full_context: bool = False

    def observe_thread(self, thread_id: str) -> str | None:
        if self.mode != "module-session":
            return None
        if not thread_id:
            return "Codex emitted an empty thread ID"
        if self.thread_id is None:
            self.thread_id = thread_id
            self.force_full_context = False
            print(f"SESSION_ID={thread_id}")
            return None
        if self.thread_id != thread_id:
            return (
                "Codex resume returned a different thread ID; "
                f"expected {self.thread_id}, found {thread_id}"
            )
        return None

    def should_refresh_context(self, interval: int, rsu_status: str) -> bool:
        if self.mode == "isolated":
            return True
        if self.force_full_context or self.validated_rsus == 0:
            return True
        return interval > 0 and self.validated_rsus % interval == 0

    def recover(self, strategy: str) -> tuple[str | None, str]:
        previous = self.thread_id
        if strategy == "fresh-session":
            self.mode = "module-session"
        elif strategy == "isolated":
            self.mode = "isolated"
        else:
            raise RunnerError(f"unsupported session recovery strategy: {strategy}")
        self.thread_id = None
        self.validated_rsus = 0
        self.consecutive_failures = 0
        self.recovery_count += 1
        self.force_full_context = True
        return previous, self.mode

    def mark_success(self) -> None:
        self.consecutive_failures = 0


@dataclass
class FoundationSession:
    mode: str
    thread_id: str | None = None
    cumulative_usage: dict[str, int] = field(default_factory=dict)

    def restore(self, thread_id: str) -> None:
        """Reuse a previously validated Foundation without creating a new turn."""

        if self.mode != "module-session":
            return
        if not thread_id:
            raise RunnerError("cannot restore an empty foundation session ID")
        if self.thread_id is not None and self.thread_id != thread_id:
            raise RunnerError("foundation session ID changed within one runner process")
        self.thread_id = thread_id
        print(f"FOUNDATION_SESSION_REUSED={thread_id}")

    def register(self, thread_id: str | None) -> None:
        if self.mode != "module-session":
            return
        if not thread_id:
            raise RunnerError("foundation bootstrap completed without a thread.started event")
        if self.thread_id is not None and self.thread_id != thread_id:
            raise RunnerError("foundation session ID changed within one runner process")
        self.thread_id = thread_id
        print(f"FOUNDATION_SESSION_ID={thread_id}")

    def require_child(self, thread_id: str | None, label: str) -> None:
        if self.mode != "module-session":
            return
        if not thread_id:
            raise RunnerError(f"{label} completed without a thread.started event")
        if thread_id == self.thread_id:
            raise RunnerError(f"{label} fork reused the foundation thread ID")

    def record_usage(self, usage: dict[str, int]) -> None:
        for key, value in usage.items():
            self.cumulative_usage[key] = self.cumulative_usage.get(key, 0) + value


def reusable_foundation_thread(
    state: dict[str, Any], output_dir: Path
) -> tuple[str | None, str]:
    """Return a persisted Foundation thread only when its fixed input is provably current."""

    foundation = state.get("foundation")
    if not isinstance(foundation, dict):
        return None, "foundation-state-missing"
    if foundation.get("status") != "validated":
        return None, f"foundation-status-{foundation.get('status') or 'missing'}"
    thread_id = foundation.get("thread_id")
    if not isinstance(thread_id, str) or not thread_id.strip():
        return None, "foundation-thread-missing"
    current_source = state.get("session_source_fingerprint_sha256")
    if (
        not isinstance(current_source, str)
        or not current_source
        or foundation.get("source_fingerprint_sha256") != current_source
    ):
        return None, "foundation-source-fingerprint-mismatch"
    input_value = foundation.get("input_file")
    expected_sha256 = foundation.get("input_sha256")
    if not isinstance(input_value, str) or not input_value:
        return None, "foundation-input-file-missing"
    if not isinstance(expected_sha256, str) or not expected_sha256:
        return None, "foundation-input-fingerprint-missing"
    input_path = Path(input_value)
    if not input_path.is_absolute():
        input_path = output_dir / input_path
    try:
        resolved_input = input_path.resolve()
        resolved_output = output_dir.resolve()
        resolved_input.relative_to(resolved_output)
    except (OSError, ValueError):
        return None, "foundation-input-outside-output"
    if file_sha256(resolved_input) != expected_sha256:
        return None, "foundation-input-fingerprint-mismatch"
    return thread_id.strip(), "validated-state-and-input"


@dataclass(frozen=True)
class RsuState:
    rsu_id: str
    status: str
    blockers: tuple[str, ...]


@dataclass(frozen=True)
class BatchState:
    batch_id: str
    mode: str
    rsu_ids: tuple[str, ...]
    status: str
    active_rsu_ids: tuple[str, ...] = ()

    @property
    def runnable(self) -> bool:
        return self.status in {"pending", "prepared", "failed"}

    @property
    def active_ids(self) -> tuple[str, ...]:
        return self.active_rsu_ids or self.rsu_ids


@dataclass(frozen=True)
class StateSnapshot:
    rsus: tuple[RsuState, ...]
    batches: tuple[BatchState, ...]
    planning_status: str
    finalization_status: str
    case_readiness_status: str
    case_readiness_result: str | None
    session_source_fingerprint_sha256: str | None = None

    @property
    def validated_count(self) -> int:
        return sum(item.status == "validated" for item in self.rsus)

    @property
    def next_rsu(self) -> RsuState | None:
        return next((item for item in self.rsus if item.status != "validated"), None)

    @property
    def pending_batches(self) -> tuple[BatchState, ...]:
        return tuple(item for item in self.batches if item.status != "validated")

    @property
    def all_rsus_validated(self) -> bool:
        return all(item.status == "validated" for item in self.rsus)


@dataclass(frozen=True)
class CodexTurnResult:
    returncode: int
    jsonl_log: Path
    stderr_log: Path
    last_message: Path
    started_at: str | None = None
    ended_at: str | None = None
    duration_seconds: float = 0.0
    termination_reason: str | None = None
    tool_calls: int = 0
    validation_attempts: int = 0
    validation_failures: int = 0
    usage: dict[str, int] = field(default_factory=dict)
    failure_evidence: str = ""
    thread_id: str | None = None


@dataclass(frozen=True)
class PipelineResult:
    state_file: Path
    run_dir: Path
    codex_turns: int
    rsu_turns: int
    case_readiness_result: str
    batch_turns: int = 0


Initializer = Callable[[RunnerConfig], Path]
Invoker = Callable[..., CodexTurnResult]
StageRunner = Callable[[RunnerConfig, str, tuple[str, ...]], str]


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def default_workdir() -> Path:
    for parent in SKILL_DIR.parents:
        if parent.name == ".codex":
            return parent.parent.resolve()
    return Path.cwd().resolve()


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return parsed


def nonnegative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or a positive integer")
    return parsed


def nonnegative_float(value: str) -> float:
    parsed = float(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be zero or a positive number")
    return parsed


def parse_args(argv: list[str] | None = None) -> RunnerConfig:
    parser = argparse.ArgumentParser(
        description=(
            "Run the RSU test-point pipeline using the selected rollout architecture."
        )
    )
    parser.add_argument("module_dir", type=Path, help="Module workspace root.")
    parser.add_argument("--manifest", type=Path, help="preanalysis/v1 manifest.")
    parser.add_argument("--preanalysis-dir", type=Path, help="Explicit preanalysis directory.")
    parser.add_argument("--output-dir", type=Path, help="Explicit generation output directory.")
    parser.add_argument(
        "--workdir",
        type=Path,
        default=default_workdir(),
        help="Codex working root; defaults to the project containing this local skill.",
    )
    parser.add_argument(
        "--logs-dir",
        type=Path,
        help="Runner log root; defaults to <generation-output>/runner-logs.",
    )
    parser.add_argument("--codex-bin", default="codex", help="Codex CLI executable.")
    parser.add_argument("--model", help="Optional Codex model override.")
    parser.add_argument("--profile", help="Optional Codex config profile.")
    parser.add_argument(
        "--pipeline-architecture",
        choices=tuple(sorted(PIPELINE_ARCHITECTURES)),
        default=DEFAULT_PIPELINE_ARCHITECTURE,
        help=(
            "Runner topology. module-baseline performs one module-wide baseline turn "
            "that routes complex scopes before candidate generation; simple RSUs are generated "
            "in the baseline and each complex scope is generated once in a fork. "
            "foundation-fork is the compatibility path."
        ),
    )
    parser.add_argument(
        "--baseline-only",
        action="store_true",
        help=(
            "For an explicitly user-designated small module, generate all RSUs in one baseline "
            "worker and reject any complex-scope routing; default routing is unchanged."
        ),
    )
    parser.add_argument(
        "--session-mode",
        choices=tuple(sorted(SESSION_MODES)),
        default="module-session",
        help=(
            "Codex conversation strategy. module-session uses one foundation session "
            "with independent fork stages; isolated is the manual fallback and runs "
            "one RSU per fresh full-context session."
        ),
    )
    parser.add_argument(
        "--context-refresh-interval",
        type=nonnegative_int,
        default=DEFAULT_CONTEXT_REFRESH_INTERVAL,
        help=(
            "Deprecated compatibility option from the removed legacy-resume runner; "
            "accepted and ignored (default: 5)."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepare and validate adaptive inputs/state without invoking Codex or publishing formal output.",
    )
    parser.add_argument(
        "--run-readiness",
        action="store_true",
        help="Run the optional readiness preparation after test-point generation (does not gate completion).",
    )
    parser.add_argument(
        "--worker-packet-budget-bytes",
        type=positive_int,
        default=DEFAULT_WORKER_PACKET_BUDGET_BYTES,
        help=(
            "Maximum UTF-8 size of a self-contained semantic worker packet; "
            "oversized packets stop with explicit context-pressure state instead of path-based reading "
            f"(default: {DEFAULT_WORKER_PACKET_BUDGET_BYTES})."
        ),
    )
    parser.add_argument(
        "--sandbox",
        choices=("read-only", "workspace-write", "danger-full-access"),
        default="workspace-write",
        help="Sandbox passed to each Codex turn (default: workspace-write).",
    )
    parser.add_argument(
        "--max-rsu-turns",
        type=positive_int,
        help="Optional safety cap; defaults to the number of nonvalidated RSUs after initialization.",
    )
    parser.add_argument(
        "--max-transient-retries",
        type=nonnegative_int,
        default=DEFAULT_MAX_TRANSIENT_RETRIES,
        help=(
            "Retries for provider/network failures after Codex CLI gives up "
            f"(default: {DEFAULT_MAX_TRANSIENT_RETRIES}; 0 disables runner-level retries)."
        ),
    )
    parser.add_argument(
        "--retry-base-delay-seconds",
        type=nonnegative_float,
        default=DEFAULT_RETRY_BASE_DELAY_SECONDS,
        help=(
            "Initial delay for bounded exponential transient retries "
            f"(default: {DEFAULT_RETRY_BASE_DELAY_SECONDS:g} seconds)."
        ),
    )
    parser.add_argument(
        "--retry-max-delay-seconds",
        type=nonnegative_float,
        default=DEFAULT_RETRY_MAX_DELAY_SECONDS,
        help=(
            "Maximum delay for a single transient retry "
            f"(default: {DEFAULT_RETRY_MAX_DELAY_SECONDS:g} seconds)."
        ),
    )
    parser.add_argument(
        "--stage-timeout-seconds",
        type=nonnegative_float,
        default=DEFAULT_STAGE_TIMEOUT_SECONDS,
        help=(
            "Maximum wall time for one Codex stage; 0 disables the total deadline "
            f"(default: {DEFAULT_STAGE_TIMEOUT_SECONDS:g} seconds)."
        ),
    )
    parser.add_argument(
        "--stall-timeout-seconds",
        type=nonnegative_float,
        default=DEFAULT_STALL_TIMEOUT_SECONDS,
        help=(
            "Maximum time without a Codex JSONL event; 0 disables the watchdog "
            f"(default: {DEFAULT_STALL_TIMEOUT_SECONDS:g} seconds)."
        ),
    )
    parser.add_argument(
        "--heartbeat-interval-seconds",
        type=nonnegative_float,
        default=DEFAULT_HEARTBEAT_INTERVAL_SECONDS,
        help=(
            "Progress heartbeat interval while waiting for Codex output "
            f"(default: {DEFAULT_HEARTBEAT_INTERVAL_SECONDS:g} seconds)."
        ),
    )
    parser.add_argument(
        "--repeated-action-limit",
        type=nonnegative_int,
        default=DEFAULT_REPEATED_ACTION_LIMIT,
        help=(
            "Terminate after this many consecutive identical tool actions; 0 disables detection "
            f"(default: {DEFAULT_REPEATED_ACTION_LIMIT})."
        ),
    )
    parser.add_argument(
        "--max-watchdog-retries",
        type=nonnegative_int,
        default=DEFAULT_MAX_WATCHDOG_RETRIES,
        help=(
            "Retries after a stage/stall/repeated-action watchdog termination "
            f"(default: {DEFAULT_MAX_WATCHDOG_RETRIES}; 0 disables)."
        ),
    )
    parser.add_argument(
        "--session-reset-after",
        type=nonnegative_int,
        default=DEFAULT_SESSION_RESET_AFTER,
        help=(
            "Consecutive transient failures before module-session is replaced by a fresh session "
            f"(default: {DEFAULT_SESSION_RESET_AFTER}; 0 disables automatic reset)."
        ),
    )
    parser.add_argument(
        "--session-recovery",
        choices=tuple(sorted(SESSION_RECOVERY_MODES)),
        default="fresh-session",
        help="Recovery after repeated session failures: fresh-session, isolated, or stop.",
    )
    parser.add_argument(
        "--max-validation-repairs",
        type=nonnegative_int,
        default=DEFAULT_MAX_VALIDATION_REPAIRS,
        help=(
            "Bounded repair turns for deterministic output validation errors "
            f"(default: {DEFAULT_MAX_VALIDATION_REPAIRS}; 0 disables)."
        ),
    )
    parser.add_argument(
        "--global-concurrency",
        type=nonnegative_int,
        default=DEFAULT_GLOBAL_CONCURRENCY,
        help=(
            "Maximum Codex turns across runner processes sharing the lock directory; "
            f"0 disables the global coordinator (default: {DEFAULT_GLOBAL_CONCURRENCY})."
        ),
    )
    parser.add_argument(
        "--module-concurrency",
        type=positive_int,
        default=DEFAULT_MODULE_CONCURRENCY,
        help=(
            "Maximum RSU batch workers within this module; effective concurrency is also "
            f"bounded by global slots (default: {DEFAULT_MODULE_CONCURRENCY})."
        ),
    )
    parser.add_argument(
        "--global-lock-dir",
        type=Path,
        help=(
            "Shared cross-process concurrency directory; defaults to "
            "%%TEMP%%/codex-rsu-runner-slots/<workdir-hash>."
        ),
    )
    parser.add_argument(
        "--global-wait-timeout-seconds",
        type=nonnegative_float,
        default=DEFAULT_GLOBAL_WAIT_TIMEOUT_SECONDS,
        help=(
            "Maximum time waiting for a global Codex slot; 0 waits indefinitely "
            f"(default: {DEFAULT_GLOBAL_WAIT_TIMEOUT_SECONDS:g} seconds)."
        ),
    )
    args = parser.parse_args(argv)
    return RunnerConfig(
        module_dir=args.module_dir.expanduser().resolve(),
        manifest=args.manifest.expanduser().resolve() if args.manifest else None,
        preanalysis_dir=args.preanalysis_dir.expanduser().resolve() if args.preanalysis_dir else None,
        output_dir=args.output_dir.expanduser().resolve() if args.output_dir else None,
        workdir=args.workdir.expanduser().resolve(),
        logs_dir=args.logs_dir.expanduser().resolve() if args.logs_dir else None,
        codex_bin=args.codex_bin,
        model=args.model,
        profile=args.profile,
        sandbox=args.sandbox,
        max_rsu_turns=args.max_rsu_turns,
        max_transient_retries=args.max_transient_retries,
        retry_base_delay_seconds=args.retry_base_delay_seconds,
        retry_max_delay_seconds=args.retry_max_delay_seconds,
        session_mode=args.session_mode,
        context_refresh_interval=args.context_refresh_interval,
        stage_timeout_seconds=args.stage_timeout_seconds,
        stall_timeout_seconds=args.stall_timeout_seconds,
        heartbeat_interval_seconds=args.heartbeat_interval_seconds,
        repeated_action_limit=args.repeated_action_limit,
        max_watchdog_retries=args.max_watchdog_retries,
        session_reset_after=args.session_reset_after,
        session_recovery=args.session_recovery,
        max_validation_repairs=args.max_validation_repairs,
        global_concurrency=args.global_concurrency,
        module_concurrency=args.module_concurrency,
        global_lock_dir=args.global_lock_dir.expanduser().resolve() if args.global_lock_dir else None,
        global_wait_timeout_seconds=args.global_wait_timeout_seconds,
        pipeline_architecture=args.pipeline_architecture,
        baseline_only=args.baseline_only,
        dry_run=args.dry_run,
        run_readiness=args.run_readiness,
        worker_packet_budget_bytes=args.worker_packet_budget_bytes,
    )


def layout_cli_args(config: RunnerConfig) -> list[str]:
    result = [str(config.module_dir)]
    if config.manifest is not None:
        result.extend(["--manifest", str(config.manifest)])
    if config.preanalysis_dir is not None:
        result.extend(["--preanalysis-dir", str(config.preanalysis_dir)])
    if config.output_dir is not None:
        result.extend(["--output-dir", str(config.output_dir)])
    return result


def layout_prompt(config: RunnerConfig) -> str:
    lines = [f"module-dir: {config.module_dir}"]
    if config.manifest is not None:
        lines.append(f"--manifest: {config.manifest}")
    if config.preanalysis_dir is not None:
        lines.append(f"--preanalysis-dir: {config.preanalysis_dir}")
    if config.output_dir is not None:
        lines.append(f"--output-dir: {config.output_dir}")
    return "\n".join(f"- {line}" for line in lines)


def phase_command(config: RunnerConfig, script_name: str) -> str:
    parts = [
        "python",
        "-B",
        f'"{SKILL_DIR / "scripts" / script_name}"',
        f'"{config.module_dir}"',
    ]
    if config.manifest is not None:
        parts.extend(["--manifest", f'"{config.manifest}"'])
    if config.preanalysis_dir is not None:
        parts.extend(["--preanalysis-dir", f'"{config.preanalysis_dir}"'])
    if config.output_dir is not None:
        parts.extend(["--output-dir", f'"{config.output_dir}"'])
    return " ".join(parts)


def initialize_generation(config: RunnerConfig) -> Path:
    command = [sys.executable, "-B", str(INIT_SCRIPT), *layout_cli_args(config)]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    combined = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if result.returncode != 0:
        raise RunnerError("generation initialization failed:\n" + (combined or "no output"))
    match = re.search(r"(?m)^STATE_FILE=(.+)$", result.stdout)
    if not match:
        raise RunnerError("init_generation.py did not report STATE_FILE")
    state_file = Path(match.group(1).strip()).expanduser().resolve()
    if not state_file.is_file():
        raise RunnerError(f"initialized state file is missing: {state_file}")
    print(combined)
    return state_file


def run_stage_script(
    config: RunnerConfig,
    script_name: str,
    positional: tuple[str, ...] = (),
    *,
    accepted_returncodes: tuple[int, ...] = (0,),
) -> str:
    command = [
        sys.executable,
        "-X",
        "utf8",
        "-B",
        str(SKILL_DIR / "scripts" / script_name),
        *layout_cli_args(config),
        *positional,
    ]
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        env=env,
    )
    combined = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    if combined:
        print(combined)
    if result.returncode not in accepted_returncodes:
        raise RunnerError(f"{script_name} failed:\n{combined or 'no output'}")
    return result.stdout


def load_state(state_file: Path) -> tuple[dict, StateSnapshot]:
    try:
        data = json.loads(state_file.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise RunnerError(f"generation state disappeared: {state_file}") from exc
    except json.JSONDecodeError as exc:
        raise RunnerError(f"invalid generation state JSON: {state_file}: {exc}") from exc
    if not isinstance(data, dict):
        raise RunnerError("generation state root must be a JSON object")
    raw_rsus = data.get("rsus")
    if not isinstance(raw_rsus, list):
        raise RunnerError("generation state rsus must be a list")
    rsus: list[RsuState] = []
    seen: set[str] = set()
    for index, item in enumerate(raw_rsus, start=1):
        if not isinstance(item, dict):
            raise RunnerError(f"generation state rsus[{index}] must be an object")
        rsu_id = item.get("rsu_id")
        status = item.get("generation_status")
        blockers = item.get("blockers", [])
        if not isinstance(rsu_id, str) or not rsu_id:
            raise RunnerError(f"generation state rsus[{index}] has invalid rsu_id")
        if rsu_id in seen:
            raise RunnerError(f"generation state contains duplicate RSU: {rsu_id}")
        if status not in ALLOWED_RSU_STATUSES:
            raise RunnerError(f"{rsu_id} has unsupported generation status: {status}")
        if not isinstance(blockers, list) or not all(isinstance(value, str) for value in blockers):
            raise RunnerError(f"{rsu_id} blockers must be a list of strings")
        seen.add(rsu_id)
        rsus.append(RsuState(rsu_id, status, tuple(blockers)))
    raw_batches = data.get("batches", [])
    if not isinstance(raw_batches, list):
        raise RunnerError("generation state batches must be a list")
    batches: list[BatchState] = []
    seen_batches: set[str] = set()
    for index, item in enumerate(raw_batches, start=1):
        if not isinstance(item, dict):
            raise RunnerError(f"generation state batches[{index}] must be an object")
        batch_id = item.get("batch_id")
        mode = item.get("mode")
        rsu_ids = item.get("rsu_ids")
        status = item.get("status")
        if not isinstance(batch_id, str) or batch_id in seen_batches:
            raise RunnerError(f"generation state batches[{index}] has invalid batch_id")
        if mode not in {"simple", "complex"}:
            raise RunnerError(f"{batch_id} has unsupported mode: {mode}")
        if not isinstance(rsu_ids, list) or not rsu_ids or not all(isinstance(value, str) for value in rsu_ids):
            raise RunnerError(f"{batch_id} rsu_ids must be a non-empty string list")
        if status not in ALLOWED_BATCH_STATUSES:
            raise RunnerError(f"{batch_id} has unsupported status: {status}")
        seen_batches.add(batch_id)
        active_rsu_ids = item.get("active_rsu_ids", [])
        if not isinstance(active_rsu_ids, list) or not all(
            isinstance(value, str) for value in active_rsu_ids
        ):
            raise RunnerError(f"{batch_id} active_rsu_ids must be a string list")
        if any(value not in rsu_ids for value in active_rsu_ids):
            raise RunnerError(f"{batch_id} active_rsu_ids contains an unplanned RSU")
        batches.append(
            BatchState(batch_id, mode, tuple(rsu_ids), status, tuple(active_rsu_ids))
        )
    finalization = data.get("finalization", {})
    readiness = data.get("case_readiness", {})
    if not isinstance(finalization, dict) or not isinstance(readiness, dict):
        raise RunnerError("finalization and case_readiness state must be objects")
    snapshot = StateSnapshot(
        tuple(rsus),
        tuple(batches),
        str(data.get("planning", {}).get("status", "pending")),
        str(finalization.get("status", "not-ready")),
        str(readiness.get("status", "not-ready")),
        readiness.get("result"),
        data.get("session_source_fingerprint_sha256"),
    )
    return data, snapshot


class RunnerLock(AbstractContextManager["RunnerLock"]):
    STALE_UNKNOWN_OWNER_SECONDS = 3600.0

    def __init__(self, output_dir: Path) -> None:
        self.path = output_dir / ".generation-runner.lock"
        self._owned = False
        self._owner_token: str | None = None

    def _read_owner_pid(self) -> int | None:
        try:
            details = self.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None
        match = re.search(r"(?:^|\s)pid=(\d+)\b", details)
        return int(match.group(1)) if match else None

    def _reclaim_if_stale(self) -> bool:
        """Remove a lock only when its owner is demonstrably gone.

        Older or hand-created lock files without a PID are reclaimed only
        after a conservative age threshold.  A live PID always wins, so a
        second runner cannot silently steal an active module lock.
        """

        owner_pid = self._read_owner_pid()
        if owner_pid is not None:
            stale = not process_is_alive(owner_pid)
        else:
            try:
                stale = (
                    time.time() - self.path.stat().st_mtime
                    >= self.STALE_UNKNOWN_OWNER_SECONDS
                )
            except OSError:
                return False
        if not stale:
            return False
        try:
            self.path.unlink()
        except FileNotFoundError:
            return True
        print(f"STALE_MODULE_LOCK_RECLAIMED={self.path}")
        return True

    def __enter__(self) -> "RunnerLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        for _ in range(2):
            try:
                fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                break
            except FileExistsError as exc:
                if self._reclaim_if_stale():
                    continue
                details = self.path.read_text(encoding="utf-8", errors="replace").strip()
                suffix = f" ({details})" if details else ""
                raise AttentionRequired(
                    f"another runner may be active: {self.path}{suffix}"
                ) from exc
        else:  # pragma: no cover - defensive race guard
            raise AttentionRequired(f"another runner may be active: {self.path}")
        try:
            self._owner_token = uuid.uuid4().hex
            payload = (
                f"pid={os.getpid()} created_at={utc_now()} "
                f"owner_token={self._owner_token}\n"
            )
            os.write(fd, payload.encode("utf-8"))
        finally:
            os.close(fd)
        self._owned = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._owned:
            try:
                details = self.path.read_text(encoding="utf-8", errors="replace")
                # A stale-lock race must not let an old runner remove a lock
                # that has already been reclaimed and acquired by a newer
                # runner.  The token is absent from legacy locks, so those
                # locks are never mistaken for this process's ownership.
                owned = (
                    self._owner_token is not None
                    and re.search(rf"(?:^|\s)pid={os.getpid()}\b", details)
                    and re.search(rf"(?:^|\s)owner_token={re.escape(self._owner_token)}\b", details)
                )
                if owned:
                    self.path.unlink()
            except FileNotFoundError:
                pass
        self._owned = False
        self._owner_token = None
        return None


class RunTelemetry:
    """Append-only machine-readable timing events for post-run attribution."""

    def __init__(self, run_dir: Path) -> None:
        self.path = run_dir / "runner-events.jsonl"
        self._lock = threading.Lock()

    def emit(self, event: str, **fields: object) -> None:
        payload = {
            "timestamp": utc_now(),
            "event": event,
            **fields,
        }
        line = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
        with self._lock:
            try:
                with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                    stream.write(line)
            except OSError as exc:
                # Telemetry is diagnostic.  A full or temporarily unavailable
                # log volume must not turn an otherwise recoverable generation
                # result into a runner failure.  The terminal/console output
                # still carries the failure when the underlying operation does.
                print(
                    f"TELEMETRY_WRITE_FAILED={self.path} "
                    f"EVENT={event} ERROR={exc}",
                    file=sys.stderr,
                )


@dataclass
class ActivePipelineTelemetry:
    """Runtime context used to record terminal pipeline outcomes.

    The runner deliberately creates a run directory only after initialization
    and state reconciliation succeed.  Once that directory exists, failures
    must still leave a machine-readable terminal event instead of being
    represented only by a process exit code.
    """

    telemetry: RunTelemetry
    state_file: Path
    run_dir: Path
    started_monotonic: float
    phase: str | None = None
    rsu_id: str | None = None
    codex_turns: int = 0
    rsu_turns: int = 0
    terminal_event_emitted: bool = False


_ACTIVE_PIPELINE: ActivePipelineTelemetry | None = None


def startup_failure_log_root(config: RunnerConfig) -> Path:
    """Choose a narrow, deterministic location for pre-run failures.

    Before initialization succeeds the manifest may not yet reveal the real
    output directory.  Prefer an explicitly supplied log/output directory;
    otherwise keep the record beside an existing module.  If even the module
    path is unavailable, fall back to a dedicated temporary directory rather
    than creating arbitrary folders at a guessed workspace root.
    """

    if config.logs_dir is not None:
        return config.logs_dir.resolve()
    if config.output_dir is not None:
        return (config.output_dir / "runner-logs").resolve()
    module_dir = config.module_dir.resolve()
    if module_dir.is_dir():
        return (module_dir / "test-points" / "runner-logs").resolve()
    return (Path(tempfile.gettempdir()) / "codex-rsu-runner-startup").resolve()


def emit_startup_failure_telemetry(config: RunnerConfig, exc: BaseException) -> None:
    """Persist setup failures that occur before a normal run directory exists."""

    try:
        root = startup_failure_log_root(config)
        run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{uuid.uuid4().hex[:8]}"
        run_dir = root / "startup-failures" / run_id
        run_dir.mkdir(parents=True, exist_ok=False)
        RunTelemetry(run_dir).emit(
            "pipeline_failed",
            startup=True,
            error_type=type(exc).__name__,
            error=str(exc),
            module_dir=str(config.module_dir),
            state_file=None,
            run_dir=str(run_dir),
            duration_seconds=0.0,
        )
        print(f"STARTUP_FAILURE_LOG={run_dir}", file=sys.stderr)
    except Exception as telemetry_exc:  # pragma: no cover - defensive logger boundary
        print(
            f"TELEMETRY_STARTUP_WRITE_FAILED={type(telemetry_exc).__name__}: "
            f"{telemetry_exc}",
            file=sys.stderr,
        )


def emit_pipeline_terminal(event: str, **fields: object) -> None:
    """Emit exactly one terminal event for the active run, when available."""

    active = _ACTIVE_PIPELINE
    if active is None or active.terminal_event_emitted:
        return
    payload: dict[str, object] = {
        "state_file": str(active.state_file),
        "run_dir": str(active.run_dir),
        "duration_seconds": round(time.monotonic() - active.started_monotonic, 3),
        "phase": active.phase,
        "rsu_id": active.rsu_id,
        "codex_turns": active.codex_turns,
        "rsu_turns": active.rsu_turns,
        **fields,
    }
    active.terminal_event_emitted = True
    try:
        active.telemetry.emit(event, **payload)
    except Exception as exc:  # pragma: no cover - defensive logger boundary
        # RunTelemetry is intentionally best-effort, but keep this boundary
        # defensive in case an embedded/test telemetry implementation raises a
        # non-OSError.  Never mask the original pipeline outcome.
        print(
            f"TELEMETRY_TERMINAL_WRITE_FAILED={event} ERROR={exc}",
            file=sys.stderr,
        )


def global_lock_dir(config: RunnerConfig) -> Path:
    if config.global_lock_dir is not None:
        return config.global_lock_dir.resolve()
    workspace_key = hashlib.sha256(str(config.workdir).casefold().encode("utf-8")).hexdigest()[:16]
    return (Path(tempfile.gettempdir()) / "codex-rsu-runner-slots" / workspace_key).resolve()


def process_is_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return False
    return True


def recover_stale_running_batches(state_file: Path, current_run_id: str) -> list[str]:
    """Recover batches whose owning parent Runner is no longer alive.

    The caller must already hold the module Runner lock.  JSON state is the
    progress source; historical logs are deliberately not consulted.
    """

    state, _ = load_state(state_file)
    records = {item["rsu_id"]: item for item in state.get("rsus", [])}
    recovered: list[str] = []
    for batch in state.get("batches", []):
        if batch.get("status") != "running":
            continue
        owner_run_id = batch.get("runner_run_id")
        owner_pid = batch.get("runner_pid")
        if owner_run_id == current_run_id and owner_pid == os.getpid():
            continue
        if isinstance(owner_pid, int) and owner_pid > 0 and process_is_alive(owner_pid):
            raise AttentionRequired(
                f"batch {batch.get('batch_id')} is still owned by live runner pid={owner_pid}"
            )
        batch["status"] = "prepared"
        batch["runner_pid"] = None
        batch["runner_run_id"] = None
        batch["started_at"] = None
        batch["recovered_at"] = utc_now()
        for rsu_id in batch.get("active_rsu_ids") or batch.get("rsu_ids", []):
            record = records.get(rsu_id)
            if record is not None and record.get("generation_status") == "running":
                record["generation_status"] = "prepared"
        recovered.append(str(batch.get("batch_id")))
    if recovered:
        state["updated_at"] = utc_now()
        _atomic_write_state(state_file, state)
    return recovered


def mark_batches_running(state_file: Path, batch_ids: tuple[str, ...], run_id: str) -> None:
    """Atomically assign prepared batches and their active RSUs to this Runner."""

    if not batch_ids:
        return
    state, _ = load_state(state_file)
    batches = {item["batch_id"]: item for item in state.get("batches", [])}
    records = {item["rsu_id"]: item for item in state.get("rsus", [])}
    for batch_id in batch_ids:
        batch = batches.get(batch_id)
        if batch is None or batch.get("status") != "prepared":
            raise RunnerError(f"cannot mark non-prepared batch running: {batch_id}")
        active = list(batch.get("active_rsu_ids") or batch.get("rsu_ids", []))
        if not active:
            raise RunnerError(f"cannot run batch without active RSUs: {batch_id}")
        for rsu_id in active:
            record = records.get(rsu_id)
            if record is None:
                raise RunnerError(f"{batch_id} references unknown RSU: {rsu_id}")
            if record.get("generation_status") == "validated":
                continue
            if record.get("generation_status") != "prepared":
                raise RunnerError(
                    f"cannot mark {rsu_id} running from {record.get('generation_status')}"
                )
            record["generation_status"] = "running"
        batch["status"] = "running"
        batch["runner_pid"] = os.getpid()
        batch["runner_run_id"] = run_id
        batch["started_at"] = utc_now()
        batch["recovered_at"] = None
    state["updated_at"] = utc_now()
    _atomic_write_state(state_file, state)


def inspect_batch_result(result_file: Path) -> str:
    """Return missing, empty, recoverable, or invalid for a private result."""

    if not result_file.is_file():
        return "missing"
    try:
        value = json.loads(result_file.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return "invalid"
    if not isinstance(value, dict) or value.get("schema_version") != (
        "rsu-test-point-generation/batch-result-v1"
    ):
        return "invalid"
    rows = value.get("rsus")
    if not isinstance(rows, list) or not rows or not all(isinstance(item, dict) for item in rows):
        return "invalid"
    statuses = [item.get("status") for item in rows]
    if any(status not in {"draft", "complete", "failed", "replan-required"} for status in statuses):
        return "invalid"
    return "recoverable" if any(status != "draft" for status in statuses) else "empty"


def quarantine_invalid_batch_result(output_dir: Path, batch_id: str, result_file: Path) -> Path:
    """Move an invalid private result aside so preparation can rebuild it."""

    resolved_output = output_dir.resolve()
    resolved_result = result_file.resolve()
    if not _is_inside(resolved_result, resolved_output):
        raise RunnerError(f"refusing to quarantine result outside output directory: {result_file}")
    history = (output_dir / "history" / "batch-results").resolve()
    history.mkdir(parents=True, exist_ok=True)
    suffix = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    target = history / f"{batch_id}-{suffix}-{uuid.uuid4().hex[:8]}.json"
    os.replace(resolved_result, target)
    return target


def terminate_process_tree(
    process: subprocess.Popen[str],
    *,
    graceful_timeout_seconds: float = 10.0,
) -> None:
    """Stop a Codex process and any children it spawned.

    On Windows the runner starts Codex in a new process group and uses
    ``taskkill /T`` as the final fallback.  ``Popen.terminate()`` alone only
    guarantees termination of the wrapper process, which could otherwise
    leave a provider request alive after the runner released its slot.
    """

    # Capture this before sending terminate() so a process that was already
    # gone cannot cause a stale/reused PID to be passed to taskkill.  After the
    # graceful wait we check poll() again: taskkill is safe only while the
    # wrapper entry process is still alive.
    was_running = process.poll() is None
    if not was_running:
        return
    try:
        process.terminate()
    except OSError:
        pass
    try:
        process.wait(timeout=max(0.0, graceful_timeout_seconds))
    except subprocess.TimeoutExpired:
        pass

    if process.poll() is None and os.name == "nt" and process.pid:
        taskkill = shutil.which("taskkill")
        if taskkill:
            try:
                subprocess.run(
                    [taskkill, "/PID", str(process.pid), "/T", "/F"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                    timeout=max(5.0, graceful_timeout_seconds),
                )
            except (OSError, subprocess.TimeoutExpired):
                pass
    # taskkill handles the entire Windows process tree.  Only force-kill the
    # wrapper locally when it is still alive (or when the platform is not
    # Windows and the graceful wait timed out).
    if process.poll() is None:
        try:
            process.kill()
        except OSError:
            pass
    try:
        process.wait(timeout=max(1.0, graceful_timeout_seconds))
    except subprocess.TimeoutExpired:
        # The caller must still be allowed to record the watchdog result.  A
        # later process/slot inspection can report any unreaped descendant.
        pass


class GlobalConcurrency:
    """A small cross-process semaphore using exclusive slot files.

    A slot is held only around the Codex process. Dead slots from a terminated
    runner are reclaimed after checking the recorded PID is no longer alive.
    """

    def __init__(
        self,
        directory: Path,
        limit: int,
        wait_timeout_seconds: float,
        heartbeat_seconds: float,
    ) -> None:
        self.directory = directory
        self.limit = limit
        self.wait_timeout_seconds = wait_timeout_seconds
        self.heartbeat_seconds = max(0.25, heartbeat_seconds or 1.0)
        self._slot_owner_tokens: dict[Path, str] = {}

    def _reclaim_dead_slots(self) -> None:
        if not self.directory.is_dir():
            return
        for path in self.directory.glob("slot-*.json"):
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                pid = int(payload.get("pid", 0))
            except (OSError, ValueError, TypeError, json.JSONDecodeError):
                try:
                    age = time.time() - path.stat().st_mtime
                except OSError:
                    continue
                if age > 3600:
                    try:
                        path.unlink()
                    except FileNotFoundError:
                        pass
                continue
            if not process_is_alive(pid):
                try:
                    path.unlink()
                except FileNotFoundError:
                    pass

    @contextmanager
    def slot(self, phase: str, turn_number: int, telemetry: RunTelemetry | None = None) -> Iterator[None]:
        if self.limit <= 0:
            yield
            return
        self.directory.mkdir(parents=True, exist_ok=True)
        started = time.monotonic()
        slot_path: Path | None = None
        while slot_path is None:
            self._reclaim_dead_slots()
            for index in range(self.limit):
                candidate = self.directory / f"slot-{index:03d}.json"
                try:
                    fd = os.open(candidate, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                except FileExistsError:
                    continue
                payload = {
                    "pid": os.getpid(),
                    "phase": phase,
                    "turn": turn_number,
                    "created_at": utc_now(),
                    "owner_token": uuid.uuid4().hex,
                }
                try:
                    os.write(fd, json.dumps(payload, ensure_ascii=False).encode("utf-8"))
                finally:
                    os.close(fd)
                slot_path = candidate
                self._slot_owner_tokens[candidate] = str(payload["owner_token"])
                break
            if slot_path is not None:
                break
            elapsed = time.monotonic() - started
            if self.wait_timeout_seconds > 0 and elapsed >= self.wait_timeout_seconds:
                raise AttentionRequired(
                    f"global Codex concurrency limit ({self.limit}) wait timed out "
                    f"after {elapsed:.1f}s for {phase} turn {turn_number}"
                )
            if telemetry:
                telemetry.emit(
                    "global_slot_wait",
                    phase=phase,
                    turn=turn_number,
                    elapsed_seconds=round(elapsed, 3),
                    limit=self.limit,
                )
            print(
                f"GLOBAL_SLOT_WAIT phase={phase} turn={turn_number} "
                f"elapsed_seconds={elapsed:.1f} limit={self.limit}"
            )
            # Do not sleep past the configured acquisition deadline.  The
            # previous fixed heartbeat floor could make a 50 ms timeout wait
            # for 250 ms (or longer when embedding the runner), which made
            # bounded-wait callers appear hung and made shutdown sluggish.
            sleep_seconds = self.heartbeat_seconds
            if self.wait_timeout_seconds > 0:
                remaining = self.wait_timeout_seconds - (time.monotonic() - started)
                sleep_seconds = min(sleep_seconds, max(0.01, remaining))
            time.sleep(min(sleep_seconds, 5.0))
        wait_seconds = time.monotonic() - started
        if telemetry:
            telemetry.emit(
                "global_slot_acquired",
                phase=phase,
                turn=turn_number,
                wait_seconds=round(wait_seconds, 3),
                slot=slot_path.name,
            )
        try:
            yield
        finally:
            if telemetry:
                telemetry.emit(
                    "global_slot_released",
                    phase=phase,
                    turn=turn_number,
                    slot=slot_path.name,
                )
            try:
                details = json.loads(slot_path.read_text(encoding="utf-8"))
                if (
                    int(details.get("pid", 0)) == os.getpid()
                    and details.get("owner_token") == self._slot_owner_tokens.get(slot_path)
                ):
                    slot_path.unlink()
            except FileNotFoundError:
                pass
            except (OSError, TypeError, ValueError, json.JSONDecodeError):
                # If the slot was replaced or corrupted, leave it for the
                # next acquisition pass to reclaim conservatively.
                pass
            finally:
                self._slot_owner_tokens.pop(slot_path, None)


def build_prompt(
    config: RunnerConfig,
    phase: str,
    rsu_id: str | None = None,
    *,
    force_context_refresh: bool = True,
    effective_session_mode: str | None = None,
    source_fingerprint_sha256: str | None = None,
) -> str:
    fixed_layout = layout_prompt(config)
    common = (
        "使用 `$rsu-test-point-generation`，并严格遵循该 skill。\n"
        f"本地 skill 文件：{SKILL_FILE}\n"
        "目标模块和 manifest 已最终确定。禁止扫描、选择、读取或处理其他模块，"
        "也不得要求用户再次指定模块。\n"
        "runner 已使用 workspace-write 和自动审批复核启动本次调用。执行脚本时使用下面给出的"
        "单条 Python 命令，不要把多个 shell 命令串联在一次调用中；不得未经实际执行就声称工作区只读。\n"
        "本次所有脚本调用必须使用以下同一组目录参数：\n"
        f"{fixed_layout}\n\n"
    )
    if phase == "rsu":
        session_mode = effective_session_mode or config.session_mode
        fingerprint_line = (
            "EXPECTED_SESSION_SOURCE_FINGERPRINT_SHA256="
            f"{source_fingerprint_sha256}\n"
            if source_fingerprint_sha256
            else ""
        )
        if session_mode == "isolated":
            context_policy = (
                "SESSION_CONTEXT_POLICY=isolated-full\n"
                f"{fingerprint_line}"
                "本次是独立会话。运行准备命令后，必须完整读取其输出的 INPUT_FILE，"
                "不得依赖其他会话的记忆。\n\n"
            )
        elif force_context_refresh:
            context_policy = (
                "SESSION_CONTEXT_POLICY=refresh-current-rsu-full\n"
                f"{fingerprint_line}"
                "本次属于模块共享会话，但这是首个 RSU、周期性刷新点或会话恢复点。"
                "运行准备命令后，必须完整重读其输出的 INPUT_FILE，以重新注入当前 RSU 的"
                "固定上下文和动态依赖；会话记忆不得覆盖文件和输入哈希。\n\n"
            )
        else:
            context_policy = (
                "SESSION_CONTEXT_POLICY=module-session-incremental-current-rsu\n"
                f"{fingerprint_line}"
                "本次延续同一模块的 Codex 会话。运行准备命令后，必须核对输出的 "
                "SESSION_SOURCE_FINGERPRINT_SHA256 与上面的 EXPECTED 值完全一致，"
                "然后只读取 SESSION_INPUT 中的当前 RSU、支持 RSU、Q、动态 FC/DC 和证据增量；"
                "不要常规性重读 INPUT_FILE 中已经加载且指纹未变化的固定资源正文和生成契约。"
                "完整 INPUT_FILE 仍是审计与独立复现的权威包。若无法准确回忆固定需求或契约、"
                "发现上下文可能被摘要/压缩、记忆与锚点冲突，或增量不足以形成可判断结果，"
                "必须补读 INPUT_FILE 的相关固定章节；仍不确定时完整重读，不能猜测。\n\n"
            )
        return common + context_policy + (
            f"本次只处理 generation-state.json 中严格意义上的最早未完成 RSU（预期为 {rsu_id}）。"
            "只完成这一个 RSU 的准备、候选生成和校验；校验成功后立即结束本次调用，"
            "不得准备或处理后续 RSU。遇到未回答问题、缺失资源、业务歧义、哈希不一致或其他阻塞时，"
            "不得猜测，不得隐藏假设，立即停止并报告。\n\n"
            "准备命令：\n"
            f"{phase_command(config, 'prepare_next_rsu.py')}\n\n"
            "按 SESSION_CONTEXT_POLICY 读取准备命令输出的 INPUT_FILE 或 SESSION_INPUT，"
            "完成候选文件后运行校验命令：\n"
            f"{phase_command(config, 'validate_rsu_test_points.py')}"
        )
    if phase == "finalization":
        return common + (
            "所有 RSU 已验证。本次调用只执行模块测试点汇总与发布：准备 finalization 输入，"
            "完成 module-test-points.md 和 coverage-matrix.md，并运行最终校验。"
            "校验后立即结束，不得在同一调用中执行用例就绪性审查；遇到阻塞立即停止。\n\n"
            "准备命令：\n"
            f"{phase_command(config, 'prepare_finalization.py')}\n\n"
            "完成汇总文件后运行校验命令：\n"
            f"{phase_command(config, 'validate_module_test_points.py')}"
        )
    if phase == "case-readiness":
        return common + (
            "全模块测试点已经验证。本次调用只执行测试用例输入就绪性审查：准备 readiness 输入，"
            "完成 test-case-readiness.md 并运行校验。不得生成测试用例；"
            "发现 blocked-input 或 upstream-gap 时保留问题和审查结果并停止，不得自行补答案。\n\n"
            "准备命令：\n"
            f"{phase_command(config, 'prepare_case_readiness.py')}\n\n"
            "完成审查文件后运行校验命令：\n"
            f"{phase_command(config, 'validate_case_readiness.py')}"
        )
    raise RunnerError(f"unsupported runner phase: {phase}")


def build_stage_prompt_v2(
    config: RunnerConfig,
    output_dir: Path,
    phase: str,
    *,
    batch_id: str | None = None,
    repair_error: str | None = None,
) -> str:
    inherited = (
        "本会话从模块基础会话独立 fork，已继承 Skill 与固定需求；不要重新读取 SKILL.md。\n"
        if config.session_mode == "module-session"
        else f"本次是独立会话，完整读取并遵循 Skill：{SKILL_FILE}\n"
    )
    common = (
        inherited
        + f"模块：{config.module_dir}\n测试点目录：{output_dir}\n"
        + "不得读取 runner-logs，不得处理其他模块，不得启动 run_generation.py，不依赖自动 compaction。"
        + "只写本阶段授权输出，不得运行准备或校验脚本；父 Runner 负责所有共享状态提交与确定性校验。"
        + "文件与 SHA-256 是权威事实，会话记忆不能替代文件校验。人工修改文件必须使用 apply_patch。\n"
    )
    if phase == "foundation":
        return (
            f"完整读取并遵循测试点生成 Skill：{SKILL_FILE}\n"
            f"完整读取模块基础输入：{output_dir / 'foundation-input.md'}\n"
            "本次只建立稳定基础上下文。不得修改任何模块、状态、计划、候选或最终文件，"
            "不得读取 runner-logs，不得启动任何生成脚本。"
        )
    if phase == "planning":
        task = (
            f"完整读取 {output_dir / 'planning-input.md'}，只填写 {output_dir / 'generation-plan.json'}。"
            "判断 simple/complex 并按相同 Context Signature 分批；普通批目标 4～6、最多 10，"
            "复杂 RSU 单独成批。不得生成候选，不得修改前置分析、状态或其他文件。"
        )
    elif phase == "batch" and batch_id:
        task = (
            f"完整读取 {output_dir / 'batches' / (batch_id + '-input.md')}，并按清单逐个读取本批 RSU delta。"
            "只填写清单授权的批次私有 by-rsu 文件和对应 batch-result JSON；不得修改正式 by-rsu、"
            "generation-state.json、generation-plan.json、输入、来源、其他批次或最终文件。"
            "你是高级测试工程师。完整生成来源支持的测试点，不设目标数量。每个候选必须能够独立触发、"
            "独立执行、独立判定并独立定位缺陷。先识别独立测试承诺，再生成候选并进行原子性自审；不同操作、"
            "控件/对象、业务结果、状态迁移、异常处理或边界约束应分别形成候选。状态、错误码、字段、等价类、"
            "边界值和页面/接口/数据库/日志观察层，若代表不同操作、对象、状态迁移、结果或可定位缺陷就拆分；"
            "只有同一操作、对象、生命周期阶段和预期结果下的等价输入或共同证据才合并。不得把复选框可选性、"
            "全选范围、操作按钮可用性和操作后的状态重算写在同一个候选中。使用测试项、测试点、备注：测试项简洁分类，测试点直接包含必要条件/操作及明确预期，备注可为空且不能隐藏关键断言。只合并三列均完全重复的候选。"
            "确有跨状态时序、冲突依赖或语义宽度导致本批无法可靠处理时，在 batch-result 中明确填写"
            " replan-required 和理由，不得扩写候选掩盖。"
        )
    elif phase == "finalization":
        source = (
            output_dir / "finalization-session-input.md"
            if config.session_mode == "module-session"
            and (output_dir / "finalization-session-input.md").is_file()
            else output_dir / "finalization-input.md"
        )
        task = (
            f"完整读取 {source}，只完成 {output_dir / 'module-test-points.md'} 和 "
            f"{output_dir / 'coverage-matrix.md'}。按 RSU map 和局部候选顺序稳定编号；默认一候选一测试点，"
            "使用测试项、测试点、备注并保留完整验证描述。仅合并三列均完全重复的候选，不做广义业务合并，也不得按数量增删测试点。"
            "不得修改状态、候选、输入或来源文件。"
        )
    elif phase == "case-readiness":
        source = (
            output_dir / "case-readiness-session-input.md"
            if config.session_mode == "module-session"
            and (output_dir / "case-readiness-session-input.md").is_file()
            else output_dir / "case-readiness-input.md"
        )
        task = (
            f"完整读取 {source}，只完成 {output_dir / 'test-case-readiness.md'}。"
            "不得生成测试用例，不得修改状态、测试点、候选、输入或来源文件。"
            "必须逐个 pending CIQ 执行反向自审；不得仅因 Data Closure 为 test-point-ready、"
            "测试版本尚未发布、字段需发版后核对、具体样本/任务 ID 未写死或 SQL 参数可执行时绑定"
            "而判定 blocked-input。只有缺少无法由来源推导、语义参数、常规查询/观察或执行时绑定"
            "替代的输入时才允许保留 CIQ。pending 的回填列只需语义上明确未回答，不锁定中英文或大小写。"
        )
    else:
        raise RunnerError(f"unsupported v2 stage prompt: {phase}")
    if repair_error:
        task += (
            "\nVALIDATION_REPAIR_MODE=deterministic-only\n父 Runner 校验错误如下：\n"
            + repair_error[-6000:]
            + "\n只修复该错误涉及的授权输出，不扩大范围。"
        )
    return common + task


def _atomic_write_state(path: Path, value: dict[str, Any]) -> None:
    text = json.dumps(value, ensure_ascii=False, indent=2) + "\n"
    temp = path.with_name(f".{path.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    with temp.open("w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temp, path)


def restore_parent_state_if_modified(path: Path, before: bytes, label: str) -> bool:
    """Rollback an AI stage's shared-state write so the parent can validate/commit."""

    if path.read_bytes() == before:
        return False
    try:
        value = json.loads(before.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RunnerError(f"cannot restore parent state after {label}: {exc}") from exc
    _atomic_write_state(path, value)
    return True


def _is_inside(path: Path, parent: Path) -> bool:
    try:
        path.resolve().relative_to(parent.resolve())
        return True
    except ValueError:
        return False


def protected_workspace_snapshot(
    module_dir: Path,
    *,
    allowed_paths: tuple[Path, ...],
    ignored_roots: tuple[Path, ...] = (),
) -> dict[str, str]:
    allowed = tuple(path.resolve() for path in allowed_paths)
    ignored = tuple(path.resolve() for path in ignored_roots)
    result: dict[str, str] = {}
    for path in module_dir.rglob("*"):
        if not path.is_file():
            continue
        resolved = path.resolve()
        if any(resolved == item or (item.is_dir() and _is_inside(resolved, item)) for item in allowed):
            continue
        if any(_is_inside(resolved, root) for root in ignored):
            continue
        if path.name in {".generation.lock", ".generation-runner.lock"} or path.suffix == ".tmp":
            continue
        try:
            result[resolved.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        except OSError as exc:
            raise RunnerError(f"cannot snapshot protected file {path}: {exc}") from exc
    return result


def require_protected_snapshot_unchanged(before: dict[str, str], after: dict[str, str], label: str) -> None:
    if before == after:
        return
    changed = sorted(set(before) ^ set(after) | {key for key in set(before) & set(after) if before[key] != after[key]})
    raise RunnerError(f"{label} modified files outside its authorization: {changed[:8]}")


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def resolve_codex_binary(value: str) -> str:
    # When the runner is launched from a terminal/IDE, ``codex`` may resolve
    # to an older globally installed npm binary even though the desktop app
    # exposes the current CLI through CODEX_CLI_PATH.  The runner must follow
    # that local configuration by default; an explicit path/name that is not
    # the default ``codex`` keeps the normal PATH resolution behavior.
    if value == "codex":
        configured = os.environ.get("CODEX_CLI_PATH", "").strip()
        if configured:
            configured_path = Path(configured).expanduser()
            if configured_path.is_file():
                return str(configured_path.resolve())
        local_appdata = os.environ.get("LOCALAPPDATA", "").strip()
        appdata_root = Path(local_appdata) if local_appdata else Path.home() / "AppData" / "Local"
        desktop_bin = appdata_root / "OpenAI" / "Codex" / "bin"
        if desktop_bin.is_dir():
            candidates = [
                candidate
                for version_dir in desktop_bin.iterdir()
                if version_dir.is_dir()
                for candidate in (version_dir / "codex.exe", version_dir / "bin" / "codex.exe")
                if candidate.is_file()
            ]
            if candidates:
                return str(max(candidates, key=lambda path: path.stat().st_mtime).resolve())
    resolved = shutil.which(value)
    if resolved:
        return resolved
    candidate = Path(value).expanduser()
    if candidate.is_file():
        return str(candidate.resolve())
    raise RunnerError(f"Codex CLI executable was not found: {value}")


def codex_supports_exec_fork(binary: str) -> bool:
    try:
        result = subprocess.run(
            [binary, "exec", "fork", "--help"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
        )
    except OSError:
        return False
    output = "\n".join(part for part in (result.stdout, result.stderr) if part)
    return result.returncode == 0 and bool(
        re.search(r"(?im)^Usage:\s+\S+\s+exec\s+fork\b", output)
    )


def select_codex_binary(value: str, *, require_fork: bool) -> str:
    binary = resolve_codex_binary(value)
    if require_fork and not codex_supports_exec_fork(binary):
        version = probe_codex_version(binary) or "unknown"
        raise RunnerError(
            "module-session requires `codex exec fork`; "
            f"checked {binary} ({version}). Use a supported CLI or --session-mode isolated."
        )
    return binary


def codex_command(
    config: RunnerConfig,
    last_message: Path,
    extra_writable_dirs: tuple[Path, ...],
    fork_from: str | None = None,
    *,
    execution_workdir: Path | None = None,
    output_schema: Path | None = None,
) -> list[str]:
    active_workdir = (execution_workdir or config.workdir).resolve()
    command = [
        resolve_codex_binary(config.codex_bin),
        "exec",
        "--json",
        "--color",
        "never",
        "--skip-git-repo-check",
        "--cd",
        str(active_workdir),
        "--output-last-message",
        str(last_message),
    ]
    if output_schema is not None:
        command.extend(["--output-schema", str(output_schema.resolve())])
    if config.sandbox == "workspace-write":
        command.append("--approve-for-me")
    else:
        command.extend(["--sandbox", config.sandbox])
    if config.profile:
        command.extend(["--profile", config.profile])
    if config.model:
        command.extend(["--model", config.model])
    added: set[Path] = set()
    for directory in extra_writable_dirs:
        resolved = directory.resolve()
        if resolved in added or is_within(resolved, active_workdir):
            continue
        command.extend(["--add-dir", str(resolved)])
        added.add(resolved)
    if fork_from is not None:
        command.extend(["fork", fork_from])
    # Pass the prompt through UTF-8 stdin. Long Chinese paths are not reliable
    # when routed through Windows .cmd argument parsing.
    command.append("-")
    return command


def safe_slug(value: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "-", value).strip("-") or "turn"


def event_message(event: dict) -> str | None:
    event_type = event.get("type")
    if event_type == "thread.started":
        return f"thread.started {event.get('thread_id', '')}".rstrip()
    if event_type == "turn.completed":
        return "turn.completed"
    if event_type in {"turn.failed", "error"}:
        message = event.get("message") or event.get("error") or event
        return f"{event_type}: {message}"
    return None


def event_action_signature(event: dict) -> str | None:
    """Return an exact signature for consecutive tool starts in Codex JSONL."""

    if event.get("type") != "item.started":
        return None
    item = event.get("item")
    if not isinstance(item, dict):
        return None
    item_type = str(item.get("type", ""))
    if item_type == "command_execution":
        action = item.get("command")
    elif item_type in {"mcp_tool_call", "custom_tool_call", "tool_call"}:
        action = {
            key: item.get(key)
            for key in ("name", "server", "arguments", "input")
            if key in item
        }
    else:
        return None
    return json.dumps([item_type, action], ensure_ascii=False, sort_keys=True, default=str)


def invoke_codex(
    config: RunnerConfig,
    run_dir: Path,
    turn_number: int,
    phase: str,
    prompt: str,
    rsu_id: str | None,
    *,
    fork_from: str | None = None,
    session: CodexSession | None = None,
    coordinator: GlobalConcurrency | None = None,
    telemetry: RunTelemetry | None = None,
    execution_workdir: Path | None = None,
    authorized_write_dirs: tuple[Path, ...] | None = None,
    output_schema: Path | None = None,
) -> CodexTurnResult:
    label = safe_slug(f"{phase}-{rsu_id}" if rsu_id else phase)
    prefix = f"{turn_number:03d}-{label}"
    jsonl_log = run_dir / f"{prefix}.jsonl"
    stderr_log = run_dir / f"{prefix}.stderr.log"
    last_message = run_dir / f"{prefix}.last-message.md"
    writable = authorized_write_dirs
    if writable is None:
        writable = tuple(
            path
            for path in (config.module_dir, config.preanalysis_dir, config.output_dir, run_dir)
            if path is not None
        )
    active_session = session or CodexSession("isolated")
    command = codex_command(
        config,
        last_message,
        writable,
        fork_from,
        execution_workdir=execution_workdir,
        output_schema=output_schema,
    )
    env = dict(os.environ)
    env["PYTHONUTF8"] = "1"
    action = "forking" if fork_from is not None else "starting"
    session_suffix = f" from {fork_from}" if fork_from is not None else ""
    print(f"[{turn_number:03d}] {action} {phase}{f' {rsu_id}' if rsu_id else ''}{session_suffix}")
    slot_context = coordinator.slot(phase, turn_number, telemetry) if coordinator else nullcontext()
    session_error: str | None = None
    started_monotonic = time.monotonic()
    started_at = utc_now()
    termination_reason: str | None = None
    returncode: int | None = None
    process_pid: int | None = None
    process_started_monotonic: float | None = None
    observed_thread_id: str | None = None
    usage: dict[str, int] = {}
    tool_calls = 0
    validation_attempts = 0
    validation_failures = 0
    failure_events: list[str] = []
    if telemetry:
        telemetry.emit(
            "codex_command_prepared",
            phase=phase,
            rsu_id=rsu_id,
            turn=turn_number,
            action=action,
            fork_from=fork_from,
            command=command,
        )
    with slot_context:
        with jsonl_log.open("w", encoding="utf-8", newline="\n") as stdout_file, stderr_log.open(
            "w", encoding="utf-8", newline="\n"
        ) as stderr_file:
            try:
                popen_kwargs: dict[str, object] = {
                    "stdin": subprocess.PIPE,
                    "stdout": subprocess.PIPE,
                    "stderr": stderr_file,
                    "text": True,
                    "encoding": "utf-8",
                    "errors": "replace",
                    "env": env,
                }
                if os.name == "nt":
                    popen_kwargs["creationflags"] = getattr(
                        subprocess, "CREATE_NEW_PROCESS_GROUP", 0
                    )
                process = subprocess.Popen(command, **popen_kwargs)
                process_pid = process.pid
                process_started_monotonic = time.monotonic()
                if telemetry:
                    telemetry.emit(
                        "codex_process_started",
                        phase=phase,
                        rsu_id=rsu_id,
                        turn=turn_number,
                        pid=process_pid,
                    )
            except OSError as exc:
                raise RunnerError(f"failed to start Codex CLI: {exc}") from exc
            assert process.stdin is not None
            assert process.stdout is not None
            try:
                process.stdin.write(prompt)
                process.stdin.close()
            except BrokenPipeError:
                pass
            try:
                events: queue.Queue[tuple[str, object | None]] = queue.Queue()

                def read_stdout() -> None:
                    try:
                        for line in process.stdout:
                            events.put(("line", line))
                    except BaseException as exc:  # pragma: no cover - platform/pipe dependent
                        events.put(("reader-error", exc))
                    finally:
                        events.put(("eof", None))

                reader = threading.Thread(
                    target=read_stdout,
                    name=f"codex-reader-{turn_number}",
                    daemon=True,
                )
                reader.start()
                last_activity = started_monotonic
                previous_action: str | None = None
                repeated_actions = 0
                while True:
                    now = time.monotonic()
                    elapsed = now - started_monotonic
                    if process.poll() is not None and events.empty():
                        returncode = process.returncode
                        break
                    if config.stage_timeout_seconds > 0 and elapsed >= config.stage_timeout_seconds:
                        termination_reason = "stage-timeout"
                    elif config.stall_timeout_seconds > 0 and now - last_activity >= config.stall_timeout_seconds:
                        termination_reason = "stall-timeout"
                    if termination_reason is not None:
                        idle_seconds = now - last_activity
                        marker = {
                            "type": "runner.watchdog",
                            "reason": termination_reason,
                            "elapsed_seconds": round(elapsed, 3),
                            "last_activity_age_seconds": round(idle_seconds, 3),
                        }
                        stdout_file.write(json.dumps(marker, ensure_ascii=False) + "\n")
                        stdout_file.flush()
                        print(
                            f"WATCHDOG_TERMINATE={termination_reason} PHASE={phase} "
                            f"ELAPSED_SECONDS={elapsed:.1f}"
                        )
                        terminate_process_tree(process, graceful_timeout_seconds=10)
                        if telemetry:
                            telemetry.emit(
                                "watchdog_terminated",
                                phase=phase,
                                rsu_id=rsu_id,
                                turn=turn_number,
                                reason=termination_reason,
                                elapsed_seconds=round(elapsed, 3),
                                idle_seconds=round(idle_seconds, 3),
                                pid=process_pid,
                            )
                        returncode = process.returncode if process.returncode not in (None, 0) else WATCHDOG_EXIT_CODE
                        break

                    wait_timeout = config.heartbeat_interval_seconds or 1.0
                    if config.stage_timeout_seconds > 0:
                        wait_timeout = min(wait_timeout, max(0.05, config.stage_timeout_seconds - elapsed))
                    if config.stall_timeout_seconds > 0:
                        wait_timeout = min(
                            wait_timeout,
                            max(0.05, config.stall_timeout_seconds - (now - last_activity)),
                        )
                    try:
                        event_kind, value = events.get(timeout=wait_timeout)
                    except queue.Empty:
                        idle = time.monotonic() - last_activity
                        print(
                            f"HEARTBEAT phase={phase} turn={turn_number} "
                            f"elapsed_seconds={time.monotonic() - started_monotonic:.1f} "
                            f"idle_seconds={idle:.1f}"
                        )
                        continue
                    if event_kind == "line":
                        line = str(value)
                        last_activity = time.monotonic()
                        stdout_file.write(line)
                        stdout_file.flush()
                        try:
                            event = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if isinstance(event, dict):
                            action_signature = event_action_signature(event)
                            if action_signature is not None:
                                if action_signature == previous_action:
                                    repeated_actions += 1
                                else:
                                    previous_action = action_signature
                                    repeated_actions = 1
                                if (
                                    config.repeated_action_limit > 0
                                    and repeated_actions >= config.repeated_action_limit
                                ):
                                    termination_reason = "repeated-action"
                            if event.get("type") == "thread.started":
                                observed_id = event.get("thread_id")
                                if isinstance(observed_id, str):
                                    if observed_thread_id is not None and observed_thread_id != observed_id:
                                        session_error = "Codex emitted multiple thread IDs in one invocation"
                                    observed_thread_id = observed_id
                            if event.get("type") in {"turn.failed", "error"}:
                                failure_events.append(json.dumps(event, ensure_ascii=False))
                            if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
                                usage = {
                                    str(key): value
                                    for key, value in event["usage"].items()
                                    if isinstance(value, int) and not isinstance(value, bool)
                                }
                            if event.get("type") == "item.completed" and isinstance(event.get("item"), dict):
                                item = event["item"]
                                if item.get("type") in {
                                    "command_execution", "mcp_tool_call", "web_search",
                                    "file_change", "computer_action",
                                }:
                                    tool_calls += 1
                                command_text = str(item.get("command") or "")
                                if "validate_" in command_text:
                                    validation_attempts += 1
                                    if isinstance(item.get("exit_code"), int) and item["exit_code"] != 0:
                                        validation_failures += 1
                            message = event_message(event)
                            if message:
                                print(f"[{turn_number:03d}] {message}")
                    elif event_kind == "reader-error":
                        stderr_file.write(f"runner stdout reader error: {value}\n")
                        stderr_file.flush()
                        last_activity = time.monotonic()
                    elif event_kind == "eof" and process.poll() is not None:
                        returncode = process.returncode
                        break
                reader.join(timeout=1)
                # Popen owns the wrapper around the pipe; close it explicitly
                # so repeated turns do not leak descriptors in long module
                # sessions (and so Windows does not retain the pipe handle).
                try:
                    process.stdout.close()
                except OSError:
                    pass
            except KeyboardInterrupt:
                terminate_process_tree(process, graceful_timeout_seconds=10)
                raise
    if returncode is None:
        returncode = process.returncode if process.returncode is not None else 1
    if session_error is not None:
        stderr_log.write_text(session_error + "\n", encoding="utf-8")
        returncode = returncode or 1
        termination_reason = "session-error"
    if returncode == 0 and observed_thread_id is None:
        message = (
            "Codex completed without a thread.started event; "
            "the runner cannot validate foundation/fork identity"
        )
        stderr_log.write_text(message + "\n", encoding="utf-8")
        returncode = 1
        termination_reason = "missing-session-id"
    if telemetry:
        telemetry.emit(
            "codex_process_finished",
            phase=phase,
            rsu_id=rsu_id,
            turn=turn_number,
            pid=process_pid,
            returncode=returncode,
            termination_reason=termination_reason,
            process_duration_seconds=(
                round(time.monotonic() - process_started_monotonic, 3)
                if process_started_monotonic is not None
                else None
            ),
            thread_id=observed_thread_id,
            tool_calls=tool_calls,
            validation_attempts=validation_attempts,
            validation_failures=validation_failures,
            usage=usage,
        )
    return CodexTurnResult(
        returncode,
        jsonl_log,
        stderr_log,
        last_message,
        started_at,
        utc_now(),
        time.monotonic() - started_monotonic,
        termination_reason,
        tool_calls,
        validation_attempts,
        validation_failures,
        usage,
        "\n".join(failure_events),
        observed_thread_id,
    )


def require_runnable_rsu(item: RsuState) -> None:
    if item.status == "blocked":
        details = "; ".join(item.blockers) or "state contains no blocker details"
        raise AttentionRequired(f"{item.rsu_id} is blocked: {details}")
    if item.status not in RUNNABLE_RSU_STATUSES:
        raise AttentionRequired(f"{item.rsu_id} cannot be scheduled from status {item.status}")


def assert_rsu_progress(before: StateSnapshot, after: StateSnapshot, expected_rsu: str) -> None:
    before_ids = tuple(item.rsu_id for item in before.rsus)
    after_ids = tuple(item.rsu_id for item in after.rsus)
    if before_ids != after_ids:
        raise RunnerError("RSU order or identity changed during a Codex turn")
    if before.session_source_fingerprint_sha256 != after.session_source_fingerprint_sha256:
        raise RunnerError("module-session fixed source fingerprint changed during an RSU turn")
    after_by_id = {item.rsu_id: item for item in after.rsus}
    if after_by_id[expected_rsu].status != "validated":
        actual = after_by_id[expected_rsu].status
        raise AttentionRequired(
            f"Codex turn ended without validating {expected_rsu}; current status is {actual}"
        )
    delta = after.validated_count - before.validated_count
    if delta != 1:
        raise RunnerError(
            f"validated RSU count must increase by exactly 1 for {expected_rsu}; observed delta={delta}"
        )


def require_success(result: CodexTurnResult, phase: str) -> None:
    if result.returncode == 0:
        return
    stderr_tail = ""
    if result.stderr_log.is_file():
        stderr_tail = result.stderr_log.read_text(encoding="utf-8", errors="replace")[-4000:].strip()
    details = f"; stderr tail: {stderr_tail}" if stderr_tail else ""
    raise RunnerError(
        f"Codex {phase} turn exited with code {result.returncode}; "
        f"logs: {result.jsonl_log}, {result.stderr_log}{details}"
    )


def log_tail(path: Path, limit: int = 32000) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")[-limit:]
    except OSError:
        return ""


def is_transient_codex_failure(result: CodexTurnResult) -> bool:
    if result.termination_reason in {"stage-timeout", "stall-timeout", "repeated-action"}:
        return True
    if result.returncode == 0:
        return False
    evidence = "\n".join(
        part for part in (log_tail(result.jsonl_log), log_tail(result.stderr_log)) if part
    )
    if NONTRANSIENT_PROVIDER_FAILURE_RE.search(evidence):
        return False
    return TRANSIENT_CODEX_FAILURE_RE.search(evidence) is not None


def retry_after_seconds(result: CodexTurnResult) -> float | None:
    """Extract a numeric Retry-After hint from Codex/provider evidence."""

    evidence = turn_evidence(result)
    values: list[float] = []
    for match in RETRY_AFTER_RE.finditer(evidence):
        try:
            value = float(match.group("seconds"))
        except (TypeError, ValueError):
            continue
        if value >= 0:
            values.append(value)
    return max(values) if values else None


def file_sha256(path: Path) -> str | None:
    """Return a file digest for telemetry without making it a hard failure."""

    try:
        digest = hashlib.sha256()
        with path.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()
    except OSError:
        return None


def probe_codex_version(binary: str | None) -> str | None:
    if not binary:
        return None
    try:
        result = subprocess.run(
            [binary, "--version"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    value = (result.stdout or result.stderr).strip()
    return value.splitlines()[0][:300] if value else None


def telemetry_environment(config: RunnerConfig, state_data: dict) -> dict[str, object]:
    """Capture enough local state to make a later timing audit reproducible."""

    resolved_binary: str | None = None
    try:
        resolved_binary = resolve_codex_binary(config.codex_bin)
    except RunnerError:
        # A custom invoker/test may not have a real Codex binary.  Keep the
        # configured value in telemetry instead of making initialization fail.
        pass
    return {
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "os_name": os.name,
        "workdir": str(config.workdir),
        "module_dir": str(config.module_dir),
        "configured_codex_bin": config.codex_bin,
        "resolved_codex_bin": resolved_binary,
        "codex_version": probe_codex_version(resolved_binary),
        "model": config.model,
        "profile": config.profile,
        "sandbox": config.sandbox,
        "session_mode": config.session_mode,
        "session_recovery": config.session_recovery,
        "runner_script_sha256": file_sha256(Path(__file__).resolve()),
        "skill_sha256": file_sha256(SKILL_FILE),
        "manifest_sha256": state_data.get("manifest_sha256"),
        "argv": list(sys.argv[1:]),
        "config": {
            "max_rsu_turns": config.max_rsu_turns,
            "max_transient_retries": config.max_transient_retries,
            "retry_base_delay_seconds": config.retry_base_delay_seconds,
            "retry_max_delay_seconds": config.retry_max_delay_seconds,
            "stage_timeout_seconds": config.stage_timeout_seconds,
            "stall_timeout_seconds": config.stall_timeout_seconds,
            "heartbeat_interval_seconds": config.heartbeat_interval_seconds,
            "repeated_action_limit": config.repeated_action_limit,
            "max_watchdog_retries": config.max_watchdog_retries,
            "session_reset_after": config.session_reset_after,
            "max_validation_repairs": config.max_validation_repairs,
            "global_concurrency": config.global_concurrency,
            "global_lock_dir": str(global_lock_dir(config)),
            "global_wait_timeout_seconds": config.global_wait_timeout_seconds,
            "context_refresh_interval": config.context_refresh_interval,
        },
    }


def turn_evidence(result: CodexTurnResult, limit: int = 48000) -> str:
    return "\n".join(
        part
        for part in (
            log_tail(result.jsonl_log, limit),
            log_tail(result.stderr_log, limit),
            log_tail(result.last_message, limit),
        )
        if part
    )[-limit:]


def is_session_resume_failure(result: CodexTurnResult) -> bool:
    return SESSION_RESUME_FAILURE_RE.search(turn_evidence(result)) is not None


def is_repairable_validation_failure(result: CodexTurnResult) -> bool:
    evidence = turn_evidence(result)
    if not evidence or NONREPAIRABLE_VALIDATION_RE.search(evidence):
        return False
    return REPAIRABLE_VALIDATION_RE.search(evidence) is not None


def build_validation_repair_prompt(
    config: RunnerConfig,
    phase: str,
    rsu_id: str | None,
    result: CodexTurnResult,
) -> str:
    phase_label = f"RSU {rsu_id}" if phase == "rsu" else phase
    evidence = turn_evidence(result, 12000)
    return (
        "VALIDATION_REPAIR_MODE=deterministic-only\n"
        f"上一轮 {phase_label} 已生成产物，但确定性校验未通过。只修复校验器明确报告的"
        "表格、连续编号、引用集合、覆盖关系、占位符或输入哈希等机器可判定问题。"
        "不得改变需求语义、补造业务规则、回答 Q/CIQ、把 blocked-input/upstream-gap 改成 ready，"
        "也不得处理其他模块或后续阶段。若错误需要语义取舍或上游修复，立即停止。\n\n"
        "不要重新运行准备脚本或覆盖当前输入；读取现有权威输入与当前输出，最小化修改后只运行"
        "本阶段既定校验命令。\n\n"
        "上一轮校验证据（可能截断）：\n"
        "```text\n"
        f"{evidence}\n"
        "```\n\n"
        f"校验命令：\n{phase_command(config, {'rsu': 'validate_rsu_test_points.py', 'finalization': 'validate_module_test_points.py', 'case-readiness': 'validate_case_readiness.py'}[phase])}"
    )


def session_recovery_prompt(prompt: str, phase: str, rsu_id: str | None, mode: str) -> str:
    target = f"RSU {rsu_id}" if phase == "rsu" else phase
    return prompt + (
        "\n\nSESSION_RECOVERY_OVERRIDE=" + mode + "\n"
        f"旧 module session 已因连续失败被丢弃。本轮从新会话恢复 {target}。"
        "必须重新读取本阶段当前输入文件的完整内容；不得依赖旧会话记忆，也不得重新处理"
        "已经由 generation-state.json 证明完成的阶段。"
    )


def phase_completed(snapshot: StateSnapshot, phase: str, rsu_id: str | None) -> bool:
    if phase == "rsu":
        return any(
            item.rsu_id == rsu_id and item.status == "validated"
            for item in snapshot.rsus
        )
    if phase == "finalization":
        return snapshot.finalization_status == "validated"
    if phase == "case-readiness":
        return snapshot.case_readiness_status == "validated"
    raise RunnerError(f"unsupported runner phase: {phase}")


def require_retry_safe(
    before: StateSnapshot,
    after: StateSnapshot,
    phase: str,
    rsu_id: str | None,
) -> None:
    before_ids = tuple(item.rsu_id for item in before.rsus)
    after_ids = tuple(item.rsu_id for item in after.rsus)
    if before_ids != after_ids:
        raise RunnerError("RSU order or identity changed during a failed Codex turn")
    if after.validated_count != before.validated_count:
        raise RunnerError(
            "validated RSU count changed without completing the expected failed turn"
        )

    if phase == "rsu":
        current = next((item for item in after.rsus if item.rsu_id == rsu_id), None)
        if current is None:
            raise RunnerError(f"expected RSU disappeared during retry check: {rsu_id}")
        require_runnable_rsu(current)
        if after.next_rsu is None or after.next_rsu.rsu_id != rsu_id:
            raise RunnerError(
                f"failed turn changed the next RSU; expected {rsu_id}, "
                f"found {after.next_rsu.rsu_id if after.next_rsu else 'NONE'}"
            )
        return

    if phase == "finalization":
        if after.finalization_status not in {"ready", "prepared"}:
            raise AttentionRequired(
                "failed finalization turn left a non-runnable state: "
                f"{after.finalization_status}"
            )
        return

    if phase == "case-readiness":
        if after.case_readiness_status not in {"not-ready", "prepared"}:
            raise AttentionRequired(
                "failed case-readiness turn left a non-runnable state: "
                f"{after.case_readiness_status}"
            )
        return

    raise RunnerError(f"unsupported runner phase: {phase}")


def invoke_phase_with_retries(
    config: RunnerConfig,
    run_dir: Path,
    state_file: Path,
    first_turn_number: int,
    phase: str,
    prompt: str,
    rsu_id: str | None,
    before: StateSnapshot,
    invoker: Invoker,
    *,
    session: CodexSession | None = None,
    coordinator: GlobalConcurrency | None = None,
    telemetry: RunTelemetry | None = None,
) -> tuple[CodexTurnResult, StateSnapshot, int]:
    attempts = 0
    transient_retries = 0
    watchdog_retries = 0
    repair_attempts = 0
    attempt_prompt = prompt
    while True:
        attempts += 1
        turn_number = first_turn_number + attempts - 1
        if telemetry:
            telemetry.emit(
                "phase_attempt_started",
                phase=phase,
                rsu_id=rsu_id,
                turn=turn_number,
                attempt=attempts,
                repair_attempt=repair_attempts,
                transient_retry=transient_retries,
            )
        started = time.monotonic()
        try:
            slot_context = coordinator.slot(phase, turn_number, telemetry) if coordinator else nullcontext()
            with slot_context:
                result = invoker(
                    config,
                    run_dir,
                    turn_number,
                    phase,
                    attempt_prompt,
                    rsu_id,
                )
        except Exception as exc:
            if telemetry:
                telemetry.emit(
                    "phase_attempt_exception",
                    phase=phase,
                    rsu_id=rsu_id,
                    turn=turn_number,
                    elapsed_seconds=round(time.monotonic() - started, 3),
                    error=repr(exc),
                )
            raise
        if telemetry:
            telemetry.emit(
                "phase_attempt_finished",
                phase=phase,
                rsu_id=rsu_id,
                turn=turn_number,
                attempt=attempts,
                returncode=result.returncode,
                duration_seconds=round(result.duration_seconds or (time.monotonic() - started), 3),
                termination_reason=result.termination_reason,
            )
        _, after = load_state(state_file)
        if result.returncode == 0 and phase_completed(after, phase, rsu_id):
            if session:
                session.mark_success()
            return result, after, attempts
        if phase_completed(after, phase, rsu_id):
            if session:
                session.mark_success()
            print(
                f"TURN_NONZERO_BUT_STATE_COMPLETED={phase} "
                f"EXIT_CODE={result.returncode}"
            )
            return result, after, attempts

        if is_repairable_validation_failure(result) and repair_attempts < config.max_validation_repairs:
            require_retry_safe(before, after, phase, rsu_id)
            repair_attempts += 1
            attempt_prompt = build_validation_repair_prompt(config, phase, rsu_id, result)
            print(
                f"VALIDATION_REPAIR={repair_attempts}/{config.max_validation_repairs} "
                f"PHASE={phase}"
            )
            if telemetry:
                telemetry.emit(
                    "validation_repair_scheduled",
                    phase=phase,
                    rsu_id=rsu_id,
                    repair_attempt=repair_attempts,
                )
            continue

        if result.returncode == 0:
            completion_label = (
                f"validating {rsu_id}" if phase == "rsu" and rsu_id else f"completing {phase}"
            )
            raise AttentionRequired(
                f"Codex turn ended without {completion_label}; "
                "no safe deterministic repair evidence was found"
            )

        phase_label = f"RSU {rsu_id}" if phase == "rsu" else phase
        if not is_transient_codex_failure(result):
            require_success(result, phase_label)
        if result.termination_reason in {"stage-timeout", "stall-timeout", "repeated-action"}:
            watchdog_retries += 1
            if watchdog_retries > config.max_watchdog_retries:
                require_success(result, phase_label)
        transient_retries += 1
        if transient_retries > config.max_transient_retries:
            require_success(result, phase_label)
        require_retry_safe(before, after, phase, rsu_id)
        if session:
            session.consecutive_failures += 1
            recovery_due = (
                session.mode == "module-session"
                and (
                    is_session_resume_failure(result)
                    or (
                        config.session_reset_after > 0
                        and session.consecutive_failures >= config.session_reset_after
                    )
                )
            )
            if recovery_due and config.session_recovery == "stop":
                raise AttentionRequired(
                    f"module session failed {session.consecutive_failures} consecutive times; "
                    "session recovery policy is stop"
                )
            should_reset = (
                recovery_due and config.session_recovery != "stop"
            )
            if should_reset:
                previous_id, new_mode = session.recover(config.session_recovery)
                recovery_base = (
                    build_prompt(
                        config,
                        phase,
                        rsu_id,
                        force_context_refresh=True,
                        effective_session_mode=new_mode,
                    )
                    if repair_attempts == 0
                    else attempt_prompt
                )
                attempt_prompt = session_recovery_prompt(recovery_base, phase, rsu_id, new_mode)
                print(
                    f"SESSION_RECOVERY={new_mode} PHASE={phase} "
                    f"PREVIOUS_SESSION={previous_id or 'NONE'}"
                )
                if telemetry:
                    telemetry.emit(
                        "session_recovered",
                        phase=phase,
                        rsu_id=rsu_id,
                        strategy=new_mode,
                        previous_session=previous_id,
                        recovery_count=session.recovery_count,
                    )
        retry_after = retry_after_seconds(result)
        exponential_delay = min(
            config.retry_base_delay_seconds * (2 ** (transient_retries - 1)),
            config.retry_max_delay_seconds,
        )
        delay = min(
            max(exponential_delay, retry_after or 0.0),
            config.retry_max_delay_seconds,
        )
        print(
            f"TRANSIENT_RETRY={transient_retries}/{config.max_transient_retries} "
            f"PHASE={phase_label} DELAY_SECONDS={delay:g}"
            f"{f' RETRY_AFTER={retry_after:g}' if retry_after is not None else ''}"
        )
        if telemetry:
            telemetry.emit(
                "transient_retry_scheduled",
                phase=phase,
                rsu_id=rsu_id,
                retry=transient_retries,
                delay_seconds=delay,
                retry_after_seconds=retry_after,
                reason=result.termination_reason or "provider-or-network",
            )
        if delay:
            time.sleep(delay)


def _run_pipeline_legacy(
    config: RunnerConfig,
    initialize_fn: Initializer | None = None,
    invoke_fn: Invoker | None = None,
) -> PipelineResult:
    if not config.module_dir.is_dir():
        raise RunnerError(f"module directory does not exist: {config.module_dir}")
    if not config.workdir.is_dir():
        raise RunnerError(f"Codex working directory does not exist: {config.workdir}")
    if config.session_mode not in SESSION_MODES:
        raise RunnerError(f"unsupported session mode: {config.session_mode}")
    if config.session_recovery not in SESSION_RECOVERY_MODES:
        raise RunnerError(f"unsupported session recovery mode: {config.session_recovery}")
    if config.context_refresh_interval < 0:
        raise RunnerError("context refresh interval cannot be negative")
    initializer = initialize_fn or initialize_generation
    session = CodexSession(config.session_mode)
    if invoke_fn is None:
        def invoker(
            invoke_config: RunnerConfig,
            invoke_run_dir: Path,
            turn_number: int,
            phase: str,
            prompt: str,
            rsu_id: str | None,
        ) -> CodexTurnResult:
            return invoke_codex(
                invoke_config,
                invoke_run_dir,
                turn_number,
                phase,
                prompt,
                rsu_id,
                session=session,
            )
    else:
        invoker = invoke_fn
    state_file = initializer(config).resolve()
    state_data, snapshot = load_state(state_file)
    output_dir_value = state_data.get("output_dir")
    if not isinstance(output_dir_value, str) or not output_dir_value:
        raise RunnerError("generation state does not define output_dir")
    output_dir = Path(output_dir_value).expanduser().resolve()
    log_root = config.logs_dir or (output_dir / "runner-logs")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{uuid.uuid4().hex[:8]}"
    run_dir = log_root / run_id
    rsu_turns = 0
    codex_turns = 0
    max_rsu_turns = config.max_rsu_turns
    if max_rsu_turns is None:
        max_rsu_turns = len(snapshot.rsus) - snapshot.validated_count

    with RunnerLock(output_dir):
        recovered_batches = recover_stale_running_batches(state_file, run_id)
        if recovered_batches:
            print(f"STALE_RUNNING_BATCHES_RECOVERED={','.join(recovered_batches)}")
        state_data, initial_snapshot = load_state(state_file)
        run_dir.mkdir(parents=True, exist_ok=False)
        telemetry = RunTelemetry(run_dir)
        pipeline_started_monotonic = time.monotonic()
        global _ACTIVE_PIPELINE
        _ACTIVE_PIPELINE = ActivePipelineTelemetry(
            telemetry=telemetry,
            state_file=state_file,
            run_dir=run_dir,
            started_monotonic=pipeline_started_monotonic,
        )
        coordinator = GlobalConcurrency(
            global_lock_dir(config),
            config.global_concurrency,
            config.global_wait_timeout_seconds,
            config.heartbeat_interval_seconds,
        )
        telemetry.emit(
            "pipeline_started",
            state_file=str(state_file),
            global_concurrency=config.global_concurrency,
            **telemetry_environment(config, state_data),
        )
        print(f"RUN_LOG_DIR={run_dir}")
        print(f"SESSION_MODE={config.session_mode}")
        print(f"GLOBAL_CONCURRENCY={config.global_concurrency}")
        print(f"STAGE_TIMEOUT_SECONDS={config.stage_timeout_seconds:g}")
        print(f"STALL_TIMEOUT_SECONDS={config.stall_timeout_seconds:g}")
        if config.session_mode == "module-session":
            print(f"CONTEXT_REFRESH_INTERVAL={config.context_refresh_interval}")
        while snapshot.next_rsu is not None:
            current = snapshot.next_rsu
            if _ACTIVE_PIPELINE is not None:
                _ACTIVE_PIPELINE.phase = "rsu"
                _ACTIVE_PIPELINE.rsu_id = current.rsu_id
                _ACTIVE_PIPELINE.rsu_turns = rsu_turns
            require_runnable_rsu(current)
            if rsu_turns >= max_rsu_turns:
                raise AttentionRequired(
                    f"reached max RSU turn limit ({max_rsu_turns}) before all RSUs were validated"
                )
            before = snapshot
            rsu_turns += 1
            if _ACTIVE_PIPELINE is not None:
                _ACTIVE_PIPELINE.phase = "rsu"
                _ACTIVE_PIPELINE.rsu_id = current.rsu_id
                _ACTIVE_PIPELINE.rsu_turns = rsu_turns
            force_context_refresh = session.should_refresh_context(
                config.context_refresh_interval,
                current.status,
            )
            if force_context_refresh:
                print(f"CONTEXT_REFRESH={current.rsu_id}")
            result, snapshot, attempts = invoke_phase_with_retries(
                config,
                run_dir,
                state_file,
                codex_turns + 1,
                "rsu",
                build_prompt(
                    config,
                    "rsu",
                    current.rsu_id,
                    force_context_refresh=force_context_refresh,
                    effective_session_mode=session.mode,
                    source_fingerprint_sha256=snapshot.session_source_fingerprint_sha256,
                ),
                current.rsu_id,
                before,
                invoker,
                session=session,
                coordinator=coordinator,
                telemetry=telemetry,
            )
            codex_turns += attempts
            if _ACTIVE_PIPELINE is not None:
                _ACTIVE_PIPELINE.codex_turns = codex_turns
            assert_rsu_progress(before, snapshot, current.rsu_id)
            session.validated_rsus += 1
            print(
                f"RSU_VALIDATED={current.rsu_id} "
                f"VALIDATED_COUNT={snapshot.validated_count}/{len(snapshot.rsus)}"
            )

        if snapshot.finalization_status != "validated":
            before = snapshot
            if _ACTIVE_PIPELINE is not None:
                _ACTIVE_PIPELINE.phase = "finalization"
                _ACTIVE_PIPELINE.rsu_id = None
            result, snapshot, attempts = invoke_phase_with_retries(
                config,
                run_dir,
                state_file,
                codex_turns + 1,
                "finalization",
                build_prompt(config, "finalization"),
                None,
                before,
                invoker,
                session=session,
                coordinator=coordinator,
                telemetry=telemetry,
            )
            codex_turns += attempts
            if _ACTIVE_PIPELINE is not None:
                _ACTIVE_PIPELINE.codex_turns = codex_turns
            if snapshot.finalization_status != "validated":
                raise AttentionRequired(
                    "finalization turn ended without validated finalization; "
                    f"current status is {snapshot.finalization_status}"
                )
            print("FINALIZATION_STATUS=validated")

        if snapshot.case_readiness_status != "validated":
            before = snapshot
            if _ACTIVE_PIPELINE is not None:
                _ACTIVE_PIPELINE.phase = "case-readiness"
                _ACTIVE_PIPELINE.rsu_id = None
            result, snapshot, attempts = invoke_phase_with_retries(
                config,
                run_dir,
                state_file,
                codex_turns + 1,
                "case-readiness",
                build_prompt(config, "case-readiness"),
                None,
                before,
                invoker,
                session=session,
                coordinator=coordinator,
                telemetry=telemetry,
            )
            codex_turns += attempts
            if _ACTIVE_PIPELINE is not None:
                _ACTIVE_PIPELINE.codex_turns = codex_turns
            if snapshot.case_readiness_status != "validated":
                raise AttentionRequired(
                    "case-readiness turn ended without a validated review; "
                    f"current status is {snapshot.case_readiness_status}"
                )

        readiness_result = snapshot.case_readiness_result
        if readiness_result != "ready":
            emit_pipeline_terminal(
                "pipeline_attention",
                result=readiness_result or "missing",
            )
            raise AttentionRequired(
                "case-readiness review requires follow-up; "
                f"result={readiness_result or 'missing'}"
            )
        print("CASE_READINESS_RESULT=ready")
        print("PIPELINE_STATUS=complete")
        emit_pipeline_terminal(
            "pipeline_completed",
            readiness_result=readiness_result,
        )
        return PipelineResult(state_file, run_dir, codex_turns, rsu_turns, readiness_result)


def _run_pipeline(
    config: RunnerConfig,
    initialize_fn: Initializer | None = None,
    invoke_fn: Invoker | None = None,
    stage_fn: StageRunner | None = None,
) -> PipelineResult:
    """Run the plan/foundation/fork batch scheduler with parent-owned state commits."""

    if not config.module_dir.is_dir():
        raise RunnerError(f"module directory does not exist: {config.module_dir}")
    if not config.workdir.is_dir():
        raise RunnerError(f"Codex working directory does not exist: {config.workdir}")
    if config.session_mode not in SESSION_MODES:
        raise RunnerError(f"unsupported session mode: {config.session_mode}")
    if config.module_concurrency <= 0:
        raise RunnerError("module concurrency must be positive")
    selected = config
    if invoke_fn is None:
        selected = replace(
            config,
            codex_bin=select_codex_binary(
                config.codex_bin,
                require_fork=config.session_mode == "module-session",
            ),
        )
    initializer = initialize_fn or initialize_generation
    stage_runner = stage_fn
    state_file = initializer(selected).resolve()
    state_data, initial_snapshot = load_state(state_file)
    output_value = state_data.get("output_dir")
    if not isinstance(output_value, str) or not output_value:
        raise RunnerError("generation state does not define output_dir")
    output_dir = Path(output_value).expanduser().resolve()
    log_root = config.logs_dir or (output_dir / "runner-logs")
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{uuid.uuid4().hex[:8]}"
    run_dir = log_root / run_id

    def call_stage(script_name: str, positional: tuple[str, ...] = (), accepted: tuple[int, ...] = (0,)) -> str:
        if stage_runner is None:
            return run_stage_script(selected, script_name, positional, accepted_returncodes=accepted)
        return stage_runner(selected, script_name, positional)

    with RunnerLock(output_dir):
        recovered_batches = recover_stale_running_batches(state_file, run_id)
        state_data, initial_snapshot = load_state(state_file)
        run_dir.mkdir(parents=True, exist_ok=False)
        telemetry = RunTelemetry(run_dir)
        pipeline_started_monotonic = time.monotonic()
        global _ACTIVE_PIPELINE
        _ACTIVE_PIPELINE = ActivePipelineTelemetry(
            telemetry=telemetry,
            state_file=state_file,
            run_dir=run_dir,
            started_monotonic=pipeline_started_monotonic,
        )
        coordinator = GlobalConcurrency(
            global_lock_dir(selected),
            selected.global_concurrency,
            selected.global_wait_timeout_seconds,
            selected.heartbeat_interval_seconds,
        )
        foundation = FoundationSession(selected.session_mode)
        effective_module_concurrency = (
            selected.module_concurrency if selected.sandbox == "workspace-write" else 1
        )
        turn_lock = threading.Lock()
        next_turn = 0
        codex_turns = 0
        batch_turns = 0
        rsu_turns = 0

        telemetry.emit(
            "pipeline_started",
            state_file=str(state_file),
            architecture="module-plan-foundation-independent-fork-batches",
            module_concurrency=effective_module_concurrency,
            requested_module_concurrency=selected.module_concurrency,
            global_concurrency=selected.global_concurrency,
            historical_log_input=False,
            automatic_compaction_primary=False,
            **telemetry_environment(selected, state_data),
        )
        if recovered_batches:
            telemetry.emit(
                "stale_running_batches_recovered",
                batch_ids=recovered_batches,
                count=len(recovered_batches),
            )
        print(f"RUN_LOG_DIR={run_dir}")
        print("PIPELINE_ARCHITECTURE=module-plan-foundation-independent-fork-batches")
        print("HISTORICAL_LOG_INPUT=disabled")
        print("AUTOMATIC_COMPACTION_POLICY=not-primary-independent-stage-forks")
        print(f"SESSION_MODE={selected.session_mode}")
        print(f"MODULE_CONCURRENCY={effective_module_concurrency}")
        if effective_module_concurrency != selected.module_concurrency:
            print(
                "MODULE_CONCURRENCY_CLAMPED="
                f"requested:{selected.module_concurrency} effective:1 "
                f"reason:sandbox-{selected.sandbox}-cannot-enforce-private-worker-writes"
            )
        print(f"GLOBAL_CONCURRENCY={selected.global_concurrency}")
        print(
            "DEPRECATED_CONTEXT_REFRESH_INTERVAL="
            f"{selected.context_refresh_interval} IGNORED=true"
        )

        def allocate_turn() -> int:
            nonlocal next_turn, codex_turns
            with turn_lock:
                next_turn += 1
                codex_turns += 1
                return next_turn

        def invoke_compatible(
            phase: str,
            prompt: str,
            label: str | None,
            parent_thread: str | None,
            *,
            execution_workdir: Path | None = None,
            authorized_write_dirs: tuple[Path, ...] | None = None,
        ) -> CodexTurnResult:
            turn_number = allocate_turn()
            with coordinator.slot(phase, turn_number, telemetry):
                if invoke_fn is None:
                    result = invoke_codex(
                        selected,
                        run_dir,
                        turn_number,
                        phase,
                        prompt,
                        label,
                        fork_from=parent_thread,
                        session=CodexSession("isolated"),
                        telemetry=telemetry,
                        execution_workdir=execution_workdir,
                        authorized_write_dirs=authorized_write_dirs,
                    )
                else:
                    try:
                        signature = inspect.signature(invoke_fn)
                        signature.bind(selected, run_dir, turn_number, phase, prompt, label, parent_thread)
                    except TypeError:
                        result = invoke_fn(selected, run_dir, turn_number, phase, prompt, label)
                    else:
                        result = invoke_fn(
                            selected, run_dir, turn_number, phase, prompt, label, parent_thread
                        )
            telemetry.emit(
                "stage_turn_metrics",
                phase=phase,
                label=label,
                turn=turn_number,
                duration_seconds=round(result.duration_seconds, 3),
                tool_calls=result.tool_calls,
                validation_attempts=result.validation_attempts,
                validation_failures=result.validation_failures,
                usage=result.usage,
                thread_id=result.thread_id,
                foundation_thread_id=parent_thread,
            )
            foundation.record_usage(result.usage)
            return result

        def invoke_with_retries(
            phase: str,
            prompt: str,
            label: str | None,
            parent_thread: str | None,
            *,
            execution_workdir: Path | None = None,
            authorized_write_dirs: tuple[Path, ...] | None = None,
        ) -> CodexTurnResult:
            retries = 0
            watchdog_retries = 0
            while True:
                result = invoke_compatible(
                    phase,
                    prompt,
                    label,
                    parent_thread,
                    execution_workdir=execution_workdir,
                    authorized_write_dirs=authorized_write_dirs,
                )
                if result.returncode == 0:
                    if selected.session_mode == "module-session" and phase != "foundation":
                        foundation.require_child(result.thread_id, label or phase)
                    return result
                phase_label = f"{phase} {label}" if label else phase
                if not is_transient_codex_failure(result):
                    require_success(result, phase_label)
                if result.termination_reason in {"stage-timeout", "stall-timeout", "repeated-action"}:
                    watchdog_retries += 1
                    if watchdog_retries > selected.max_watchdog_retries:
                        require_success(result, phase_label)
                retries += 1
                if retries > selected.max_transient_retries:
                    require_success(result, phase_label)
                retry_after = retry_after_seconds(result)
                delay = min(
                    max(
                        selected.retry_base_delay_seconds * (2 ** (retries - 1)),
                        retry_after or 0.0,
                    ),
                    selected.retry_max_delay_seconds,
                )
                telemetry.emit(
                    "transient_retry_scheduled",
                    phase=phase,
                    label=label,
                    retry=retries,
                    delay_seconds=delay,
                )
                print(
                    f"TRANSIENT_RETRY={retries}/{selected.max_transient_retries} "
                    f"PHASE={phase_label} DELAY_SECONDS={delay:g}"
                )
                if delay:
                    time.sleep(delay)

        def authorized_snapshot(allowed: tuple[Path, ...]) -> dict[str, str]:
            return protected_workspace_snapshot(
                selected.module_dir,
                allowed_paths=allowed,
                ignored_roots=(run_dir, output_dir / "runner-logs", output_dir / "history"),
            )

        def invoke_guarded_stage(
            phase: str,
            label: str | None,
            allowed: tuple[Path, ...],
            *,
            batch_id: str | None = None,
            repair_error: str | None = None,
        ) -> CodexTurnResult:
            state_before = state_file.read_bytes()
            protected_before = authorized_snapshot(allowed)
            prompt = build_stage_prompt_v2(
                selected,
                output_dir,
                phase,
                batch_id=batch_id,
                repair_error=repair_error,
            )
            result = invoke_with_retries(
                phase,
                prompt,
                label,
                foundation.thread_id if selected.session_mode == "module-session" and phase != "foundation" else None,
            )
            if restore_parent_state_if_modified(state_file, state_before, label or phase):
                telemetry.emit(
                    "unauthorized_state_write_rolled_back",
                    phase=phase,
                    label=label,
                )
                print(f"STATE_WRITE_ROLLED_BACK={label or phase}")
            protected_after = authorized_snapshot(allowed)
            require_protected_snapshot_unchanged(protected_before, protected_after, label or phase)
            return result

        def record_foundation(result: CodexTurnResult) -> None:
            state, _ = load_state(state_file)
            source_fingerprint = state.get("session_source_fingerprint_sha256")
            state["foundation"] = {
                **state.get("foundation", {}),
                "status": "validated",
                "thread_id": result.thread_id,
                "source_fingerprint_sha256": source_fingerprint,
                "created_at": utc_now(),
            }
            state["updated_at"] = utc_now()
            _atomic_write_state(state_file, state)

        def ensure_foundation() -> None:
            if selected.session_mode != "module-session":
                return
            if foundation.thread_id is not None:
                return
            current_state, _ = load_state(state_file)
            reusable_thread, reuse_reason = reusable_foundation_thread(
                current_state, output_dir
            )
            if reusable_thread is not None:
                foundation.restore(reusable_thread)
                telemetry.emit(
                    "foundation_session_reused",
                    thread_id=reusable_thread,
                    reason=reuse_reason,
                )
                return
            telemetry.emit(
                "foundation_session_new_required",
                reason=reuse_reason,
            )
            result = invoke_guarded_stage("foundation", None, ())
            foundation.register(result.thread_id)
            record_foundation(result)

        def run_serial_ai_and_validate(
            phase: str,
            label: str,
            allowed: tuple[Path, ...],
            validator_script: str,
            validator_args: tuple[str, ...] = (),
        ) -> str:
            repair_error: str | None = None
            for repair in range(selected.max_validation_repairs + 1):
                invoke_guarded_stage(
                    phase,
                    label,
                    allowed,
                    batch_id=label if phase == "batch" else None,
                    repair_error=repair_error,
                )
                try:
                    return call_stage(validator_script, validator_args)
                except RunnerError as exc:
                    if repair >= selected.max_validation_repairs:
                        raise
                    repair_error = str(exc)
                    telemetry.emit(
                        "validation_repair_scheduled",
                        phase=phase,
                        label=label,
                        repair_attempt=repair + 1,
                        error=repair_error[-3000:],
                    )
                    print(
                        f"VALIDATION_REPAIR={repair + 1}/{selected.max_validation_repairs} "
                        f"PHASE={label}"
                    )
            raise RunnerError(f"unreachable validation loop for {label}")

        # A previously complete v1-v3 module remains complete after migration;
        # do not force a planning turn merely to rewrite already delivered output.
        if (
            initial_snapshot.all_rsus_validated
            and initial_snapshot.finalization_status == "validated"
            and initial_snapshot.case_readiness_status == "validated"
            and initial_snapshot.case_readiness_result == "ready"
        ):
            print("PIPELINE_STATUS=complete-existing")
            emit_pipeline_terminal("pipeline_completed", readiness_result="ready", migrated_complete=True)
            return PipelineResult(state_file, run_dir, 0, 0, "ready", 0)

        call_stage("prepare_generation_plan.py")
        state_data, snapshot = load_state(state_file)
        blocked = [item for item in snapshot.rsus if item.status == "blocked"]
        if blocked:
            details = "; ".join(
                f"{item.rsu_id}: {', '.join(item.blockers)}" for item in blocked
            )
            raise AttentionRequired(details)
        if snapshot.planning_status != "validated":
            ensure_foundation()
            run_serial_ai_and_validate(
                "planning",
                "module-planning",
                (output_dir / "generation-plan.json",),
                "validate_generation_plan.py",
            )
            state_data, snapshot = load_state(state_file)

        max_batch_turns = selected.max_rsu_turns
        replan_cycles = 0
        while snapshot.pending_batches:
            if any(item.status == "replan-required" for item in snapshot.pending_batches):
                replan_cycles += 1
                if replan_cycles > len(snapshot.rsus):
                    raise AttentionRequired("replanning did not converge")
                call_stage("replan_generation.py")
                call_stage("validate_generation_plan.py")
                state_data, snapshot = load_state(state_file)
                telemetry.emit("generation_replanned", cycle=replan_cycles)
                continue
            runnable = [item for item in snapshot.pending_batches if item.runnable]
            if not runnable:
                details = ", ".join(f"{item.batch_id}:{item.status}" for item in snapshot.pending_batches)
                raise AttentionRequired(f"no runnable batch remains: {details}")
            remaining = runnable
            if max_batch_turns is not None:
                allowance = max_batch_turns - batch_turns
                if allowance <= 0:
                    raise AttentionRequired(f"reached max batch turn limit ({max_batch_turns})")
                remaining = remaining[:allowance]
            wave = remaining[:effective_module_concurrency]
            for batch in wave:
                call_stage("prepare_next_batch.py", ("--batch-id", batch.batch_id))
            state_data, prepared_snapshot = load_state(state_file)
            prepared_by_id = {item.batch_id: item for item in prepared_snapshot.batches}
            for batch in wave:
                if prepared_by_id[batch.batch_id].status not in {"prepared", "validated"}:
                    raise RunnerError(f"prepare_next_batch.py did not prepare {batch.batch_id}")

            replan_requested = False
            raw_batches = {item["batch_id"]: item for item in state_data.get("batches", [])}
            for batch in wave:
                prepared = prepared_by_id[batch.batch_id]
                if prepared.status == "validated":
                    continue
                raw_batch = raw_batches[batch.batch_id]
                result_value = raw_batch.get("result_file")
                if not isinstance(result_value, str) or not result_value:
                    raise RunnerError(f"{batch.batch_id} has no private result file")
                result_file = output_dir / result_value
                inspection = inspect_batch_result(result_file)
                if inspection == "invalid":
                    quarantined = quarantine_invalid_batch_result(
                        output_dir, batch.batch_id, result_file
                    )
                    print(
                        f"INVALID_BATCH_RESULT_QUARANTINED={batch.batch_id}:{quarantined}"
                    )
                    call_stage("prepare_next_batch.py", ("--batch-id", batch.batch_id))
                    continue
                if inspection != "recoverable":
                    continue
                try:
                    recovered_output = call_stage(
                        "validate_batch_candidates.py",
                        (batch.batch_id,),
                        accepted=(0, 2, 3),
                    )
                except RunnerError:
                    quarantined = quarantine_invalid_batch_result(
                        output_dir, batch.batch_id, result_file
                    )
                    print(
                        f"INVALID_BATCH_RESULT_QUARANTINED={batch.batch_id}:{quarantined}"
                    )
                    call_stage("prepare_next_batch.py", ("--batch-id", batch.batch_id))
                    continue
                if "STATUS=replan-required" in recovered_output:
                    replan_requested = True
                elif "STATUS=partial" in recovered_output:
                    call_stage("prepare_next_batch.py", ("--batch-id", batch.batch_id))
                print(f"BATCH_RESULT_RECOVERED={batch.batch_id}")

            state_data, prepared_snapshot = load_state(state_file)
            if replan_requested:
                snapshot = prepared_snapshot
                continue
            prepared_by_id = {item.batch_id: item for item in prepared_snapshot.batches}
            active_wave = [
                prepared_by_id[batch.batch_id]
                for batch in wave
                if prepared_by_id[batch.batch_id].status == "prepared"
            ]
            if not active_wave:
                snapshot = prepared_snapshot
                continue
            ensure_foundation()
            mark_batches_running(
                state_file,
                tuple(batch.batch_id for batch in active_wave),
                run_id,
            )
            allowed_union: list[Path] = []
            for batch in active_wave:
                allowed_union.append(output_dir / "batches" / batch.batch_id)
                allowed_union.append(output_dir / "batch-results" / batch.batch_id)
            state_before_wave = state_file.read_bytes()
            protected_before_wave = authorized_snapshot(tuple(allowed_union))
            results: dict[str, CodexTurnResult] = {}
            with ThreadPoolExecutor(max_workers=min(effective_module_concurrency, len(active_wave) or 1)) as executor:
                futures: dict[Future[CodexTurnResult], BatchState] = {}
                for batch in active_wave:
                    prompt = build_stage_prompt_v2(
                        selected, output_dir, "batch", batch_id=batch.batch_id
                    )
                    future = executor.submit(
                        invoke_with_retries,
                        "batch",
                        prompt,
                        batch.batch_id,
                        foundation.thread_id if selected.session_mode == "module-session" else None,
                        execution_workdir=output_dir / "batches" / batch.batch_id,
                        authorized_write_dirs=(
                            output_dir / "batches" / batch.batch_id,
                            output_dir / "batch-results" / batch.batch_id,
                        ),
                    )
                    futures[future] = batch
                for future in as_completed(futures):
                    batch = futures[future]
                    result = future.result()
                    if selected.session_mode == "module-session":
                        foundation.require_child(result.thread_id, batch.batch_id)
                    results[batch.batch_id] = result
                    print(f"BATCH_WORKER_COMPLETED={batch.batch_id}")
            if state_file.read_bytes() != state_before_wave:
                raise RunnerError("a batch Worker modified generation-state.json")
            require_protected_snapshot_unchanged(
                protected_before_wave,
                authorized_snapshot(tuple(allowed_union)),
                "parallel batch wave",
            )

            for batch in sorted(active_wave, key=lambda item: item.batch_id):
                validator_error: str | None = None
                for repair in range(selected.max_validation_repairs + 1):
                    try:
                        output = call_stage(
                            "validate_batch_candidates.py",
                            (batch.batch_id,),
                            accepted=(0, 2, 3),
                        )
                        if "STATUS=replan-required" in output:
                            replan_requested = True
                        break
                    except RunnerError as exc:
                        if repair >= selected.max_validation_repairs:
                            raise
                        validator_error = str(exc)
                        invoke_guarded_stage(
                            "batch",
                            batch.batch_id,
                            (
                                output_dir / "batches" / batch.batch_id,
                                output_dir / "batch-results" / batch.batch_id,
                            ),
                            batch_id=batch.batch_id,
                            repair_error=validator_error,
                        )
                batch_turns += 1
                rsu_turns += len(batch.active_ids)
                print(
                    f"BATCH_COMMITTED={batch.batch_id} RSU_COUNT={len(batch.active_ids)}"
                )
            state_data, snapshot = load_state(state_file)
            if replan_requested:
                continue

        if not snapshot.all_rsus_validated:
            raise AttentionRequired("all planned batches completed but one or more RSUs are not validated")

        if snapshot.finalization_status != "validated":
            call_stage("prepare_finalization.py")
            ensure_foundation()
            run_serial_ai_and_validate(
                "finalization",
                "module-finalization",
                (output_dir / "module-test-points.md", output_dir / "coverage-matrix.md"),
                "validate_module_test_points.py",
            )
            state_data, snapshot = load_state(state_file)
        if snapshot.finalization_status != "validated":
            raise AttentionRequired("finalization did not reach validated state")
        print("FINALIZATION_STATUS=validated")

        if snapshot.case_readiness_status != "validated":
            call_stage("prepare_case_readiness.py")
            ensure_foundation()
            run_serial_ai_and_validate(
                "case-readiness",
                "case-readiness",
                (output_dir / "test-case-readiness.md",),
                "validate_case_readiness.py",
            )
            state_data, snapshot = load_state(state_file)
        if snapshot.case_readiness_status != "validated":
            raise AttentionRequired("case-readiness did not reach validated state")
        if snapshot.case_readiness_result != "ready":
            emit_pipeline_terminal("pipeline_attention", result=snapshot.case_readiness_result or "missing")
            raise AttentionRequired(
                f"case-readiness review requires follow-up; result={snapshot.case_readiness_result or 'missing'}"
            )
        print("CASE_READINESS_RESULT=ready")
        print("PIPELINE_STATUS=complete")
        telemetry.emit(
            "pipeline_usage_summary",
            cumulative_usage=foundation.cumulative_usage,
            codex_turns=codex_turns,
            batch_turns=batch_turns,
            rsu_turns=rsu_turns,
            replan_cycles=replan_cycles,
        )
        emit_pipeline_terminal("pipeline_completed", readiness_result="ready")
        return PipelineResult(
            state_file, run_dir, codex_turns, rsu_turns, "ready", batch_turns
        )


def run_pipeline(
    config: RunnerConfig,
    initialize_fn: Initializer | None = None,
    invoke_fn: Invoker | None = None,
    stage_fn: StageRunner | None = None,
) -> PipelineResult:
    """Run one module and persist a terminal telemetry event when possible."""

    global _ACTIVE_PIPELINE
    _ACTIVE_PIPELINE = None
    try:
        # Explicit isolated mode remains the manual one-RSU-at-a-time path,
        # regardless of the selected default architecture.
        if config.session_mode == "isolated":
            if config.pipeline_architecture not in {"module-baseline", "foundation-fork"}:
                raise RunnerError("unsupported pipeline architecture for isolated mode")
            return _run_pipeline_legacy(config, initialize_fn, invoke_fn)
        if config.pipeline_architecture == "module-baseline":
            from adaptive_runner import run_adaptive
            initializer = initialize_fn or initialize_generation
            return run_adaptive(config, initializer, invoke_fn)
        if config.pipeline_architecture != "foundation-fork":
            raise RunnerError(
                "unsupported pipeline architecture; use module-baseline or foundation-fork"
            )
        return _run_pipeline(config, initialize_fn, invoke_fn, stage_fn)
    except AttentionRequired as exc:
        if _ACTIVE_PIPELINE is None:
            emit_startup_failure_telemetry(config, exc)
        else:
            emit_pipeline_terminal(
                "pipeline_attention",
                error_type=type(exc).__name__,
                error=str(exc),
            )
        raise
    except RunnerError as exc:
        if _ACTIVE_PIPELINE is None:
            emit_startup_failure_telemetry(config, exc)
        else:
            emit_pipeline_terminal(
                "pipeline_failed",
                error_type=type(exc).__name__,
                error=str(exc),
            )
        raise
    except KeyboardInterrupt as exc:
        if _ACTIVE_PIPELINE is None:
            emit_startup_failure_telemetry(config, exc)
        else:
            emit_pipeline_terminal(
                "pipeline_interrupted",
                error_type=type(exc).__name__,
                error="runner interrupted by user",
            )
        raise
    except Exception as exc:
        # Keep unexpected implementation/IO errors observable in the same
        # machine-readable stream as explicit RunnerError failures.  Re-raise
        # so callers embedding the runner can still handle the original type.
        if _ACTIVE_PIPELINE is None:
            emit_startup_failure_telemetry(config, exc)
        else:
            emit_pipeline_terminal(
                "pipeline_failed",
                error_type=type(exc).__name__,
                error=str(exc),
                unexpected=True,
            )
        raise
    finally:
        _ACTIVE_PIPELINE = None


def main(argv: list[str] | None = None) -> int:
    configure_process_stdio()
    try:
        config = parse_args(argv)
        run_pipeline(config)
        return EXIT_OK
    except AttentionRequired as exc:
        print(f"ATTENTION_REQUIRED: {exc}", file=sys.stderr)
        return EXIT_ATTENTION
    except RunnerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except Exception as exc:
        print(f"ERROR: unexpected runner failure: {exc}", file=sys.stderr)
        return EXIT_ERROR
    except KeyboardInterrupt:
        print("INTERRUPTED: runner stopped by user", file=sys.stderr)
        return EXIT_INTERRUPTED


if __name__ == "__main__":
    raise SystemExit(main())
