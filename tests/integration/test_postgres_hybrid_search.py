import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from fabcopilot.application.services.knowledge import (
    IndexKnowledgeDocumentService,
    SearchKnowledgeService,
)
from fabcopilot.config import Settings
from fabcopilot.domain.equipment import EquipmentType
from fabcopilot.domain.knowledge import KnowledgeDocument
from fabcopilot.infrastructure.database import create_database_engine
from fabcopilot.infrastructure.embeddings import HashingEmbeddingProvider
from fabcopilot.infrastructure.repositories.sqlalchemy_knowledge_repository import (
    SqlAlchemyKnowledgeRepository,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def database_engine() -> Engine:
    engine = create_database_engine(Settings().database_url)
    yield engine
    engine.dispose()


def test_hybrid_search_combines_lexical_and_vector_ranks(
    database_engine: Engine,
) -> None:
    connection = database_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        repository = SqlAlchemyKnowledgeRepository(session)
        embedding_provider = HashingEmbeddingProvider()
        index_service = IndexKnowledgeDocumentService(
            repository,
            embedding_provider,
        )
        search_service = SearchKnowledgeService(
            repository,
            embedding_provider,
        )
        index_service.execute(
            KnowledgeDocument(
                document_id="KB-INTEGRATION-TEMP",
                equipment_type=EquipmentType.DIFFUSION_FURNACE,
                title="Diffusion furnace temperature non-uniformity",
                content=(
                    "Inspect heater zones and thermocouple drift when the wafer "
                    "temperature profile exceeds the uniformity limit."
                ),
                source="diffusion-furnace-maintenance-manual",
            )
        )
        index_service.execute(
            KnowledgeDocument(
                document_id="KB-INTEGRATION-PARTICLE",
                equipment_type=EquipmentType.DIFFUSION_FURNACE,
                title="Quartz tube particle contamination",
                content=(
                    "Check boat handling, quartz tube deposits, and cleaning cycle "
                    "history when particle counts rise."
                ),
                source="diffusion-furnace-maintenance-manual",
            )
        )

        results = search_service.execute(
            query="thermocouple temperature drift",
            equipment_type=EquipmentType.DIFFUSION_FURNACE,
            limit=2,
        )

        assert results[0].document.document_id == "KB-INTEGRATION-TEMP"
        assert results[0].lexical_rank == 1
        assert results[0].vector_rank == 1
        assert results[0].score > results[1].score
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
