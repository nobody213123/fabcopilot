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


def test_equipment_rejects_unknown_equipment_type() -> None:
    response = client.post(
        "/equipment",
        json={"equipment_id": "DF-01", "equipment_type": "etcher"},
    )
    assert response.status_code == 422


def test_create_equipment_rejects_blank_equipment_id() -> None:
    response = client.post(
        "/equipment",
        json={"equipment_id": "  ", "equipment_type": "diffusion_furnace"},
    )
    assert response.status_code == 422
