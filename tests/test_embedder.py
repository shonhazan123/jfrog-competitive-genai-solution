def test_get_embedder_returns_object_with_embed():
    from agent.llm import get_embedder
    e = get_embedder()
    assert hasattr(e, "embed")
