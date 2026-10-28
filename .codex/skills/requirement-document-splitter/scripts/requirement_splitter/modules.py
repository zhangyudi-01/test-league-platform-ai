from __future__ import annotations

import dataclasses
import re
from pathlib import Path
from typing import Optional

from .sources import SplitError, normalize_title


@dataclasses.dataclass
class ModuleNode:
    prefix: str
    id_part: str
    title: str
    normalized_title: str
    path: Path
    parent_key: Optional[str]
    children: list[str] = dataclasses.field(default_factory=list)

    @property
    def key(self) -> str:
        return f"{self.prefix}-{self.id_part}"

    @property
    def depth(self) -> int:
        return len(self.id_part.split("-"))

    @property
    def is_leaf(self) -> bool:
        return not self.children


class ModuleTree:
    def __init__(self, root: Path, pattern: str) -> None:
        self.root = root.resolve()
        self.pattern = re.compile(pattern)
        self.nodes = self._scan()
        self._assign_children()

    def _scan(self) -> dict[str, ModuleNode]:
        if not self.root.exists():
            raise SplitError(f"Modules root does not exist: {self.root}")

        nodes: dict[str, ModuleNode] = {}
        for path in sorted((p for p in self.root.rglob("*") if p.is_dir()), key=lambda p: str(p)):
            match = self.pattern.match(path.name)
            if not match:
                continue
            prefix = match.group("prefix")
            id_part = match.group("id")
            title = match.group("title")
            parent_key = None
            if "-" in id_part:
                parent_id = "-".join(id_part.split("-")[:-1])
                parent_key = f"{prefix}-{parent_id}"
            node = ModuleNode(
                prefix=prefix,
                id_part=id_part,
                title=title,
                normalized_title=normalize_title(title),
                path=path.resolve(),
                parent_key=parent_key,
            )
            if node.key in nodes:
                raise SplitError(f"Duplicate module id {node.key}: {nodes[node.key].path} and {path}")
            nodes[node.key] = node
        if not nodes:
            raise SplitError(f"No module directories found under: {self.root}")
        return nodes

    def _assign_children(self) -> None:
        for node in self.nodes.values():
            if node.parent_key and node.parent_key in self.nodes:
                self.nodes[node.parent_key].children.append(node.key)
        for node in self.nodes.values():
            node.children.sort(key=self._sort_key_for_key)

    def _sort_key_for_key(self, key: str) -> tuple[int, ...]:
        id_part = key.split("-", 1)[1]
        return tuple(int(part) for part in id_part.split("-"))

    def sorted_nodes(self) -> list[ModuleNode]:
        return sorted(self.nodes.values(), key=lambda node: tuple(int(part) for part in node.id_part.split("-")))

    def ancestors(self, node: ModuleNode) -> list[ModuleNode]:
        result: list[ModuleNode] = []
        current = node
        while current.parent_key and current.parent_key in self.nodes:
            parent = self.nodes[current.parent_key]
            result.append(parent)
            current = parent
        return list(reversed(result))

    def ancestor_titles(self, node: ModuleNode) -> list[str]:
        return [ancestor.normalized_title for ancestor in self.ancestors(node)]
