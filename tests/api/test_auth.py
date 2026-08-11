from fastapi.testclient import TestClient


def test_mutation_endpoint_rejects_invalid_configured_api_key(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("FABCOPILOT_API_KEY", "portfolio-secret")

    response = client.post(
        "/equipment",
        json={
            "equipment_id": "DF-AUTH-01",
            "equipment_type": "diffusion_furnace",
        },
    )

    assert response.status_code == 401


def test_mutation_endpoint_accepts_valid_configured_api_key(
    client: TestClient,
    monkeypatch,
) -> None:
    monkeypatch.setenv("FABCOPILOT_API_KEY", "portfolio-secret")

    response = client.post(
        "/equipment",
        headers={"X-API-Key": "portfolio-secret"},
        json={
            "equipment_id": "DF-AUTH-02",
            "equipment_type": "diffusion_furnace",
        },
    )

    assert response.status_code == 201
