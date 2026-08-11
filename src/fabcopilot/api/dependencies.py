from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from fabcopilot.application.ports.equipment_repository import EquipmentRepository
from fabcopilot.application.ports.knowledge_repository import KnowledgeRepository
from fabcopilot.application.services.create_equipment import CreateEquipmentService
from fabcopilot.application.services.get_equipment import GetEquipmentService
from fabcopilot.application.services.knowledge import (
    IndexKnowledgeDocumentService,
    SearchKnowledgeService,
)
from fabcopilot.application.services.natural_language_query import (
    NaturalLanguageQueryService,
)
from fabcopilot.config import Settings
from fabcopilot.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from fabcopilot.infrastructure.embeddings import HashingEmbeddingProvider
from fabcopilot.infrastructure.nl2sql import (
    RuleBasedSqlGenerator,
    SqlAlchemyReadOnlyQueryExecutor,
    SqlGlotSafetyValidator,
)
from fabcopilot.infrastructure.repositories.sqlalchemy_equipment_repository import (
    SqlAlchemyEquipmentRepository,
)
from fabcopilot.infrastructure.repositories.sqlalchemy_knowledge_repository import (
    SqlAlchemyKnowledgeRepository,
)


@lru_cache
def get_engine() -> Engine:
    return create_database_engine(Settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory(get_engine())


def get_session() -> Iterator[Session]:
    with get_session_factory().begin() as session:
        yield session


def get_equipment_repository(
    session: Annotated[Session, Depends(get_session)],
) -> EquipmentRepository:
    return SqlAlchemyEquipmentRepository(session)


def get_create_equipment_service(
    repository: Annotated[EquipmentRepository, Depends(get_equipment_repository)],
) -> CreateEquipmentService:
    return CreateEquipmentService(repository)


def get_get_equipment_service(
    repository: Annotated[EquipmentRepository, Depends(get_equipment_repository)],
) -> GetEquipmentService:
    return GetEquipmentService(repository)


@lru_cache
def get_embedding_provider() -> HashingEmbeddingProvider:
    return HashingEmbeddingProvider()


def get_knowledge_repository(
    session: Annotated[Session, Depends(get_session)],
) -> KnowledgeRepository:
    return SqlAlchemyKnowledgeRepository(session)


def get_index_knowledge_service(
    repository: Annotated[KnowledgeRepository, Depends(get_knowledge_repository)],
) -> IndexKnowledgeDocumentService:
    return IndexKnowledgeDocumentService(repository, get_embedding_provider())


def get_search_knowledge_service(
    repository: Annotated[KnowledgeRepository, Depends(get_knowledge_repository)],
) -> SearchKnowledgeService:
    return SearchKnowledgeService(repository, get_embedding_provider())


@lru_cache
def get_sql_generator() -> RuleBasedSqlGenerator:
    return RuleBasedSqlGenerator()


@lru_cache
def get_sql_validator() -> SqlGlotSafetyValidator:
    return SqlGlotSafetyValidator()


def get_natural_language_query_service(
    session: Annotated[Session, Depends(get_session)],
) -> NaturalLanguageQueryService:
    return NaturalLanguageQueryService(
        generator=get_sql_generator(),
        validator=get_sql_validator(),
        executor=SqlAlchemyReadOnlyQueryExecutor(session),
    )
