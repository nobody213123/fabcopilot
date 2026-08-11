from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete

from fabcopilot.api.app import app
from fabcopilot.api.dependencies import get_session_factory
from fabcopilot.infrastructure.models import EquipmentRecord

pytestmark = pytest.mark.integration

EQUIPMENT_ID = "DF-API-INTEGRATION-01"


def delete_test_equipment() -> None:
    with get_session_factory().begin() as session:
        session.execute(
            delete(EquipmentRecord).where(
                EquipmentRecord.equipment_id == EQUIPMENT_ID,
            )
        )


@pytest.fixture
def postgres_client() -> Iterator[TestClient]:
    delete_test_equipment()

    with TestClient(app) as client:
        yield client
        delete_test_equipment()


def test_equipment_api_persists_across_requests(
    postgres_client: TestClient,
) -> None:
    payload = {
        "equipment_id": EQUIPMENT_ID,
        "equipment_type": "diffusion_furnace",
    }

    create_response = postgres_client.post("/equipment", json=payload)
    get_response = postgres_client.get(f"/equipment/{EQUIPMENT_ID}")
    duplicate_response = postgres_client.post("/equipment", json=payload)

    assert create_response.status_code == 201
    assert get_response.status_code == 200
    assert get_response.json() == payload
    assert duplicate_response.status_code == 409
