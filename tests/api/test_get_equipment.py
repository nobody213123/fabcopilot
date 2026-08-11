from fastapi.testclient import TestClient

from fabcopilot.api.app import app

client = TestClient(app)


def test_get_equipment_by_id() -> None:
    create_response = client.post(
        "/equipment",
        json={
            "equipment_id": "DF-GET-01",
            "equipment_type": "diffusion_furnace",
        },
    )
    assert create_response.status_code == 201

    response = client.get("/equipment/DF-GET-01")

    assert response.status_code == 200
    assert response.json() == {
        "equipment_id": "DF-GET-01",
        "equipment_type": "diffusion_furnace",
    }


def test_get_equipment_returns_404_for_unknown_id() -> None:
    response = client.get("/equipment/UNKNOWN")

    assert response.status_code == 404
    assert response.json() == {"detail": "Equipment not found"}
