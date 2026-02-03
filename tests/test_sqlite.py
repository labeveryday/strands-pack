"""Tests for SQLite tool."""

import os
import tempfile

import pytest


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield f.name
    os.unlink(f.name)


@pytest.fixture
def temp_dir():
    """Create a temp directory."""
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_sqlite_create_table(temp_db):
    """Test creating a table."""
    from strands_pack import sqlite

    result = sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER", "name": "TEXT", "email": "TEXT"},
        primary_key="id",
    )

    assert result["success"] is True
    assert result["action"] == "create_table"
    assert result["table"] == "users"


def test_sqlite_insert_single(temp_db):
    """Test inserting a single row."""
    from strands_pack import sqlite

    # Create table first
    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER", "name": "TEXT"},
    )

    result = sqlite(
        action="insert",
        db_path=temp_db,
        table="users",
        data={"id": 1, "name": "Alice"},
    )

    assert result["success"] is True
    assert result["action"] == "insert"
    assert result["inserted"] == 1


def test_sqlite_insert_multiple(temp_db):
    """Test inserting multiple rows."""
    from strands_pack import sqlite

    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER", "name": "TEXT"},
    )

    result = sqlite(
        action="insert",
        db_path=temp_db,
        table="users",
        data=[
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 3, "name": "Charlie"},
        ],
    )

    assert result["success"] is True
    assert result["inserted"] == 3


def test_sqlite_query(temp_db):
    """Test querying data."""
    from strands_pack import sqlite

    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER", "name": "TEXT"},
    )
    sqlite(
        action="insert",
        db_path=temp_db,
        table="users",
        data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
    )

    result = sqlite(
        action="query",
        db_path=temp_db,
        sql="SELECT * FROM users ORDER BY id",
    )

    assert result["success"] is True
    assert result["action"] == "query"
    assert result["count"] == 2
    assert result["results"][0]["name"] == "Alice"
    assert result["results"][1]["name"] == "Bob"


def test_sqlite_query_with_params(temp_db):
    """Test querying with parameters."""
    from strands_pack import sqlite

    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER", "name": "TEXT"},
    )
    sqlite(
        action="insert",
        db_path=temp_db,
        table="users",
        data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
    )

    result = sqlite(
        action="query",
        db_path=temp_db,
        sql="SELECT * FROM users WHERE name = ?",
        params=["Alice"],
    )

    assert result["success"] is True
    assert result["count"] == 1
    assert result["results"][0]["name"] == "Alice"


def test_sqlite_update(temp_db):
    """Test updating rows."""
    from strands_pack import sqlite

    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER", "name": "TEXT"},
    )
    sqlite(
        action="insert",
        db_path=temp_db,
        table="users",
        data={"id": 1, "name": "Alice"},
    )

    result = sqlite(
        action="update",
        db_path=temp_db,
        table="users",
        data={"name": "Alicia"},
        where="id = ?",
        where_params=[1],
    )

    assert result["success"] is True
    assert result["action"] == "update"
    assert result["rowcount"] == 1

    # Verify update
    query_result = sqlite(
        action="query",
        db_path=temp_db,
        sql="SELECT name FROM users WHERE id = 1",
    )
    assert query_result["results"][0]["name"] == "Alicia"


def test_sqlite_delete(temp_db):
    """Test deleting rows."""
    from strands_pack import sqlite

    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER", "name": "TEXT"},
    )
    sqlite(
        action="insert",
        db_path=temp_db,
        table="users",
        data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
    )

    result = sqlite(
        action="delete",
        db_path=temp_db,
        table="users",
        where="id = ?",
        where_params=[1],
    )

    assert result["success"] is True
    assert result["action"] == "delete"
    assert result["rowcount"] == 1

    # Verify deletion
    query_result = sqlite(
        action="query",
        db_path=temp_db,
        sql="SELECT COUNT(*) as count FROM users",
    )
    assert query_result["results"][0]["count"] == 1


