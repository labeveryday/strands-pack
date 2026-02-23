"""
Keyword Search Tool

BM25 keyword search for hybrid retrieval alongside vector search.

Actions
-------
- create_index: Build a BM25 index from documents (name, documents, ids)
- search: Search an existing index (name, query, n_results)
- add_documents: Add documents to an existing index (name, documents, ids)
- delete_index: Remove a cached index (name)
- list_indexes: List all cached index names with doc counts

Requirements:
    pip install strands-pack[keyword_search]
"""

from typing import Any, Dict, List, Optional

from strands import tool

try:
    from rank_bm25 import BM25Okapi

    HAS_BM25 = True
except ImportError:
    HAS_BM25 = False

# Module-level cache: name -> {"bm25": BM25Okapi, "documents": [...], "ids": [...], "tokenized": [...]}
_index_cache: Dict[str, Dict[str, Any]] = {}


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


def _check_bm25() -> Optional[Dict[str, Any]]:
    if not HAS_BM25:
        return _err("rank_bm25 not installed. Run: pip install strands-pack[keyword_search]", error_type="ImportError")
    return None


def _tokenize(text: str) -> List[str]:
    return text.lower().split()


@tool
def keyword_search(
    action: str,
    name: Optional[str] = None,
    documents: Optional[List[str]] = None,
    ids: Optional[List[str]] = None,
    query: Optional[str] = None,
    n_results: int = 10,
) -> Dict[str, Any]:
    """
    BM25 keyword search for hybrid retrieval alongside vector search.

    Args:
        action: The action to perform. One of:
            - "create_index": Build a BM25 index from documents.
            - "search": Search an existing index by keyword.
            - "add_documents": Add documents to an existing index (rebuilds index).
            - "delete_index": Remove a cached index.
            - "list_indexes": List all cached index names with document counts.
        name: Index name (required for create_index, search, add_documents, delete_index).
        documents: List of document strings (required for create_index, add_documents).
        ids: Optional list of document IDs. Auto-generated if not provided.
        query: Search query string (required for search action).
        n_results: Number of results to return (default 10, for search action).

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> keyword_search(action="create_index", name="papers", documents=["doc1 text", "doc2 text"])
        >>> keyword_search(action="search", name="papers", query="machine learning", n_results=5)
        >>> keyword_search(action="add_documents", name="papers", documents=["doc3 text"])
        >>> keyword_search(action="list_indexes")
    """
    action = (action or "").strip().lower()

    try:
        if action == "create_index":
            if err := _check_bm25():
                return err
            if not name:
                return _err("name is required")
            if not documents:
                return _err("documents is required (list of strings)")

            doc_ids = ids if ids else [str(i) for i in range(len(documents))]
            if len(doc_ids) != len(documents):
                return _err("ids length must match documents length")

            tokenized = [_tokenize(doc) for doc in documents]
            bm25 = BM25Okapi(tokenized)

            _index_cache[name] = {
                "bm25": bm25,
                "documents": list(documents),
                "ids": list(doc_ids),
                "tokenized": tokenized,
            }

            return _ok(
                action="create_index",
                name=name,
                document_count=len(documents),
            )

        if action == "search":
            if err := _check_bm25():
                return err
            if not name:
                return _err("name is required")
            if name not in _index_cache:
                return _err(f"Index not found: {name}", error_type="NotFound")
            if not query:
                return _ok(
                    action="search",
                    name=name,
                    query="",
                    results=[],
                    total_results=0,
                )

            index = _index_cache[name]
            tokenized_query = _tokenize(query)
            scores = index["bm25"].get_scores(tokenized_query)

            # Rank by score descending
            scored = sorted(
                zip(range(len(scores)), scores, strict=True),
                key=lambda x: x[1],
                reverse=True,
            )

            # Filter to top n_results with score > 0
            results = []
            for rank, (idx, score) in enumerate(scored[:n_results], start=1):
                if score <= 0:
                    break
                results.append({
                    "id": index["ids"][idx],
                    "document": index["documents"][idx],
                    "score": float(score),
                    "rank": rank,
                })

            return _ok(
                action="search",
                name=name,
                query=query,
                results=results,
                total_results=len(results),
            )

        if action == "add_documents":
            if err := _check_bm25():
                return err
            if not name:
                return _err("name is required")
            if name not in _index_cache:
                return _err(f"Index not found: {name}", error_type="NotFound")
            if not documents:
                return _err("documents is required (list of strings)")

            index = _index_cache[name]
            existing_count = len(index["documents"])

            new_ids = ids if ids else [str(existing_count + i) for i in range(len(documents))]
            if len(new_ids) != len(documents):
                return _err("ids length must match documents length")

            # Append documents and rebuild BM25
            index["documents"].extend(documents)
            index["ids"].extend(new_ids)
            new_tokenized = [_tokenize(doc) for doc in documents]
            index["tokenized"].extend(new_tokenized)
            index["bm25"] = BM25Okapi(index["tokenized"])

            return _ok(
                action="add_documents",
                name=name,
                added=len(documents),
                total_documents=len(index["documents"]),
            )

        if action == "delete_index":
            if not name:
                return _err("name is required")
            if name not in _index_cache:
                return _err(f"Index not found: {name}", error_type="NotFound")

            del _index_cache[name]

            return _ok(
                action="delete_index",
                name=name,
                deleted=True,
            )

        if action == "list_indexes":
            indexes = [
                {"name": idx_name, "document_count": len(idx_data["documents"])}
                for idx_name, idx_data in _index_cache.items()
            ]

            return _ok(
                action="list_indexes",
                indexes=indexes,
                count=len(indexes),
            )

        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=["create_index", "search", "add_documents", "delete_index", "list_indexes"],
        )

    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
