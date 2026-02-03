def test_openai_embeddings_invalid_action():
    from strands_pack.openai_embeddings import openai_embeddings

    res = openai_embeddings(action="nope")
    assert res["success"] is False
    assert res["error_type"] == "InvalidAction"


def test_openai_embeddings_missing_deps_returns_helpful_error():
    # Test that _require_deps returns error when HAS_OPENAI is False
    from strands_pack.openai_embeddings import _require_deps

    # Directly test the helper function with no client_override
    result = _require_deps(client_override=None)
    # If openai IS installed, result will be None (no error)
    # If not installed, result will be the error dict
    if result is not None:
        assert result["success"] is False
        assert result["error_type"] == "MissingDependency"


def test_openai_embeddings_client_override():
    from strands_pack.openai_embeddings import openai_embeddings

    class Item:
        def __init__(self, embedding):
            self.embedding = embedding

    class Resp:
        def __init__(self, data):
            self.data = data

    class Embeddings:
        def create(self, model, input, **kwargs):
            # Return deterministic 2-d vectors
            return Resp([Item([1.0, 2.0]) for _ in input])

    class FakeClient:
        def __init__(self):
            self.embeddings = Embeddings()

    res = openai_embeddings(action="embed_texts", texts=["a", "b"], client_override=FakeClient())
    assert res["success"] is True
    assert res["count"] == 2
    assert res["dimensions"] == 2


def test_embed_query_with_override():
    from strands_pack.openai_embeddings import openai_embeddings

    class Item:
        def __init__(self, embedding):
            self.embedding = embedding

    class Resp:
        def __init__(self, data):
            self.data = data

    class Embeddings:
        def create(self, model, input, **kwargs):
            return Resp([Item([0.1, 0.2, 0.3, 0.4])])

    class FakeClient:
        def __init__(self):
            self.embeddings = Embeddings()

    res = openai_embeddings(action="embed_query", text="hello", client_override=FakeClient())
    assert res["success"] is True
    assert res["dimensions"] == 4
    assert "embedding" in res


def test_embed_query_missing_text():
    from strands_pack.openai_embeddings import openai_embeddings

    class FakeClient:
        pass

    res = openai_embeddings(action="embed_query", client_override=FakeClient())
    assert res["success"] is False
    assert "text is required" in res["error"]


def test_embed_texts_missing_texts():
    from strands_pack.openai_embeddings import openai_embeddings

    class FakeClient:
        pass

    res = openai_embeddings(action="embed_texts", client_override=FakeClient())
    assert res["success"] is False
    assert "texts is required" in res["error"]


def test_model_parameter_passed():
    from strands_pack.openai_embeddings import openai_embeddings

    class Item:
        def __init__(self, embedding):
            self.embedding = embedding

    class Resp:
        def __init__(self, data):
            self.data = data

    class Embeddings:
        def create(self, model, input, **kwargs):
            return Resp([Item([0.5, 0.5])])

    class FakeClient:
        def __init__(self):
            self.embeddings = Embeddings()

    res = openai_embeddings(
        action="embed_query",
        text="test",
        model="text-embedding-3-large",
        client_override=FakeClient(),
    )
    assert res["success"] is True
    assert res["model"] == "text-embedding-3-large"


def test_openai_embeddings_dimensions_passed():
    from strands_pack.openai_embeddings import openai_embeddings

    class Item:
        def __init__(self, embedding):
            self.embedding = embedding

    class Resp:
        def __init__(self, data):
            self.data = data

    class Embeddings:
        def __init__(self):
            self.last_kwargs = None

        def create(self, model, input, **kwargs):
            self.last_kwargs = kwargs
            return Resp([Item([1.0, 2.0]) for _ in input])

    class FakeClient:
        def __init__(self):
            self.embeddings = Embeddings()

    c = FakeClient()
    res = openai_embeddings(action="embed_query", text="hello", dimensions=256, client_override=c)
    assert res["success"] is True
    assert c.embeddings.last_kwargs["dimensions"] == 256


def test_openai_embeddings_normalize_parity():
    from strands_pack.openai_embeddings import openai_embeddings

    class Item:
        def __init__(self, embedding):
            self.embedding = embedding

    class Resp:
        def __init__(self, data):
            self.data = data

    class Embeddings:
        def create(self, model, input, **kwargs):
            return Resp([Item([3.0, 4.0])])

    class FakeClient:
        def __init__(self):
            self.embeddings = Embeddings()

    r_norm = openai_embeddings(action="embed_query", text="x", normalize=True, client_override=FakeClient())
    assert r_norm["success"] is True
    assert abs(r_norm["embedding"][0] - 0.6) < 1e-9
    assert abs(r_norm["embedding"][1] - 0.8) < 1e-9

    r_raw = openai_embeddings(action="embed_query", text="x", normalize=False, client_override=FakeClient())
    assert r_raw["success"] is True
    assert r_raw["embedding"] == [3.0, 4.0]


def test_openai_embeddings_similarity_cosine():
    from strands_pack.openai_embeddings import openai_embeddings

    res = openai_embeddings(action="similarity", embedding_a=[1, 0], embedding_b=[0, 1])
    assert res["success"] is True
    assert abs(res["similarity"] - 0.0) < 1e-9

