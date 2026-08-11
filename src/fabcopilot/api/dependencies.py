from fabcopilot.application.services.create_equipment import CreateEquipmentService
from fabcopilot.application.services.get_equipment import GetEquipmentService
from fabcopilot.infrastructure.repositories.in_memory_equipment_repository import (
    InMemoryEquipmentRepository,
)

equipment_repository = InMemoryEquipmentRepository()
create_equipment_service = CreateEquipmentService(equipment_repository)
get_equipment_service = GetEquipmentService(equipment_repository)
