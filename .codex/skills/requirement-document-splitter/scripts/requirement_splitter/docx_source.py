from __future__ import annotations

import posixpath
import re
import zipfile
from pathlib import Path
from typing import Any, Optional
from xml.etree import ElementTree as ET

from .sources import (
    DocumentSource,
    Heading,
    SplitError,
    assign_heading_ancestors,
    assign_heading_ends,
    markdown_escape_table_cell,
    normalize_title,
    sha256_bytes,
)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
A_NS = "http://schemas.openxmlformats.org/drawingml/2006/main"
WP_NS = "http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"

NS = {
    "w": W_NS,
    "r": R_NS,
    "a": A_NS,
    "wp": WP_NS,
    "rel": REL_NS,
}

DEFAULT_HEADING_STYLE_MAP = {
    "dingding-heading1": 1,
    "dingding-heading2": 2,
    "dingding-heading3": 3,
    "dingding-heading4": 4,
    "dingding-heading5": 5,
    "dingding-heading6": 6,
    "Heading1": 1,
    "Heading2": 2,
    "Heading3": 3,
    "Heading4": 4,
    "Heading5": 5,
    "Heading6": 6,
    "heading 1": 1,
    "heading 2": 2,
    "heading 3": 3,
    "heading 4": 4,
    "heading 5": 5,
    "heading 6": 6,
    "标题 1": 1,
    "标题 2": 2,
    "标题 3": 3,
    "标题 4": 4,
    "标题 5": 5,
    "标题 6": 6,
}


