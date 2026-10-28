from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Optional


# PRD exports may indent headings by four spaces while nesting them under a
# list item; accept that export indentation without changing source slices.
HEADING_RE = re.compile(r"^[ \t]{0,4}(#{1,6})(?:[ \t]+|$)(.*?)[ \t]*$")
FENCE_RE = re.compile(r"^[ \t]{0,3}(`{3,}|~{3,})")
IMAGE_RE = re.compile(r"!\[[^\]]*\]\(([^)]+)\)")
LINK_RE = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


class SplitError(RuntimeError):
    """Raised for recoverable user-facing orchestration errors."""


@dataclasses.dataclass
class Heading:
    line_index: int
    level: int
    title: str
    normalized_title: str
    line_text: str
    end_line_index_exclusive: int = 0
    ancestors: list["Heading"] = dataclasses.field(default_factory=list)
    source_info: dict[str, Any] = dataclasses.field(default_factory=dict)

    @property
    def start_line(self) -> int:
        return self.line_index + 1

    @property
    def end_line(self) -> int:
        return self.end_line_index_exclusive


@dataclasses.dataclass
class ScopeRange:
    start_index: int
    end_index_exclusive: int
    scope_heading: Optional[Heading]
    stop_heading: Optional[Heading]

    def contains(self, start_index: int, end_index_exclusive: int) -> bool:
        return self.start_index <= start_index < end_index_exclusive <= self.end_index_exclusive


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalize_title(value: str) -> str:
    value = value.replace("﻿", "").replace(" ", " ")
    value = re.sub(r"\\([_`*\[\]()#+.!-])", r"\1", value)
    value = re.sub(r"^\s*(?:\d+|[一二三四五六七八九十百千万]+)[）).、．.\-]\s*", "", value)
    value = re.sub(r"[（(]\s*(?:增|新增|改|修改|删|删除|原|旧|新)\s*[）)]", "", value)
    value = re.sub(r"\s+", " ", value)
    return value.strip()


def strip_closing_hashes(title: str) -> str:
    return re.sub(r"[ \t]+#+[ \t]*$", "", title).strip()


