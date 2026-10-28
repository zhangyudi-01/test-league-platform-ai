from __future__ import annotations

import dataclasses
from typing import Any, Optional

from .modules import ModuleNode, ModuleTree
from .sources import DocumentSource, Heading, ScopeResolver, extract_link_inventory, path_str, sha256_bytes


@dataclasses.dataclass
class MatchRecord:
    module: ModuleNode
    status: str
    reason: str
    heading: Optional[Heading] = None
    candidates: list[Heading] = dataclasses.field(default_factory=list)
    agent_decisions: list[dict[str, Any]] = dataclasses.field(default_factory=list)

    @property
    def has_range(self) -> bool:
        return self.heading is not None or self.status == "agent_mapped"


class DeterministicMapper:
    def __init__(self, source: DocumentSource, modules: ModuleTree, scope_resolver: ScopeResolver) -> None:
        self.source = source
        self.modules = modules
        self.scope_resolver = scope_resolver
        self.scoped_headings = scope_resolver.headings_in_scope()

    def map_all(self) -> list[MatchRecord]:
        return [self._map_node(node) for node in self.modules.sorted_nodes()]

    def _map_node(self, node: ModuleNode) -> MatchRecord:
        candidates = [heading for heading in self.scoped_headings if heading.normalized_title == node.normalized_title]
        if not candidates:
            return MatchRecord(module=node, status="unmapped", reason="no heading with matching normalized title")

        module_ancestors = self.modules.ancestor_titles(node)
        exact: list[Heading] = []
        for heading in candidates:
            scope_range = self.scope_resolver.scope_for_heading(heading)
            scope_heading = scope_range.scope_heading if scope_range else None
            heading_ancestors = self.source.relative_ancestors(heading, scope_heading)
            source_depth = len(heading_ancestors) + 1
            if source_depth == node.depth and heading_ancestors == module_ancestors:
                exact.append(heading)

        if len(exact) == 1:
            return MatchRecord(module=node, status="mapped", reason="title, depth, and ancestor path matched", heading=exact[0], candidates=candidates)
        if len(exact) > 1:
            return MatchRecord(module=node, status="ambiguous", reason="multiple exact heading matches", candidates=exact)

        if len(candidates) == 1:
            return MatchRecord(module=node, status="mapped", reason="single title match; depth/ancestor mismatch accepted", heading=candidates[0], candidates=candidates)

        return MatchRecord(module=node, status="ambiguous", reason="multiple title matches; no exact ancestor match", candidates=candidates)


def range_dict(start_index: int, end_index: int) -> dict[str, int]:
    return {
        "start_line_index": start_index,
        "end_line_index_exclusive": end_index,
        "start_line": start_index + 1,
        "end_line": end_index,
    }


def heading_to_dict(heading: Heading, source: DocumentSource, scope_resolver: ScopeResolver) -> dict[str, Any]:
    scope_range = scope_resolver.scope_for_heading(heading)
    return {
        "line": heading.start_line,
        "line_index": heading.line_index,
        "level": heading.level,
        "title": heading.title,
        "normalized_title": heading.normalized_title,
        "end_line": heading.end_line,
        "end_line_index_exclusive": heading.end_line_index_exclusive,
        "relative_ancestors": source.relative_ancestors(heading, scope_range.scope_heading if scope_range else None),
        "source_info": heading.source_info,
    }


def record_to_plan_dict(record: MatchRecord, source: DocumentSource, modules: ModuleTree, scope_resolver: ScopeResolver, attachments: Any) -> dict[str, Any]:
    module = record.module
    result: dict[str, Any] = {
        "module_id": module.key,
        "id_part": module.id_part,
        "prefix": module.prefix,
        "title": module.title,
        "normalized_title": module.normalized_title,
        "path": path_str(module.path),
        "parent_id": module.parent_key,
        "depth": module.depth,
        "is_leaf": module.is_leaf,
        "ancestor_titles": [ancestor.title for ancestor in modules.ancestors(module)],
        "status": record.status,
        "reason": record.reason,
        "candidates": [heading_to_dict(heading, source, scope_resolver) for heading in record.candidates[:20]],
        "agent_decisions": record.agent_decisions,
    }
    if record.heading:
        text = source.slice_text(record.heading.line_index, record.heading.end_line_index_exclusive)
        result["heading"] = heading_to_dict(record.heading, source, scope_resolver)
        result["range"] = range_dict(record.heading.line_index, record.heading.end_line_index_exclusive)
        direct_start, direct_end = source.direct_range_for(record.heading)
        if source.has_body_content(direct_start, direct_end):
            direct_text = source.slice_text(direct_start, direct_end)
            result["direct_body_range"] = range_dict(direct_start, direct_end)
            result["direct_body_sha256"] = sha256_bytes(source.slice_bytes(direct_start, direct_end))
            result["direct_link_inventory"] = extract_link_inventory(direct_text)
        result["source_slice_sha256"] = sha256_bytes(source.slice_bytes(record.heading.line_index, record.heading.end_line_index_exclusive))
        result["link_inventory"] = extract_link_inventory(text)
        result["attachment_candidates"] = attachments.candidates_for(module, text) if attachments else []
        result["source_assets"] = source.assets_for_text(text)
    return result


def summarize_plan(plan_modules: list[dict[str, Any]]) -> dict[str, int]:
    counts = {"total": len(plan_modules), "mapped": 0, "agent_mapped": 0, "ambiguous": 0, "unmapped": 0, "agent_conflict": 0}
    for module in plan_modules:
        status = module["status"]
        counts[status] = counts.get(status, 0) + 1
    return counts
