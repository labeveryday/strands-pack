"""
Local Embeddings Tool

Generate embeddings locally (no API keys) for semantic search, clustering, and retrieval.

Default backend: SentenceTransformers (optional dependency).

Requires:
    pip install "strands-pack[local_embeddings]"

Actions
-------
- embed_texts
    Parameters:
      - texts (list[str], required)
      - model (str, default "all-MiniLM-L6-v2")
      - normalize (bool, default True)
      - batch_size (int, optional)  # chunk input texts to limit memory usage

- embed_query
    Parameters:
      - text (str, required)
      - model (str, default "all-MiniLM-L6-v2")
      - normalize (bool, default True)

- similarity
    Compute cosine similarity between two embeddings.
    Parameters:
      - embedding_a (list[float], required)
      - embedding_b (list[float], required)
      - normalize_inputs (bool, default True)

Notes
-----
For unit tests / advanced usage, you can pass `embedder_override` to avoid loading a model.
"""

from __future__ import annotations

import math
import os
import threading
from collections import OrderedDict
from typing import Any, Dict, List, Optional

from strands import tool

try:
    from sentence_transformers import SentenceTransformer

    HAS_SENTENCE_TRANSFORMERS = True
except ImportError:  # pragma: no cover
    SentenceTransformer = None
    HAS_SENTENCE_TRANSFORMERS = False


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


def _require_deps(embedder_override: Any) -> Optional[Dict[str, Any]]:
    if embedder_override is not None:
        return None
    if HAS_SENTENCE_TRANSFORMERS:
        return None
    return _err(
        "Missing local embeddings dependency. Install with: pip install strands-pack[local_embeddings]",
        error_type="MissingDependency",
    )


_MODEL_CACHE_LOCK = threading.Lock()
_MODEL_CACHE: "OrderedDict[str, Any]" = OrderedDict()


def _cache_max_size() -> int:
    """
    Max number of SentenceTransformer models to keep in-process.

    Controlled by STRANDS_PACK_LOCAL_EMBEDDINGS_CACHE_SIZE.
    - "0" disables caching
    - default: 2
    """
    raw = os.getenv("STRANDS_PACK_LOCAL_EMBEDDINGS_CACHE_SIZE", "2").strip()
    try:
        n = int(raw)
    except Exception:
        n = 2
    if n < 0:
        n = 0
    # keep a sane upper bound; these models can be large
    if n > 16:
        n = 16
    return n


def _get_embedder(model: str, embedder_override: Any):
    if embedder_override is not None:
        return embedder_override
    max_size = _cache_max_size()
    if max_size == 0:
        # SentenceTransformer() may download model weights on first run.
        return SentenceTransformer(model)

    with _MODEL_CACHE_LOCK:
        cached = _MODEL_CACHE.get(model)
        if cached is not None:
            _MODEL_CACHE.move_to_end(model, last=True)
            return cached

        embedder = SentenceTransformer(model)
        _MODEL_CACHE[model] = embedder
        _MODEL_CACHE.move_to_end(model, last=True)
        while len(_MODEL_CACHE) > max_size:
            _MODEL_CACHE.popitem(last=False)
        return embedder


def _to_list_of_floats(vec: Any) -> List[float]:
    # sentence-transformers may return numpy arrays; we normalize to plain list[float]
    if hasattr(vec, "tolist"):
        vec = vec.tolist()
    return [float(x) for x in vec]


def _cosine_similarity(a: List[float], b: List[float], *, normalize_inputs: bool = True) -> float:
    if len(a) != len(b):
        raise ValueError("embeddings must have the same length")
    if not a:
        raise ValueError("embeddings must not be empty")

    if normalize_inputs:
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0.0 or nb == 0.0:
            raise ValueError("embeddings must not be all zeros")
        return sum((x / na) * (y / nb) for x, y in zip(a, b))

    # raw cosine; guard against zero vectors
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        raise ValueError("embeddings must not be all zeros")
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


