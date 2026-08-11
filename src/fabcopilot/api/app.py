from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Response, status
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import Engine, text

from fabcopilot import __version__
from fabcopilot.api.dependencies import (
    get_approval_service,
    get_create_equipment_service,
    get_diagnostic_agent_service,
    get_engine,
    get_get_equipment_service,
    get_index_knowledge_service,
    get_json_cache,
    get_natural_language_query_service,
    get_redis_client,
    get_search_knowledge_service,
    get_session_factory,
    require_api_key,
)
from fabcopilot.api.schemas.agent import (
    ApprovalDecisionRequest,
    ApprovalResponse,
    DiagnosticAgentRequest,
    DiagnosticAgentResponse,
)
from fabcopilot.api.schemas.analytics import (
    AnalyticsQueryRequest,
    AnalyticsQueryResponse,
)
from fabcopilot.api.schemas.equipment import (
    EquipmentCreateRequest,
    EquipmentResponse,
)
from fabcopilot.api.schemas.knowledge import (
    KnowledgeDocumentRequest,
    KnowledgeDocumentResponse,
    KnowledgeSearchResultResponse,
    NonBlankString,
    SearchLimit,
)
from fabcopilot.application.exceptions import (
    ApprovalNotFoundError,
    EquipmentAlreadyExistsError,
    InvalidApprovalTransitionError,
)
from fabcopilot.application.services.approval import ApprovalService
from fabcopilot.application.services.cached_diagnostic_agent import (
    CachedDiagnosticAgentService,
)
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
from fabcopilot.domain.agent import DiagnosticAgentResult
from fabcopilot.domain.analytics import AnalyticsQueryResult
from fabcopilot.domain.approval import ApprovalRequest
from fabcopilot.domain.equipment import Equipment, EquipmentType
from fabcopilot.domain.knowledge import KnowledgeDocument, KnowledgeSearchResult
from fabcopilot.infrastructure.cache import RedisJsonCache
from fabcopilot.infrastructure.observability import configure_logging, observe_request


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(Settings().log_level)
    yield

    get_json_cache.cache_clear()
    if get_redis_client.cache_info().currsize:
        get_redis_client().close()
        get_redis_client.cache_clear()
    get_session_factory.cache_clear()
    if get_engine.cache_info().currsize:
        get_engine().dispose()
        get_engine.cache_clear()


app = FastAPI(
    title="FabCopilot",
    version=__version__,
    lifespan=lifespan,
)
app.middleware("http")(observe_request)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/ready")
def readiness_check(
    engine: Annotated[Engine, Depends(get_engine)],
    cache: Annotated[RedisJsonCache, Depends(get_json_cache)],
) -> dict[str, object]:
    checks = {"postgres": False, "redis": False}
    try:
        with engine.connect() as connection:
            checks["postgres"] = connection.scalar(text("SELECT 1")) == 1
    except Exception:
        pass
    checks["redis"] = cache.ping()
    if not all(checks.values()):
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "checks": checks},
        )
    return {"status": "ready", "checks": checks}


@app.get("/metrics", include_in_schema=False)
def metrics() -> Response:
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.post(
    "/equipment",
    response_model=EquipmentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def create_equipment(
    request: EquipmentCreateRequest,
    service: Annotated[
        CreateEquipmentService,
        Depends(get_create_equipment_service),
    ],
) -> Equipment:
    try:
        return service.execute(
            equipment_id=request.equipment_id,
            equipment_type=request.equipment_type,
        )
    except EquipmentAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@app.get("/equipment/{equipment_id}", response_model=EquipmentResponse)
def get_equipment(
    equipment_id: str,
    service: Annotated[
        GetEquipmentService,
        Depends(get_get_equipment_service),
    ],
) -> Equipment:
    equipment = service.execute(equipment_id)

    if equipment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Equipment not found",
        )

    return equipment


@app.post(
    "/knowledge/documents",
    response_model=KnowledgeDocumentResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_api_key)],
)
def index_knowledge_document(
    request: KnowledgeDocumentRequest,
    service: Annotated[
        IndexKnowledgeDocumentService,
        Depends(get_index_knowledge_service),
    ],
    cache: Annotated[RedisJsonCache, Depends(get_json_cache)],
) -> KnowledgeDocument:
    document = KnowledgeDocument(
        document_id=request.document_id,
        equipment_type=request.equipment_type,
        title=request.title,
        content=request.content,
        source=request.source,
    )
    service.execute(document)
    cache.bump_version("knowledge")
    return document


@app.get(
    "/knowledge/search",
    response_model=list[KnowledgeSearchResultResponse],
)
def search_knowledge(
    query: NonBlankString,
    equipment_type: EquipmentType,
    service: Annotated[
        SearchKnowledgeService,
        Depends(get_search_knowledge_service),
    ],
    limit: SearchLimit = 5,
) -> list[KnowledgeSearchResult]:
    return service.execute(
        query=query,
        equipment_type=equipment_type,
        limit=limit,
    )


@app.post(
    "/analytics/query",
    response_model=AnalyticsQueryResponse,
    dependencies=[Depends(require_api_key)],
)
def query_analytics(
    request: AnalyticsQueryRequest,
    service: Annotated[
        NaturalLanguageQueryService,
        Depends(get_natural_language_query_service),
    ],
) -> AnalyticsQueryResult:
    return service.execute(request.question)


@app.post(
    "/agent/diagnose",
    response_model=DiagnosticAgentResponse,
    dependencies=[Depends(require_api_key)],
)
def diagnose(
    request: DiagnosticAgentRequest,
    service: Annotated[
        CachedDiagnosticAgentService,
        Depends(get_diagnostic_agent_service),
    ],
) -> DiagnosticAgentResult:
    return service.execute(request.prompt)


@app.get("/approvals/{approval_id}", response_model=ApprovalResponse)
def get_approval(
    approval_id: str,
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> ApprovalRequest:
    try:
        return service.get(approval_id)
    except ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        ) from exc


@app.post(
    "/approvals/{approval_id}/decision",
    response_model=ApprovalResponse,
    dependencies=[Depends(require_api_key)],
)
def decide_approval(
    approval_id: str,
    request: ApprovalDecisionRequest,
    service: Annotated[ApprovalService, Depends(get_approval_service)],
) -> ApprovalRequest:
    try:
        return service.decide(
            approval_id=approval_id,
            decision=request.decision,
            decided_by=request.decided_by,
            decision_note=request.decision_note,
        )
    except ApprovalNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        ) from exc
    except InvalidApprovalTransitionError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
