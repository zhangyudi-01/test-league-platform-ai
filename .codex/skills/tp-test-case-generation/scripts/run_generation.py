#!/usr/bin/env python3
"""Run module testcase generation through planning, SQL, batches and finalization."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from contextlib import AbstractContextManager
from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable


SKILL_DIR = Path(__file__).resolve().parents[1]
INIT_SCRIPT = SKILL_DIR / "scripts" / "init_generation.py"
SKILL_FILE = SKILL_DIR / "SKILL.md"
STATE_SCHEMA_VERSION = "tp-test-case-generation/v3"
SESSION_MODES = {"module-session", "isolated"}
TP_STATUSES = {"pending", "prepared", "validated"}
STAGE_STATUSES = {"pending", "prepared", "validated"}
BATCH_MODES = {"simple", "query-display", "complex"}
FINALIZATION_STATUSES = {"not-ready", "prepared", "validated"}

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_ATTENTION = 2
EXIT_INTERRUPTED = 130
MAX_RETRY_DELAY_SECONDS = 60.0
DEFAULT_REASONING_EFFORT = "medium"
REASONING_EFFORTS = ("none", "minimal", "low", "medium", "high", "xhigh", "max", "ultra")

TRANSIENT_CODEX_FAILURE_RE = re.compile(
    r"(?:unexpected\s+status\s+(?:408|425|429|500|502|503|504|529)\b|"
    r"\b(?:502\s+bad\s+gateway|503\s+service\s+unavailable|504\s+gateway\s+timeout)\b|"
    r"service\s+unavailable|bad\s+gateway|gateway\s+timeout|too\s+many\s+requests|"
    r"rate\s+limit(?:ed|ing)?|stream\s+disconnected|connection\s+(?:reset|refused|closed|aborted)|"
    r"error\s+sending\s+request|failed\s+to\s+connect|temporar(?:y|ily)\s+unavailable|"
    r"request\s+timed\s+out|local\s+proxy\s+failed|"
    r"provider[^\r\n]{0,120}(?:unavailable|circuit\s+open))",
    re.IGNORECASE,
)
NONTRANSIENT_PROVIDER_FAILURE_RE = re.compile(
    r"(?:用户额度不足|余额不足|insufficient[_\s-]+quota|billing[_\s-]+hard[_\s-]+limit|"
    r"billing_error|insufficient[_\s-]+balance|"
    r"credit\s+balance[^\r\n]{0,80}(?:too\s+low|insufficient)|"
    r"(?:account\s+)?concurrency\s+window\s+(?:is\s+)?full|"
    r"model[^\r\n]{0,160}(?:requires?[^\r\n]{0,80}newer\s+(?:version\s+of\s+)?codex|"
    r"(?:not\s+supported|unsupported)[^\r\n]{0,80}codex)|"
    r"(?:upgrade|update)[^\r\n]{0,80}codex[^\r\n]{0,80}(?:model|version))",
    re.IGNORECASE,
)
UNAVAILABLE_FOUNDATION_RE = re.compile(
    r"(?:no\s+(?:rollout|session|thread)\s+found(?:\s+for)?|"
    r"(?:foundation|parent|source)\s+(?:session|thread)[^\r\n]{0,80}"
    r"(?:not\s+found|does\s+not\s+exist)|"
    r"(?:session|thread)\s+[^\s:]+\s+(?:not\s+found|does\s+not\s+exist))",
    re.IGNORECASE,
)
REFRESH_REQUIRED_RE = re.compile(
    r"rerun\s+init_generation\.py\s+--refresh|重新运行\s*init_generation\.py\s+--refresh",
    re.IGNORECASE,
)


class RunnerError(RuntimeError):
    pass


class AttentionRequired(RuntimeError):
    pass


@dataclass(frozen=True)
class RunnerConfig:
    module_dir: Path
    manifest: Path | None
    preanalysis_dir: Path | None
    case_output_dir: Path | None
    workdir: Path
    logs_dir: Path | None
    codex_bin: str
    model: str | None
    profile: str | None
    sandbox: str
    max_batch_turns: int | None
    reasoning_effort: str = DEFAULT_REASONING_EFFORT
    max_transient_retries: int = 3
    retry_base_delay_seconds: float = 5.0
    session_mode: str = "module-session"
    db_config: Path | None = None

    @property
    def max_tp_turns(self) -> int | None:
        return self.max_batch_turns


@dataclass(frozen=True)
class BatchState:
    batch_id: str
    mode: str
    tp_ids: tuple[str, ...]
    status: str


@dataclass(frozen=True)
class StateSnapshot:
    module_dir: Path
    case_output_dir: Path
    source_fingerprint: str
    readiness_result: str
    planning_status: str
    sql_planning_status: str
    batches: tuple[BatchState, ...]
    tp_statuses: tuple[tuple[str, str], ...]
    finalization_status: str

    @property
    def next_batch(self) -> BatchState | None:
        return next((item for item in self.batches if item.status != "validated"), None)


@dataclass(frozen=True)
class InitializationResult:
    state_file: Path
    case_output_dir: Path
    ready: bool
    output: str = ""


@dataclass(frozen=True)
class CodexTurnResult:
    returncode: int
    jsonl_log: Path
    stderr_log: Path
    last_message: Path
    elapsed_seconds: float = 0.0
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
    batch_turns: int

    @property
    def tp_turns(self) -> int:
        return self.batch_turns


@dataclass
class FoundationSession:
    mode: str
    thread_id: str | None = None
    cumulative_usage: dict[str, int] = field(default_factory=dict)

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


Initializer = Callable[[RunnerConfig], InitializationResult]
Invoker = Callable[[RunnerConfig, Path, int, str, str, str | None, str | None], CodexTurnResult]
StageRunner = Callable[[RunnerConfig, str, tuple[str, ...]], str]


def configure_process_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
            except (OSError, ValueError):
                pass


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
        description="Plan once, generate query SQL once, batch simple TPs, isolate complex TPs, then finalize."
    )
    parser.add_argument("module_dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--preanalysis-dir", type=Path)
    parser.add_argument("--case-output-dir", type=Path)
    parser.add_argument("--db-config", type=Path)
    parser.add_argument("--workdir", type=Path, default=default_workdir())
    parser.add_argument("--logs-dir", type=Path)
    parser.add_argument("--codex-bin", default="codex")
    parser.add_argument("--model")
    parser.add_argument("--profile")
    parser.add_argument("--reasoning-effort", choices=REASONING_EFFORTS, default=DEFAULT_REASONING_EFFORT)
    parser.add_argument("--session-mode", choices=tuple(sorted(SESSION_MODES)), default="module-session")
    parser.add_argument(
        "--session-rotation-interval", "--context-refresh-interval",
        dest="ignored_rotation_interval", type=positive_int,
        help="Deprecated compatibility option; accepted and ignored.",
    )
    parser.add_argument(
        "--sandbox", choices=("read-only", "workspace-write", "danger-full-access"),
        default="workspace-write",
    )
    parser.add_argument(
        "--max-batch-turns", "--max-tp-turns", dest="max_batch_turns", type=positive_int,
        help="Maximum testcase batches in this run; old name is a compatibility alias.",
    )
    parser.add_argument("--max-transient-retries", type=nonnegative_int, default=3)
    parser.add_argument("--retry-base-delay-seconds", type=nonnegative_float, default=5.0)
    args = parser.parse_args(argv)
    return RunnerConfig(
        module_dir=args.module_dir.expanduser().resolve(),
        manifest=args.manifest.expanduser().resolve() if args.manifest else None,
        preanalysis_dir=args.preanalysis_dir.expanduser().resolve() if args.preanalysis_dir else None,
        case_output_dir=args.case_output_dir.expanduser().resolve() if args.case_output_dir else None,
        db_config=args.db_config.expanduser().resolve() if args.db_config else None,
        workdir=args.workdir.expanduser().resolve(),
        logs_dir=args.logs_dir.expanduser().resolve() if args.logs_dir else None,
        codex_bin=args.codex_bin,
        model=args.model,
        profile=args.profile,
        sandbox=args.sandbox,
        max_batch_turns=args.max_batch_turns,
        reasoning_effort=args.reasoning_effort,
        max_transient_retries=args.max_transient_retries,
        retry_base_delay_seconds=args.retry_base_delay_seconds,
        session_mode=args.session_mode,
    )


def resolved_case_output_dir(config: RunnerConfig) -> Path:
    return config.case_output_dir or (config.module_dir / "test-cases").resolve()


def layout_cli_args(config: RunnerConfig) -> list[str]:
    result = [str(config.module_dir)]
    if config.manifest is not None:
        result.extend(["--manifest", str(config.manifest)])
    if config.preanalysis_dir is not None:
        result.extend(["--preanalysis-dir", str(config.preanalysis_dir)])
    if config.case_output_dir is not None:
        result.extend(["--case-output-dir", str(config.case_output_dir)])
    return result


def phase_command(config: RunnerConfig, script_name: str, positional: tuple[str, ...] = ()) -> str:
    parts = [
        "python", "-X", "utf8", "-B", f'"{SKILL_DIR / "scripts" / script_name}"',
        f'"{config.module_dir}"', *(f'"{item}"' for item in positional),
    ]
    if config.manifest is not None:
        parts.extend(["--manifest", f'"{config.manifest}"'])
    if config.preanalysis_dir is not None:
        parts.extend(["--preanalysis-dir", f'"{config.preanalysis_dir}"'])
    if config.case_output_dir is not None:
        parts.extend(["--case-output-dir", f'"{config.case_output_dir}"'])
    if script_name in {"validate_planned_sql.py", "validate_batch_test_cases.py", "validate_module_test_cases.py"} and config.db_config is not None:
        parts.extend(["--db-config", f'"{config.db_config}"'])
    return " ".join(parts)


def _child_env() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    env["PYTHONUTF8"] = "1"
    return env


def _combined_output(result: subprocess.CompletedProcess[str]) -> str:
    return "\n".join(part.strip() for part in (result.stdout, result.stderr) if part and part.strip())


def _reported_value(output: str, key: str) -> str:
    match = re.search(rf"(?m)^{re.escape(key)}=(.+)$", output)
    return match.group(1).strip() if match else ""


def initialize_generation(config: RunnerConfig) -> InitializationResult:
    result = subprocess.run(
        [sys.executable, "-X", "utf8", "-B", str(INIT_SCRIPT), *layout_cli_args(config)],
        capture_output=True, text=True, encoding="utf-8", errors="replace", env=_child_env(),
    )
    combined = _combined_output(result)
    if combined:
        print(combined)
    if result.returncode != 0:
        if REFRESH_REQUIRED_RE.search(combined):
            raise AttentionRequired(
                "testcase inputs or state contract changed; review impact and run init_generation.py --refresh"
            )
        raise RunnerError("testcase generation initialization failed:\n" + (combined or "no output"))
    case_dir = resolved_case_output_dir(config)
    return InitializationResult(
        case_dir / "generation-state.json", case_dir, _reported_value(combined, "STATUS") == "initialized", combined
    )


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise RunnerError(f"generation state disappeared: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RunnerError(f"invalid generation state JSON: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise RunnerError("generation state root must be a JSON object")
    return value


def load_state(state_file: Path) -> tuple[dict[str, Any], StateSnapshot]:
    data = _load_json(state_file)
    schema = data.get("schema_version")
    if schema != STATE_SCHEMA_VERSION:
        raise RunnerError(
            f"unsupported generation state schema: {schema}; run init_generation.py --refresh to enter {STATE_SCHEMA_VERSION}"
        )
    if not all(key in data for key in ("planning", "sql_planning", "batches")):
        raise RunnerError(
            "legacy generation state has no module planning/batch scheduler; "
            "run init_generation.py --refresh before using the refactored runner"
        )
    module_value, case_value = data.get("module_dir"), data.get("case_output_dir")
    if not isinstance(module_value, str) or not isinstance(case_value, str):
        raise RunnerError("generation state must define module_dir and case_output_dir")
    module_dir, case_dir = Path(module_value).expanduser().resolve(), Path(case_value).expanduser().resolve()
    if case_dir != state_file.parent.resolve():
        raise RunnerError(f"generation state belongs to {case_dir}, not {state_file.parent.resolve()}")
    source_hashes = data.get("source_hashes")
    if not isinstance(source_hashes, dict):
        raise RunnerError("generation state source_hashes must be an object")
    source_fingerprint = json.dumps(source_hashes, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    readiness = data.get("readiness_result")
    if readiness not in {"ready", "blocked-input", "upstream-gap"}:
        raise RunnerError(f"unsupported readiness result: {readiness}")

    raw_tps = data.get("tps")
    if not isinstance(raw_tps, list) or not raw_tps:
        raise RunnerError("generation state tps must be a non-empty list")
    tp_statuses: list[tuple[str, str]] = []
    seen_tp: set[str] = set()
    reached_unvalidated = False
    for index, item in enumerate(raw_tps, start=1):
        if not isinstance(item, dict):
            raise RunnerError(f"generation state tps[{index}] must be an object")
        tp_id, status = item.get("tp_id"), item.get("status")
        if not isinstance(tp_id, str) or re.fullmatch(r"TP-\d{3}", tp_id) is None:
            raise RunnerError(f"generation state tps[{index}] has invalid tp_id")
        if tp_id in seen_tp or item.get("order") != index or status not in TP_STATUSES:
            raise RunnerError(f"invalid or duplicate TP state at position {index}")
        if item.get("readiness_status") not in {"ready", "blocked-input", "upstream-gap"}:
            raise RunnerError(f"{tp_id} has unsupported readiness status")
        if status != "validated":
            reached_unvalidated = True
        elif reached_unvalidated:
            raise RunnerError(f"{tp_id} is validated after an earlier nonvalidated TP")
        seen_tp.add(tp_id)
        tp_statuses.append((tp_id, status))

    planning, sql_planning = data.get("planning", {}), data.get("sql_planning", {})
    if not isinstance(planning, dict) or planning.get("status", "pending") not in STAGE_STATUSES:
        raise RunnerError("generation state planning stage is invalid")
    if not isinstance(sql_planning, dict) or sql_planning.get("status", "pending") not in STAGE_STATUSES:
        raise RunnerError("generation state SQL planning stage is invalid")
    planning_status, sql_status = planning.get("status", "pending"), sql_planning.get("status", "pending")
    if sql_status != "pending" and planning_status != "validated":
        raise RunnerError("SQL planning advanced before module planning validated")

    raw_batches = data.get("batches", [])
    if not isinstance(raw_batches, list):
        raise RunnerError("generation state batches must be an array")
    batches: list[BatchState] = []
    assigned: list[str] = []
    reached_open = False
    for index, item in enumerate(raw_batches, start=1):
        if not isinstance(item, dict):
            raise RunnerError(f"generation state batches[{index}] must be an object")
        batch_id, mode, tp_ids, status = item.get("batch_id"), item.get("mode"), item.get("tp_ids"), item.get("status")
        if batch_id != f"BATCH-{index:03d}" or mode not in BATCH_MODES:
            raise RunnerError(f"invalid batch record at position {index}")
        if not isinstance(tp_ids, list) or not tp_ids or not all(isinstance(v, str) for v in tp_ids):
            raise RunnerError(f"{batch_id} tp_ids must be a non-empty string array")
        if status not in STAGE_STATUSES:
            raise RunnerError(f"{batch_id} has unsupported status: {status}")
        if status != "validated":
            reached_open = True
        elif reached_open:
            raise RunnerError(f"{batch_id} validated before an earlier batch")
        assigned.extend(tp_ids)
        batches.append(BatchState(batch_id, mode, tuple(tp_ids), status))
    if planning_status == "validated":
        if assigned != [tp_id for tp_id, _ in tp_statuses]:
            raise RunnerError("validated generation plan must assign every TP exactly once in order")
    elif raw_batches:
        raise RunnerError("batches exist before module planning validated")
    if raw_batches and sql_status != "validated" and any(batch.status != "pending" for batch in batches):
        raise RunnerError("a testcase batch advanced before SQL planning validated")
    status_by_tp = dict(tp_statuses)
    for batch in batches:
        if {status_by_tp.get(tp_id) for tp_id in batch.tp_ids} != {batch.status}:
            raise RunnerError(f"{batch.batch_id} status conflicts with its TP statuses")

    finalization = data.get("finalization", {})
    if not isinstance(finalization, dict):
        raise RunnerError("generation state finalization must be an object")
    final_status = finalization.get("status", "not-ready")
    if final_status not in FINALIZATION_STATUSES:
        raise RunnerError(f"unsupported finalization status: {final_status}")
    if final_status != "not-ready" and any(status != "validated" for _, status in tp_statuses):
        raise RunnerError("module finalization advanced before all testcase batches validated")
    return data, StateSnapshot(
        module_dir, case_dir, source_fingerprint, readiness, planning_status, sql_status,
        tuple(batches), tuple(tp_statuses), final_status,
    )


def require_state_binding(config: RunnerConfig, snapshot: StateSnapshot) -> None:
    if snapshot.module_dir != config.module_dir.resolve():
        raise RunnerError("generation state module binding changed")
    if snapshot.case_output_dir != resolved_case_output_dir(config):
        raise RunnerError("generation state testcase output binding changed")


def require_ready(data: dict[str, Any], snapshot: StateSnapshot) -> None:
    blocked = [item.get("tp_id") for item in data.get("tps", []) if item.get("readiness_status") != "ready"]
    if snapshot.readiness_result != "ready" or blocked:
        raise AttentionRequired(f"testcase readiness requires follow-up: {blocked or snapshot.readiness_result}")


class RunnerLock(AbstractContextManager["RunnerLock"]):
    def __init__(self, case_output_dir: Path) -> None:
        self.path = case_output_dir / ".generation-runner.lock"
        self._owned = False

    def __enter__(self) -> "RunnerLock":
        self.path.parent.mkdir(parents=True, exist_ok=True)
        try:
            fd = os.open(self.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as exc:
            raise AttentionRequired(f"another runner may be active: {self.path}") from exc
        try:
            os.write(fd, f"pid={os.getpid()} created_at={utc_now()}\n".encode("utf-8"))
        finally:
            os.close(fd)
        self._owned = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._owned:
            try:
                self.path.unlink()
            except FileNotFoundError:
                pass
        self._owned = False


def is_within(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def resolve_codex_binary(value: str) -> str:
    resolved = shutil.which(value)
    if resolved:
        return str(Path(resolved).resolve())
    candidate = Path(value).expanduser()
    if candidate.is_file():
        return str(candidate.resolve())
    raise RunnerError(f"Codex CLI executable was not found: {value}")


def _explicit_binary_path(value: str) -> bool:
    candidate = Path(value).expanduser()
    return candidate.is_absolute() or "/" in value or "\\" in value


def _desktop_codex_candidates() -> tuple[str, ...]:
    if os.name != "nt" or not os.environ.get("LOCALAPPDATA"):
        return ()
    root = Path(os.environ["LOCALAPPDATA"]) / "OpenAI" / "Codex" / "bin"
    if not root.is_dir():
        return ()
    paths = [path.resolve() for path in root.glob("*/codex.exe") if path.is_file()]
    paths.sort(key=lambda path: path.stat().st_mtime_ns, reverse=True)
    return tuple(str(path) for path in paths)


def codex_binary_candidates(value: str) -> tuple[str, ...]:
    if _explicit_binary_path(value):
        return (resolve_codex_binary(value),)
    values: list[str] = []
    resolved = shutil.which(value)
    if resolved:
        values.append(str(Path(resolved).resolve()))
    if value.lower() in {"codex", "codex.exe"}:
        values.extend(_desktop_codex_candidates())
    unique: list[str] = []
    seen: set[str] = set()
    for candidate in values:
        key = os.path.normcase(os.path.abspath(candidate))
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    if not unique:
        raise RunnerError(f"Codex CLI executable was not found: {value}")
    return tuple(unique)


@lru_cache(maxsize=None)
def codex_version(binary: str) -> str:
    try:
        result = subprocess.run([binary, "--version"], capture_output=True, text=True, encoding="utf-8", errors="replace")
    except OSError:
        return "unknown"
    output = _combined_output(result)
    return output.splitlines()[0].strip() if output else "unknown"


@lru_cache(maxsize=None)
def codex_supports_exec_fork(binary: str) -> bool:
    try:
        result = subprocess.run(
            [binary, "exec", "fork", "--help"], capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
    except OSError:
        return False
    return result.returncode == 0 and bool(re.search(r"(?im)^Usage:\s+\S+\s+exec\s+fork\b", _combined_output(result)))


def select_codex_binary(value: str, *, require_fork: bool) -> str:
    candidates = codex_binary_candidates(value)
    if not require_fork:
        return candidates[0]
    for candidate in candidates:
        if codex_supports_exec_fork(candidate):
            return candidate
    checked = ", ".join(f"{item} ({codex_version(item)})" for item in candidates)
    suffix = " The explicitly selected CLI will not be replaced automatically." if _explicit_binary_path(value) else " Install or select a CLI with `codex exec fork`."
    raise RunnerError(f"module-session requires `codex exec fork`; checked: {checked}.{suffix}")


def codex_command(config: RunnerConfig, last_message: Path, writable: tuple[Path, ...], fork_from: str | None = None) -> list[str]:
    command = [
        resolve_codex_binary(config.codex_bin), "exec", "--json", "--color", "never",
        "--skip-git-repo-check", "--cd", str(config.workdir), "--output-last-message", str(last_message),
    ]
    if config.sandbox == "workspace-write":
        command.append("--approve-for-me")
    else:
        command.extend(["--sandbox", config.sandbox])
    if config.profile:
        command.extend(["--profile", config.profile])
    if config.model:
        command.extend(["--model", config.model])
    command.extend(["-c", f'model_reasoning_effort="{config.reasoning_effort}"'])
    for directory in dict.fromkeys(path.resolve() for path in writable):
        if not is_within(directory, config.workdir):
            command.extend(["--add-dir", str(directory)])
    if fork_from:
        command.extend(["fork", fork_from])
    command.append("-")
    return command


def terminate_process_tree(process: subprocess.Popen, timeout: float = 10.0) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    else:
        process.terminate()
    try:
        process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        process.kill(); process.wait()


def event_tool_metrics(event: dict[str, Any]) -> tuple[int, int, int]:
    if event.get("type") != "item.completed" or not isinstance(event.get("item"), dict):
        return 0, 0, 0
    item = event["item"]
    tool = int(item.get("type") in {"command_execution", "mcp_tool_call", "web_search", "file_change", "computer_action"})
    command = str(item.get("command") or "") if item.get("type") == "command_execution" else ""
    validation = int(any(name in command for name in ("validate_generation_plan.py", "validate_planned_sql.py", "validate_batch_test_cases.py")))
    failed = int(validation and isinstance(item.get("exit_code"), int) and item["exit_code"] != 0)
    return tool, validation, failed


def normalized_usage(event: dict[str, Any]) -> dict[str, int]:
    raw = event.get("usage") if event.get("type") == "turn.completed" else None
    return {str(k): v for k, v in raw.items() if isinstance(v, int) and not isinstance(v, bool)} if isinstance(raw, dict) else {}


def format_usage(usage: dict[str, int]) -> str:
    return ",".join(f"{key}:{usage[key]}" for key in sorted(usage)) if usage else "unavailable"


def invoke_codex(
    config: RunnerConfig, run_dir: Path, turn_number: int, phase: str, prompt: str,
    label: str | None, fork_from: str | None = None, session: FoundationSession | None = None,
) -> CodexTurnResult:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", f"{phase}-{label}" if label else phase).strip("-")
    prefix = run_dir / f"{turn_number:03d}-{slug or 'turn'}"
    jsonl_log, stderr_log, last_message = prefix.with_suffix(".jsonl"), prefix.with_suffix(".stderr.log"), prefix.with_suffix(".last-message.md")
    writable = tuple(path for path in (config.module_dir, config.manifest.parent if config.manifest else None, config.preanalysis_dir, config.case_output_dir, run_dir) if path is not None)
    command = codex_command(config, last_message, writable, fork_from)
    print(f"[{turn_number:03d}] {'forking' if fork_from else 'starting'} {phase}{f' {label}' if label else ''}")
    thread_id: str | None = None
    usage: dict[str, int] = {}
    failures: list[str] = []
    tools = validations = validation_failures = 0
    started = time.monotonic()
    with jsonl_log.open("w", encoding="utf-8", newline="\n") as stdout_file, stderr_log.open("w", encoding="utf-8", newline="\n") as stderr_file:
        try:
            process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr_file, text=True, encoding="utf-8", errors="replace", env=_child_env())
        except OSError as exc:
            raise RunnerError(f"failed to start Codex CLI: {exc}") from exc
        assert process.stdin is not None and process.stdout is not None
        try:
            process.stdin.write(prompt); process.stdin.close()
        except BrokenPipeError:
            pass
        try:
            for line in process.stdout:
                stdout_file.write(line); stdout_file.flush()
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                if event.get("type") == "thread.started" and isinstance(event.get("thread_id"), str):
                    observed = event["thread_id"]
                    if thread_id is not None and observed != thread_id:
                        raise RunnerError("Codex emitted multiple thread IDs in one invocation")
                    thread_id = observed
                    print(f"[{turn_number:03d}] thread.started {thread_id}")
                if event.get("type") == "turn.completed":
                    print(f"[{turn_number:03d}] turn.completed")
                if event.get("type") in {"turn.failed", "error"}:
                    failures.append(json.dumps(event, ensure_ascii=False))
                t, v, f = event_tool_metrics(event); tools += t; validations += v; validation_failures += f
                event_usage = normalized_usage(event)
                if event_usage:
                    usage = event_usage
            returncode = process.wait()
        except KeyboardInterrupt:
            terminate_process_tree(process); raise
    if returncode == 0 and not thread_id:
        raise RunnerError("Codex completed without a thread.started event")
    if session is not None:
        session.record_usage(usage)
    elapsed = time.monotonic() - started
    print(f"[{turn_number:03d}] TURN_METRICS ELAPSED_SECONDS={elapsed:.1f} TOOL_CALLS={tools} VALIDATION_ATTEMPTS={validations} VALIDATION_FAILURES={validation_failures}")
    print(f"[{turn_number:03d}] TURN_USAGE={format_usage(usage)}")
    return CodexTurnResult(returncode, jsonl_log, stderr_log, last_message, elapsed, tools, validations, validation_failures, usage, "\n".join(failures), thread_id)


def _run_stage_script(config: RunnerConfig, script_name: str, positional: tuple[str, ...] = ()) -> str:
    command = [sys.executable, "-X", "utf8", "-B", str(SKILL_DIR / "scripts" / script_name), str(config.module_dir), *positional]
    if config.manifest is not None:
        command.extend(["--manifest", str(config.manifest)])
    if config.preanalysis_dir is not None:
        command.extend(["--preanalysis-dir", str(config.preanalysis_dir)])
    if config.case_output_dir is not None:
        command.extend(["--case-output-dir", str(config.case_output_dir)])
    if script_name in {"validate_planned_sql.py", "validate_batch_test_cases.py", "validate_module_test_cases.py"} and config.db_config is not None:
        command.extend(["--db-config", str(config.db_config)])
    result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8", errors="replace", env=_child_env())
    combined = _combined_output(result)
    if combined:
        print(combined)
    if result.returncode != 0:
        raise RunnerError(f"{script_name} failed:\n{combined or 'no output'}")
    return result.stdout


def _foundation_prompt() -> str:
    return (
        f"完整读取并遵循测试用例生成 Skill：{SKILL_FILE}\n"
        f"并完整读取固定契约：{SKILL_DIR / 'references' / 'output-contract.md'}、"
        f"{SKILL_DIR / 'references' / 'tp-worker-contract.md'}、"
        f"{SKILL_DIR / 'references' / 'sql-assets.md'}。不要仅依据链接推断契约。\n"
        "这是模块基础会话，只建立稳定的 Skill 规则上下文。不得读取 runner-logs，"
        "不得生成或修改模块、状态、SQL、测试用例文件，也不得启动 run_generation.py。"
    )


def _foundation_fingerprint(config: RunnerConfig, state: dict[str, Any]) -> str:
    """Bind reusable rule context to sources, runtime rules and local CLI settings."""
    home = Path(os.environ.get("CODEX_HOME", str(Path.home() / ".codex"))).expanduser().resolve()
    files = {SKILL_FILE, home / "config.toml", home / "AGENTS.md", home / "instructions.md"}
    for directory in ("scripts", "references", "assets"):
        files.update(p for p in (SKILL_DIR / directory).rglob("*")
                     if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc")
    for directory in (config.workdir.resolve(), *config.workdir.resolve().parents):
        files.update(directory / name for name in
                     ("AGENTS.md", "AGENTS.override.md", ".codex/config.toml"))
    try:
        hashes = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None
                  for p in sorted(files, key=str)}
        executable = Path(shutil.which(config.codex_bin) or config.codex_bin).expanduser().resolve()
        identity = [str(executable)]
        if executable.is_file():
            stat = executable.stat()
            identity.extend([stat.st_size, stat.st_mtime_ns])
    except OSError as exc:
        raise RunnerError(f"cannot fingerprint foundation inputs: {exc}") from exc
    payload = {
        "version": 1, "source_hashes": state.get("source_hashes"),
        "module": str(config.module_dir.resolve()), "output": str(resolved_case_output_dir(config)),
        "manifest": str(config.manifest) if config.manifest else None,
        "preanalysis": str(config.preanalysis_dir) if config.preanalysis_dir else None,
        "workdir": str(config.workdir.resolve()), "codex_home": str(home), "cli": identity,
        "model": config.model, "profile": config.profile, "sandbox": config.sandbox,
        "reasoning_effort": config.reasoning_effort, "files": hashes,
        # Hash inherited provider settings without persisting credentials or endpoints.
        "environment": {key: os.environ.get(key) for key in (
            "OPENAI_BASE_URL", "OPENAI_API_BASE", "OPENAI_API_KEY", "OPENAI_ORG_ID",
            "OPENAI_PROJECT_ID", "AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_API_KEY",
        )},
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def _save_foundation(state_file: Path, before: dict[str, Any], thread_id: str, fingerprint: str) -> None:
    from common import save_json, state_lock, utc_now

    with state_lock(state_file.parent):
        state = _load_json(state_file)
        if state != before:
            raise RunnerError("generation state changed while recording foundation")
        state["foundation_session"] = {"version": 1, "thread_id": thread_id,
                                       "fingerprint": fingerprint, "created_at": utc_now()}
        state["updated_at"] = utc_now()
        save_json(state_file, state)


def _stage_prompt(config: RunnerConfig, phase: str, batch_id: str | None = None) -> str:
    case_dir = resolved_case_output_dir(config)
    inherited = "本会话从模块基础会话独立 fork，已继承完整 Skill；不要重新读取 SKILL.md。\n" if config.session_mode == "module-session" else f"完整读取并遵循 Skill：{SKILL_FILE}\n"
    common = inherited + f"模块：{config.module_dir}\n测试用例目录：{case_dir}\n" + "不得读取 runner-logs，不得处理其他模块，不得启动 run_generation.py，不依赖自动 compaction。人工填写 Markdown、SQL、JSON 时必须使用 apply_patch。\n"
    if phase == "planning":
        return common + (
            f"完整读取 {case_dir / 'planning-input.md'}，填写 {case_dir / 'generation-plan.json'}。\n"
            "复杂度与 SQL 必要性独立判断。SQL 只用于页面查询结果、顶部/详情字段、列表列、聚合或明确数据库核对；不得因引用 DC 就写 SQL。"
            "需求含原型图时先识别原型中的实际功能区，每条 SQL 必须填写 functional_module 并按功能区组织，查询字段/别名和结果顺序便于逐项对照；无原型时按需求功能模块组织。不得虚构区域或业务口径；归属不明则列为待澄清。"
            "简单/查询展示 TP 每批最多 10 个，复杂并发、轮询、短路、重试或多状态组合 TP 单独成批。每个 TP 只能进入一个批次并保持顺序。完成后运行：\n"
            f"{phase_command(config, 'validate_generation_plan.py')}\n"
        )
    if phase == "sql":
        return common + (
            f"完整读取 {case_dir / 'sql-generation-input.md'}。只实现计划中的 SELECT SQL，按每项 functional_module 对应的原型功能区/需求功能模块组织；字段、别名和结果顺序应便于对照该区域。相同功能视图优先参数化复用，不按 TP 或底层表机械拆 SQL，不虚构区域/口径，不增加计划外 SQL，不生成 DML。写入 {case_dir / 'sql'}。完成后运行：\n"
            f"{phase_command(config, 'validate_planned_sql.py')}\n"
        )
    if phase == "batch" and batch_id:
        return common + (
            f"完整读取批次清单：{case_dir / 'inputs' / (batch_id + '-input.md')}。按清单读取模块基线、上下文基线和各 TP delta，一次完成全部 by-tp 输出。"
            "对批内每个TP单独判断用例数量，不预设1 TP = 1 TC。只有独立业务风险、不可合并前置或操作、独立可判断预期、独立回归价值四项同时成立才拆分，并在每条追溯说明中给出具体依据；否则合并可执行验证，但必须覆盖该TP全部承诺。只写当前测试点的关键前置、具体动作和可判断结果，不重复入口、相邻测试点或其他模块。"
            "简单前置填无或一句关键条件；复杂多类前置才分类。若包含多个值或状态组合，必须在前置或步骤中直接列明具体条件和顺序，不能写多个场景/各场景让执行者回查。步骤和预期从 1. 连续编号、逐项换行且一一对应。"
            "不得使用当前 TP、来源场景、场景矩阵、数据闭包执行计划、核心操作等内部占位话术。只引用分配的 SQL-ID；查询预期简洁写与具体 SQL-ID 查询结果一致。"
            "入库或更新用例在预期描述目标记录内容，不生成 DML。\n"
            "写入前读取清单中每个 OUTPUT 模板；固定章节、表头、列数及分隔行保持不变。"
            "元数据填当前 TP-ID、输入 SHA-256 和生成结果 validated；这仅是文档声明，不能直接把状态 JSON 改为 validated。"
            "必填单元格不得为空；冲刺、备注等不适用填无，三列测试结果填未执行。"
            "每条数据变量声明只含一个 $变量 和非空字段描述，声明之间用分号分隔；变量须在前置或步骤实际使用。"
            "表格单元格内多条前置、步骤、预期均用 <br> 分行，不能把多项编号挤在同一逻辑行。\n"
            "全部输出完成后首次运行下列校验。若仅为当前批次输出的格式、编号、变量声明或已有输入引用填写错误，"
            "在同一 worker turn 内按错误修正后重新运行同一命令，最多 2 轮修正重验（含首次共最多 3 次）。"
            "只有校验通过才报告完成；超过上限或缺业务事实、来源漂移、SQL资产/报告不一致时立即停止并报告阻断，"
            "不得猜测事实、扩大读取范围、修改 SQL 或直接写 validated 状态。校验命令：\n"
            f"{phase_command(config, 'validate_batch_test_cases.py', (batch_id,))}\n"
        )
    raise RunnerError(f"unsupported stage prompt: {phase}")


def _without_updated_at(value: dict[str, Any]) -> dict[str, Any]:
    result = json.loads(json.dumps(value, ensure_ascii=False)); result.pop("updated_at", None); return result


def _assert_unchanged_except(before: dict[str, Any], after: dict[str, Any], allowed: set[str], label: str) -> None:
    left, right = _without_updated_at(before), _without_updated_at(after)
    for key in allowed:
        left.pop(key, None); right.pop(key, None)
    if left != right:
        raise RunnerError(f"{label} changed state outside its authorized fields")


def _assert_planning_transition(before: dict[str, Any], after: dict[str, Any]) -> None:
    _assert_unchanged_except(before, after, {"planning", "sql_planning", "batches", "tps", "finalization"}, "planning")
    for old, new in zip(before.get("tps", []), after.get("tps", [])):
        old_copy, new_copy = dict(old), dict(new)
        old_copy.pop("planned_sql_refs", None); new_copy.pop("planned_sql_refs", None)
        if old_copy != new_copy:
            raise RunnerError("planning changed TP state outside planned_sql_refs")


def _assert_sql_transition(before: dict[str, Any], after: dict[str, Any]) -> None:
    _assert_unchanged_except(before, after, {"sql_planning"}, "SQL generation")


def _assert_batch_transition(before: dict[str, Any], after: dict[str, Any], batch_id: str) -> None:
    _assert_unchanged_except(before, after, {"batches", "tps"}, batch_id)
    old_batches = {item["batch_id"]: item for item in before.get("batches", [])}
    new_batches = {item["batch_id"]: item for item in after.get("batches", [])}
    if set(old_batches) != set(new_batches):
        raise RunnerError(f"{batch_id} changed batch identity")
    for key in old_batches:
        if key != batch_id and old_batches[key] != new_batches[key]:
            raise RunnerError(f"{batch_id} changed sibling batch {key}")
    old_target, new_target = dict(old_batches[batch_id]), dict(new_batches[batch_id])
    for key in ("status", "case_count", "validated_at"):
        old_target.pop(key, None)
        new_target.pop(key, None)
    if old_target != new_target:
        raise RunnerError(f"{batch_id} changed its immutable batch definition")
    target_tps = set(old_batches[batch_id]["tp_ids"])
    old_tps = {item["tp_id"]: item for item in before.get("tps", [])}
    new_tps = {item["tp_id"]: item for item in after.get("tps", [])}
    if set(old_tps) != set(new_tps):
        raise RunnerError(f"{batch_id} changed TP identity")
    for tp_id in old_tps:
        if tp_id not in target_tps and old_tps[tp_id] != new_tps[tp_id]:
            raise RunnerError(f"{batch_id} changed TP outside the batch: {tp_id}")
        if tp_id in target_tps:
            old_record, new_record = dict(old_tps[tp_id]), dict(new_tps[tp_id])
            for key in ("status", "case_count", "output_sha256", "validated_at", "sql_refs"):
                old_record.pop(key, None)
                new_record.pop(key, None)
            if old_record != new_record:
                raise RunnerError(f"{batch_id} changed immutable TP fields for {tp_id}")


def _phase_completed(snapshot: StateSnapshot, phase: str, batch_id: str | None) -> bool:
    if phase == "planning":
        return snapshot.planning_status == "validated"
    if phase == "sql":
        return snapshot.sql_planning_status == "validated"
    if phase == "batch" and batch_id:
        return any(item.batch_id == batch_id and item.status == "validated" for item in snapshot.batches)
    raise RunnerError(f"unsupported phase completion check: {phase}")


def _assert_completed_transition(before: dict[str, Any], after: dict[str, Any], phase: str, batch_id: str | None) -> None:
    if phase == "planning":
        _assert_planning_transition(before, after)
    elif phase == "sql":
        _assert_sql_transition(before, after)
    elif phase == "batch" and batch_id:
        _assert_batch_transition(before, after, batch_id)
    else:
        raise RunnerError(f"unsupported transition check: {phase}")


def _require_success(result: CodexTurnResult, phase: str) -> None:
    if result.returncode == 0:
        return
    tail = ""
    try:
        tail = result.stderr_log.read_text(encoding="utf-8", errors="replace")[-4000:].strip()
    except OSError:
        pass
    raise RunnerError(f"Codex {phase} exited with code {result.returncode}; logs: {result.jsonl_log}, {result.stderr_log}{f'; stderr tail: {tail}' if tail else ''}")


def _failure_text(result: CodexTurnResult) -> str:
    stderr = ""
    try:
        stderr = result.stderr_log.read_text(encoding="utf-8", errors="replace")[-32000:]
    except OSError:
        pass
    return "\n".join(part for part in (result.failure_evidence, stderr) if part)


def _is_transient(result: CodexTurnResult) -> bool:
    if result.returncode == 0:
        return False
    evidence = _failure_text(result)
    return not NONTRANSIENT_PROVIDER_FAILURE_RE.search(evidence) and bool(TRANSIENT_CODEX_FAILURE_RE.search(evidence))


def run_pipeline(
    config: RunnerConfig,
    initialize_fn: Initializer | None = None,
    invoke_fn: Invoker | None = None,
    stage_fn: StageRunner | None = None,
) -> PipelineResult:
    if not config.module_dir.is_dir() or not config.workdir.is_dir():
        raise RunnerError("module directory or Codex working directory does not exist")
    case_dir = resolved_case_output_dir(config)
    initializer, stage_runner = initialize_fn or initialize_generation, stage_fn or _run_stage_script
    session = FoundationSession(config.session_mode)
    with RunnerLock(case_dir):
        initialized = initializer(config)
        if initialized.case_output_dir.resolve() != case_dir.resolve():
            raise RunnerError("initializer returned a different testcase output directory")
        state_file = initialized.state_file.resolve()
        state, snapshot = load_state(state_file)
        require_state_binding(config, snapshot); require_ready(state, snapshot)
        if not initialized.ready:
            raise AttentionRequired("complete readiness and execution-context.md before restarting")
        run_dir = (config.logs_dir or case_dir / "runner-logs") / (datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + f"-{uuid.uuid4().hex[:8]}")
        run_dir.mkdir(parents=True, exist_ok=False)
        print(f"RUN_LOG_DIR={run_dir}")
        print("PIPELINE_ARCHITECTURE=module-plan-sql-first-hybrid-batches")
        print(f"SCHEDULER_STATE={state_file}")
        print("HISTORICAL_LOG_INPUT=disabled")
        print("AUTOMATIC_COMPACTION_POLICY=not-primary-independent-stage-forks")
        print(f"SESSION_MODE={config.session_mode}")
        turns = batch_turns = 0
        selected = config
        binary_selected = False
        foundation_reused = False
        foundation_rebuilt = False

        def select_binary() -> None:
            nonlocal selected, binary_selected
            if not binary_selected:
                if invoke_fn is None:
                    selected = replace(selected, codex_bin=select_codex_binary(
                        config.codex_bin, require_fork=config.session_mode == "module-session"))
                binary_selected = True

        def call_invoker(phase: str, prompt: str, label: str | None, parent: str | None) -> CodexTurnResult:
            nonlocal turns
            select_binary()
            if invoke_fn is None:
                invoker = lambda cfg, rd, num, ph, pr, lab, par: invoke_codex(cfg, rd, num, ph, pr, lab, par, session)
            else:
                invoker = invoke_fn
            turns += 1
            return invoker(selected, run_dir, turns, phase, prompt, label, parent)

        def ensure_foundation(*, force_new: bool = False) -> None:
            nonlocal foundation_reused
            if config.session_mode != "module-session" or session.thread_id is not None:
                return
            select_binary()
            current = _load_json(state_file)
            fingerprint = _foundation_fingerprint(selected, current)
            record = current.get("foundation_session")
            if (not force_new and isinstance(record, dict) and record.get("version") == 1
                    and record.get("fingerprint") == fingerprint
                    and isinstance(record.get("thread_id"), str) and record["thread_id"].strip()):
                session.register(record["thread_id"])
                foundation_reused = True
                print("FOUNDATION_SESSION_REUSED=true")
                return
            attempt = 0
            while True:
                attempt += 1
                before = _load_json(state_file)
                result = call_invoker("foundation", _foundation_prompt(), None, None)
                if before != _load_json(state_file):
                    raise RunnerError("foundation bootstrap changed generation-state.json")
                if result.returncode == 0:
                    session.register(result.thread_id)
                    if _foundation_fingerprint(selected, before) != fingerprint:
                        raise RunnerError("foundation inputs changed during bootstrap; restart runner")
                    _save_foundation(state_file, before, session.thread_id, fingerprint)
                    foundation_reused = False
                    return
                if attempt > config.max_transient_retries or not _is_transient(result):
                    _require_success(result, "foundation")
                delay = min(
                    config.retry_base_delay_seconds * (2 ** (attempt - 1)),
                    MAX_RETRY_DELAY_SECONDS,
                )
                print(f"TRANSIENT_RETRY={attempt}/{config.max_transient_retries} PHASE=foundation")
                if delay:
                    time.sleep(delay)

        def invoke_stage(phase: str, label: str, batch_id: str | None = None) -> None:
            nonlocal foundation_rebuilt
            ensure_foundation()
            attempt = 0
            while True:
                attempt += 1
                before, _ = load_state(state_file)
                result = call_invoker(
                    phase, _stage_prompt(selected, phase, batch_id), label,
                    session.thread_id if config.session_mode == "module-session" else None,
                )
                if result.thread_id is not None:
                    session.require_child(result.thread_id, label)
                after, after_snapshot = load_state(state_file)
                if _phase_completed(after_snapshot, phase, batch_id):
                    session.require_child(result.thread_id, label)
                    _assert_completed_transition(before, after, phase, batch_id)
                    if result.returncode != 0:
                        print(f"TURN_NONZERO_BUT_STATE_COMPLETED={label} EXIT_CODE={result.returncode}")
                    return
                if result.returncode == 0:
                    session.require_child(result.thread_id, label)
                    raise AttentionRequired(f"{label} ended without validated state")
                if after != before:
                    raise RunnerError(f"failed {label} turn changed generation-state.json")
                evidence = _failure_text(result)
                if (foundation_reused and not foundation_rebuilt
                        and not NONTRANSIENT_PROVIDER_FAILURE_RE.search(evidence)
                        and UNAVAILABLE_FOUNDATION_RE.search(evidence)):
                    foundation_rebuilt = True
                    session.thread_id = None
                    print("FOUNDATION_SESSION_UNAVAILABLE=rebuild-once")
                    ensure_foundation(force_new=True)
                    continue
                if attempt > config.max_transient_retries or not _is_transient(result):
                    _require_success(result, label)
                delay = min(config.retry_base_delay_seconds * (2 ** (attempt - 1)), MAX_RETRY_DELAY_SECONDS)
                print(f"TRANSIENT_RETRY={attempt}/{config.max_transient_retries} PHASE={label}")
                if delay:
                    time.sleep(delay)

        if snapshot.planning_status != "validated":
            stage_runner(config, "prepare_generation_plan.py", ())
            invoke_stage("planning", "module-planning")
            state, snapshot = load_state(state_file)
        if snapshot.sql_planning_status != "validated":
            stage_runner(config, "prepare_sql_generation.py", ())
            state, snapshot = load_state(state_file)
            if snapshot.sql_planning_status != "validated":
                invoke_stage("sql", "module-sql")
                state, snapshot = load_state(state_file)
        max_batches = config.max_batch_turns if config.max_batch_turns is not None else len(snapshot.batches)
        while snapshot.next_batch is not None:
            if batch_turns >= max_batches:
                raise AttentionRequired(f"reached max batch turn limit ({max_batches})")
            batch = snapshot.next_batch
            stage_runner(config, "prepare_next_batch.py", ())
            _, prepared_snapshot = load_state(state_file)
            if next(item for item in prepared_snapshot.batches if item.batch_id == batch.batch_id).status != "prepared":
                raise RunnerError(f"prepare_next_batch.py did not prepare {batch.batch_id}")
            invoke_stage("batch", batch.batch_id, batch.batch_id)
            batch_turns += 1
            state, snapshot = load_state(state_file)
            print(f"BATCH_VALIDATED={batch.batch_id} TP_COUNT={len(batch.tp_ids)}")
        if snapshot.finalization_status != "validated":
            stage_runner(config, "prepare_finalization.py", ())
            stage_runner(config, "validate_module_test_cases.py", ())
            state, snapshot = load_state(state_file)
        if snapshot.finalization_status != "validated":
            raise AttentionRequired("deterministic finalization did not validate")
        print("FINALIZATION_MODE=deterministic-no-ai-rewrite")
        print("PIPELINE_STATUS=complete")
        return PipelineResult(state_file, run_dir, turns, batch_turns)


run_hybrid_pipeline = run_pipeline


def main(argv: list[str] | None = None) -> int:
    configure_process_stdio()
    try:
        run_pipeline(parse_args(argv)); return EXIT_OK
    except AttentionRequired as exc:
        print(f"ATTENTION_REQUIRED: {exc}", file=sys.stderr); return EXIT_ATTENTION
    except RunnerError as exc:
        print(f"ERROR: {exc}", file=sys.stderr); return EXIT_ERROR
    except KeyboardInterrupt:
        print("INTERRUPTED: runner stopped by user", file=sys.stderr); return EXIT_INTERRUPTED


if __name__ == "__main__":
    raise SystemExit(main())
