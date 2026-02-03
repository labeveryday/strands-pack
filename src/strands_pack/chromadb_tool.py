"""
ChromaDB Tool

Vector database for embeddings and semantic search.

Requires:
    pip install strands-pack[chromadb]

Supported actions
-----------------
- create_collection
    Parameters: name (required), metadata (optional), embedding_function (optional)
- get_collection
    Parameters: name (required)
- list_collections
    Parameters: none
- delete_collection
    Parameters: name (required)
- add
    Parameters: collection (required), documents (optional), embeddings (optional),
                ids (required), metadatas (optional)
- query
    Parameters: collection (required), query_texts (optional), query_embeddings (optional),
                n_results (default 10), where (optional), where_document (optional)
- get
    Parameters: collection (required), ids (optional), where (optional),
                where_document (optional), limit (optional)
- update
    Parameters: collection (required), ids (required), documents (optional),
                embeddings (optional), metadatas (optional)
- upsert
    Parameters: collection (required), ids (required), documents (optional),
                embeddings (optional), metadatas (optional)
- delete
    Parameters: collection (required), ids (optional), where (optional), where_document (optional)
- count
    Parameters: collection (required)
- peek
    Parameters: collection (required), limit (default 10)
- get_or_create_collection
    Parameters: name (required), metadata (optional)
- modify_collection
    Parameters: name (required), metadata (optional)

Notes:
  - By default uses persistent storage at ./chroma_data
  - Set persist_directory to change storage location
  - Use ":memory:" as persist_directory for in-memory only
  - ChromaDB auto-generates embeddings using default model if not provided
  - Or set CHROMA_PERSIST_DIRECTORY in your environment to change the default location
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from strands import tool

# Lazy import for chromadb
_chromadb = None
_client_cache: Dict[str, Any] = {}


def _get_chromadb():
    global _chromadb
    if _chromadb is None:
        try:
            import chromadb
            _chromadb = chromadb
        except ImportError:
            raise ImportError("chromadb not installed. Run: pip install strands-pack[chromadb]") from None
    return _chromadb


def _get_client(persist_directory: Optional[str] = None):
    """Get or create a ChromaDB client."""
    chromadb = _get_chromadb()

    # Default to local persistent storage
    if persist_directory is None:
        persist_directory = (
            os.environ.get("CHROMA_PERSIST_DIRECTORY")
            or os.environ.get("CHROMADB_PERSIST_DIRECTORY")
            or os.environ.get("STRANDS_CHROMA_PERSIST_DIRECTORY")
            or "./chroma_data"
        )

    # Check cache
    cache_key = persist_directory
    if cache_key in _client_cache:
        return _client_cache[cache_key]

    # Create client
    if persist_directory == ":memory:":
        client = chromadb.Client()
    else:
        path = Path(persist_directory).expanduser()
        path.mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=str(path))

    _client_cache[cache_key] = client
    return client


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


def _create_collection(name: str, metadata: Optional[Dict] = None,
                       persist_directory: Optional[str] = None,
                       **kwargs) -> Dict[str, Any]:
    """Create a new collection."""
    if not name:
        return _err("name is required")

    client = _get_client(persist_directory)

    collection = client.create_collection(
        name=name,
        metadata=metadata,
    )

    return _ok(
        action="create_collection",
        collection={
            "name": collection.name,
            "id": str(collection.id),
            "metadata": collection.metadata,
        },
    )


def _get_collection(name: str, persist_directory: Optional[str] = None,
                    **kwargs) -> Dict[str, Any]:
    """Get an existing collection."""
    if not name:
        return _err("name is required")

    client = _get_client(persist_directory)

    try:
        collection = client.get_collection(name=name)
    except Exception as e:
        if "does not exist" in str(e).lower():
            return _err(f"Collection not found: {name}", error_type="NotFound")
        raise

    return _ok(
        action="get_collection",
        collection={
            "name": collection.name,
            "id": str(collection.id),
            "metadata": collection.metadata,
            "count": collection.count(),
        },
    )


def _list_collections(persist_directory: Optional[str] = None,
                      **kwargs) -> Dict[str, Any]:
    """List all collections."""
    client = _get_client(persist_directory)

    collections = client.list_collections()

    return _ok(
        action="list_collections",
        collections=[
            {
                "name": c.name,
                "id": str(c.id),
                "metadata": c.metadata,
            }
            for c in collections
        ],
        count=len(collections),
    )


def _delete_collection(name: str, persist_directory: Optional[str] = None,
                       **kwargs) -> Dict[str, Any]:
    """Delete a collection."""
    if not name:
        return _err("name is required")

    client = _get_client(persist_directory)

    try:
        client.delete_collection(name=name)
    except Exception as e:
        if "does not exist" in str(e).lower():
            return _err(f"Collection not found: {name}", error_type="NotFound")
        raise

    return _ok(
        action="delete_collection",
        name=name,
        deleted=True,
    )


def _add(collection: str, ids: List[str], documents: Optional[List[str]] = None,
         embeddings: Optional[List[List[float]]] = None,
         metadatas: Optional[List[Dict]] = None,
         persist_directory: Optional[str] = None,
         **kwargs) -> Dict[str, Any]:
    """Add documents to a collection."""
    if not collection:
        return _err("collection is required")
    if not ids:
        return _err("ids is required")
    if not documents and not embeddings:
        return _err("Either documents or embeddings is required")

    client = _get_client(persist_directory)

    try:
        coll = client.get_collection(name=collection)
    except Exception as e:
        if "does not exist" in str(e).lower():
            return _err(f"Collection not found: {collection}", error_type="NotFound")
        raise

    add_kwargs = {"ids": ids}
    if documents:
        add_kwargs["documents"] = documents
    if embeddings:
        add_kwargs["embeddings"] = embeddings
    if metadatas:
        add_kwargs["metadatas"] = metadatas

    coll.add(**add_kwargs)

    return _ok(
        action="add",
        collection=collection,
        added=len(ids),
    )


def _query(collection: str, query_texts: Optional[List[str]] = None,
           query_embeddings: Optional[List[List[float]]] = None,
           n_results: int = 10, where: Optional[Dict] = None,
           where_document: Optional[Dict] = None,
           include: Optional[List[str]] = None,
           persist_directory: Optional[str] = None,
           **kwargs) -> Dict[str, Any]:
    """Query similar documents."""
    if not collection:
        return _err("collection is required")
    if not query_texts and not query_embeddings:
        return _err("Either query_texts or query_embeddings is required")

    client = _get_client(persist_directory)

    try:
        coll = client.get_collection(name=collection)
    except Exception as e:
        if "does not exist" in str(e).lower():
            return _err(f"Collection not found: {collection}", error_type="NotFound")
        raise

    query_kwargs = {
        "n_results": n_results,
        "include": include or ["documents", "metadatas", "distances"],
    }
    if query_texts:
        query_kwargs["query_texts"] = query_texts
    if query_embeddings:
        query_kwargs["query_embeddings"] = query_embeddings
    if where:
        query_kwargs["where"] = where
    if where_document:
        query_kwargs["where_document"] = where_document

    results = coll.query(**query_kwargs)

    # Format results
    formatted_results = []
    if results["ids"]:
        for i, id_list in enumerate(results["ids"]):
            query_results = []
            for j, doc_id in enumerate(id_list):
                result = {"id": doc_id}
                if results.get("documents") and results["documents"][i]:
                    result["document"] = results["documents"][i][j]
                if results.get("metadatas") and results["metadatas"][i]:
                    result["metadata"] = results["metadatas"][i][j]
                if results.get("distances") and results["distances"][i]:
                    result["distance"] = results["distances"][i][j]
                query_results.append(result)
            formatted_results.append(query_results)

    return _ok(
        action="query",
        collection=collection,
        results=formatted_results,
        n_results=n_results,
    )


def _get(collection: str, ids: Optional[List[str]] = None,
         where: Optional[Dict] = None, where_document: Optional[Dict] = None,
         limit: Optional[int] = None, include: Optional[List[str]] = None,
         persist_directory: Optional[str] = None,
         **kwargs) -> Dict[str, Any]:
    """Get documents from a collection."""
    if not collection:
        return _err("collection is required")

    client = _get_client(persist_directory)

    try:
        coll = client.get_collection(name=collection)
    except Exception as e:
        if "does not exist" in str(e).lower():
            return _err(f"Collection not found: {collection}", error_type="NotFound")
        raise

    get_kwargs = {
        "include": include or ["documents", "metadatas"],
    }
    if ids:
        get_kwargs["ids"] = ids
    if where:
        get_kwargs["where"] = where
    if where_document:
        get_kwargs["where_document"] = where_document
    if limit:
        get_kwargs["limit"] = limit

    results = coll.get(**get_kwargs)

    # Format results
    documents = []
    for i, doc_id in enumerate(results["ids"]):
        doc = {"id": doc_id}
        if results.get("documents") and i < len(results["documents"]):
            doc["document"] = results["documents"][i]
        if results.get("metadatas") and i < len(results["metadatas"]):
            doc["metadata"] = results["metadatas"][i]
        documents.append(doc)

    return _ok(
        action="get",
        collection=collection,
        documents=documents,
        count=len(documents),
    )


def _update(collection: str, ids: List[str], documents: Optional[List[str]] = None,
            embeddings: Optional[List[List[float]]] = None,
            metadatas: Optional[List[Dict]] = None,
            persist_directory: Optional[str] = None,
            **kwargs) -> Dict[str, Any]:
    """Update documents in a collection."""
    if not collection:
        return _err("collection is required")
    if not ids:
        return _err("ids is required")

    client = _get_client(persist_directory)

    try:
        coll = client.get_collection(name=collection)
    except Exception as e:
        if "does not exist" in str(e).lower():
            return _err(f"Collection not found: {collection}", error_type="NotFound")
        raise

    update_kwargs = {"ids": ids}
    if documents:
        update_kwargs["documents"] = documents
    if embeddings:
        update_kwargs["embeddings"] = embeddings
    if metadatas:
        update_kwargs["metadatas"] = metadatas

    coll.update(**update_kwargs)

    return _ok(
        action="update",
        collection=collection,
        updated=len(ids),
    )


def _upsert(
    collection: str,
    ids: List[str],
    documents: Optional[List[str]] = None,
    embeddings: Optional[List[List[float]]] = None,
    metadatas: Optional[List[Dict]] = None,
    persist_directory: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Add or update documents in a collection."""
    if not collection:
        return _err("collection is required")
    if not ids:
        return _err("ids is required")
    if documents is None and embeddings is None and metadatas is None:
        return _err("At least one of documents, embeddings, or metadatas is required")

    client = _get_client(persist_directory)
    try:
        coll = client.get_collection(name=collection)
    except Exception as e:
        if "does not exist" in str(e).lower():
            return _err(f"Collection not found: {collection}", error_type="NotFound")
        raise

    upsert_kwargs = {"ids": ids}
    if documents is not None:
        upsert_kwargs["documents"] = documents
    if embeddings is not None:
        upsert_kwargs["embeddings"] = embeddings
    if metadatas is not None:
        upsert_kwargs["metadatas"] = metadatas

    # Prefer native upsert when available.
    if hasattr(coll, "upsert"):
        coll.upsert(**upsert_kwargs)
        return _ok(action="upsert", collection=collection, upserted=len(ids), mode="native")

    # Fallback: emulate upsert by splitting ids into existing/new and calling update/add.
    try:
        existing = coll.get(ids=ids, include=[]).get("ids", [])
    except Exception:
        existing = []
    existing_set = set(existing or [])
    new_ids = [i for i in ids if i not in existing_set]
    old_ids = [i for i in ids if i in existing_set]

    def _slice(values: Optional[list], keep_ids: List[str]) -> Optional[list]:
        if values is None:
            return None
        if len(values) != len(ids):
            raise ValueError("Length of documents/embeddings/metadatas must match ids for upsert fallback")
        idx = [ids.index(i) for i in keep_ids]
        return [values[j] for j in idx]

    updated = 0
    added = 0

    if old_ids:
        upd = {"ids": old_ids}
        if documents is not None:
            upd["documents"] = _slice(documents, old_ids)
        if embeddings is not None:
            upd["embeddings"] = _slice(embeddings, old_ids)
        if metadatas is not None:
            upd["metadatas"] = _slice(metadatas, old_ids)
        coll.update(**upd)
        updated = len(old_ids)

    if new_ids:
        if documents is None and embeddings is None:
            return _err("Cannot add new ids without documents or embeddings (upsert fallback)")
        add = {"ids": new_ids}
        if documents is not None:
            add["documents"] = _slice(documents, new_ids)
        if embeddings is not None:
            add["embeddings"] = _slice(embeddings, new_ids)
        if metadatas is not None:
            add["metadatas"] = _slice(metadatas, new_ids)
        coll.add(**add)
        added = len(new_ids)

    return _ok(
        action="upsert",
        collection=collection,
        upserted=len(ids),
        mode="emulated",
        added=added,
        updated=updated,
    )


