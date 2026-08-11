from fabcopilot.application.exceptions import EquipmentAlreadyExistsError
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
        if self._repository.get_by_id(equipment_id) is not None:
            raise EquipmentAlreadyExistsError(equipment_id)

        equipment = Equipment(
            equipment_id=equipment_id,
            equipment_type=equipment_type,
        )
        self._repository.add(equipment)
        return equipment
