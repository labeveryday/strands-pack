"""
OpenAI Embeddings Tool

Generate embeddings using the OpenAI API.

Requires:
    pip install "strands-pack[openai_embeddings]"

Environment:
  - OPENAI_API_KEY (required unless you pass client_override)

Actions
-------
- embed_texts
    Parameters:
      - texts (list[str], required)
      - model (str, default "text-embedding-3-small")
      - dimensions (int, optional)  # supported by text-embedding-3-* models
      - normalize (bool, default True)  # optional client-side normalization for parity

- embed_query
    Parameters:
      - text (str, required)
      - model (str, default "text-embedding-3-small")
      - dimensions (int, optional)  # supported by text-embedding-3-* models
      - normalize (bool, default True)  # optional client-side normalization for parity

- similarity
    Compute cosine similarity between two embeddings.
    Parameters:
      - embedding_a (list[float], required)
      - embedding_b (list[float], required)
      - normalize_inputs (bool, default True)

Notes
-----
For unit tests / advanced usage, you can pass `client_override` to avoid network calls.
"""

from __future__ import annotations

import math
import os
from typing import Any, Dict, List, Optional

from strands import tool

try:
    from openai import OpenAI

    HAS_OPENAI = True
except ImportError:  # pragma: no cover
    OpenAI = None
    HAS_OPENAI = False


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


def _require_deps(client_override: Any) -> Optional[Dict[str, Any]]:
    if client_override is not None:
        return None
    if HAS_OPENAI:
        return None
    return _err(
        "Missing OpenAI dependency. Install with: pip install strands-pack[openai_embeddings]",
        error_type="MissingDependency",
    )


def _get_client(client_override: Any):
    if client_override is not None:
        return client_override
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    return OpenAI(api_key=api_key)


def _extract_embeddings(resp: Any) -> List[List[float]]:
    # OpenAI python client returns an object with .data; each item has .embedding
    data = getattr(resp, "data", None)
    if data is None:
        raise ValueError("Unexpected embeddings response (missing data)")
    out: List[List[float]] = []
    for item in data:
        emb = getattr(item, "embedding", None)
        if emb is None:
            raise ValueError("Unexpected embeddings response (missing embedding)")
        out.append([float(x) for x in emb])
    return out


def _l2_normalize(vec: List[float]) -> List[float]:
    n = math.sqrt(sum(x * x for x in vec))
    if n == 0.0:
        return vec
    return [x / n for x in vec]


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

    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    if na == 0.0 or nb == 0.0:
        raise ValueError("embeddings must not be all zeros")
    return sum(x * y for x, y in zip(a, b)) / (na * nb)


@tool
def openai_embeddings(
    action: str,
    text: Optional[str] = None,
    texts: Optional[List[str]] = None,
    model: str = "text-embedding-3-small",
    dimensions: Optional[int] = None,
    normalize: bool = True,
    embedding_a: Optional[List[float]] = None,
    embedding_b: Optional[List[float]] = None,
    normalize_inputs: bool = True,
    client_override: Any = None,
) -> Dict[str, Any]:
    """
    Generate embeddings using the OpenAI API.

    Args:
        action: One of:
            - "embed_query": Embed a single text string
            - "embed_texts": Embed multiple texts at once
            - "similarity": Compute cosine similarity between two embeddings
        text: The text to embed (for embed_query action).
        texts: List of texts to embed (for embed_texts action).
        model: Model name (default "text-embedding-3-small"). Options:
            - "text-embedding-3-small" (1536 dims, fast, cheap)
            - "text-embedding-3-large" (3072 dims, better quality)
            - "text-embedding-ada-002" (legacy, 1536 dims)
        dimensions: Optional output embedding dimensions (supported by text-embedding-3-* models).
        normalize: Whether to L2-normalize embeddings client-side (default True). This is mostly
            for parity with local embeddings tooling and downstream cosine similarity.
        embedding_a: First embedding vector (for similarity).
        embedding_b: Second embedding vector (for similarity).
        normalize_inputs: Whether to normalize inputs when computing similarity (default True).
        client_override: Optional custom OpenAI client for testing.

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

    if err := _require_deps(client_override):
        return err

    try:
        client = _get_client(client_override)

        dims = None
        if dimensions is not None:
            dims = int(dimensions)
            if dims <= 0:
                return _err("dimensions must be a positive integer")

        if action == "embed_query":
            if text is None or str(text).strip() == "":
                return _err("text is required")
            kwargs = {}
            if dims is not None:
                kwargs["dimensions"] = dims
            resp = client.embeddings.create(model=model, input=[str(text)], **kwargs)
            vecs = _extract_embeddings(resp)
            v0 = vecs[0]
            if normalize:
                v0 = _l2_normalize(v0)
            return _ok(model=model, dimensions=len(v0), embedding=v0, normalize=normalize, requested_dimensions=dims)

        if not isinstance(texts, list) or not texts:
            return _err("texts is required (list[str])")
        cleaned = [str(t) for t in texts]
        kwargs = {}
        if dims is not None:
            kwargs["dimensions"] = dims
        resp = client.embeddings.create(model=model, input=cleaned, **kwargs)
        vecs = _extract_embeddings(resp)
        if normalize:
            vecs = [_l2_normalize(v) for v in vecs]
        dims = len(vecs[0]) if vecs else 0
        return _ok(
            model=model,
            dimensions=dims,
            embeddings=vecs,
            count=len(vecs),
            normalize=normalize,
            requested_dimensions=dimensions,
        )

    except Exception as e:
        hint = None
        if "dimensions" in str(e).lower():
            hint = "If you set dimensions, use a text-embedding-3-* model and a supported dimensions value."
        return _err(str(e), error_type=type(e).__name__, action=action, hint=hint)