def _get_or_create_collection(
    name: str,
    metadata: Optional[Dict] = None,
    persist_directory: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Get an existing collection, or create it if missing."""
    if not name:
        return _err("name is required")

    client = _get_client(persist_directory)
    if hasattr(client, "get_or_create_collection"):
        coll = client.get_or_create_collection(name=name, metadata=metadata)
        return _ok(
            action="get_or_create_collection",
            collection={"name": coll.name, "id": str(coll.id), "metadata": coll.metadata, "count": coll.count()},
            mode="native",
        )

    try:
        coll = client.get_collection(name=name)
        return _ok(
            action="get_or_create_collection",
            collection={"name": coll.name, "id": str(coll.id), "metadata": coll.metadata, "count": coll.count()},
            mode="get",
        )
    except Exception as e:
        if "does not exist" not in str(e).lower():
            raise

    coll = client.create_collection(name=name, metadata=metadata)
    return _ok(
        action="get_or_create_collection",
        collection={"name": coll.name, "id": str(coll.id), "metadata": coll.metadata, "count": coll.count()},
        mode="create",
    )


def _modify_collection(
    name: str,
    metadata: Optional[Dict] = None,
    persist_directory: Optional[str] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Update collection metadata (best-effort; API varies by Chroma version)."""
    if not name:
        return _err("name is required")

    client = _get_client(persist_directory)
    # Try collection-level modify first
    try:
        coll = client.get_collection(name=name)
    except Exception as e:
        if "does not exist" in str(e).lower():
            return _err(f"Collection not found: {name}", error_type="NotFound")
        raise

    if metadata is None:
        metadata = {}

    # Chroma versions differ: collection.modify(metadata=...), or client.modify_collection(name, new_metadata=...)
    if hasattr(coll, "modify"):
        try:
            coll.modify(metadata=metadata)
            return _ok(action="modify_collection", name=name, metadata=metadata, mode="collection.modify")
        except TypeError:
            # Some versions use "new_metadata"
            coll.modify(new_metadata=metadata)
            return _ok(action="modify_collection", name=name, metadata=metadata, mode="collection.modify_new_metadata")

    if hasattr(client, "modify_collection"):
        try:
            client.modify_collection(name=name, new_metadata=metadata)
        except TypeError:
            client.modify_collection(name=name, metadata=metadata)
        return _ok(action="modify_collection", name=name, metadata=metadata, mode="client.modify_collection")

    return _err("modify_collection not supported by installed chromadb version", error_type="NotSupported")

def _delete(collection: str, ids: Optional[List[str]] = None,
            where: Optional[Dict] = None, where_document: Optional[Dict] = None,
            persist_directory: Optional[str] = None,
            **kwargs) -> Dict[str, Any]:
    """Delete documents from a collection."""
    if not collection:
        return _err("collection is required")
    if not ids and not where and not where_document:
        return _err("At least one of ids, where, or where_document is required")

    client = _get_client(persist_directory)

    try:
        coll = client.get_collection(name=collection)
    except Exception as e:
        if "does not exist" in str(e).lower():
            return _err(f"Collection not found: {collection}", error_type="NotFound")
        raise

    delete_kwargs = {}
    if ids:
        delete_kwargs["ids"] = ids
    if where:
        delete_kwargs["where"] = where
    if where_document:
        delete_kwargs["where_document"] = where_document

    coll.delete(**delete_kwargs)

    return _ok(
        action="delete",
        collection=collection,
        deleted=True,
    )


def _count(collection: str, persist_directory: Optional[str] = None,
           **kwargs) -> Dict[str, Any]:
    """Count documents in a collection."""
    if not collection:
        return _err("collection is required")

    client = _get_client(persist_directory)

    try:
        coll = client.get_collection(name=collection)
    except Exception as e:
        if "does not exist" in str(e).lower():
            return _err(f"Collection not found: {collection}", error_type="NotFound")
        raise

    count = coll.count()

    return _ok(
        action="count",
        collection=collection,
        count=count,
    )


def _peek(collection: str, limit: int = 10,
          persist_directory: Optional[str] = None,
          **kwargs) -> Dict[str, Any]:
    """Preview documents in a collection."""
    if not collection:
        return _err("collection is required")

    client = _get_client(persist_directory)

    try:
        coll = client.get_collection(name=collection)
    except Exception as e:
        if "does not exist" in str(e).lower():
            return _err(f"Collection not found: {collection}", error_type="NotFound")
        raise

    results = coll.peek(limit=limit)

    # Format results
    documents = []
    for i, doc_id in enumerate(results["ids"]):
        doc = {"id": doc_id}
        if results.get("documents") and i < len(results["documents"]):
            doc["document"] = results["documents"][i]
        if results.get("metadatas") and i < len(results["metadatas"]):
            doc["metadata"] = results["metadatas"][i]
        documents.append(doc)

    return _ok(
        action="peek",
        collection=collection,
        documents=documents,
        count=len(documents),
    )


_ACTIONS = {
    "create_collection": _create_collection,
    "get_collection": _get_collection,
    "get_or_create_collection": _get_or_create_collection,
    "list_collections": _list_collections,
    "delete_collection": _delete_collection,
    "modify_collection": _modify_collection,
    "add": _add,
    "query": _query,
    "get": _get,
    "update": _update,
    "upsert": _upsert,
    "delete": _delete,
    "count": _count,
    "peek": _peek,
}


@tool
def chromadb_tool(
    action: str,
    name: Optional[str] = None,
    collection: Optional[str] = None,
    persist_directory: Optional[str] = None,
    metadata: Optional[Dict] = None,
    ids: Optional[List[str]] = None,
    documents: Optional[List[str]] = None,
    embeddings: Optional[List[List[float]]] = None,
    metadatas: Optional[List[Dict]] = None,
    query_texts: Optional[List[str]] = None,
    query_embeddings: Optional[List[List[float]]] = None,
    n_results: int = 10,
    where: Optional[Dict] = None,
    where_document: Optional[Dict] = None,
    include: Optional[List[str]] = None,
    limit: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Vector database for embeddings and semantic search.

    Args:
        action: The action to perform. One of:
            - "create_collection": Create a new collection
            - "get_collection": Get an existing collection
            - "get_or_create_collection": Get an existing collection or create it if missing
            - "list_collections": List all collections
            - "delete_collection": Delete a collection
            - "modify_collection": Update collection metadata
            - "add": Add documents/embeddings to a collection
            - "query": Query similar documents (semantic search)
            - "get": Get documents by ID or filter
            - "update": Update documents in a collection
            - "upsert": Add or update documents in a collection
            - "delete": Delete documents from a collection
            - "count": Count documents in a collection
            - "peek": Preview documents in a collection
        name: Collection name (for create/get/delete_collection).
        collection: Collection name (for add/query/get/update/delete/count/peek).
        persist_directory: Storage directory (default ./chroma_data, use ":memory:" for RAM).
        metadata: Collection metadata dict.
        ids: Document IDs (required for add/update, optional for get/delete).
        documents: List of document strings.
        embeddings: List of embedding vectors (list of floats).
        metadatas: List of metadata dicts for each document.
        query_texts: Text strings to search for (for query action).
        query_embeddings: Embedding vectors to search for (for query action).
        n_results: Number of results to return (default 10, for query).
        where: Filter dict for metadata (e.g., {"category": "news"}).
        where_document: Filter dict for document content.
        include: Fields to include in results (documents, metadatas, distances).
        limit: Max documents to return (for get/peek).

    Returns:
        dict with success status and action-specific data

    Examples:
        >>> chromadb_tool(action="create_collection", name="docs")
        >>> chromadb_tool(action="add", collection="docs", ids=["1", "2"], documents=["Hello", "World"])
        >>> chromadb_tool(action="query", collection="docs", query_texts=["greeting"], n_results=5)
    """
    action = (action or "").strip().lower()

    if action not in _ACTIONS:
        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=list(_ACTIONS.keys()),
        )

    # Build kwargs for the action function
    kwargs: Dict[str, Any] = {}
    if name is not None:
        kwargs["name"] = name
    if collection is not None:
        kwargs["collection"] = collection
    if persist_directory is not None:
        kwargs["persist_directory"] = persist_directory
    if metadata is not None:
        kwargs["metadata"] = metadata
    if ids is not None:
        kwargs["ids"] = ids
    if documents is not None:
        kwargs["documents"] = documents
    if embeddings is not None:
        kwargs["embeddings"] = embeddings
    if metadatas is not None:
        kwargs["metadatas"] = metadatas
    if query_texts is not None:
        kwargs["query_texts"] = query_texts
    if query_embeddings is not None:
        kwargs["query_embeddings"] = query_embeddings
    kwargs["n_results"] = n_results
    if where is not None:
        kwargs["where"] = where
    if where_document is not None:
        kwargs["where_document"] = where_document
    if include is not None:
        kwargs["include"] = include
    if limit is not None:
        kwargs["limit"] = limit

    try:
        return _ACTIONS[action](**kwargs)
    except ImportError as e:
        return _err(str(e), error_type="ImportError")
    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)
