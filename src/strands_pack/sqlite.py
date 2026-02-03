"""
SQLite Tool

Local SQLite database operations with no external dependencies.

Requires:
    No extra dependencies - uses Python's built-in sqlite3

Supported actions
-----------------
- execute
    Parameters: db_path (required), sql (required), params (optional - list or dict)
- query
    Parameters: db_path (required), sql (required), params (optional), limit (default 100)
- create_table
    Parameters: db_path (required), table (required), columns (required - dict of name: type)
- drop_table
    Parameters: db_path (required), table (required)
- insert
    Parameters: db_path (required), table (required), data (required - dict or list of dicts)
- update
    Parameters: db_path (required), table (required), data (required), where (required)
- delete
    Parameters: db_path (required), table (required), where (required)
- list_tables
    Parameters: db_path (required)
- describe_table
    Parameters: db_path (required), table (required)
- get_info
    Parameters: db_path (required)
- backup
    Parameters: db_path (required), backup_path (required)
- upsert
    Parameters: db_path (required), table (required), data (required - dict or list of dicts),
                conflict_columns (optional - list of column names for ON CONFLICT),
                update_columns (optional - list of columns to update; default all non-conflict cols)
- vacuum
    Parameters: db_path (required)
- create_index
    Parameters: db_path (required), table (required), index_name (required), index_columns (required - list),
                unique (optional), if_not_exists (optional)
- drop_index
    Parameters: db_path (required), index_name (required), if_exists (optional)
- truncate
    Parameters: db_path (required), table (required), confirm (required True), reset_identity (optional)
- export_csv
    Parameters: db_path (required), table (required), csv_path (required), include_header (optional)
- import_csv
    Parameters: db_path (required), table (required), csv_path (required),
                has_header (optional), delimiter (optional), create_table_if_missing (optional)

Notes:
  - All operations auto-commit by default
  - Use :memory: as db_path for in-memory database
  - SQL injection is prevented via parameterized queries
  - Column types: TEXT, INTEGER, REAL, BLOB, NULL
"""

from __future__ import annotations

import csv
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from strands import tool


def _ok(**data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": True}
    out.update(data)
    return out


def _err(message: str, *, error_type: Optional[str] = None, **data: Any) -> Dict[str, Any]:
    out: Dict[str, Any] = {"success": False, "error": message}
    if error_type:
        out["error_type"] = error_type
    out.update(data)
    return out


def _get_connection(db_path: str) -> sqlite3.Connection:
    """Get a database connection."""
    if db_path != ":memory:":
        path = Path(db_path).expanduser()
        path.parent.mkdir(parents=True, exist_ok=True)
        db_path = str(path)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def _row_to_dict(row: sqlite3.Row) -> Dict[str, Any]:
    """Convert a Row to a dict."""
    return dict(row)


def _validate_identifier(name: str, *, kind: str = "identifier") -> Optional[str]:
    """Return error message if identifier is invalid, else None."""
    if not name:
        return f"{kind} is required"
    if not name.replace("_", "").isalnum():
        return f"Invalid {kind}: {name}"
    return None


def _validate_identifiers(names: List[str], *, kind: str = "identifier") -> Optional[str]:
    if not names:
        return f"{kind} list cannot be empty"
    for n in names:
        err = _validate_identifier(n, kind=kind)
        if err:
            return err
    return None


def _execute(db_path: str, sql: str, params: Optional[Union[List, Dict]] = None,
             **kwargs) -> Dict[str, Any]:
    """Execute a SQL statement (INSERT, UPDATE, DELETE, CREATE, etc.)."""
    if not db_path:
        return _err("db_path is required")
    if not sql:
        return _err("sql is required")

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        conn.commit()

        return _ok(
            action="execute",
            db_path=db_path,
            rowcount=cursor.rowcount,
            lastrowid=cursor.lastrowid,
        )
    finally:
        conn.close()


def _query(db_path: str, sql: str, params: Optional[Union[List, Dict]] = None,
           limit: int = 100, **kwargs) -> Dict[str, Any]:
    """Execute a SELECT query and return results."""
    if not db_path:
        return _err("db_path is required")
    if not sql:
        return _err("sql is required")

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)

        rows = cursor.fetchmany(limit)
        results = [_row_to_dict(row) for row in rows]

        # Check if there are more rows
        has_more = cursor.fetchone() is not None

        return _ok(
            action="query",
            db_path=db_path,
            results=results,
            count=len(results),
            has_more=has_more,
        )
    finally:
        conn.close()


