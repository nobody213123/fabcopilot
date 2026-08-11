from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from fabcopilot.api.app import app
from fabcopilot.api.dependencies import get_session_factory
from fabcopilot.infrastructure.models import KnowledgeDocumentRecord

pytestmark = pytest.mark.integration

DOCUMENT_IDS = ("KB-API-TEMP", "KB-API-PARTICLE")


def delete_test_documents() -> None:
    with get_session_factory().begin() as session:
        session.execute(
            delete(KnowledgeDocumentRecord).where(
                KnowledgeDocumentRecord.document_id.in_(DOCUMENT_IDS),
            )
        )


@pytest.fixture
def postgres_client() -> Iterator[TestClient]:
    delete_test_documents()

    with TestClient(app) as client:
        yield client
        delete_test_documents()


def test_knowledge_api_indexes_and_hybrid_searches_documents(
    postgres_client: TestClient,
) -> None:
    documents = [
        {
            "document_id": "KB-API-TEMP",
            "equipment_type": "diffusion_furnace",
            "title": "Diffusion furnace temperature non-uniformity",
            "content": "Inspect heater zones and thermocouple drift after an alarm.",
            "source": "maintenance-manual",
        },
        {
            "document_id": "KB-API-PARTICLE",
            "equipment_type": "diffusion_furnace",
            "title": "Quartz tube particle contamination",
            "content": "Inspect tube deposits and the wet cleaning cycle.",
            "source": "maintenance-manual",
        },
    ]
    for document in documents:
        response = postgres_client.post("/knowledge/documents", json=document)
        assert response.status_code == 201

    response = postgres_client.get(
        "/knowledge/search",
        params={
            "query": "thermocouple temperature drift",
            "equipment_type": "diffusion_furnace",
            "limit": 2,
        },
    )

    assert response.status_code == 200
    results = response.json()
    assert results[0]["document"]["document_id"] == "KB-API-TEMP"
    assert results[0]["lexical_rank"] == 1
    assert results[0]["vector_rank"] == 1
    assert results[0]["document"]["source"] == "maintenance-manual"
