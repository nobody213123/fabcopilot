from fabcopilot.application.ports.equipment_repository import EquipmentRepository
from fabcopilot.domain.equipment import Equipment, EquipmentType


class CreateEquipmentService:
    def __init__(self, repository: EquipmentRepository) -> None:
        self._repository = repository

    def execute(
        self,
        equipment_id: str,
        equipment_type: EquipmentType,
    ) -> Equipment:
        equipment = Equipment(
            equipment_id=equipment_id,
            equipment_type=equipment_type,
        )
        self._repository.add(equipment)
        return equipment
