from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .modules import ModuleNode
from .sources import normalize_title, path_str, sha256_bytes


class AttachmentIndex:
    def __init__(self, root: Optional[Path]) -> None:
        self.root = root.resolve() if root else None
        self.files = self._scan()

    def _scan(self) -> list[dict[str, Any]]:
        if self.root is None or not self.root.exists():
            return []
        result: list[dict[str, Any]] = []
        for path in sorted((p for p in self.root.rglob("*") if p.is_file()), key=lambda p: str(p)):
            data = path.read_bytes()
            result.append(
                {
                    "path": path_str(path),
                    "name": path.name,
                    "stem": path.stem,
                    "sha256": sha256_bytes(data),
                    "size_bytes": len(data),
                    "normalized_stem": normalize_title(path.stem),
                }
            )
        return result

    def candidates_for(self, module: ModuleNode, text: str) -> list[dict[str, Any]]:
        normalized_text = normalize_title(text)
        candidates = []
        for item in self.files:
            stem = item["normalized_stem"]
            if module.normalized_title and module.normalized_title in stem:
                candidates.append(item)
            elif stem and stem in normalized_text:
                candidates.append(item)
        return candidates