def _create_table(db_path: str, table: str, columns: Dict[str, str],
                  primary_key: Optional[str] = None, if_not_exists: bool = True,
                  **kwargs) -> Dict[str, Any]:
    """Create a new table."""
    if not db_path:
        return _err("db_path is required")
    if not table:
        return _err("table is required")
    if not columns:
        return _err("columns is required (dict of name: type)")

    # Validate table name (prevent SQL injection)
    if not table.replace("_", "").isalnum():
        return _err("Invalid table name")

    # Build column definitions
    col_defs = []
    for col_name, col_type in columns.items():
        if not col_name.replace("_", "").isalnum():
            return _err(f"Invalid column name: {col_name}")
        col_type = col_type.upper()
        if col_type not in ("TEXT", "INTEGER", "REAL", "BLOB", "NULL"):
            col_type = "TEXT"  # Default to TEXT for safety

        if primary_key and col_name == primary_key:
            col_defs.append(f"{col_name} {col_type} PRIMARY KEY")
        else:
            col_defs.append(f"{col_name} {col_type}")

    exists_clause = "IF NOT EXISTS " if if_not_exists else ""
    sql = f"CREATE TABLE {exists_clause}{table} ({', '.join(col_defs)})"

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()

        return _ok(
            action="create_table",
            db_path=db_path,
            table=table,
            columns=columns,
            sql=sql,
        )
    finally:
        conn.close()


def _drop_table(db_path: str, table: str, if_exists: bool = True,
                **kwargs) -> Dict[str, Any]:
    """Drop a table."""
    if not db_path:
        return _err("db_path is required")
    if not table:
        return _err("table is required")

    if not table.replace("_", "").isalnum():
        return _err("Invalid table name")

    exists_clause = "IF EXISTS " if if_exists else ""
    sql = f"DROP TABLE {exists_clause}{table}"

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()

        return _ok(
            action="drop_table",
            db_path=db_path,
            table=table,
        )
    finally:
        conn.close()


def _insert(db_path: str, table: str, data: Union[Dict, List[Dict]],
            **kwargs) -> Dict[str, Any]:
    """Insert one or more rows into a table."""
    if not db_path:
        return _err("db_path is required")
    if not table:
        return _err("table is required")
    if not data:
        return _err("data is required (dict or list of dicts)")

    if not table.replace("_", "").isalnum():
        return _err("Invalid table name")

    # Normalize to list
    rows = [data] if isinstance(data, dict) else data
    if not rows:
        return _err("data cannot be empty")

    # Get columns from first row
    columns = list(rows[0].keys())
    for col in columns:
        if not col.replace("_", "").isalnum():
            return _err(f"Invalid column name: {col}")

    placeholders = ", ".join(["?" for _ in columns])
    col_names = ", ".join(columns)
    sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        inserted = 0
        last_id = None

        for row in rows:
            values = [row.get(col) for col in columns]
            cursor.execute(sql, values)
            inserted += 1
            last_id = cursor.lastrowid

        conn.commit()

        return _ok(
            action="insert",
            db_path=db_path,
            table=table,
            inserted=inserted,
            lastrowid=last_id,
        )
    finally:
        conn.close()


