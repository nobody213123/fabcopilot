from fastapi.testclient import TestClient


def test_create_equipment(client: TestClient) -> None:
    response = client.post(
        "/equipment",
        json={"equipment_id": "DF-01", "equipment_type": "diffusion_furnace"},
    )
    assert response.status_code == 201
    assert response.json() == {
        "equipment_id": "DF-01",
        "equipment_type": "diffusion_furnace",
    }


def test_equipment_rejects_unknown_equipment_type(client: TestClient) -> None:
    response = client.post(
        "/equipment",
        json={"equipment_id": "DF-01", "equipment_type": "etcher"},
    )
    assert response.status_code == 422


def test_create_equipment_rejects_blank_equipment_id(client: TestClient) -> None:
    response = client.post(
        "/equipment",
        json={"equipment_id": "  ", "equipment_type": "diffusion_furnace"},
    )
    assert response.status_code == 422


def test_create_equipment_returns_409_for_duplicate_id(client: TestClient) -> None:
    payload = {
        "equipment_id": "DF-DUP-01",
        "equipment_type": "diffusion_furnace",
    }

    first_response = client.post("/equipment", json=payload)
    duplicate_response = client.post("/equipment", json=payload)

    assert first_response.status_code == 201
    assert duplicate_response.status_code == 409
    assert duplicate_response.json() == {
        "detail": "Equipment 'DF-DUP-01' already exists"
    }
