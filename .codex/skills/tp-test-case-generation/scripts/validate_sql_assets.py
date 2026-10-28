#!/usr/bin/env python3
"""Validate reusable SQL assets with static checks and MySQL EXPLAIN."""
from __future__ import annotations

import argparse
from pathlib import Path

from common import WorkflowError, module_paths
from sql_assets import SqlAssetError, validate_assets


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate module SQL assets against MySQL.")
    parser.add_argument("module_dir", type=Path)
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--preanalysis-dir", type=Path)
    parser.add_argument("--case-output-dir", type=Path)
    parser.add_argument("--db-config", type=Path)
    parser.add_argument("--sql-id", action="append", dest="sql_ids")
    args = parser.parse_args()
    try:
        _, _, _, case_dir = module_paths(
            args.module_dir, args.preanalysis_dir, args.manifest, args.case_output_dir
        )
        report = validate_assets(
            case_dir,
            args.module_dir,
            db_config_path=args.db_config,
            required_sql_ids=args.sql_ids,
        )
        print("STATUS=validated")
        print(f"SQL_COUNT={len(report['assets'])}")
        print(f"VALIDATION_REPORT={case_dir / 'sql' / 'validation.json'}")
        return 0
    except (WorkflowError, SqlAssetError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
