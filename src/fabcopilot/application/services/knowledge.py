from fabcopilot.application.ports.embedding_provider import EmbeddingProvider
from fabcopilot.application.ports.knowledge_repository import KnowledgeRepository
from fabcopilot.domain.equipment import EquipmentType
from fabcopilot.domain.knowledge import KnowledgeDocument, KnowledgeSearchResult


class IndexKnowledgeDocumentService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._repository = repository
        self._embedding_provider = embedding_provider

    def execute(self, document: KnowledgeDocument) -> None:
        embedding = self._embedding_provider.embed(
            f"{document.title}\n{document.content}"
        )
        self._validate_embedding(embedding)
        self._repository.save(document, embedding)

    def _validate_embedding(self, embedding: list[float]) -> None:
        if len(embedding) != self._embedding_provider.dimensions:
            raise ValueError("embedding dimensions do not match provider contract")


class SearchKnowledgeService:
    def __init__(
        self,
        repository: KnowledgeRepository,
        embedding_provider: EmbeddingProvider,
    ) -> None:
        self._repository = repository
        self._embedding_provider = embedding_provider

    def execute(
        self,
        query: str,
        equipment_type: EquipmentType,
        limit: int = 5,
    ) -> list[KnowledgeSearchResult]:
        if not query.strip():
            raise ValueError("query must not be blank")
        if not 1 <= limit <= 20:
            raise ValueError("limit must be between 1 and 20")

        query_embedding = self._embedding_provider.embed(query)
        if len(query_embedding) != self._embedding_provider.dimensions:
            raise ValueError("embedding dimensions do not match provider contract")

        return self._repository.hybrid_search(
            query=query,
            query_embedding=query_embedding,
            equipment_type=equipment_type,
            limit=limit,
        )
