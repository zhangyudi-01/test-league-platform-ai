from __future__ import annotations

import argparse
import datetime as _dt
import sys
from pathlib import Path
from typing import Any, Optional

from .agents import AgentRunner
from .attachments import AttachmentIndex
from .config import SplitConfig, args_to_config, config_to_dict
from .mapper import DeterministicMapper, record_to_plan_dict, summarize_plan
from .modules import ModuleTree
from .source_factory import load_source
from .sources import ScopeResolver, SplitError, json_dump, path_str
from .validate import validate_manifest
from .writer import write_coverage_tsv, write_split


def safe_stdout() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except AttributeError:
        pass


def build_plan(config: SplitConfig, create_run_dir: bool = True) -> tuple[dict[str, Any], Any, Any, Any, Any]:
    source = load_source(config.source, config.source_format, config.docx)
    modules = ModuleTree(config.modules_root, config.module_dir_pattern)
    scope_resolver = ScopeResolver(source, config.scope_headings, config.stop_headings)
    mapper = DeterministicMapper(source, modules, scope_resolver)
    records = mapper.map_all()

    if create_run_dir:
        config.run_dir.mkdir(parents=True, exist_ok=True)

    if config.agent != "none":
        AgentRunner(source, scope_resolver, config.run_dir, config, modules).maybe_resolve(records)

    attachments = AttachmentIndex(config.attachments_root)
    plan_modules = [record_to_plan_dict(record, source, modules, scope_resolver, attachments) for record in records]
    plan = {
        "schema_version": 2,
        "created_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "config": config_to_dict(config),
        "source": {
            "path": path_str(source.path),
            "kind": source.kind,
            "raw_sha256": source.raw_sha256,
            "canonical_sha256": source.canonical_sha256,
            "sha256": source.canonical_sha256,
            "line_count": source.line_count,
            "stats": source.stats,
            "warnings": source.warnings,
            "docx_options": config.docx if source.kind == "docx" else {},
        },
        "modules_root": path_str(modules.root),
        "attachments_root": path_str(config.attachments_root) if config.attachments_root else None,
        "scope": scope_resolver.to_dict(),
        "write_scope": config.write_scope,
        "output_name": config.output_name,
        "run_dir": path_str(config.run_dir),
        "modules": plan_modules,
        "summary": summarize_plan(plan_modules),
    }
    return plan, records, source, modules, scope_resolver


def command_inspect(args: argparse.Namespace) -> int:
    config = args_to_config(args)
    plan, _records, source, modules, scope_resolver = build_plan(config, create_run_dir=False)
    print(f"Source: {source.path}")
    print(f"Source kind: {source.kind}")
    print(f"Canonical lines: {source.line_count}")
    print(f"Stats: {source.stats}")
    print("\nScope ranges:")
    for item in plan["scope"]["ranges"]:
        print(f"- lines {item['start_line']}-{item['end_line']} scope={item['scope_heading']} stop={item['stop_heading']}")
    print("\nHeadings in scope:")
    for heading in scope_resolver.headings_in_scope():
        scope_range = scope_resolver.scope_for_heading(heading)
        rel_depth = len(source.relative_ancestors(heading, scope_range.scope_heading if scope_range else None)) + 1
        indent = "  " * max(rel_depth - 1, 0)
        print(f"{indent}- L{heading.level} line {heading.start_line}: {heading.title}")
    print("\nModules:")
    for node in modules.sorted_nodes():
        indent = "  " * (node.depth - 1)
        print(f"{indent}- {node.key} {node.title} ({node.path})")
    print("\nMapping summary:")
    for module in plan["modules"]:
        line = module.get("range", {}).get("start_line", "-")
        print(f"- {module['module_id']} {module['title']}: {module['status']} line={line} reason={module['reason']}")
    return 0


