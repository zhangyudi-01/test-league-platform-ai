#!/usr/bin/env python3
"""Manage reusable SQL assets and validate them against a MySQL database."""
from __future__ import annotations

import hashlib
import json
import os
import re
import tomllib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable


SQL_MANIFEST_NAME = "sql-manifest.json"
SQL_VALIDATION_NAME = "validation.json"
SQL_SCHEMA_VERSION = "tp-test-case-generation/sql-assets-v1"
SQL_VALIDATION_SCHEMA_VERSION = "tp-test-case-generation/sql-validation-v1"
SQL_ID_RE = re.compile(r"SQL-[A-Z0-9]+(?:-[A-Z0-9]+)*")
DC_ID_RE = re.compile(r"DC-\d{3}")
PARAMETER_RE = re.compile(r"[A-Z][A-Z0-9_]*")
SUPPORTED_STATEMENTS = {"SELECT", "INSERT", "UPDATE", "DELETE"}
TEXT_CONFIG_ALIASES = {
    "host": ("host", "hostname", "服务器地址", "数据库地址"),
    "port": ("port", "数据库端口", "端口"),
    "database": ("database", "dbname", "数据库", "数据库名"),
    "user": ("user", "username", "用户名", "数据库用户名"),
    "password": ("password", "passwd", "密码", "数据库密码"),
    "charset": ("charset", "字符集"),
    "connect_timeout": ("connect_timeout", "连接超时"),
}


class SqlAssetError(RuntimeError):
    """A SQL asset, configuration, or database validation is invalid."""


@dataclass(frozen=True)
class DatabaseConfig:
    path: Path
    host: str
    port: int
    database: str
    user: str
    password: str
    charset: str = "utf8mb4"
    connect_timeout: int = 10

    def connection_kwargs(self) -> dict[str, Any]:
        return {
            "host": self.host,
            "port": self.port,
            "database": self.database,
            "user": self.user,
            "password": self.password,
            "charset": self.charset,
            "connect_timeout": self.connect_timeout,
            "read_timeout": max(self.connect_timeout, 10),
            "write_timeout": max(self.connect_timeout, 10),
            "autocommit": False,
        }


@dataclass(frozen=True)
class SqlParameter:
    name: str
    description: str
    example: Any