def test_sqlite_list_tables(temp_db):
    """Test listing tables."""
    from strands_pack import sqlite

    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER"},
    )
    sqlite(
        action="create_table",
        db_path=temp_db,
        table="orders",
        columns={"id": "INTEGER"},
    )

    result = sqlite(action="list_tables", db_path=temp_db)

    assert result["success"] is True
    assert result["action"] == "list_tables"
    assert "users" in result["tables"]
    assert "orders" in result["tables"]


def test_sqlite_describe_table(temp_db):
    """Test describing a table."""
    from strands_pack import sqlite

    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER", "name": "TEXT", "email": "TEXT"},
        primary_key="id",
    )

    result = sqlite(
        action="describe_table",
        db_path=temp_db,
        table="users",
    )

    assert result["success"] is True
    assert result["action"] == "describe_table"
    assert len(result["columns"]) == 3

    # Find the id column
    id_col = next(c for c in result["columns"] if c["name"] == "id")
    assert id_col["type"] == "INTEGER"
    assert id_col["primary_key"] is True


def test_sqlite_drop_table(temp_db):
    """Test dropping a table."""
    from strands_pack import sqlite

    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER"},
    )

    result = sqlite(
        action="drop_table",
        db_path=temp_db,
        table="users",
    )

    assert result["success"] is True
    assert result["action"] == "drop_table"

    # Verify table is gone
    list_result = sqlite(action="list_tables", db_path=temp_db)
    assert "users" not in list_result["tables"]


def test_sqlite_get_info(temp_db):
    """Test getting database info."""
    from strands_pack import sqlite

    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER"},
    )

    result = sqlite(action="get_info", db_path=temp_db)

    assert result["success"] is True
    assert result["action"] == "get_info"
    assert result["table_count"] == 1
    assert "sqlite_version" in result


def test_sqlite_backup(temp_db, temp_dir):
    """Test backing up a database."""
    from strands_pack import sqlite

    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER"},
    )
    sqlite(
        action="insert",
        db_path=temp_db,
        table="users",
        data={"id": 1},
    )

    backup_path = os.path.join(temp_dir, "backup.db")
    result = sqlite(
        action="backup",
        db_path=temp_db,
        backup_path=backup_path,
    )

    assert result["success"] is True
    assert result["action"] == "backup"
    assert os.path.exists(backup_path)

    # Verify backup contains data
    query_result = sqlite(
        action="query",
        db_path=backup_path,
        sql="SELECT COUNT(*) as count FROM users",
    )
    assert query_result["results"][0]["count"] == 1


def test_sqlite_upsert_replace(temp_db):
    """Test upsert via INSERT OR REPLACE."""
    from strands_pack import sqlite

    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER", "name": "TEXT"},
        primary_key="id",
    )
    sqlite(action="insert", db_path=temp_db, table="users", data={"id": 1, "name": "Alice"})

    res = sqlite(action="upsert", db_path=temp_db, table="users", data={"id": 1, "name": "Alicia"})
    assert res["success"] is True
    assert res["action"] == "upsert"
    q = sqlite(action="query", db_path=temp_db, sql="SELECT name FROM users WHERE id = 1")
    assert q["results"][0]["name"] == "Alicia"


def test_sqlite_create_and_drop_index(temp_db):
    """Test create_index and drop_index."""
    from strands_pack import sqlite

    sqlite(
        action="create_table",
        db_path=temp_db,
        table="users",
        columns={"id": "INTEGER", "email": "TEXT"},
    )

    res = sqlite(
        action="create_index",
        db_path=temp_db,
        table="users",
        index_name="idx_users_email",
        index_columns=["email"],
        unique=True,
    )
    assert res["success"] is True

    # Index exists
    q = sqlite(
        action="query",
        db_path=temp_db,
        sql="SELECT name FROM sqlite_master WHERE type='index' AND name = ?",
        params=["idx_users_email"],
    )
    assert q["count"] == 1

    res2 = sqlite(action="drop_index", db_path=temp_db, index_name="idx_users_email")
    assert res2["success"] is True
    q2 = sqlite(
        action="query",
        db_path=temp_db,
        sql="SELECT name FROM sqlite_master WHERE type='index' AND name = ?",
        params=["idx_users_email"],
    )
    assert q2["count"] == 0


