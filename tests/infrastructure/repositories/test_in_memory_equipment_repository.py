from fabcopilot.domain.equipment import Equipment, EquipmentType
from fabcopilot.infrastructure.repositories.in_memory_equipment_repository import (
    InMemoryEquipmentRepository,
)


def test_repository_adds_and_gets_equipment() -> None:
    repository = InMemoryEquipmentRepository()
    equipment = Equipment(
        equipment_id="DF-01",
        equipment_type=EquipmentType.DIFFUSION_FURNACE,
    )

    repository.add(equipment)

    assert repository.get_by_id("DF-01") is equipment


def test_repository_returns_none_for_unknown_equipment_id() -> None:
    repository = InMemoryEquipmentRepository()

    assert repository.get_by_id("UNKNOWN") is None
