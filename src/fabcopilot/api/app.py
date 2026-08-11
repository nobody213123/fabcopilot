from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, status

from fabcopilot import __version__
from fabcopilot.api.dependencies import (
    get_approval_service,
    get_create_equipment_service,
    get_diagnostic_agent_service,
    get_engine,
    get_get_equipment_service,
    get_index_knowledge_service,
    get_natural_language_query_service,
    get_search_knowledge_service,
    get_session_factory,
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
from fabcopilot.domain.agent import DiagnosticAgentResult
from fabcopilot.domain.analytics import AnalyticsQueryResult
from fabcopilot.domain.approval import ApprovalRequest
from fabcopilot.domain.equipment import Equipment, EquipmentType
from fabcopilot.domain.knowledge import KnowledgeDocument, KnowledgeSearchResult


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield

    get_session_factory.cache_clear()
    if get_engine.cache_info().currsize:
        get_engine().dispose()
        get_engine.cache_clear()


app = FastAPI(
    title="FabCopilot",
    version=__version__,
    lifespan=lifespan,
)


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/equipment",
    response_model=EquipmentResponse,
    status_code=status.HTTP_201_CREATED,
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
)
def index_knowledge_document(
    request: KnowledgeDocumentRequest,
    service: Annotated[
        IndexKnowledgeDocumentService,
        Depends(get_index_knowledge_service),
    ],
) -> KnowledgeDocument:
    document = KnowledgeDocument(
        document_id=request.document_id,
        equipment_type=request.equipment_type,
        title=request.title,
        content=request.content,
        source=request.source,
    )
    service.execute(document)
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


@app.post("/analytics/query", response_model=AnalyticsQueryResponse)
def query_analytics(
    request: AnalyticsQueryRequest,
    service: Annotated[
        NaturalLanguageQueryService,
        Depends(get_natural_language_query_service),
    ],
) -> AnalyticsQueryResult:
    return service.execute(request.question)


@app.post("/agent/diagnose", response_model=DiagnosticAgentResponse)
def diagnose(
    request: DiagnosticAgentRequest,
    service: Annotated[
        DiagnosticAgentService,
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


@app.post("/approvals/{approval_id}/decision", response_model=ApprovalResponse)
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
