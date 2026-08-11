import math

from fabcopilot.infrastructure.embeddings import HashingEmbeddingProvider


def test_hashing_embedding_is_deterministic_and_normalized() -> None:
    provider = HashingEmbeddingProvider(dimensions=32)

    first = provider.embed("diffusion furnace temperature alarm")
    second = provider.embed("diffusion furnace temperature alarm")

    assert first == second
    assert len(first) == 32
    assert math.isclose(math.sqrt(sum(value * value for value in first)), 1.0)


def test_hashing_embedding_rejects_invalid_dimensions() -> None:
    try:
        HashingEmbeddingProvider(dimensions=0)
    except ValueError as exc:
        assert str(exc) == "dimensions must be positive"
    else:
        raise AssertionError("expected invalid dimensions to be rejected")
