from fabcopilot.application.services.get_equipment import GetEquipmentService
from fabcopilot.domain.equipment import Equipment, EquipmentType
from fabcopilot.infrastructure.repositories.in_memory_equipment_repository import (
    InMemoryEquipmentRepository,
)


def test_get_equipment_service_returns_saved_equipment() -> None:
    repository = InMemoryEquipmentRepository()
    equipment = Equipment(
        equipment_id="DF-01",
        equipment_type=EquipmentType.DIFFUSION_FURNACE,
    )
    repository.add(equipment)
    service = GetEquipmentService(repository)

    result = service.execute("DF-01")

    assert result is equipment


def test_get_equipment_service_returns_none_for_unknown_id() -> None:
    repository = InMemoryEquipmentRepository()
    service = GetEquipmentService(repository)

    assert service.execute("UNKNOWN") is None
