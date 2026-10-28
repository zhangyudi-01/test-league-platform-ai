from __future__ import annotations

from pathlib import Path
from typing import Any

from .docx_source import DocxSource
from .markdown_source import MarkdownSource
from .sources import DocumentSource, SplitError


def load_source(path: Path, source_format: str, docx_options: dict[str, Any] | None = None) -> DocumentSource:
    source_format = (source_format or "auto").lower()
    if source_format == "auto":
        source_format = "docx" if path.suffix.lower() == ".docx" else "markdown"
    if source_format == "markdown":
        return MarkdownSource(path)
    if source_format == "docx":
        return DocxSource(path, docx_options or {})
    raise SplitError("source_format must be one of: auto, markdown, docx")
