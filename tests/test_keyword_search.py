"""Tests for keyword_search tool."""

import pytest

try:
    from rank_bm25 import BM25Okapi

    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False


@pytest.fixture(autouse=True)
def clear_index_cache():
    """Clear the index cache before each test."""
    from strands_pack.keyword_search import _index_cache
    _index_cache.clear()
    yield
    _index_cache.clear()


def _skip_if_no_bm25():
    if not HAS_BM25:
        pytest.skip("rank_bm25 not installed")


def test_create_index():
    """Test creating a BM25 index."""
    _skip_if_no_bm25()
    from strands_pack.keyword_search import keyword_search

    result = keyword_search(
        action="create_index",
        name="test",
        documents=["hello world", "foo bar baz"],
    )

    assert result["success"] is True
    assert result["action"] == "create_index"
    assert result["name"] == "test"
    assert result["document_count"] == 2


def test_search():
    """Test searching an index."""
    _skip_if_no_bm25()
    from strands_pack.keyword_search import keyword_search

    keyword_search(
        action="create_index",
        name="test",
        documents=[
            "python programming language",
            "javascript web development",
            "machine learning with python",
        ],
    )

    result = keyword_search(action="search", name="test", query="python", n_results=10)

    assert result["success"] is True
    assert result["action"] == "search"
    assert result["total_results"] > 0
    assert len(result["results"]) > 0
    # Each result has expected fields
    first = result["results"][0]
    assert "id" in first
    assert "document" in first
    assert "score" in first
    assert "rank" in first
    assert first["rank"] == 1


def test_search_relevance():
    """Test that BM25 ranks relevant docs higher."""
    _skip_if_no_bm25()
    from strands_pack.keyword_search import keyword_search

    keyword_search(
        action="create_index",
        name="relevance",
        documents=[
            "the cat sat on the mat",
            "retrieval augmented generation for NLP",
            "BM25 is a ranking function used in information retrieval",
            "the quick brown fox jumps over the lazy dog",
        ],
        ids=["cat", "rag", "bm25", "fox"],
    )

    result = keyword_search(action="search", name="relevance", query="information retrieval ranking")

    assert result["success"] is True
    assert result["total_results"] > 0
    # BM25 doc should rank first since it matches all query terms
    assert result["results"][0]["id"] == "bm25"


def test_add_documents():
    """Test adding documents to an existing index."""
    _skip_if_no_bm25()
    from strands_pack.keyword_search import keyword_search

    keyword_search(
        action="create_index",
        name="grow",
        documents=["original document about cats", "another document about dogs"],
    )

    result = keyword_search(
        action="add_documents",
        name="grow",
        documents=["new document about testing and validation"],
        ids=["new1"],
    )

    assert result["success"] is True
    assert result["action"] == "add_documents"
    assert result["added"] == 1
    assert result["total_documents"] == 3

    # Search should find the new doc
    search = keyword_search(action="search", name="grow", query="testing validation")
    assert search["success"] is True
    assert search["total_results"] > 0
    assert any(r["id"] == "new1" for r in search["results"])


def test_delete_index():
    """Test deleting an index."""
    _skip_if_no_bm25()
    from strands_pack.keyword_search import keyword_search

    keyword_search(action="create_index", name="deleteme", documents=["test"])

    result = keyword_search(action="delete_index", name="deleteme")

    assert result["success"] is True
    assert result["deleted"] is True

    # Verify it's gone
    search = keyword_search(action="search", name="deleteme", query="test")
    assert search["success"] is False
    assert "not found" in search["error"].lower()


def test_list_indexes():
    """Test listing all indexes."""
    _skip_if_no_bm25()
    from strands_pack.keyword_search import keyword_search

    keyword_search(action="create_index", name="idx1", documents=["doc1", "doc2"])
    keyword_search(action="create_index", name="idx2", documents=["doc3"])

    result = keyword_search(action="list_indexes")

    assert result["success"] is True
    assert result["action"] == "list_indexes"
    assert result["count"] == 2
    names = [idx["name"] for idx in result["indexes"]]
    assert "idx1" in names
    assert "idx2" in names

    # Check doc counts
    by_name = {idx["name"]: idx for idx in result["indexes"]}
    assert by_name["idx1"]["document_count"] == 2
    assert by_name["idx2"]["document_count"] == 1


def test_search_nonexistent_index():
    """Test error when searching a nonexistent index."""
    _skip_if_no_bm25()
    from strands_pack.keyword_search import keyword_search

    result = keyword_search(action="search", name="nonexistent", query="test")

    assert result["success"] is False
    assert "not found" in result["error"].lower()


def test_create_index_with_ids():
    """Test creating index with custom IDs."""
    _skip_if_no_bm25()
    from strands_pack.keyword_search import keyword_search

    result = keyword_search(
        action="create_index",
        name="custom_ids",
        documents=["alpha", "beta", "gamma"],
        ids=["a", "b", "c"],
    )

    assert result["success"] is True
    assert result["document_count"] == 3

    search = keyword_search(action="search", name="custom_ids", query="alpha")
    assert search["success"] is True
    assert search["results"][0]["id"] == "a"


def test_search_empty_query():
    """Test searching with empty query."""
    _skip_if_no_bm25()
    from strands_pack.keyword_search import keyword_search

    keyword_search(action="create_index", name="empty_q", documents=["test doc"])

    result = keyword_search(action="search", name="empty_q", query="")

    assert result["success"] is True
    assert result["total_results"] == 0
    assert result["results"] == []


def test_unknown_action():
    """Test error for unknown action."""
    from strands_pack.keyword_search import keyword_search

    result = keyword_search(action="bad_action")

    assert result["success"] is False
    assert "Unknown action" in result["error"]
    assert "available_actions" in result


def test_create_index_missing_name():
    """Test error when name is missing."""
    from strands_pack.keyword_search import keyword_search

    result = keyword_search(action="create_index", documents=["test"])

    assert result["success"] is False
    assert "name" in result["error"]


def test_create_index_missing_documents():
    """Test error when documents are missing."""
    from strands_pack.keyword_search import keyword_search

    result = keyword_search(action="create_index", name="test")

    assert result["success"] is False
    assert "documents" in result["error"]


def test_ids_length_mismatch():
    """Test error when ids and documents have different lengths."""
    _skip_if_no_bm25()
    from strands_pack.keyword_search import keyword_search

    result = keyword_search(
        action="create_index",
        name="mismatch",
        documents=["a", "b"],
        ids=["1"],
    )

    assert result["success"] is False
    assert "length" in result["error"].lower() or "match" in result["error"].lower()