@dataclass(frozen=True)
class SqlAsset:
    sql_id: str
    path: Path
    statement_type: str
    purpose: str
    data_closure_refs: tuple[str, ...]
    parameters: tuple[SqlParameter, ...]
    sql: str
    sha256: str


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    temporary.write_text(
        json.dumps(value, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(path)


def empty_manifest() -> dict[str, Any]:
    return {"schema_version": SQL_SCHEMA_VERSION, "assets": []}


def ensure_sql_workspace(case_dir: Path) -> Path:
    sql_dir = case_dir / "sql"
    sql_dir.mkdir(parents=True, exist_ok=True)
    manifest = sql_dir / SQL_MANIFEST_NAME
    if not manifest.exists():
        atomic_write_json(manifest, empty_manifest())
    return manifest


def _clean_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SqlAssetError(f"{label} must be a non-empty string")
    return value.strip()


def _ordered_unique_strings(value: Any, pattern: re.Pattern[str], label: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise SqlAssetError(f"{label} must be a non-empty JSON array")
    result: list[str] = []
    for item in value:
        text = _clean_text(item, label)
        if pattern.fullmatch(text) is None:
            raise SqlAssetError(f"{label} contains an invalid value: {text}")
        if text in result:
            raise SqlAssetError(f"{label} repeats a value: {text}")
        result.append(text)
    return tuple(result)


def _scan_sql(sql: str) -> tuple[str, list[str], int]:
    """Return comment-free SQL, named parameters, and statement separators.

    Parameters use ``:NAME`` outside strings and comments. MySQL ``::`` is not
    treated as a parameter prefix. The scanner is intentionally small because
    assets are constrained to one DML statement and no stored-program syntax.
    """
    code: list[str] = []
    params: list[str] = []
    separators = 0
    index = 0
    state = "code"
    quote = ""
    while index < len(sql):
        char = sql[index]
        next_char = sql[index + 1] if index + 1 < len(sql) else ""
        if state == "line-comment":
            if char in "\r\n":
                state = "code"
                code.append(char)
            index += 1
            continue
        if state == "block-comment":
            if char == "*" and next_char == "/":
                state = "code"
                code.append(" ")
                index += 2
            else:
                index += 1
            continue
        if state == "quote":
            code.append(char)
            if char == "\\" and index + 1 < len(sql):
                code.append(sql[index + 1])
                index += 2
                continue
            if char == quote:
                if index + 1 < len(sql) and sql[index + 1] == quote:
                    code.append(sql[index + 1])
                    index += 2
                    continue
                state = "code"
            index += 1
            continue
        if char == "-" and next_char == "-":
            state = "line-comment"
            index += 2
            continue
        if char == "#":
            state = "line-comment"
            index += 1
            continue
        if char == "/" and next_char == "*":
            state = "block-comment"
            index += 2
            continue
        if char in {"'", '"', "`"}:
            state = "quote"
            quote = char
            code.append(char)
            index += 1
            continue
        if char == ";":
            separators += 1
            code.append(char)
            index += 1
            continue
        if char == ":" and next_char != ":":
            match = re.match(r"[A-Z][A-Z0-9_]*", sql[index + 1 :])
            if match:
                name = match.group(0)
                params.append(name)
                code.append(":" + name)
                index += len(name) + 1
                continue
        code.append(char)
        index += 1
    if state in {"quote", "block-comment"}:
        raise SqlAssetError("SQL contains an unterminated quote or block comment")
    return "".join(code).strip(), params, separators


def _statement_type(code: str) -> str:
    normalized = code.strip().rstrip(";").strip()
    match = re.match(r"([A-Za-z]+)", normalized)
    if match is None:
        raise SqlAssetError("SQL file has no executable statement")
    statement_type = match.group(1).upper()
    if statement_type not in SUPPORTED_STATEMENTS:
        raise SqlAssetError(
            f"unsupported SQL statement {statement_type}; expected SELECT/INSERT/UPDATE/DELETE"
        )
    return statement_type


def _require_one_statement(code: str, separators: int) -> None:
    normalized = code.strip()
    if separators > 1 or (separators == 1 and not normalized.endswith(";")):
        raise SqlAssetError("each SQL asset must contain exactly one statement")


def _parse_parameters(value: Any, sql_id: str) -> tuple[SqlParameter, ...]:
    if not isinstance(value, dict):
        raise SqlAssetError(f"{sql_id} parameters must be a JSON object")
    result: list[SqlParameter] = []
    for name, details in value.items():
        if not isinstance(name, str) or PARAMETER_RE.fullmatch(name) is None:
            raise SqlAssetError(f"{sql_id} has invalid parameter name: {name}")
        if not isinstance(details, dict):
            raise SqlAssetError(f"{sql_id} parameter {name} must be an object")
        description = _clean_text(details.get("description"), f"{sql_id} parameter {name} description")
        if "example" not in details:
            raise SqlAssetError(f"{sql_id} parameter {name} must define an example")
        result.append(SqlParameter(name, description, details["example"]))
    return tuple(result)


def load_registry(case_dir: Path, *, require_files: bool = True) -> dict[str, SqlAsset]:
    manifest_path = case_dir / "sql" / SQL_MANIFEST_NAME
    if not manifest_path.is_file():
        raise SqlAssetError(f"SQL manifest is missing: {manifest_path}")
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SqlAssetError(f"cannot parse SQL manifest {manifest_path}: {exc}") from exc
    if not isinstance(raw, dict) or raw.get("schema_version") != SQL_SCHEMA_VERSION:
        raise SqlAssetError(f"SQL manifest schema_version must be {SQL_SCHEMA_VERSION}")
    rows = raw.get("assets")
    if not isinstance(rows, list):
        raise SqlAssetError("SQL manifest assets must be a JSON array")
    result: dict[str, SqlAsset] = {}
    registered_files: set[Path] = set()
    for position, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise SqlAssetError(f"SQL manifest asset {position} must be an object")
        sql_id = _clean_text(row.get("sql_id"), f"SQL asset {position} sql_id")
        if SQL_ID_RE.fullmatch(sql_id) is None:
            raise SqlAssetError(f"invalid SQL-ID: {sql_id}")
        if sql_id in result:
            raise SqlAssetError(f"duplicate SQL-ID: {sql_id}")
        filename = _clean_text(row.get("file"), f"{sql_id} file")
        if filename != f"{sql_id}.sql":
            raise SqlAssetError(f"{sql_id} file must be {sql_id}.sql")
        path = (manifest_path.parent / filename).resolve()
        try:
            path.relative_to(manifest_path.parent.resolve())
        except ValueError as exc:
            raise SqlAssetError(f"{sql_id} file escapes the SQL directory") from exc
        if require_files and not path.is_file():
            raise SqlAssetError(f"registered SQL file is missing: {path}")
        statement_type = _clean_text(row.get("statement_type"), f"{sql_id} statement_type").upper()
        if statement_type not in SUPPORTED_STATEMENTS:
            raise SqlAssetError(f"{sql_id} has unsupported statement_type: {statement_type}")
        purpose = _clean_text(row.get("purpose"), f"{sql_id} purpose")
        closure_refs = _ordered_unique_strings(
            row.get("data_closure_refs"), DC_ID_RE, f"{sql_id} data_closure_refs"
        )
        parameters = _parse_parameters(row.get("parameters", {}), sql_id)
        sql = path.read_text(encoding="utf-8-sig") if path.is_file() else ""
        code, occurrences, separators = _scan_sql(sql)
        _require_one_statement(code, separators)
        actual_type = _statement_type(code)
        if actual_type != statement_type:
            raise SqlAssetError(
                f"{sql_id} statement_type is {statement_type}, but SQL starts with {actual_type}"
            )
        declared = {item.name for item in parameters}
        used = set(occurrences)
        if declared != used:
            raise SqlAssetError(
                f"{sql_id} parameter mismatch; declared={sorted(declared)}, used={sorted(used)}"
            )
        comment_lines = [line.strip() for line in sql.splitlines() if line.strip().startswith(("--", "#"))]
        for name in sorted(used):
            if not any(re.search(rf"(?<![A-Z0-9_]):{re.escape(name)}(?![A-Z0-9_])", line) for line in comment_lines):
                raise SqlAssetError(
                    f"{sql_id} parameter :{name} must be explained in a -- or # comment"
                )
        digest = sha256_file(path) if path.is_file() else ""
        result[sql_id] = SqlAsset(
            sql_id,
            path,
            statement_type,
            purpose,
            closure_refs,
            parameters,
            sql,
            digest,
        )
        registered_files.add(path)
    if manifest_path.parent.is_dir():
        unregistered = sorted(
            path.name
            for path in manifest_path.parent.glob("*.sql")
            if path.resolve() not in registered_files
        )
        if unregistered:
            raise SqlAssetError(f"unregistered SQL files: {', '.join(unregistered)}")
    return result


def registry_manifest(case_dir: Path, registry: dict[str, SqlAsset] | None = None) -> dict[str, Any]:
    registry = registry if registry is not None else load_registry(case_dir)
    return {
        "schema_version": SQL_SCHEMA_VERSION,
        "manifest_file": f"sql/{SQL_MANIFEST_NAME}",
        "manifest_sha256": sha256_file(case_dir / "sql" / SQL_MANIFEST_NAME),
        "assets": [
            {
                "sql_id": asset.sql_id,
                "file": asset.path.relative_to(case_dir).as_posix(),
                "sha256": asset.sha256,
                "statement_type": asset.statement_type,
                "purpose": asset.purpose,
                "data_closure_refs": list(asset.data_closure_refs),
                "parameters": [item.name for item in asset.parameters],
            }
            for asset in registry.values()
        ],
    }


def _parse_text_config(path: Path) -> dict[str, Any]:
    values: dict[str, str] = {}
    aliases = {alias.lower(): target for target, names in TEXT_CONFIG_ALIASES.items() for alias in names}
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("#", ";")):
            continue
        match = re.match(r"^([^=：:]+?)\s*(?:=|：|:)\s*(.*)$", line)
        if match is None:
            continue
        key = aliases.get(match.group(1).strip().lower())
        if key is not None and key not in values:
            values[key] = match.group(2).strip().strip('"').strip("'")
    return values


def load_database_config(path: Path) -> DatabaseConfig:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise SqlAssetError(f"database config is missing: {resolved}")
    try:
        if resolved.suffix.lower() == ".toml":
            raw = tomllib.loads(resolved.read_text(encoding="utf-8-sig"))
            values = raw.get("database", raw) if isinstance(raw, dict) else {}
        else:
            values = _parse_text_config(resolved)
    except (OSError, UnicodeError, tomllib.TOMLDecodeError) as exc:
        raise SqlAssetError(f"cannot parse database config {resolved}: {exc}") from exc
    if not isinstance(values, dict):
        raise SqlAssetError(f"database config root must be an object: {resolved}")
    required = ("host", "port", "database", "user", "password")
    missing = [key for key in required if str(values.get(key, "")).strip() == ""]
    if missing:
        raise SqlAssetError(f"database config is missing keys: {', '.join(missing)}")
    try:
        port = int(values["port"])
        timeout = int(values.get("connect_timeout", 10))
    except (TypeError, ValueError) as exc:
        raise SqlAssetError("database port and connect_timeout must be integers") from exc
    if not 1 <= port <= 65535 or timeout <= 0:
        raise SqlAssetError("database port or connect_timeout is outside the valid range")
    return DatabaseConfig(
        path=resolved,
        host=str(values["host"]).strip(),
        port=port,
        database=str(values["database"]).strip(),
        user=str(values["user"]).strip(),
        password=str(values["password"]),
        charset=str(values.get("charset", "utf8mb4")).strip() or "utf8mb4",
        connect_timeout=timeout,
    )


def find_database_config(module_dir: Path, explicit: Path | None = None) -> Path:
    if explicit is not None:
        return explicit.expanduser().resolve()
    start = module_dir.expanduser().resolve()
    directories = (start, *start.parents)
    for name in ("database.toml", "config.txt"):
        for directory in directories:
            candidate = directory / name
            if candidate.is_file():
                return candidate.resolve()
    raise SqlAssetError(
        "database config not found; use --db-config or add database.toml/config.txt to a module ancestor"
    )


def _prepared_statement(asset: SqlAsset) -> tuple[str, list[Any]]:
    """Convert named asset parameters without touching SQL string literals."""
    examples = {item.name: item.example for item in asset.parameters}
    values: list[Any] = []
    code, _, _ = _scan_sql(asset.sql)
    output: list[str] = []
    index = 0
    state = "code"
    quote = ""
    while index < len(code):
        char = code[index]
        next_char = code[index + 1] if index + 1 < len(code) else ""
        if state == "quote":
            output.append(char)
            if char == "\\" and index + 1 < len(code):
                output.append(code[index + 1])
                index += 2
                continue
            if char == quote:
                if index + 1 < len(code) and code[index + 1] == quote:
                    output.append(code[index + 1])
                    index += 2
                    continue
                state = "code"
            index += 1
            continue
        if char in {"'", '"', "`"}:
            state = "quote"
            quote = char
            output.append(char)
            index += 1
            continue
        if char == ":" and next_char != ":":
            match = re.match(r"[A-Z][A-Z0-9_]*", code[index + 1 :])
            if match:
                name = match.group(0)
                if name not in examples:
                    raise SqlAssetError(f"SQL parameter :{name} has no example value")
                values.append(examples[name])
                output.append("%s")
                index += len(name) + 1
                continue
        output.append(char)
        index += 1
    prepared = "".join(output).rstrip().rstrip(";")
    return prepared, values


def _default_connect(config: DatabaseConfig):
    try:
        import pymysql
    except ModuleNotFoundError as exc:
        raise SqlAssetError("PyMySQL is required for database SQL validation") from exc
    return pymysql.connect(**config.connection_kwargs())


def validate_assets(
    case_dir: Path,
    module_dir: Path,
    *,
    db_config_path: Path | None = None,
    required_sql_ids: Iterable[str] | None = None,
    connect_fn: Callable[[DatabaseConfig], Any] | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    registry = load_registry(case_dir)
    required = list(dict.fromkeys(required_sql_ids if required_sql_ids is not None else registry))
    unknown = sorted(set(required) - set(registry))
    if unknown:
        raise SqlAssetError(f"unknown SQL Refs: {', '.join(unknown)}")
    report: dict[str, Any] = {
        "schema_version": SQL_VALIDATION_SCHEMA_VERSION,
        "validated_at": utc_now(),
        "method": "MYSQL_EXPLAIN",
        "registry": registry_manifest(case_dir, registry),
        "database_config": None,
        "database_config_sha256": None,
        "server_version": None,
        "assets": [],
        "status": "validated",
    }
    if not required:
        if write_report:
            atomic_write_json(case_dir / "sql" / SQL_VALIDATION_NAME, report)
        return report

    config_path = find_database_config(module_dir, db_config_path)
    config = load_database_config(config_path)
    report["database_config"] = config.path.as_posix()
    report["database_config_sha256"] = sha256_file(config.path)
    connector = connect_fn or _default_connect
    try:
        connection = connector(config)
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT VERSION()")
                row = cursor.fetchone()
                report["server_version"] = str(row[0] if row else "unknown")
                for sql_id in required:
                    asset = registry[sql_id]
                    statement, values = _prepared_statement(asset)
                    cursor.execute("EXPLAIN " + statement, values)
                    cursor.fetchall()
                    report["assets"].append(
                        {
                            "sql_id": asset.sql_id,
                            "file": asset.path.relative_to(case_dir).as_posix(),
                            "sha256": asset.sha256,
                            "statement_type": asset.statement_type,
                            "method": "EXPLAIN",
                            "status": "validated",
                        }
                    )
        finally:
            try:
                connection.rollback()
            except Exception:
                pass
            connection.close()
    except SqlAssetError:
        raise
    except Exception as exc:
        raise SqlAssetError(f"database SQL validation failed: {exc}") from exc
    if write_report:
        atomic_write_json(case_dir / "sql" / SQL_VALIDATION_NAME, report)
    return report


def require_current_validation(
    case_dir: Path,
    required_sql_ids: Iterable[str] | None = None,
    *,
    module_dir: Path | None = None,
    db_config_path: Path | None = None,
) -> dict[str, Any]:
    """Reuse the SQL-stage EXPLAIN report only while every pinned asset is unchanged."""

    registry = load_registry(case_dir)
    required = list(dict.fromkeys(required_sql_ids if required_sql_ids is not None else registry))
    unknown = sorted(set(required) - set(registry))
    if unknown:
        raise SqlAssetError(f"unknown SQL Refs: {', '.join(unknown)}")
    report_path = case_dir / "sql" / SQL_VALIDATION_NAME
    try:
        report = json.loads(report_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise SqlAssetError(f"SQL validation report is missing: {report_path}") from exc
    except json.JSONDecodeError as exc:
        raise SqlAssetError(f"invalid SQL validation report: {report_path}: {exc}") from exc
    if not isinstance(report, dict) or report.get("schema_version") != SQL_VALIDATION_SCHEMA_VERSION:
        raise SqlAssetError("SQL validation report schema is invalid")
    if report.get("status") != "validated":
        raise SqlAssetError("SQL validation report is not validated")
    current_registry = registry_manifest(case_dir, registry)
    if report.get("registry") != current_registry:
        raise SqlAssetError("SQL assets or sql-manifest.json changed after the SQL validation stage")
    validated = {
        item.get("sql_id"): item
        for item in report.get("assets", [])
        if isinstance(item, dict) and item.get("status") == "validated"
    }
    missing = sorted(set(required) - set(validated))
    if missing:
        raise SqlAssetError(
            "SQL validation report does not cover required assets: " + ", ".join(missing)
        )
    for sql_id in required:
        if validated[sql_id].get("sha256") != registry[sql_id].sha256:
            raise SqlAssetError(f"{sql_id} changed after the SQL validation stage")
    if required and module_dir is not None:
        config_path = find_database_config(module_dir, db_config_path)
        if report.get("database_config") != config_path.as_posix():
            raise SqlAssetError("database config path changed after the SQL validation stage")
        if report.get("database_config_sha256") != sha256_file(config_path):
            raise SqlAssetError("database config changed after the SQL validation stage")
    return report


def relevant_assets_manifest(
    case_dir: Path,
    data_closure_refs: Iterable[str],
    registry: dict[str, SqlAsset] | None = None,
) -> dict[str, Any]:
    """Return metadata only for SQL assets relevant to the current TP closure."""

    registry = registry if registry is not None else load_registry(case_dir)
    closures = set(data_closure_refs)
    relevant = {
        sql_id: asset
        for sql_id, asset in registry.items()
        if closures & set(asset.data_closure_refs)
    }
    return registry_manifest(case_dir, relevant)


def relevant_assets_index_text(case_dir: Path, data_closure_refs: Iterable[str]) -> str:
    """Render a compact SQL index without embedding SQL statement bodies."""

    registry = load_registry(case_dir)
    closures = set(data_closure_refs)
    relevant = [asset for asset in registry.values() if closures & set(asset.data_closure_refs)]
    if not relevant:
        return (
            f"- 注册表：`sql/{SQL_MANIFEST_NAME}`\n"
            "- 当前闭包尚无可复用 SQL；按 SQL 资产契约新增后再在用例中引用。"
        )
    rows = []
    for asset in relevant:
        params = "、".join(f":{item.name}" for item in asset.parameters) or "无"
        rows.append(
            "| "
            + " | ".join(
                (
                    asset.sql_id,
                    asset.path.relative_to(case_dir).as_posix(),
                    asset.statement_type,
                    asset.purpose.replace("|", "\\|"),
                    "、".join(asset.data_closure_refs),
                    params,
                    asset.sha256,
                )
            )
            + " |"
        )
    return (
        f"- 注册表：`sql/{SQL_MANIFEST_NAME}`\n\n"
        "| SQL-ID | 文件 | 类型 | 用途 | Data Closure Refs | 参数 | SHA-256 |\n"
        "|---|---|---|---|---|---|---|\n"
        + "\n".join(rows)
        + "\n\n只有当某条资产的用途与当前 TP 场景匹配时，才打开该 SQL 文件；"
        "不得为了浏览而批量读取 SQL 正文。"
    )
