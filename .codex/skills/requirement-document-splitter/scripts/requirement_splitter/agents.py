from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from .config import SplitConfig
from .mapper import MatchRecord
from .sources import DocumentSource, Heading, ScopeResolver, SplitError, json_dump


def agent_range(start_index: int, end_index_exclusive: int) -> dict[str, int]:
    return {"start_line": start_index + 1, "end_line_exclusive": end_index_exclusive + 1}


class AgentRunner:
    def __init__(self, source: DocumentSource, scope_resolver: ScopeResolver, run_dir: Path, config: SplitConfig, modules: Any) -> None:
        self.source = source
        self.scope_resolver = scope_resolver
        self.run_dir = run_dir
        self.config = config
        self.modules = modules

    def maybe_resolve(self, records: list[MatchRecord]) -> None:
        if self.config.agent == "none":
            return
        commands: list[tuple[str, str]] = []
        if self.config.agent in {"claude", "both"}:
            if not self.config.claude_command:
                raise SplitError("agent requires claude_command when claude is selected")
            commands.append(("claude", self.config.claude_command))
        if self.config.agent in {"codex", "both"}:
            if not self.config.codex_command:
                raise SplitError("agent requires codex_command when codex is selected")
            commands.append(("codex", self.config.codex_command))

        for record in records:
            if self.config.agent_scope == "problems" and record.status == "mapped":
                continue
            decisions = []
            for agent_name, command in commands:
                decisions.append(self._run_one(record, agent_name, command))
            record.agent_decisions = decisions
            self._apply_decisions(record, decisions)

    def _run_one(self, record: MatchRecord, agent_name: str, command: str) -> dict[str, Any]:
        prompt = self._build_prompt(record)
        agent_dir = self.run_dir / "agent-decisions"
        agent_dir.mkdir(parents=True, exist_ok=True)
        (agent_dir / f"{record.module.key}-{agent_name}-prompt.md").write_text(prompt, encoding="utf-8", newline="\n")

        completed = subprocess.run(
            command,
            input=prompt,
            text=True,
            shell=True,
            capture_output=True,
            encoding="utf-8",
            errors="replace",
        )
        payload: dict[str, Any] = {
            "agent": agent_name,
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "parsed": None,
            "valid": False,
            "error": None,
        }
        try:
            parsed = self._parse_json_object(completed.stdout)
            payload["parsed"] = parsed
            payload["valid"] = self._validate_agent_range(parsed)
        except Exception as exc:  # noqa: BLE001 - recorded for audit.
            payload["error"] = str(exc)
        json_dump(agent_dir / f"{record.module.key}-{agent_name}-result.json", payload)
        return payload

    def _build_prompt(self, record: MatchRecord) -> str:
        module = record.module
        candidates = record.candidates or self.scope_resolver.headings_in_scope()
        candidate_lines = []
        for heading in candidates[:120]:
            scope_range = self.scope_resolver.scope_for_heading(heading)
            ancestors = " > ".join(self.source.relative_ancestors(heading, scope_range.scope_heading if scope_range else None))
            candidate_lines.append(
                f"- line {heading.start_line}, end_line_exclusive {heading.end_line + 1}, level {heading.level}, ancestors [{ancestors}], title: {heading.title}, info: {heading.source_info}"
            )

        proposed = "None"
        if record.heading:
            proposed = json.dumps(
                {"selected_ranges": [agent_range(record.heading.line_index, record.heading.end_line_index_exclusive)], "reason": record.reason},
                ensure_ascii=False,
            )

        if self.config.agent_task == "review":
            task_lines = [
                "Task: review the proposed selected range for this module.",
                "If the proposed range is correct, return the same range and agreement=true.",
                "If it is wrong, return the corrected range and agreement=false.",
            ]
        else:
            task_lines = [
                "Task: select the source line range for this module.",
                "Return the best matching range and agreement=null.",
            ]

        source_note = "Line numbers refer to the original Markdown source." if self.source.kind == "markdown" else "Line numbers refer to deterministic canonical Markdown generated from the DOCX source."
        return "\n".join(
            [
                "You are selecting source line ranges for a lossless requirement split.",
                source_note,
                "Return JSON only. Do not rewrite requirement text.",
                "Schema: {\"selected_ranges\":[{\"start_line\": <1-based inclusive>, \"end_line_exclusive\": <1-based exclusive>}], \"agreement\": true|false|null, \"confidence\": \"high|medium|low\", \"notes\": \"...\"}",
                *task_lines,
                f"Source kind: {self.source.kind}",
                f"Module id: {module.key}",
                f"Module title: {module.title}",
                f"Module ancestors: {' > '.join(a.title for a in self.modules.ancestors(module))}",
                f"Source path: {self.source.path}",
                f"Current script proposal: {proposed}",
                "Candidate headings:",
                *candidate_lines,
            ]
        )

    def _parse_json_object(self, text: str) -> dict[str, Any]:
        start = text.find("{")
        end = text.rfind("}")
        if start < 0 or end < start:
            raise SplitError("agent output did not contain a JSON object")
        parsed = json.loads(text[start : end + 1])
        if not isinstance(parsed, dict):
            raise SplitError("agent JSON is not an object")
        return parsed

    def _validate_agent_range(self, parsed: dict[str, Any]) -> bool:
        ranges = parsed.get("selected_ranges")
        if not isinstance(ranges, list) or not ranges:
            return False
        for item in ranges:
            if not isinstance(item, dict):
                return False
            start_line = item.get("start_line")
            end_line_exclusive = item.get("end_line_exclusive")
            if not isinstance(start_line, int) or not isinstance(end_line_exclusive, int):
                return False
            start_index = start_line - 1
            end_index = end_line_exclusive - 1
            if start_index >= end_index or not self.scope_resolver.contains(start_index, end_index):
                return False
        return True

    def _apply_decisions(self, record: MatchRecord, decisions: list[dict[str, Any]]) -> None:
        valid = [decision for decision in decisions if decision.get("valid")]
        if not valid:
            return
        ranges_as_text = [json.dumps(decision["parsed"].get("selected_ranges"), sort_keys=True) for decision in valid]
        if len(set(ranges_as_text)) != 1:
            record.status = "agent_conflict"
            record.reason = "valid agent decisions disagree"
            return

        ranges = valid[0]["parsed"]["selected_ranges"]
        script_ranges = []
        if record.heading:
            script_ranges = [agent_range(record.heading.line_index, record.heading.end_line_index_exclusive)]

        if self.config.agent_task == "review" and script_ranges and ranges != script_ranges:
            record.status = "agent_conflict"
            record.reason = "agent review disagrees with script-selected range"
            return

        if self.config.agent_task == "review" and record.heading:
            record.reason = f"{record.reason}; agent-reviewed"
            return

        first_range = ranges[0]
        start_index = first_range["start_line"] - 1
        end_index = first_range["end_line_exclusive"] - 1
        record.heading = Heading(
            line_index=start_index,
            level=0,
            title=f"agent-selected range for {record.module.key}",
            normalized_title=record.module.normalized_title,
            line_text="",
            end_line_index_exclusive=end_index,
        )
        record.status = "agent_mapped"
        record.reason = "agent-selected line range"
