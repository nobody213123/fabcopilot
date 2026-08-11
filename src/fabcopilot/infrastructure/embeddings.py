import hashlib
import math
import re
import warnings
from collections.abc import Iterable
from threading import Lock
from typing import Protocol

EMBEDDING_DIMENSIONS = 1536
DEFAULT_FASTEMBED_MODEL = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
_TOKEN_PATTERN = re.compile(r"[a-zA-Z0-9_-]+|[\u4e00-\u9fff]")


class _FastEmbedModel(Protocol):
    def embed(self, documents: Iterable[str]) -> Iterable[object]: ...


class HashingEmbeddingProvider:
    """Deterministic offline embedding for development and repeatable tests."""

    def __init__(self, dimensions: int = EMBEDDING_DIMENSIONS) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self._dimensions = dimensions

    @property
    def dimensions(self) -> int:
        return self._dimensions

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dimensions
        for token in _TOKEN_PATTERN.findall(text.lower()):
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=16).digest()
            index = int.from_bytes(digest[:8], "big") % self._dimensions
            sign = 1.0 if digest[8] & 1 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]


class FastEmbedEmbeddingProvider:
    """Local multilingual semantic embeddings backed by quantized ONNX.

    The PostgreSQL vector column predates this provider and has 1536 dimensions.
    FastEmbed models commonly emit shorter vectors; zero-padding preserves cosine
    similarity while allowing a no-data-loss migration path for the prototype.
    """

    def __init__(
        self,
        model_name: str = DEFAULT_FASTEMBED_MODEL,
        dimensions: int = EMBEDDING_DIMENSIONS,
        cache_dir: str | None = None,
    ) -> None:
        if not model_name.strip():
            raise ValueError("model_name must not be blank")
        if dimensions <= 0:
            raise ValueError("dimensions must be positive")
        self._model_name = model_name
        self._dimensions = dimensions
        self._cache_dir = cache_dir
        self._model: _FastEmbedModel | None = None
        self._lock = Lock()

    @property
    def dimensions(self) -> int:
        return self._dimensions

    @property
    def model_name(self) -> str:
        return self._model_name

    def embed(self, text: str) -> list[float]:
        if not text.strip():
            return [0.0] * self._dimensions
        raw = next(iter(self._get_model().embed([text])))
        vector = [float(value) for value in raw]  # type: ignore[union-attr]
        if len(vector) > self._dimensions:
            raise ValueError(
                f"embedding model emitted {len(vector)} dimensions, exceeding "
                f"the storage contract of {self._dimensions}"
            )
        if len(vector) < self._dimensions:
            vector.extend([0.0] * (self._dimensions - len(vector)))
        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0.0:
            return vector
        return [value / norm for value in vector]

    def _get_model(self) -> _FastEmbedModel:
        if self._model is not None:
            return self._model
        with self._lock:
            if self._model is None:
                from fastembed import TextEmbedding

                # FastEmbed 0.7 warns that this model now uses mean pooling.
                # Mean pooling matches the upstream SentenceTransformers model
                # card and is the behavior this provider intentionally targets.
                with warnings.catch_warnings():
                    warnings.filterwarnings(
                        "ignore",
                        message="The model .* now uses mean pooling instead of CLS.*",
                        category=UserWarning,
                    )
                    self._model = TextEmbedding(
                        model_name=self._model_name,
                        cache_dir=self._cache_dir,
                    )
        return self._model


def create_embedding_provider(
    provider_name: str,
    model_name: str = DEFAULT_FASTEMBED_MODEL,
    cache_dir: str | None = None,
) -> HashingEmbeddingProvider | FastEmbedEmbeddingProvider:
    if provider_name == "hashing":
        return HashingEmbeddingProvider()
    if provider_name == "fastembed":
        return FastEmbedEmbeddingProvider(
            model_name=model_name,
            cache_dir=cache_dir,
        )
    raise ValueError(f"unsupported embedding provider: {provider_name}")