def _upsert(
    db_path: str,
    table: str,
    data: Union[Dict, List[Dict]],
    conflict_columns: Optional[List[str]] = None,
    update_columns: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """
    Insert or update rows.

    - If conflict_columns is provided, uses SQLite UPSERT:
        INSERT ... ON CONFLICT(col1,...) DO UPDATE SET ...
    - Otherwise, uses INSERT OR REPLACE (requires PK/UNIQUE to have effect).
    """
    if not db_path:
        return _err("db_path is required")
    if not table:
        return _err("table is required")
    if not data:
        return _err("data is required (dict or list of dicts)")

    t_err = _validate_identifier(table, kind="table name")
    if t_err:
        return _err(t_err)

    rows = [data] if isinstance(data, dict) else data
    if not rows:
        return _err("data cannot be empty")

    columns = list(rows[0].keys())
    c_err = _validate_identifiers(columns, kind="column name")
    if c_err:
        return _err(c_err)

    if conflict_columns is not None:
        cc_err = _validate_identifiers(conflict_columns, kind="conflict column")
        if cc_err:
            return _err(cc_err)
        for c in conflict_columns:
            if c not in columns:
                return _err(f"conflict_columns must be present in data columns. Missing: {c}")

    if update_columns is not None:
        uc_err = _validate_identifiers(update_columns, kind="update column")
        if uc_err:
            return _err(uc_err)
        for c in update_columns:
            if c not in columns:
                return _err(f"update_columns must be present in data columns. Missing: {c}")

    placeholders = ", ".join(["?" for _ in columns])
    col_names = ", ".join(columns)

    if conflict_columns:
        # Default update columns: all non-conflict columns
        upd_cols = update_columns or [c for c in columns if c not in conflict_columns]
        set_clause = ", ".join([f"{c}=excluded.{c}" for c in upd_cols])
        conflict_clause = ", ".join(conflict_columns)
        sql = (
            f"INSERT INTO {table} ({col_names}) VALUES ({placeholders}) "
            f"ON CONFLICT({conflict_clause}) DO UPDATE SET {set_clause}"
        )
    else:
        sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        count = 0
        last_id = None
        for row in rows:
            values = [row.get(col) for col in columns]
            cursor.execute(sql, values)
            count += 1
            last_id = cursor.lastrowid
        conn.commit()
        return _ok(
            action="upsert",
            db_path=db_path,
            table=table,
            upserted=count,
            lastrowid=last_id,
            sql=sql,
        )
    finally:
        conn.close()


def _vacuum(db_path: str, **kwargs) -> Dict[str, Any]:
    """Run VACUUM to rebuild/compact the database."""
    if not db_path:
        return _err("db_path is required")
    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute("VACUUM")
        conn.commit()
        return _ok(action="vacuum", db_path=db_path)
    finally:
        conn.close()


def _create_index(
    db_path: str,
    table: str,
    index_name: str,
    index_columns: List[str],
    unique: bool = False,
    if_not_exists: bool = True,
    **kwargs,
) -> Dict[str, Any]:
    """Create an index on a table."""
    if not db_path:
        return _err("db_path is required")
    for name, kind in ((table, "table name"), (index_name, "index name")):
        err = _validate_identifier(name, kind=kind)
        if err:
            return _err(err)
    err = _validate_identifiers(index_columns, kind="index column")
    if err:
        return _err(err)

    unique_clause = "UNIQUE " if unique else ""
    ine = "IF NOT EXISTS " if if_not_exists else ""
    cols = ", ".join(index_columns)
    sql = f"CREATE {unique_clause}INDEX {ine}{index_name} ON {table} ({cols})"

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        return _ok(action="create_index", db_path=db_path, table=table, index_name=index_name, columns=index_columns, sql=sql)
    finally:
        conn.close()


def _drop_index(
    db_path: str,
    index_name: str,
    if_exists: bool = True,
    **kwargs,
) -> Dict[str, Any]:
    """Drop an index."""
    if not db_path:
        return _err("db_path is required")
    err = _validate_identifier(index_name, kind="index name")
    if err:
        return _err(err)

    ie = "IF EXISTS " if if_exists else ""
    sql = f"DROP INDEX {ie}{index_name}"
    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        conn.commit()
        return _ok(action="drop_index", db_path=db_path, index_name=index_name)
    finally:
        conn.close()


def _truncate(
    db_path: str,
    table: str,
    confirm: bool = False,
    reset_identity: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Delete all rows from a table. Requires confirm=True."""
    if not db_path:
        return _err("db_path is required")
    err = _validate_identifier(table, kind="table name")
    if err:
        return _err(err)
    if not confirm:
        return _err("Refusing to truncate without confirm=True", error_type="ConfirmationRequired")

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(f"DELETE FROM {table}")
        deleted = cursor.rowcount
        if reset_identity:
            cursor.execute("DELETE FROM sqlite_sequence WHERE name = ?", [table])
        conn.commit()
        return _ok(action="truncate", db_path=db_path, table=table, deleted=deleted, reset_identity=reset_identity)
    finally:
        conn.close()


def _export_csv(
    db_path: str,
    table: str,
    csv_path: str,
    include_header: bool = True,
    **kwargs,
) -> Dict[str, Any]:
    """Export an entire table to CSV."""
    if not db_path:
        return _err("db_path is required")
    if not csv_path:
        return _err("csv_path is required")
    err = _validate_identifier(table, kind="table name")
    if err:
        return _err(err)

    out_path = Path(csv_path).expanduser()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(f"SELECT * FROM {table}")
        rows = cursor.fetchall()
        col_names = [d[0] for d in (cursor.description or [])]

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if include_header:
                writer.writerow(col_names)
            for r in rows:
                writer.writerow([r[c] for c in col_names])

        return _ok(action="export_csv", db_path=db_path, table=table, csv_path=str(out_path), rows_exported=len(rows), columns=col_names)
    finally:
        conn.close()


def _import_csv(
    db_path: str,
    table: str,
    csv_path: str,
    has_header: bool = True,
    delimiter: str = ",",
    create_table_if_missing: bool = False,
    **kwargs,
) -> Dict[str, Any]:
    """Import a CSV file into a table (inserts all rows)."""
    if not db_path:
        return _err("db_path is required")
    if not csv_path:
        return _err("csv_path is required")
    err = _validate_identifier(table, kind="table name")
    if err:
        return _err(err)

    p = Path(csv_path).expanduser()
    if not p.exists():
        return _err(f"CSV not found: {csv_path}")

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        # If table missing and create_table_if_missing, create with TEXT columns based on header.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name = ?", [table])
        exists = cursor.fetchone() is not None

        with p.open("r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=delimiter)
            header: List[str]
            first_row: Optional[List[str]] = None
            if has_header:
                header = next(reader, [])
            else:
                first_row = next(reader, None)
                if first_row is None:
                    return _err("CSV is empty")
                header = [f"col_{i+1}" for i in range(len(first_row))]

            h_err = _validate_identifiers(header, kind="csv column")
            if h_err:
                return _err(h_err)

            if not exists and create_table_if_missing:
                cols = {c: "TEXT" for c in header}
                create_res = _create_table(db_path=db_path, table=table, columns=cols, primary_key=None, if_not_exists=True)
                if not create_res.get("success"):
                    return create_res
            elif not exists and not create_table_if_missing:
                return _err(f"Table not found: {table}. Set create_table_if_missing=True to create it.")

            placeholders = ", ".join(["?" for _ in header])
            col_names = ", ".join(header)
            sql = f"INSERT INTO {table} ({col_names}) VALUES ({placeholders})"

            inserted = 0
            if first_row is not None:
                cursor.execute(sql, first_row)
                inserted += 1

            for row in reader:
                if not row:
                    continue
                cursor.execute(sql, row)
                inserted += 1

            conn.commit()
            return _ok(action="import_csv", db_path=db_path, table=table, csv_path=str(p), rows_imported=inserted, columns=header)
    finally:
        conn.close()

def _update(db_path: str, table: str, data: Dict, where: str,
            where_params: Optional[List] = None, **kwargs) -> Dict[str, Any]:
    """Update rows in a table."""
    if not db_path:
        return _err("db_path is required")
    if not table:
        return _err("table is required")
    if not data:
        return _err("data is required (dict of column: value)")
    if not where:
        return _err("where is required (WHERE clause without 'WHERE')")

    if not table.replace("_", "").isalnum():
        return _err("Invalid table name")

    # Build SET clause
    set_parts = []
    params = []
    for col, val in data.items():
        if not col.replace("_", "").isalnum():
            return _err(f"Invalid column name: {col}")
        set_parts.append(f"{col} = ?")
        params.append(val)

    # Add where params
    if where_params:
        params.extend(where_params)

    sql = f"UPDATE {table} SET {', '.join(set_parts)} WHERE {where}"

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        conn.commit()

        return _ok(
            action="update",
            db_path=db_path,
            table=table,
            rowcount=cursor.rowcount,
        )
    finally:
        conn.close()


def _delete(db_path: str, table: str, where: str,
            where_params: Optional[List] = None, **kwargs) -> Dict[str, Any]:
    """Delete rows from a table."""
    if not db_path:
        return _err("db_path is required")
    if not table:
        return _err("table is required")
    if not where:
        return _err("where is required (WHERE clause without 'WHERE')")

    if not table.replace("_", "").isalnum():
        return _err("Invalid table name")

    sql = f"DELETE FROM {table} WHERE {where}"

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        if where_params:
            cursor.execute(sql, where_params)
        else:
            cursor.execute(sql)
        conn.commit()

        return _ok(
            action="delete",
            db_path=db_path,
            table=table,
            rowcount=cursor.rowcount,
        )
    finally:
        conn.close()


def _list_tables(db_path: str, **kwargs) -> Dict[str, Any]:
    """List all tables in the database."""
    if not db_path:
        return _err("db_path is required")

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        tables = [row["name"] for row in cursor.fetchall()]

        return _ok(
            action="list_tables",
            db_path=db_path,
            tables=tables,
            count=len(tables),
        )
    finally:
        conn.close()


def _describe_table(db_path: str, table: str, **kwargs) -> Dict[str, Any]:
    """Get table schema information."""
    if not db_path:
        return _err("db_path is required")
    if not table:
        return _err("table is required")

    if not table.replace("_", "").isalnum():
        return _err("Invalid table name")

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()
        cursor.execute(f"PRAGMA table_info({table})")
        columns = []
        for row in cursor.fetchall():
            columns.append({
                "cid": row["cid"],
                "name": row["name"],
                "type": row["type"],
                "notnull": bool(row["notnull"]),
                "default": row["dflt_value"],
                "primary_key": bool(row["pk"]),
            })

        if not columns:
            return _err(f"Table not found: {table}")

        # Get row count
        cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
        row_count = cursor.fetchone()["count"]

        return _ok(
            action="describe_table",
            db_path=db_path,
            table=table,
            columns=columns,
            row_count=row_count,
        )
    finally:
        conn.close()


def _get_info(db_path: str, **kwargs) -> Dict[str, Any]:
    """Get database information."""
    if not db_path:
        return _err("db_path is required")

    if db_path == ":memory:":
        file_size = 0
    else:
        path = Path(db_path).expanduser()
        if not path.exists():
            return _err(f"Database not found: {db_path}")
        file_size = path.stat().st_size

    conn = _get_connection(db_path)
    try:
        cursor = conn.cursor()

        # Get table count
        cursor.execute(
            "SELECT COUNT(*) as count FROM sqlite_master WHERE type='table'"
        )
        table_count = cursor.fetchone()["count"]

        # Get SQLite version
        cursor.execute("SELECT sqlite_version()")
        sqlite_version = cursor.fetchone()[0]

        # Get page info
        cursor.execute("PRAGMA page_count")
        page_count = cursor.fetchone()[0]
        cursor.execute("PRAGMA page_size")
        page_size = cursor.fetchone()[0]

        return _ok(
            action="get_info",
            db_path=db_path,
            file_size_bytes=file_size,
            table_count=table_count,
            sqlite_version=sqlite_version,
            page_count=page_count,
            page_size=page_size,
        )
    finally:
        conn.close()


def _backup(db_path: str, backup_path: str, **kwargs) -> Dict[str, Any]:
    """Backup database to a new file."""
    if not db_path:
        return _err("db_path is required")
    if not backup_path:
        return _err("backup_path is required")

    if db_path == ":memory:":
        return _err("Cannot backup in-memory database")

    source_path = Path(db_path).expanduser()
    if not source_path.exists():
        return _err(f"Database not found: {db_path}")

    dest_path = Path(backup_path).expanduser()
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    source_conn = sqlite3.connect(str(source_path))
    dest_conn = sqlite3.connect(str(dest_path))

    try:
        source_conn.backup(dest_conn)

        return _ok(
            action="backup",
            db_path=db_path,
            backup_path=str(dest_path),
            size_bytes=dest_path.stat().st_size,
        )
    finally:
        source_conn.close()
        dest_conn.close()


_ACTIONS = {
    "execute": _execute,
    "query": _query,
    "create_table": _create_table,
    "drop_table": _drop_table,
    "insert": _insert,
    "update": _update,
    "delete": _delete,
    "list_tables": _list_tables,
    "describe_table": _describe_table,
    "get_info": _get_info,
    "backup": _backup,
    "upsert": _upsert,
    "vacuum": _vacuum,
    "create_index": _create_index,
    "drop_index": _drop_index,
    "truncate": _truncate,
    "export_csv": _export_csv,
    "import_csv": _import_csv,
}


@tool
def sqlite(
    action: str,
    db_path: Optional[str] = None,
    sql: Optional[str] = None,
    params: Optional[Union[List, Dict]] = None,
    table: Optional[str] = None,
    columns: Optional[Dict[str, str]] = None,
    primary_key: Optional[str] = None,
    if_not_exists: bool = True,
    if_exists: bool = True,
    data: Optional[Union[Dict, List[Dict]]] = None,
    where: Optional[str] = None,
    where_params: Optional[List] = None,
    limit: int = 100,
    backup_path: Optional[str] = None,
    # new action args
    conflict_columns: Optional[List[str]] = None,
    update_columns: Optional[List[str]] = None,
    index_name: Optional[str] = None,
    index_columns: Optional[List[str]] = None,
    unique: bool = False,
    confirm: bool = False,
    reset_identity: bool = False,
    csv_path: Optional[str] = None,
    include_header: bool = True,
    has_header: bool = True,
    delimiter: str = ",",
    create_table_if_missing: bool = False,
) -> Dict[str, Any]:
    """
    Local SQLite database operations.

    Args:
        action: The action to perform. One of:
            - "execute": Execute a SQL statement (INSERT, UPDATE, DELETE, CREATE, etc.)
            - "query": Execute a SELECT query and return results
            - "create_table": Create a new table
            - "drop_table": Drop a table
            - "insert": Insert one or more rows
            - "update": Update rows matching a condition
            - "delete": Delete rows matching a condition
            - "list_tables": List all tables
            - "describe_table": Get table schema
            - "get_info": Get database information
            - "backup": Backup database to a new file
            - "upsert": Insert or update rows (uses ON CONFLICT if conflict_columns is provided; else INSERT OR REPLACE)
            - "vacuum": Optimize/compact database (VACUUM)
            - "create_index": Create an index
            - "drop_index": Drop an index
            - "truncate": Delete all rows from a table (requires confirm=True)
            - "export_csv": Export a table to a CSV file
            - "import_csv": Import a CSV file into a table
        db_path: Path to database file, or ":memory:" for in-memory database.
        sql: SQL statement for execute/query actions.
        params: Parameters for SQL statement (list or dict).
        table: Table name for table operations.
        columns: Dict of column_name: type for create_table (TEXT, INTEGER, REAL, BLOB).
        primary_key: Column name to use as primary key.
        if_not_exists: For create_table, don't error if table exists (default True).
        if_exists: For drop_table, don't error if table doesn't exist (default True).
        data: Data dict or list of dicts for insert/update.
        where: WHERE clause (without 'WHERE') for update/delete.
        where_params: Parameters for WHERE clause.
        limit: Max rows to return for query (default 100).
        backup_path: Destination path for backup action.
        conflict_columns: For upsert, columns that define a conflict target for ON CONFLICT.
        update_columns: For upsert, columns to update (defaults to all non-conflict columns).
        index_name: Index name for create_index/drop_index.
        index_columns: Columns for create_index.
        unique: Whether the created index is UNIQUE.
        confirm: Required for destructive actions like truncate.
        reset_identity: For truncate, reset AUTOINCREMENT (sqlite_sequence) if present.
        csv_path: Path for export_csv/import_csv.
        include_header: Whether export_csv writes header row.
        has_header: Whether import_csv reads header row.
        delimiter: CSV delimiter for import_csv.
        create_table_if_missing: For import_csv, create table if missing with TEXT columns.

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> sqlite(action="create_table", db_path="test.db", table="users", columns={"id": "INTEGER", "name": "TEXT"}, primary_key="id")
        >>> sqlite(action="insert", db_path="test.db", table="users", data={"id": 1, "name": "Alice"})
        >>> sqlite(action="query", db_path="test.db", sql="SELECT * FROM users WHERE id = ?", params=[1])

    Environment:
        - SQLITE_DB_PATH: Optional default database path used when db_path is omitted.
    """
    action = (action or "").strip().lower()

    # Optional env default for db_path to improve agent UX (so db_path can be omitted).
    if db_path is None:
        db_path = os.environ.get("SQLITE_DB_PATH") or os.environ.get("STRANDS_SQLITE_DB_PATH")

    if action not in _ACTIONS:
        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=list(_ACTIONS.keys()),
        )

    # Build kwargs for the action function
    kwargs: Dict[str, Any] = {}
    if db_path is not None:
        kwargs["db_path"] = db_path
    if sql is not None:
        kwargs["sql"] = sql
    if params is not None:
        kwargs["params"] = params
    if table is not None:
        kwargs["table"] = table
    if columns is not None:
        kwargs["columns"] = columns
    if primary_key is not None:
        kwargs["primary_key"] = primary_key
    kwargs["if_not_exists"] = if_not_exists
    kwargs["if_exists"] = if_exists
    if data is not None:
        kwargs["data"] = data
    if where is not None:
        kwargs["where"] = where
    if where_params is not None:
        kwargs["where_params"] = where_params
    kwargs["limit"] = limit
    if backup_path is not None:
        kwargs["backup_path"] = backup_path
    if conflict_columns is not None:
        kwargs["conflict_columns"] = conflict_columns
    if update_columns is not None:
        kwargs["update_columns"] = update_columns
    if index_name is not None:
        kwargs["index_name"] = index_name
    if index_columns is not None:
        kwargs["index_columns"] = index_columns
    kwargs["unique"] = unique
    kwargs["confirm"] = confirm
    kwargs["reset_identity"] = reset_identity
    if csv_path is not None:
        kwargs["csv_path"] = csv_path
    kwargs["include_header"] = include_header
    kwargs["has_header"] = has_header
    kwargs["delimiter"] = delimiter
    kwargs["create_table_if_missing"] = create_table_if_missing

    try:
        return _ACTIONS[action](**kwargs)
    except sqlite3.Error as e:
        return _err(str(e), error_type="SQLiteError", action=action)
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