def test_sqlite_truncate_requires_confirm(temp_db):
    """Truncate should require confirm=True."""
    from strands_pack import sqlite

    sqlite(action="create_table", db_path=temp_db, table="t", columns={"id": "INTEGER"})
    sqlite(action="insert", db_path=temp_db, table="t", data=[{"id": 1}, {"id": 2}])

    res = sqlite(action="truncate", db_path=temp_db, table="t")
    assert res["success"] is False
    assert res.get("error_type") == "ConfirmationRequired"


def test_sqlite_export_import_csv_roundtrip(temp_db, temp_dir):
    """Export a table to CSV, then import into a new table."""
    from pathlib import Path
    from strands_pack import sqlite

    sqlite(action="create_table", db_path=temp_db, table="users", columns={"id": "INTEGER", "name": "TEXT"})
    sqlite(
        action="insert",
        db_path=temp_db,
        table="users",
        data=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
    )

    csv_path = str(Path(temp_dir) / "users.csv")
    exp = sqlite(action="export_csv", db_path=temp_db, table="users", csv_path=csv_path)
    assert exp["success"] is True
    assert exp["rows_exported"] == 2

    imp = sqlite(
        action="import_csv",
        db_path=temp_db,
        table="users2",
        csv_path=csv_path,
        create_table_if_missing=True,
    )
    assert imp["success"] is True

    q = sqlite(action="query", db_path=temp_db, sql="SELECT COUNT(*) as c FROM users2")
    assert q["results"][0]["c"] == 2


def test_sqlite_vacuum(temp_db):
    """VACUUM should succeed on file-backed DB."""
    from strands_pack import sqlite

    sqlite(action="create_table", db_path=temp_db, table="t", columns={"id": "INTEGER"})
    res = sqlite(action="vacuum", db_path=temp_db)
    assert res["success"] is True
    assert res["action"] == "vacuum"


def test_sqlite_execute_raw_sql(temp_db):
    """Test executing raw SQL."""
    from strands_pack import sqlite

    result = sqlite(
        action="execute",
        db_path=temp_db,
        sql="CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)",
    )

    assert result["success"] is True
    assert result["action"] == "execute"


def test_sqlite_memory_database():
    """Test using in-memory database."""
    from strands_pack import sqlite

    # Note: Each call creates a new in-memory DB, so this just tests the path works
    result = sqlite(
        action="execute",
        db_path=":memory:",
        sql="CREATE TABLE test (id INTEGER)",
    )

    assert result["success"] is True


def test_sqlite_invalid_table_name(temp_db):
    """Test error on invalid table name."""
    from strands_pack import sqlite

    result = sqlite(
        action="create_table",
        db_path=temp_db,
        table="users; DROP TABLE--",
        columns={"id": "INTEGER"},
    )

    assert result["success"] is False
    assert "Invalid table name" in result["error"]


def test_sqlite_missing_db_path():
    """Test error when db_path is missing."""
    from strands_pack import sqlite

    result = sqlite(action="list_tables")

    assert result["success"] is False
    assert "db_path" in result["error"]


def test_sqlite_unknown_action():
    """Test error for unknown action."""
    from strands_pack import sqlite

    result = sqlite(action="unknown_action", db_path=":memory:")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result


def test_sqlite_env_default_db_path(temp_db, monkeypatch):
    """If SQLITE_DB_PATH is set, db_path can be omitted."""
    from strands_pack import sqlite

    monkeypatch.setenv("SQLITE_DB_PATH", temp_db)
    sqlite(action="create_table", table="t", columns={"id": "INTEGER"})
    res = sqlite(action="list_tables")
    assert res["success"] is True
    assert "t" in res["tables"]
