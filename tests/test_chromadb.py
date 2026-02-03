"""Tests for ChromaDB tool."""

import tempfile

import pytest


@pytest.fixture
def temp_dir():
    """Create a temp directory for persistent storage."""
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_chromadb_create_collection(temp_dir):
    """Test creating a collection."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    result = chromadb_tool(
        action="create_collection",
        name="test_collection",
        persist_directory=temp_dir,
    )

    assert result["success"] is True
    assert result["action"] == "create_collection"
    assert result["collection"]["name"] == "test_collection"


def test_chromadb_create_collection_with_metadata(temp_dir):
    """Test creating a collection with metadata."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    result = chromadb_tool(
        action="create_collection",
        name="test_with_meta",
        metadata={"description": "A test collection"},
        persist_directory=temp_dir,
    )

    assert result["success"] is True
    assert result["collection"]["metadata"]["description"] == "A test collection"


def test_chromadb_get_collection(temp_dir):
    """Test getting a collection."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    # Create first
    chromadb_tool(
        action="create_collection",
        name="get_test",
        persist_directory=temp_dir,
    )

    # Then get
    result = chromadb_tool(
        action="get_collection",
        name="get_test",
        persist_directory=temp_dir,
    )

    assert result["success"] is True
    assert result["action"] == "get_collection"
    assert result["collection"]["name"] == "get_test"
    assert "count" in result["collection"]


def test_chromadb_get_collection_not_found(temp_dir):
    """Test error when collection doesn't exist."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    result = chromadb_tool(
        action="get_collection",
        name="nonexistent",
        persist_directory=temp_dir,
    )

    assert result["success"] is False
    assert "not found" in result["error"].lower() or "NotFound" in result.get("error_type", "")


def test_chromadb_list_collections(temp_dir):
    """Test listing collections."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    # Create some collections
    chromadb_tool(action="create_collection", name="list_test_1", persist_directory=temp_dir)
    chromadb_tool(action="create_collection", name="list_test_2", persist_directory=temp_dir)

    result = chromadb_tool(action="list_collections", persist_directory=temp_dir)

    assert result["success"] is True
    assert result["action"] == "list_collections"
    assert result["count"] >= 2
    names = [c["name"] for c in result["collections"]]
    assert "list_test_1" in names
    assert "list_test_2" in names


def test_chromadb_delete_collection(temp_dir):
    """Test deleting a collection."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    # Create first
    chromadb_tool(action="create_collection", name="to_delete", persist_directory=temp_dir)

    # Delete
    result = chromadb_tool(action="delete_collection", name="to_delete", persist_directory=temp_dir)

    assert result["success"] is True
    assert result["deleted"] is True

    # Verify it's gone
    get_result = chromadb_tool(action="get_collection", name="to_delete", persist_directory=temp_dir)
    assert get_result["success"] is False


def test_chromadb_add_documents(temp_dir):
    """Test adding documents to a collection."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    chromadb_tool(action="create_collection", name="add_test", persist_directory=temp_dir)

    result = chromadb_tool(
        action="add",
        collection="add_test",
        ids=["doc1", "doc2", "doc3"],
        documents=[
            "The quick brown fox",
            "jumps over the lazy dog",
            "Hello world",
        ],
        metadatas=[
            {"source": "test1"},
            {"source": "test2"},
            {"source": "test3"},
        ],
        persist_directory=temp_dir,
    )

    assert result["success"] is True
    assert result["action"] == "add"
    assert result["added"] == 3


def test_chromadb_query(temp_dir):
    """Test querying documents."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    chromadb_tool(action="create_collection", name="query_test", persist_directory=temp_dir)
    chromadb_tool(
        action="add",
        collection="query_test",
        ids=["doc1", "doc2", "doc3"],
        documents=[
            "Python is a programming language",
            "JavaScript is used for web development",
            "Machine learning uses Python extensively",
        ],
        persist_directory=temp_dir,
    )

    result = chromadb_tool(
        action="query",
        collection="query_test",
        query_texts=["programming with Python"],
        n_results=2,
        persist_directory=temp_dir,
    )

    assert result["success"] is True
    assert result["action"] == "query"
    assert len(result["results"]) == 1  # One query
    assert len(result["results"][0]) <= 2  # Up to 2 results


