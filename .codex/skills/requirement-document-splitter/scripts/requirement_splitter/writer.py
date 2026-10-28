from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from .config import SplitConfig
from .sources import DocumentSource, SplitError, extract_link_inventory, json_dump, path_str, sha256_bytes


def should_write_module(module_entry: dict[str, Any], write_scope: str) -> bool:
    if "range" not in module_entry:
        return False
    if write_scope == "all":
        return True
    if write_scope == "leaf":
        return bool(module_entry.get("is_leaf"))
    if write_scope == "direct":
        return bool(module_entry.get("is_leaf")) or bool(module_entry.get("direct_body_range"))
    raise SplitError(f"Unsupported write scope: {write_scope}")


def write_coverage_tsv(path: Path, plan: dict[str, Any], written_entries: Optional[list[dict[str, Any]]] = None) -> None:
    written_entries = written_entries or []
    rows = ["status\tstart_line\tend_line\tmodule_id\tnote"]
    written_ranges = []
    for entry in written_entries:
        source_range = entry["source_range"]
        written_ranges.append((source_range["start_line_index"], source_range["end_line_index_exclusive"], entry["module_id"]))

    parent_ranges = []
    for module in plan["modules"]:
        if "range" not in module:
            continue
        if any(module["module_id"] == entry["module_id"] for entry in written_entries):
            continue
        parent_ranges.append((module["range"]["start_line_index"], module["range"]["end_line_index_exclusive"], module["module_id"]))

    def classify(index: int) -> tuple[str, str]:
        for start, end, module_id in written_ranges:
            if start <= index < end:
                return "assigned", module_id
        containing = [(end - start, module_id) for start, end, module_id in parent_ranges if start <= index < end]
        if containing:
            containing.sort()
            return "parent-only", containing[0][1]
        return "unmapped", ""

    for scope_range in plan["scope"]["ranges"]:
        start = scope_range["start_line_index"]
        end = scope_range["end_line_index_exclusive"]
        if start >= end:
            continue
        current_status, current_module = classify(start)
        run_start = start
        for index in range(start + 1, end):
            status, module_id = classify(index)
            if (status, module_id) != (current_status, current_module):
                rows.append(f"{current_status}\t{run_start + 1}\t{index}\t{current_module}\t")
                run_start = index
                current_status, current_module = status, module_id
        rows.append(f"{current_status}\t{run_start + 1}\t{end}\t{current_module}\t")

    path.write_text("\n".join(rows) + "\n", encoding="utf-8", newline="\n")


def write_split(plan: dict[str, Any], source: DocumentSource, config: SplitConfig, overwrite: bool, allow_unmapped: bool, allow_empty: bool) -> dict[str, Any]:
    run_dir = Path(plan["run_dir"])
    plan_path = run_dir / "split-plan.json"
    json_dump(plan_path, plan)

    leaf_unmapped = [module for module in plan["modules"] if module.get("is_leaf") and "range" not in module]
    if leaf_unmapped and not allow_unmapped:
        names = ", ".join(module["module_id"] for module in leaf_unmapped)
        raise SplitError(f"Leaf modules are unmapped; refusing to split without --allow-unmapped: {names}")

    output_entries: list[dict[str, Any]] = []
    for module in plan["modules"]:
        if not should_write_module(module, config.write_scope):
            continue
        output_range = module["range"]
        if config.write_scope == "direct" and module.get("direct_body_range"):
            output_range = module["direct_body_range"]
        data = source.slice_bytes(output_range["start_line_index"], output_range["end_line_index_exclusive"])
        if not data and not allow_empty:
            raise SplitError(f"Refusing to write empty output for {module['module_id']}")
        output_path = Path(module["path"]) / config.output_name
        if output_path.exists():
            existing = output_path.read_bytes()
            if existing != data and not overwrite:
                raise SplitError(f"Output exists with different content; use --overwrite: {output_path}")
            status = "unchanged" if existing == data else "overwritten"
        else:
            status = "created"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_bytes(data)
        output_text = data.decode("utf-8")
        copied_assets = source.copy_assets_for_text(output_text, output_path.parent)
        output_entries.append(
            {
                "module_id": module["module_id"],
                "title": module["title"],
                "module_path": module["path"],
                "output_path": path_str(output_path),
                "write_status": status,
                "source_range": output_range,
                "source_slice_sha256": sha256_bytes(data),
                "output_sha256": sha256_bytes(output_path.read_bytes()),
                "link_inventory": extract_link_inventory(output_text),
                "attachment_candidates": module.get("attachment_candidates", []),
                "assets": copied_assets,
            }
        )

    manifest = {
        "schema_version": 2,
        "created_at": plan["created_at"],
        "source": plan["source"],
        "modules_root": plan["modules_root"],
        "run_dir": plan["run_dir"],
        "plan_path": path_str(plan_path),
        "write_scope": config.write_scope,
        "output_name": config.output_name,
        "outputs": output_entries,
        "summary": {
            "planned_modules": len(plan["modules"]),
            "written_outputs": len(output_entries),
            "unmapped_leaf_modules": [module["module_id"] for module in leaf_unmapped],
        },
    }
    manifest_path = run_dir / "split-manifest.json"
    coverage_path = run_dir / "coverage.tsv"
    json_dump(manifest_path, manifest)
    write_coverage_tsv(coverage_path, plan, output_entries)
    return {"manifest": manifest, "manifest_path": manifest_path, "coverage_path": coverage_path, "plan_path": plan_path}
