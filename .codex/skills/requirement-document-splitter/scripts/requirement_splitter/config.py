from __future__ import annotations

import dataclasses
import datetime as _dt
import json
from pathlib import Path
from typing import Any, Optional

from .sources import SplitError, read_json


CONFIG_FIELDS = {
    "schema_version",
    "source",
    "source_format",
    "modules_root",
    "attachments_root",
    "scope_heading",
    "stop_heading",
    "scope_headings",
    "stop_headings",
    "run_dir",
    "output_name",
    "write_scope",
    "module_dir_pattern",
    "docx",
    "agent",
    "agent_scope",
    "agent_task",
    "claude_command",
    "codex_command",
}

GENERIC_DEFAULTS = {
    "source_format": "auto",
    "attachments_root": "",
    "scope_headings": [],
    "stop_headings": [],
    "output_name": "00-module-requirement-pack.md",
    "write_scope": "direct",
    "module_dir_pattern": r"^(?P<prefix>[A-Za-z]+)-(?P<id>\d+(?:-\d+)*)-(?P<title>.+)$",
    "docx": {},
    "agent": "none",
    "agent_scope": "problems",
    "agent_task": "review",
    "claude_command": "",
    "codex_command": "",
}


@dataclasses.dataclass
class SplitConfig:
    config_path: Optional[Path]
    source: Path
    source_format: str
    modules_root: Path
    attachments_root: Optional[Path]
    scope_headings: list[str]
    stop_headings: list[str]
    run_dir: Path
    output_name: str
    write_scope: str
    module_dir_pattern: str
    docx: dict[str, Any]
    agent: str
    agent_scope: str
    agent_task: str
    claude_command: str
    codex_command: str


def listify(value: Any) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        return [str(item) for item in value if str(item)]
    raise SplitError(f"Expected string or list, got {type(value).__name__}")


def resolve_path(value: str, base: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = base / path
    return path.resolve()


def default_run_dir(modules_root: Path) -> Path:
    stamp = _dt.datetime.now(_dt.timezone.utc).strftime("run-%Y%m%d-%H%M%S")
    parent = modules_root.parent
    return (parent / "requirement-split-work" / "runs" / stamp).resolve()


def load_config_dict(path: Optional[str]) -> tuple[dict[str, Any], Optional[Path]]:
    if not path:
        return {}, None
    config_path = Path(path).resolve()
    if not config_path.exists():
        raise SplitError(f"Config file does not exist: {config_path}")
    config = read_json(config_path)
    if not isinstance(config, dict):
        raise SplitError("Config file must be a JSON object")
    unknown = sorted(set(config) - CONFIG_FIELDS)
    if unknown:
        raise SplitError(f"Unknown config fields: {', '.join(unknown)}")
    return config, config_path


def args_to_config(args: Any) -> SplitConfig:
    config, config_path = load_config_dict(getattr(args, "config", None))
    data = dict(GENERIC_DEFAULTS)
    data.update(config)

    # Legacy scalar fields remain supported.
    if "scope_heading" in data and data.get("scope_heading") and not data.get("scope_headings"):
        data["scope_headings"] = listify(data["scope_heading"])
    if "stop_heading" in data and data.get("stop_heading") and not data.get("stop_headings"):
        data["stop_headings"] = listify(data["stop_heading"])

    for field in CONFIG_FIELDS:
        if hasattr(args, field):
            value = getattr(args, field)
            if value is not None:
                data[field] = value

    if "scope_heading" in data and data.get("scope_heading") and not data.get("scope_headings"):
        data["scope_headings"] = listify(data["scope_heading"])
    if "stop_heading" in data and data.get("stop_heading") and not data.get("stop_headings"):
        data["stop_headings"] = listify(data["stop_heading"])

    if not data.get("source"):
        raise SplitError("Missing required config: source")
    if not data.get("modules_root"):
        raise SplitError("Missing required config: modules_root")

    base = config_path.parent if config_path else Path.cwd()
    source = resolve_path(str(data["source"]), base)
    modules_root = resolve_path(str(data["modules_root"]), base)
    attachments_root = resolve_path(str(data["attachments_root"]), base) if data.get("attachments_root") else None
    run_dir = resolve_path(str(data["run_dir"]), base) if data.get("run_dir") else default_run_dir(modules_root)

    source_format = str(data.get("source_format") or "auto").lower()
    if source_format not in {"auto", "markdown", "docx"}:
        raise SplitError("source_format must be one of: auto, markdown, docx")
    if source_format == "auto":
        suffix = source.suffix.lower()
        source_format = "docx" if suffix == ".docx" else "markdown"

    return SplitConfig(
        config_path=config_path,
        source=source,
        source_format=source_format,
        modules_root=modules_root,
        attachments_root=attachments_root,
        scope_headings=listify(data.get("scope_headings")),
        stop_headings=listify(data.get("stop_headings")),
        run_dir=run_dir,
        output_name=str(data.get("output_name") or "00-module-requirement-pack.md"),
        write_scope=str(data.get("write_scope") or "direct"),
        module_dir_pattern=str(data.get("module_dir_pattern") or GENERIC_DEFAULTS["module_dir_pattern"]),
        docx=dict(data.get("docx") or {}),
        agent=str(data.get("agent") or "none"),
        agent_scope=str(data.get("agent_scope") or "problems"),
        agent_task=str(data.get("agent_task") or "review"),
        claude_command=str(data.get("claude_command") or ""),
        codex_command=str(data.get("codex_command") or ""),
    )


def config_to_dict(config: SplitConfig) -> dict[str, Any]:
    return {
        "config_path": str(config.config_path) if config.config_path else None,
        "source": str(config.source),
        "source_format": config.source_format,
        "modules_root": str(config.modules_root),
        "attachments_root": str(config.attachments_root) if config.attachments_root else None,
        "scope_headings": config.scope_headings,
        "stop_headings": config.stop_headings,
        "run_dir": str(config.run_dir),
        "output_name": config.output_name,
        "write_scope": config.write_scope,
        "module_dir_pattern": config.module_dir_pattern,
        "docx": config.docx,
        "agent": config.agent,
        "agent_scope": config.agent_scope,
        "agent_task": config.agent_task,
        "claude_command": config.claude_command,
        "codex_command": config.codex_command,
    }
