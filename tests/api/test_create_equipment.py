from fastapi.testclient import TestClient

from fabcopilot.api.app import app

client = TestClient(app)


def test_create_equipment() -> None:
    response = client.post(
        "/equipment",
        json={"equipment_id": "DF-01", "equipment_type": "diffusion_furnace"},
    )
    assert response.status_code == 201
    assert response.json() == {
        "equipment_id": "DF-01",
        "equipment_type": "diffusion_furnace",
    }
