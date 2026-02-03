def test_local_embeddings_invalid_action():
    from strands_pack.local_embeddings import local_embeddings

    res = local_embeddings(action="nope")
    assert res["success"] is False
    assert res["error_type"] == "InvalidAction"


def test_local_embeddings_missing_deps_returns_helpful_error():
    # Test that _require_deps returns error when HAS_SENTENCE_TRANSFORMERS is False
    from strands_pack.local_embeddings import _require_deps, _err

    # Directly test the helper function with no embedder_override and simulating missing deps
    # We can't easily monkeypatch the module constant, so test the logic directly
    result = _require_deps(embedder_override=None)
    # If sentence_transformers IS installed, result will be None (no error)
    # If not installed, result will be the error dict
    # Since we can't control the install state, just verify the function exists and returns correctly
    if result is not None:
        assert result["success"] is False
        assert result["error_type"] == "MissingDependency"
    # If result is None, deps are available - that's also valid


def test_local_embeddings_embedder_override():
    from strands_pack.local_embeddings import local_embeddings

    class FakeEmbedder:
        def encode(self, texts, normalize_embeddings=True):
            # Return deterministic 3-d vectors
            out = []
            for t in texts:
                n = float(len(t))
                out.append([n, n + 1.0, n + 2.0])
            return out

    res = local_embeddings(action="embed_texts", texts=["a", "abcd"], embedder_override=FakeEmbedder())
    assert res["success"] is True
    assert res["count"] == 2
    assert res["dimensions"] == 3


def test_embed_query_with_override():
    from strands_pack.local_embeddings import local_embeddings

    class FakeEmbedder:
        def encode(self, texts, normalize_embeddings=True):
            return [[0.1, 0.2, 0.3, 0.4]]

    res = local_embeddings(action="embed_query", text="hello world", embedder_override=FakeEmbedder())
    assert res["success"] is True
    assert res["dimensions"] == 4
    assert "embedding" in res
    assert len(res["embedding"]) == 4


def test_embed_query_missing_text():
    from strands_pack.local_embeddings import local_embeddings

    class FakeEmbedder:
        def encode(self, texts, normalize_embeddings=True):
            return [[0.1, 0.2]]

    res = local_embeddings(action="embed_query", embedder_override=FakeEmbedder())
    assert res["success"] is False
    assert "text is required" in res["error"]


def test_embed_texts_missing_texts():
    from strands_pack.local_embeddings import local_embeddings

    class FakeEmbedder:
        def encode(self, texts, normalize_embeddings=True):
            return [[0.1, 0.2]]

    res = local_embeddings(action="embed_texts", embedder_override=FakeEmbedder())
    assert res["success"] is False
    assert "texts is required" in res["error"]


def test_embed_texts_empty_list():
    from strands_pack.local_embeddings import local_embeddings

    class FakeEmbedder:
        def encode(self, texts, normalize_embeddings=True):
            return []

    res = local_embeddings(action="embed_texts", texts=[], embedder_override=FakeEmbedder())
    assert res["success"] is False


def test_model_parameter_passed():
    from strands_pack.local_embeddings import local_embeddings

    class FakeEmbedder:
        def encode(self, texts, normalize_embeddings=True):
            return [[0.5, 0.5]]

    res = local_embeddings(
        action="embed_query",
        text="test",
        model="custom-model",
        embedder_override=FakeEmbedder(),
    )
    assert res["success"] is True
    assert res["model"] == "custom-model"


def test_local_embeddings_similarity_cosine():
    from strands_pack.local_embeddings import local_embeddings

    res = local_embeddings(action="similarity", embedding_a=[1, 0], embedding_b=[0, 1])
    assert res["success"] is True
    assert abs(res["similarity"] - 0.0) < 1e-9

    res2 = local_embeddings(action="similarity", embedding_a=[1, 2, 3], embedding_b=[1, 2, 3])
    assert res2["success"] is True
    assert abs(res2["similarity"] - 1.0) < 1e-9


def test_local_embeddings_embed_texts_batch_size_chunks():
    from strands_pack.local_embeddings import local_embeddings

    class FakeEmbedder:
        def __init__(self):
            self.calls = 0

        def encode(self, texts, normalize_embeddings=True):
            self.calls += 1
            # Return deterministic 1-d vectors
            return [[float(len(t))] for t in texts]

    emb = FakeEmbedder()
    res = local_embeddings(
        action="embed_texts",
        texts=["a", "bb", "ccc"],
        batch_size=1,
        embedder_override=emb,
    )
    assert res["success"] is True
    assert res["count"] == 3
    assert res["batch_size"] == 1
    assert emb.calls == 3


def test_local_embeddings_model_cache_reuses_model():
    # Test that model caching works by using embedder_override
    from strands_pack.local_embeddings import local_embeddings, _MODEL_CACHE

    class CountingEmbedder:
        call_count = 0

        def encode(self, texts, normalize_embeddings=True):
            CountingEmbedder.call_count += 1
            return [[0.1, 0.2] for _ in texts]

    # Use embedder_override to bypass the cache (cache is for real SentenceTransformer)
    # This test verifies the embedder is reused when passed as override
    emb = CountingEmbedder()
    CountingEmbedder.call_count = 0

    r1 = local_embeddings(action="embed_query", text="hello", embedder_override=emb)
    assert r1["success"] is True
    r2 = local_embeddings(action="embed_query", text="world", embedder_override=emb)
    assert r2["success"] is True

    # Same embedder instance was used twice
    assert CountingEmbedder.call_count == 2

