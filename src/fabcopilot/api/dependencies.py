from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from redis import Redis
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from fabcopilot.application.ports.equipment_repository import EquipmentRepository
from fabcopilot.application.ports.knowledge_repository import KnowledgeRepository
from fabcopilot.application.services.approval import ApprovalService
from fabcopilot.application.services.cached_diagnostic_agent import (
    CachedDiagnosticAgentService,
)
from fabcopilot.application.services.create_equipment import CreateEquipmentService
from fabcopilot.application.services.diagnostic_agent import DiagnosticAgentService
from fabcopilot.application.services.get_equipment import GetEquipmentService
from fabcopilot.application.services.knowledge import (
    IndexKnowledgeDocumentService,
    SearchKnowledgeService,
)
from fabcopilot.application.services.natural_language_query import (
    NaturalLanguageQueryService,
)
from fabcopilot.config import Settings
from fabcopilot.infrastructure.agent_models import (
    OpenAIResponsesAgentModel,
    RuleBasedDiagnosticAgentModel,
)
from fabcopilot.infrastructure.agent_tools import FabAgentToolRegistry
from fabcopilot.infrastructure.cache import RedisJsonCache
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
from fabcopilot.infrastructure.repositories.sqlalchemy_approval_repository import (
    SqlAlchemyApprovalRepository,
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


@lru_cache
def get_redis_client() -> Redis:
    return Redis.from_url(Settings().redis_url, decode_responses=True)


@lru_cache
def get_json_cache() -> RedisJsonCache:
    return RedisJsonCache(get_redis_client())


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


def get_approval_service(
    session: Annotated[Session, Depends(get_session)],
) -> ApprovalService:
    return ApprovalService(SqlAlchemyApprovalRepository(session))


@lru_cache
def get_agent_model() -> RuleBasedDiagnosticAgentModel | OpenAIResponsesAgentModel:
    settings = Settings()
    if settings.openai_api_key is None:
        return RuleBasedDiagnosticAgentModel()
    return OpenAIResponsesAgentModel(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.openai_model,
    )


def get_agent_tool_registry() -> Iterator[FabAgentToolRegistry]:
    session_factory = get_session_factory()
    with (
        session_factory.begin() as knowledge_session,
        session_factory.begin() as analytics_session,
        session_factory.begin() as approval_session,
    ):
        yield FabAgentToolRegistry(
            knowledge_search=SearchKnowledgeService(
                SqlAlchemyKnowledgeRepository(knowledge_session),
                get_embedding_provider(),
            ),
            analytics_query=NaturalLanguageQueryService(
                generator=get_sql_generator(),
                validator=get_sql_validator(),
                executor=SqlAlchemyReadOnlyQueryExecutor(analytics_session),
            ),
            approval_service=ApprovalService(
                SqlAlchemyApprovalRepository(approval_session)
            ),
        )


def get_diagnostic_agent_service(
    tool_registry: Annotated[FabAgentToolRegistry, Depends(get_agent_tool_registry)],
    cache: Annotated[RedisJsonCache, Depends(get_json_cache)],
) -> CachedDiagnosticAgentService:
    settings = Settings()
    service = DiagnosticAgentService(get_agent_model(), tool_registry)
    return CachedDiagnosticAgentService(
        delegate=service,
        cache=cache,
        ttl_seconds=settings.diagnostic_cache_ttl_seconds,
    )
