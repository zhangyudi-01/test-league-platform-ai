from __future__ import annotations

from pathlib import Path
from typing import Optional

from .sources import (
    DocumentSource,
    FENCE_RE,
    HEADING_RE,
    Heading,
    assign_heading_ancestors,
    assign_heading_ends,
    normalize_title,
    sha256_bytes,
    strip_closing_hashes,
)


class MarkdownSource(DocumentSource):
    kind = "markdown"

    def __init__(self, path: Path) -> None:
        super().__init__(path)
        self.canonical_bytes = self.raw_bytes
        self.canonical_sha256 = sha256_bytes(self.canonical_bytes)
        self.lines_bytes = self.raw_bytes.splitlines(keepends=True)
        self.lines_text = [line.decode("utf-8") for line in self.lines_bytes]
        self.headings = self._parse_headings()
        assign_heading_ends(self.headings, self.line_count)
        assign_heading_ancestors(self.headings)
        self.stats = {
            "source_kind": self.kind,
            "line_count": self.line_count,
            "heading_count": len(self.headings),
        }

    def _parse_headings(self) -> list[Heading]:
        headings: list[Heading] = []
        fence_marker: Optional[str] = None
        fence_length = 0

        for index, raw_line in enumerate(self.lines_text):
            line = raw_line.rstrip("\r\n")
            fence_match = FENCE_RE.match(line)
            if fence_match:
                marker = fence_match.group(1)
                marker_char = marker[0]
                if fence_marker is None:
                    fence_marker = marker_char
                    fence_length = len(marker)
                elif marker_char == fence_marker and len(marker) >= fence_length:
                    fence_marker = None
                    fence_length = 0
                continue

            if fence_marker is not None:
                continue

            match = HEADING_RE.match(line)
            if not match:
                continue

            hashes, raw_title = match.groups()
            title = strip_closing_hashes(raw_title)
            if not title:
                continue
            headings.append(
                Heading(
                    line_index=index,
                    level=len(hashes),
                    title=title,
                    normalized_title=normalize_title(title),
                    line_text=line,
                )
            )
        return headings
