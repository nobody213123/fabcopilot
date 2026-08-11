from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from fabcopilot.api.app import app
from fabcopilot.api.dependencies import get_equipment_repository
from fabcopilot.infrastructure.repositories.in_memory_equipment_repository import (
    InMemoryEquipmentRepository,
)


@pytest.fixture
def client() -> Iterator[TestClient]:
    repository = InMemoryEquipmentRepository()
    app.dependency_overrides[get_equipment_repository] = lambda: repository

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()