def json_dump(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8", newline="\n")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def path_str(path: Path) -> str:
    return str(path.resolve())


def extract_link_inventory(text: str) -> dict[str, Any]:
    images = [match.group(0) for match in IMAGE_RE.finditer(text)]
    image_targets = [match.group(1) for match in IMAGE_RE.finditer(text)]
    links = [match.group(0) for match in LINK_RE.finditer(text)]
    link_targets = [match.group(1) for match in LINK_RE.finditer(text)]
    return {
        "image_count": len(images),
        "image_targets": image_targets,
        "images": images,
        "link_count": len(links),
        "link_targets": link_targets,
        "links": links,
    }


def markdown_escape_table_cell(value: str) -> str:
    value = value.replace("|", "\\|")
    value = re.sub(r"\s*\n\s*", "<br>", value.strip())
    return value


class DocumentSource:
    kind = "base"

    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.raw_bytes = self.path.read_bytes()
        self.raw_sha256 = sha256_bytes(self.raw_bytes)
        self.canonical_bytes = self.raw_bytes
        self.canonical_sha256 = sha256_bytes(self.canonical_bytes)
        self.lines_bytes: list[bytes] = []
        self.lines_text: list[str] = []
        self.headings: list[Heading] = []
        self.stats: dict[str, Any] = {}
        self.assets: dict[str, dict[str, Any]] = {}
        self.warnings: list[str] = []

    @property
    def line_count(self) -> int:
        return len(self.lines_bytes)

    @property
    def sha256(self) -> str:
        return self.raw_sha256

    def relative_ancestors(self, heading: Heading, scope_heading: Optional[Heading]) -> list[str]:
        if scope_heading is None:
            return [ancestor.normalized_title for ancestor in heading.ancestors]

        found_scope = False
        result: list[str] = []
        for ancestor in heading.ancestors:
            if ancestor.line_index == scope_heading.line_index:
                found_scope = True
                continue
            if found_scope:
                result.append(ancestor.normalized_title)
        return result

    def direct_range_for(self, heading: Heading) -> tuple[int, int]:
        if heading.level <= 0:
            return heading.line_index, heading.end_line_index_exclusive
        direct_end = heading.end_line_index_exclusive
        for later in self.headings:
            if later.line_index <= heading.line_index:
                continue
            if later.line_index >= heading.end_line_index_exclusive:
                break
            if later.level > heading.level:
                direct_end = later.line_index
                break
        return heading.line_index, direct_end

    def has_body_content(self, start_index: int, end_index_exclusive: int) -> bool:
        body = b"".join(self.lines_bytes[start_index + 1 : end_index_exclusive])
        return bool(body.decode("utf-8").strip())

    def slice_bytes(self, start_index: int, end_index_exclusive: int) -> bytes:
        return b"".join(self.lines_bytes[start_index:end_index_exclusive])

    def slice_text(self, start_index: int, end_index_exclusive: int) -> str:
        return self.slice_bytes(start_index, end_index_exclusive).decode("utf-8")

    def assets_for_text(self, text: str) -> list[dict[str, Any]]:
        result = []
        for target in IMAGE_RE.findall(text):
            normalized = target.replace("\\", "/")
            if normalized in self.assets:
                result.append(self.assets[normalized])
        return result

    def copy_assets_for_text(self, text: str, module_dir: Path) -> list[dict[str, Any]]:
        copied = []
        for asset in self.assets_for_text(text):
            relative_path = asset["relative_path"]
            output_path = module_dir / relative_path
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(asset["data"])
            copied.append(
                {
                    "relative_path": relative_path,
                    "output_path": path_str(output_path),
                    "sha256": asset["sha256"],
                    "source_name": asset.get("source_name"),
                    "size_bytes": asset.get("size_bytes"),
                }
            )
        return copied


def assign_heading_ends(headings: list[Heading], line_count: int) -> None:
    for index, heading in enumerate(headings):
        end = line_count
        for later in headings[index + 1 :]:
            if later.level <= heading.level:
                end = later.line_index
                break
        heading.end_line_index_exclusive = end


def assign_heading_ancestors(headings: list[Heading]) -> None:
    stack: list[Heading] = []
    for heading in headings:
        while stack and stack[-1].level >= heading.level:
            stack.pop()
        heading.ancestors = list(stack)
        stack.append(heading)


class ScopeResolver:
    def __init__(self, source: DocumentSource, scope_headings: list[str], stop_headings: list[str]) -> None:
        self.source = source
        self.scope_headings = [normalize_title(item) for item in scope_headings if item]
        self.stop_headings = [normalize_title(item) for item in stop_headings if item]
        self.ranges = self._resolve()

    def _resolve(self) -> list[ScopeRange]:
        if not self.scope_headings:
            return [self._range_from(None, 0, self.source.line_count)]

        ranges = []
        for title in self.scope_headings:
            matches = [heading for heading in self.source.headings if heading.normalized_title == title]
            if not matches:
                raise SplitError(f"Scope heading not found: {title}")
            for heading in matches:
                ranges.append(self._range_from(heading, heading.line_index + 1, heading.end_line_index_exclusive))
        ranges.sort(key=lambda item: (item.start_index, item.end_index_exclusive))
        for left, right in zip(ranges, ranges[1:]):
            if left.end_index_exclusive > right.start_index:
                raise SplitError(
                    f"Overlapping scope ranges: {left.start_index + 1}-{left.end_index_exclusive} and {right.start_index + 1}-{right.end_index_exclusive}"
                )
        return ranges

    def _range_from(self, scope_heading: Optional[Heading], start_index: int, natural_end: int) -> ScopeRange:
        stop = None
        end_index = natural_end
        if self.stop_headings:
            for heading in self.source.headings:
                if heading.line_index < start_index:
                    continue
                if heading.line_index >= natural_end:
                    break
                if heading.normalized_title in self.stop_headings:
                    stop = heading
                    end_index = heading.line_index
                    break
        return ScopeRange(start_index, end_index, scope_heading, stop)

    def contains(self, start_index: int, end_index_exclusive: int) -> bool:
        return any(scope_range.contains(start_index, end_index_exclusive) for scope_range in self.ranges)

    def headings_in_scope(self) -> list[Heading]:
        scoped = []
        for heading in self.source.headings:
            if any(scope_range.start_index <= heading.line_index < scope_range.end_index_exclusive for scope_range in self.ranges):
                scoped.append(heading)
        return scoped

    def scope_for_heading(self, heading: Heading) -> Optional[ScopeRange]:
        for scope_range in self.ranges:
            if scope_range.start_index <= heading.line_index < scope_range.end_index_exclusive:
                return scope_range
        return None

    def to_dict(self) -> dict[str, Any]:
        ranges = []
        for scope_range in self.ranges:
            ranges.append(
                {
                    "scope_heading": scope_range.scope_heading.title if scope_range.scope_heading else None,
                    "scope_heading_line": scope_range.scope_heading.start_line if scope_range.scope_heading else None,
                    "stop_heading": scope_range.stop_heading.title if scope_range.stop_heading else None,
                    "stop_heading_line": scope_range.stop_heading.start_line if scope_range.stop_heading else None,
                    "start_line_index": scope_range.start_index,
                    "end_line_index_exclusive": scope_range.end_index_exclusive,
                    "start_line": scope_range.start_index + 1,
                    "end_line": scope_range.end_index_exclusive,
                }
            )
        result: dict[str, Any] = {
            "scope_headings": self.scope_headings,
            "stop_headings": self.stop_headings,
            "ranges": ranges,
        }
        if len(ranges) == 1:
            result.update(ranges[0])
        return result
