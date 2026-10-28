from __future__ import annotations

import datetime as _dt
from pathlib import Path
from typing import Any

from .config import SplitConfig
from .sources import SplitError, extract_link_inventory, json_dump, path_str, read_json, sha256_bytes
from .source_factory import load_source


def validate_manifest(manifest_path: Path) -> tuple[int, Path]:
    manifest_path = manifest_path.resolve()
    manifest = read_json(manifest_path)
    source_info = manifest["source"]
    source = load_source(Path(source_info["path"]), source_info.get("kind", "auto"), source_info.get("docx_options", {}))
    failures: list[str] = []
    warnings: list[str] = []

    if source.raw_sha256 != source_info.get("raw_sha256", source_info.get("sha256")):
        failures.append("source raw SHA256 changed since split manifest was created")
    if source.canonical_sha256 != source_info.get("canonical_sha256", source_info.get("sha256")):
        failures.append("source canonical SHA256 changed since split manifest was created")

    ranges: list[tuple[int, int, str]] = []
    for output in manifest.get("outputs", []):
        output_path = Path(output["output_path"])
        if not output_path.exists():
            failures.append(f"missing output: {output_path}")
            continue
        data = output_path.read_bytes()
        source_range = output["source_range"]
        expected = source.slice_bytes(source_range["start_line_index"], source_range["end_line_index_exclusive"])
        if data != expected:
            failures.append(f"output does not exactly match canonical source slice: {output_path}")
        if sha256_bytes(data) != output["output_sha256"]:
            failures.append(f"output SHA256 changed: {output_path}")
        if extract_link_inventory(expected.decode("utf-8")) != extract_link_inventory(data.decode("utf-8")):
            failures.append(f"link/image inventory mismatch: {output_path}")
        for asset in output.get("assets", []):
            asset_path = Path(asset["output_path"])
            if not asset_path.exists():
                failures.append(f"missing asset: {asset_path}")
            elif sha256_bytes(asset_path.read_bytes()) != asset["sha256"]:
                failures.append(f"asset SHA256 changed: {asset_path}")
        if not data:
            warnings.append(f"empty output: {output_path}")
        ranges.append((source_range["start_line_index"], source_range["end_line_index_exclusive"], output["module_id"]))

    if manifest.get("write_scope") == "leaf":
        sorted_ranges = sorted(ranges)
        for left, right in zip(sorted_ranges, sorted_ranges[1:]):
            if left[1] > right[0]:
                failures.append(f"overlapping leaf ranges: {left[2]} and {right[2]}")

    report = {
        "manifest": path_str(manifest_path),
        "checked_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "failure_count": len(failures),
        "warning_count": len(warnings),
        "failures": failures,
        "warnings": warnings,
    }
    report_path = manifest_path.parent / "validation-report.json"
    json_dump(report_path, report)
    return (1 if failures else 0), report_path
