from fabcopilot.application.services.create_equipment import (
    CreateEquipmentService,
)
from fabcopilot.domain.equipment import EquipmentType
from fabcopilot.infrastructure.repositories.in_memory_equipment_repository import (
    InMemoryEquipmentRepository,
)


def test_create_equipment_service_saves_equipment() -> None:
    repository = InMemoryEquipmentRepository()
    service = CreateEquipmentService(repository)

    equipment = service.execute(
        equipment_id="DF-01",
        equipment_type=EquipmentType.DIFFUSION_FURNACE,
    )

    assert repository.get_by_id("DF-01") is equipment