class DocxSource(DocumentSource):
    kind = "docx"

    def __init__(self, path: Path, options: Optional[dict[str, Any]] = None) -> None:
        super().__init__(path)
        self.options = options or {}
        self.heading_style_map = dict(DEFAULT_HEADING_STYLE_MAP)
        self.heading_style_map.update(self.options.get("heading_style_map") or {})
        self.ignore_toc = bool(self.options.get("ignore_toc", True))
        self.asset_dir_name = self.options.get("asset_dir_name") or "assets"
        self.table_format = self.options.get("table_format") or "markdown"
        self.relationships: dict[str, dict[str, str]] = {}
        self.style_names: dict[str, str] = {}
        self.media: dict[str, bytes] = {}
        self.generated_lines: list[str] = []
        self.stats = {
            "source_kind": self.kind,
            "paragraph_count": 0,
            "non_empty_paragraph_count": 0,
            "table_count": 0,
            "drawing_count": 0,
            "image_count": 0,
            "external_link_count": 0,
            "ignored_toc_paragraph_count": 0,
            "heading_count_by_level": {},
            "warnings": self.warnings,
        }
        self._load_docx()

    def _load_docx(self) -> None:
        with zipfile.ZipFile(self.path) as zf:
            names = set(zf.namelist())
            if "word/document.xml" not in names:
                raise SplitError(f"DOCX missing word/document.xml: {self.path}")
            self.relationships = self._read_relationships(zf)
            self.style_names = self._read_styles(zf)
            self.media = {name: zf.read(name) for name in names if name.startswith("word/media/")}
            document = ET.fromstring(zf.read("word/document.xml"))

        body = document.find("w:body", NS)
        if body is None:
            raise SplitError(f"DOCX missing w:body: {self.path}")

        for child in list(body):
            if child.tag == f"{{{W_NS}}}p":
                self._emit_paragraph(child)
            elif child.tag == f"{{{W_NS}}}tbl":
                self._emit_table(child)

        text = "\n".join(self.generated_lines)
        if text and not text.endswith("\n"):
            text += "\n"
        self.canonical_bytes = text.encode("utf-8")
        self.canonical_sha256 = sha256_bytes(self.canonical_bytes)
        self.lines_bytes = self.canonical_bytes.splitlines(keepends=True)
        self.lines_text = [line.decode("utf-8") for line in self.lines_bytes]
        assign_heading_ends(self.headings, self.line_count)
        assign_heading_ancestors(self.headings)
        self.stats["line_count"] = self.line_count
        self.stats["heading_count"] = len(self.headings)
        self.stats["media_file_count"] = len(self.media)

    def _read_relationships(self, zf: zipfile.ZipFile) -> dict[str, dict[str, str]]:
        rels_path = "word/_rels/document.xml.rels"
        if rels_path not in zf.namelist():
            return {}
        root = ET.fromstring(zf.read(rels_path))
        rels: dict[str, dict[str, str]] = {}
        external_count = 0
        for rel in root.findall("rel:Relationship", NS):
            rel_id = rel.attrib.get("Id")
            if not rel_id:
                continue
            target = rel.attrib.get("Target", "")
            mode = rel.attrib.get("TargetMode", "")
            rel_type = rel.attrib.get("Type", "")
            rels[rel_id] = {"target": target, "mode": mode, "type": rel_type}
            if mode == "External":
                external_count += 1
        self.stats["external_link_count"] = external_count
        return rels

    def _read_styles(self, zf: zipfile.ZipFile) -> dict[str, str]:
        styles_path = "word/styles.xml"
        if styles_path not in zf.namelist():
            return {}
        root = ET.fromstring(zf.read(styles_path))
        styles: dict[str, str] = {}
        for style in root.findall("w:style", NS):
            style_id = style.attrib.get(f"{{{W_NS}}}styleId")
            if not style_id:
                continue
            name = style.find("w:name", NS)
            styles[style_id] = name.attrib.get(f"{{{W_NS}}}val", style_id) if name is not None else style_id
        return styles

    def _paragraph_style(self, paragraph: ET.Element) -> tuple[str, str]:
        style = paragraph.find("w:pPr/w:pStyle", NS)
        style_id = style.attrib.get(f"{{{W_NS}}}val", "") if style is not None else ""
        return style_id, self.style_names.get(style_id, style_id)

    def _heading_level(self, style_id: str, style_name: str) -> Optional[int]:
        for key in (style_id, style_name):
            if key in self.heading_style_map:
                return int(self.heading_style_map[key])
        for key in (style_id, style_name):
            match = re.search(r"(?:heading|标题)\s*([1-6])", key, re.I)
            if match:
                return int(match.group(1))
        return None

    def _is_toc_paragraph(self, paragraph: ET.Element, style_id: str, style_name: str) -> bool:
        if not self.ignore_toc:
            return False
        if re.fullmatch(r"TOC\d+", style_id or "", re.I) or re.fullmatch(r"TOC\d+", style_name or "", re.I):
            return True
        instr_text = "".join((node.text or "") for node in paragraph.findall(".//w:instrText", NS))
        return "TOC" in instr_text.upper()

    def _emit_paragraph(self, paragraph: ET.Element) -> None:
        self.stats["paragraph_count"] += 1
        style_id, style_name = self._paragraph_style(paragraph)
        if self._is_toc_paragraph(paragraph, style_id, style_name):
            self.stats["ignored_toc_paragraph_count"] += 1
            return

        text = self._paragraph_markdown(paragraph).strip()
        if not text:
            return
        self.stats["non_empty_paragraph_count"] += 1
        heading_level = self._heading_level(style_id, style_name)
        if heading_level:
            line = f"{'#' * heading_level} {text}"
            line_index = self._append_block([line])
            heading = Heading(
                line_index=line_index,
                level=heading_level,
                title=text,
                normalized_title=normalize_title(text),
                line_text=line,
                source_info={"style_id": style_id, "style_name": style_name, "paragraph_index": self.stats["paragraph_count"]},
            )
            self.headings.append(heading)
            by_level = self.stats["heading_count_by_level"]
            by_level[str(heading_level)] = by_level.get(str(heading_level), 0) + 1
        else:
            self._append_block([text])

    def _append_block(self, lines: list[str]) -> int:
        if self.generated_lines and self.generated_lines[-1] != "":
            self.generated_lines.append("")
        start = len(self.generated_lines)
        self.generated_lines.extend(lines)
        self.generated_lines.append("")
        return start

    def _paragraph_markdown(self, paragraph: ET.Element) -> str:
        parts: list[str] = []
        for child in list(paragraph):
            if child.tag == f"{{{W_NS}}}hyperlink":
                parts.append(self._hyperlink_text(child))
            else:
                parts.append(self._inline_text(child))
        return "".join(parts)

    def _hyperlink_text(self, element: ET.Element) -> str:
        text = "".join(self._inline_text(child) for child in list(element)).strip()
        if not text:
            return ""
        rel_id = element.attrib.get(f"{{{R_NS}}}id")
        anchor = element.attrib.get(f"{{{W_NS}}}anchor")
        if rel_id and rel_id in self.relationships:
            target = self.relationships[rel_id]["target"]
            return f"[{text}]({target})"
        if anchor:
            return f"[{text}](#{anchor})"
        return text

    def _inline_text(self, element: ET.Element) -> str:
        if element.tag == f"{{{W_NS}}}t":
            return element.text or ""
        if element.tag == f"{{{W_NS}}}tab":
            return "\t"
        if element.tag in {f"{{{W_NS}}}br", f"{{{W_NS}}}cr"}:
            return "\n"
        if element.tag == f"{{{W_NS}}}drawing":
            return self._drawing_markdown(element)
        return "".join(self._inline_text(child) for child in list(element))

    def _drawing_markdown(self, drawing: ET.Element) -> str:
        self.stats["drawing_count"] += 1
        blip = drawing.find(".//a:blip", NS)
        if blip is None:
            return ""
        rel_id = blip.attrib.get(f"{{{R_NS}}}embed") or blip.attrib.get(f"{{{R_NS}}}link")
        if not rel_id or rel_id not in self.relationships:
            self.warnings.append(f"Unresolved drawing relationship: {rel_id}")
            return ""
        target = self.relationships[rel_id]["target"]
        media_path = posixpath.normpath(posixpath.join("word", target)) if not target.startswith("word/") else target
        data = self.media.get(media_path)
        if data is None:
            self.warnings.append(f"Missing media target: {media_path}")
            return ""
        sha8 = sha256_bytes(data)[:8]
        source_name = posixpath.basename(media_path)
        output_name = f"{Path(source_name).stem}-{sha8}{Path(source_name).suffix.lower()}"
        relative_path = f"{self.asset_dir_name}/{output_name}"
        self.assets[relative_path] = {
            "relative_path": relative_path,
            "source_name": source_name,
            "source_path": media_path,
            "sha256": sha256_bytes(data),
            "size_bytes": len(data),
            "data": data,
        }
        self.stats["image_count"] = len(self.assets)
        alt = source_name
        doc_pr = drawing.find(".//wp:docPr", NS)
        if doc_pr is not None:
            alt = doc_pr.attrib.get("descr") or doc_pr.attrib.get("title") or doc_pr.attrib.get("name") or source_name
        return f"![{alt}]({relative_path})"

    def _emit_table(self, table: ET.Element) -> None:
        self.stats["table_count"] += 1
        rows = []
        max_cols = 0
        merged = False
        for tr in table.findall("w:tr", NS):
            cells = []
            for tc in tr.findall("w:tc", NS):
                if tc.find(".//w:gridSpan", NS) is not None or tc.find(".//w:vMerge", NS) is not None:
                    merged = True
                text = self._cell_text(tc)
                cells.append(markdown_escape_table_cell(text))
            max_cols = max(max_cols, len(cells))
            rows.append(cells)
        if not rows:
            return
        if merged:
            self.warnings.append(f"Table {self.stats['table_count']} contains merged cells; Markdown output preserves text but not visual merges.")
        normalized_rows = [row + [""] * (max_cols - len(row)) for row in rows]
        lines = []
        header = normalized_rows[0]
        lines.append("| " + " | ".join(header) + " |")
        lines.append("|" + "|".join(["---"] * max_cols) + "|")
        for row in normalized_rows[1:]:
            lines.append("| " + " | ".join(row) + " |")
        self._append_block(lines)

    def _cell_text(self, cell: ET.Element) -> str:
        pieces = []
        for child in list(cell):
            if child.tag == f"{{{W_NS}}}p":
                text = self._paragraph_markdown(child).strip()
                if text:
                    pieces.append(text)
            elif child.tag == f"{{{W_NS}}}tbl":
                pieces.append("[嵌套表格]")
                self.warnings.append("Nested table found; represented as placeholder text.")
        return "\n".join(pieces)