def command_plan(args: argparse.Namespace) -> int:
    config = args_to_config(args)
    plan, _records, _source, _modules, _scope_resolver = build_plan(config, create_run_dir=True)
    plan_path = config.run_dir / "split-plan.json"
    coverage_path = config.run_dir / "coverage.tsv"
    json_dump(plan_path, plan)
    write_coverage_tsv(coverage_path, plan)
    print(f"Plan written: {plan_path}")
    print(f"Coverage written: {coverage_path}")
    print(f"Summary: {plan['summary']}")
    return 0


def command_split(args: argparse.Namespace) -> int:
    config = args_to_config(args)
    plan, _records, source, _modules, _scope_resolver = build_plan(config, create_run_dir=True)
    result = write_split(plan, source, config, args.overwrite, args.allow_unmapped, args.allow_empty)
    print(f"Plan written: {result['plan_path']}")
    print(f"Manifest written: {result['manifest_path']}")
    print(f"Coverage written: {result['coverage_path']}")
    print(f"Written outputs: {len(result['manifest']['outputs'])}")
    return 0


def command_validate(args: argparse.Namespace) -> int:
    code, report_path = validate_manifest(Path(args.manifest))
    if code:
        print(f"Validation failed. Report: {report_path}", file=sys.stderr)
    else:
        print(f"Validation passed. Report: {report_path}")
    return code


def add_common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--config", default=None, help="Optional JSON config file with defaults for this run.")
    parser.add_argument("--source", default=None, help="Source document path (.md/.markdown/.docx).")
    parser.add_argument("--source-format", choices=["auto", "markdown", "docx"], default=None, help="Source format.")
    parser.add_argument("--modules-root", default=None, help="Root directory containing module directories.")
    parser.add_argument("--attachments-root", default=None, help="Optional local attachments root.")
    parser.add_argument("--scope-heading", action="append", default=None, help="Scope heading. Repeat for multiple scopes.")
    parser.add_argument("--stop-heading", action="append", default=None, help="Stop heading. Repeat for multiple stops.")
    parser.add_argument("--run-dir", default=None, help="Directory for plan/manifest/coverage outputs.")
    parser.add_argument("--output-name", default=None, help="Output file name inside each module directory.")
    parser.add_argument("--write-scope", choices=["leaf", "all", "direct"], default=None, help="Which mapped modules should receive output files.")
    parser.add_argument("--module-dir-pattern", default=None, help="Regex for module directory names.")


def add_agent_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--agent", choices=["none", "claude", "codex", "both"], default=None, help="Optional local model CLI assistance.")
    parser.add_argument("--agent-scope", choices=["problems", "all"], default=None, help="Call agents for problems only or every module.")
    parser.add_argument("--agent-task", choices=["select", "review"], default=None, help="Ask agents to select or review ranges.")
    parser.add_argument("--claude-command", default=None, help="Claude Code CLI command, e.g. 'claude -p'.")
    parser.add_argument("--codex-command", default=None, help="Codex CLI command, e.g. 'codex exec'.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Split Markdown or DOCX requirements into existing module directories.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="Read-only scan of headings, modules, and mapping.")
    add_common_args(inspect_parser)
    inspect_parser.set_defaults(func=command_inspect)

    plan_parser = subparsers.add_parser("plan", help="Create a reviewable split plan without writing module files.")
    add_common_args(plan_parser)
    add_agent_args(plan_parser)
    plan_parser.set_defaults(func=command_plan)

    split_parser = subparsers.add_parser("split", help="Write canonical source slices into module directories.")
    add_common_args(split_parser)
    add_agent_args(split_parser)
    split_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing outputs if content differs.")
    split_parser.add_argument("--allow-unmapped", action="store_true", help="Continue even if leaf modules are unmapped.")
    split_parser.add_argument("--allow-empty", action="store_true", help="Allow empty output files.")
    split_parser.set_defaults(func=command_split)

    validate_parser = subparsers.add_parser("validate", help="Validate a split manifest.")
    validate_parser.add_argument("--manifest", required=True, help="Path to split-manifest.json.")
    validate_parser.set_defaults(func=command_validate)
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    safe_stdout()
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args))
    except SplitError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except UnicodeDecodeError as exc:
        print(f"Error: source file must be UTF-8 decodable: {exc}", file=sys.stderr)
        return 2