def test_chromadb_get_documents(temp_dir):
    """Test getting documents by ID."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    chromadb_tool(action="create_collection", name="get_docs_test", persist_directory=temp_dir)
    chromadb_tool(
        action="add",
        collection="get_docs_test",
        ids=["doc1", "doc2"],
        documents=["First document", "Second document"],
        persist_directory=temp_dir,
    )

    result = chromadb_tool(
        action="get",
        collection="get_docs_test",
        ids=["doc1"],
        persist_directory=temp_dir,
    )

    assert result["success"] is True
    assert result["action"] == "get"
    assert result["count"] == 1
    assert result["documents"][0]["id"] == "doc1"


def test_chromadb_update_documents(temp_dir):
    """Test updating documents."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    chromadb_tool(action="create_collection", name="update_test", persist_directory=temp_dir)
    chromadb_tool(
        action="add",
        collection="update_test",
        ids=["doc1"],
        documents=["Original content"],
        persist_directory=temp_dir,
    )

    result = chromadb_tool(
        action="update",
        collection="update_test",
        ids=["doc1"],
        documents=["Updated content"],
        persist_directory=temp_dir,
    )

    assert result["success"] is True
    assert result["action"] == "update"
    assert result["updated"] == 1


def test_chromadb_get_or_create_collection(temp_dir):
    """Get-or-create should create on first call and return on second."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    r1 = chromadb_tool(action="get_or_create_collection", name="goc_test", metadata={"a": 1}, persist_directory=temp_dir)
    assert r1["success"] is True
    assert r1["action"] == "get_or_create_collection"
    assert r1["collection"]["name"] == "goc_test"

    r2 = chromadb_tool(action="get_or_create_collection", name="goc_test", persist_directory=temp_dir)
    assert r2["success"] is True
    assert r2["collection"]["name"] == "goc_test"


def test_chromadb_modify_collection_metadata(temp_dir):
    """Modify collection metadata should update stored metadata."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    chromadb_tool(action="create_collection", name="meta_test", metadata={"v": 1}, persist_directory=temp_dir)
    mod = chromadb_tool(action="modify_collection", name="meta_test", metadata={"v": 2}, persist_directory=temp_dir)
    assert mod["success"] is True
    assert mod["action"] == "modify_collection"

    got = chromadb_tool(action="get_collection", name="meta_test", persist_directory=temp_dir)
    assert got["success"] is True
    # Some Chroma versions may merge/overwrite; we just assert key present and updated where possible.
    assert got["collection"]["metadata"] is not None
    assert got["collection"]["metadata"].get("v") == 2


def test_chromadb_upsert_documents(temp_dir):
    """Upsert should add new ids and update existing ids."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    chromadb_tool(action="create_collection", name="upsert_test", persist_directory=temp_dir)

    # Add doc1 with explicit embeddings (avoid embedding model downloads in tests)
    chromadb_tool(
        action="add",
        collection="upsert_test",
        ids=["doc1"],
        embeddings=[[0.0, 0.0]],
        documents=["old"],
        metadatas=[{"v": 1}],
        persist_directory=temp_dir,
    )

    # Upsert doc1 (update) + doc2 (insert)
    res = chromadb_tool(
        action="upsert",
        collection="upsert_test",
        ids=["doc1", "doc2"],
        embeddings=[[1.0, 1.0], [2.0, 2.0]],
        documents=["new", "second"],
        metadatas=[{"v": 2}, {"v": 3}],
        persist_directory=temp_dir,
    )
    assert res["success"] is True
    assert res["action"] == "upsert"
    assert res["upserted"] == 2

    # Verify by get
    got = chromadb_tool(action="get", collection="upsert_test", ids=["doc1", "doc2"], persist_directory=temp_dir)
    assert got["success"] is True
    assert got["count"] == 2
    docs_by_id = {d["id"]: d for d in got["documents"]}
    assert docs_by_id["doc1"]["document"] == "new"
    assert docs_by_id["doc2"]["document"] == "second"


def test_chromadb_env_default_persist_directory(temp_dir, monkeypatch):
    """If CHROMA_PERSIST_DIRECTORY is set, persist_directory can be omitted."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    monkeypatch.setenv("CHROMA_PERSIST_DIRECTORY", temp_dir)
    r = chromadb_tool(action="create_collection", name="env_default_test")
    assert r["success"] is True
    assert r["collection"]["name"] == "env_default_test"

    # Verify we can use the collection without specifying persist_directory
    chromadb_tool(action="add", collection="env_default_test", ids=["doc1"], documents=["Test content"])
    get_result = chromadb_tool(action="get", collection="env_default_test", ids=["doc1"])
    assert get_result["success"] is True
    assert get_result["documents"][0]["document"] == "Test content"