@tool
def local_embeddings(
    action: str,
    text: Optional[str] = None,
    texts: Optional[List[str]] = None,
    model: str = "all-MiniLM-L6-v2",
    normalize: bool = True,
    batch_size: Optional[int] = None,
    embedding_a: Optional[List[float]] = None,
    embedding_b: Optional[List[float]] = None,
    normalize_inputs: bool = True,
    embedder_override: Any = None,
) -> Dict[str, Any]:
    """
    Generate embeddings locally using SentenceTransformers (no API keys required).

    Args:
        action: One of:
            - "embed_query": Embed a single text string
            - "embed_texts": Embed multiple texts at once
            - "similarity": Compute cosine similarity between two embeddings
        text: The text to embed (for embed_query action).
        texts: List of texts to embed (for embed_texts action).
        model: Model name (default "all-MiniLM-L6-v2"). Popular options:
            - "all-MiniLM-L6-v2" (fast, 384 dims)
            - "all-mpnet-base-v2" (better quality, 768 dims)
            - "paraphrase-MiniLM-L6-v2" (paraphrase detection)
        normalize: Whether to L2-normalize embeddings (default True).
        batch_size: Optional chunk size for embed_texts to limit memory usage.
        embedding_a: First embedding vector (for similarity).
        embedding_b: Second embedding vector (for similarity).
        normalize_inputs: Whether to normalize inputs when computing similarity (default True).
        embedder_override: Optional custom embedder for testing.

    Returns:
        dict with:
            - success: bool
            - embedding: list[float] (for embed_query)
            - embeddings: list[list[float]] (for embed_texts)
            - dimensions: int
            - model: str
    """
    action = (action or "").strip().lower()

    if action not in ("embed_texts", "embed_query", "similarity"):
        return _err(
            f"Unknown action: {action}",
            error_type="InvalidAction",
            available_actions=["embed_texts", "embed_query", "similarity"],
        )

    if action == "similarity":
        try:
            if not isinstance(embedding_a, list) or not isinstance(embedding_b, list):
                return _err("embedding_a and embedding_b are required (list[float])")
            a = [float(x) for x in embedding_a]
            b = [float(x) for x in embedding_b]
            sim = float(_cosine_similarity(a, b, normalize_inputs=bool(normalize_inputs)))
            return _ok(similarity=sim, distance=1.0 - sim, metric="cosine", normalize_inputs=bool(normalize_inputs))
        except Exception as e:
            return _err(str(e), error_type=type(e).__name__, action=action)

    if err := _require_deps(embedder_override):
        return err

    try:
        embedder = _get_embedder(model=model, embedder_override=embedder_override)

        if action == "embed_query":
            if text is None or str(text).strip() == "":
                return _err("text is required")
            vectors = embedder.encode([str(text)], normalize_embeddings=normalize)
            v0 = _to_list_of_floats(vectors[0])
            return _ok(model=model, dimensions=len(v0), embedding=v0, normalize=normalize)

        # embed_texts
        if not isinstance(texts, list) or not texts:
            return _err("texts is required (list[str])")
        cleaned = [str(t) for t in texts]
        # Chunk to reduce peak memory usage for large inputs.
        bs = None if batch_size is None else int(batch_size)
        if bs is not None and bs <= 0:
            bs = None
        if bs is None:
            vectors = embedder.encode(cleaned, normalize_embeddings=normalize)
            out_vecs = [_to_list_of_floats(v) for v in vectors]
        else:
            out_vecs: List[List[float]] = []
            for i in range(0, len(cleaned), bs):
                chunk = cleaned[i : i + bs]
                vectors = embedder.encode(chunk, normalize_embeddings=normalize)
                out_vecs.extend(_to_list_of_floats(v) for v in vectors)
        dims = len(out_vecs[0]) if out_vecs else 0
        return _ok(
            model=model,
            dimensions=dims,
            embeddings=out_vecs,
            count=len(out_vecs),
            normalize=normalize,
            batch_size=bs,
        )

    except Exception as e:
        return _err(str(e), error_type=type(e).__name__, action=action)