def test_chromadb_delete_documents(temp_dir):
    """Test deleting documents."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    chromadb_tool(action="create_collection", name="delete_docs_test", persist_directory=temp_dir)
    chromadb_tool(
        action="add",
        collection="delete_docs_test",
        ids=["doc1", "doc2"],
        documents=["First", "Second"],
        persist_directory=temp_dir,
    )

    result = chromadb_tool(
        action="delete",
        collection="delete_docs_test",
        ids=["doc1"],
        persist_directory=temp_dir,
    )

    assert result["success"] is True
    assert result["deleted"] is True

    # Verify deletion
    count_result = chromadb_tool(
        action="count",
        collection="delete_docs_test",
        persist_directory=temp_dir,
    )
    assert count_result["count"] == 1


def test_chromadb_count(temp_dir):
    """Test counting documents."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    chromadb_tool(action="create_collection", name="count_test", persist_directory=temp_dir)
    chromadb_tool(
        action="add",
        collection="count_test",
        ids=["doc1", "doc2", "doc3"],
        documents=["One", "Two", "Three"],
        persist_directory=temp_dir,
    )

    result = chromadb_tool(
        action="count",
        collection="count_test",
        persist_directory=temp_dir,
    )

    assert result["success"] is True
    assert result["action"] == "count"
    assert result["count"] == 3


def test_chromadb_peek(temp_dir):
    """Test peeking at documents."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    chromadb_tool(action="create_collection", name="peek_test", persist_directory=temp_dir)
    chromadb_tool(
        action="add",
        collection="peek_test",
        ids=["doc1", "doc2"],
        documents=["First", "Second"],
        persist_directory=temp_dir,
    )

    result = chromadb_tool(
        action="peek",
        collection="peek_test",
        limit=1,
        persist_directory=temp_dir,
    )

    assert result["success"] is True
    assert result["action"] == "peek"
    assert result["count"] <= 1


def test_chromadb_memory_mode():
    """Test in-memory mode."""
    try:
        import chromadb
    except ImportError:
        pytest.skip("chromadb not installed")

    from strands_pack import chromadb_tool

    # Clear the client cache for this test
    from strands_pack.chromadb_tool import _client_cache
    _client_cache.clear()

    result = chromadb_tool(
        action="create_collection",
        name="memory_test",
        persist_directory=":memory:",
    )

    assert result["success"] is True


def test_chromadb_missing_collection_name():
    """Test error when collection name is missing."""
    from strands_pack import chromadb_tool

    result = chromadb_tool(action="create_collection")

    assert result["success"] is False
    assert "name" in result["error"]


def test_chromadb_missing_ids_for_add():
    """Test error when ids are missing for add."""
    from strands_pack import chromadb_tool

    result = chromadb_tool(
        action="add",
        collection="test",
        documents=["test"],
    )

    assert result["success"] is False
    assert "ids" in result["error"]


def test_chromadb_unknown_action():
    """Test error for unknown action."""
    from strands_pack import chromadb_tool

    result = chromadb_tool(action="unknown_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result
