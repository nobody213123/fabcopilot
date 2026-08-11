from fabcopilot.application.ports.equipment_repository import EquipmentRepository
from fabcopilot.domain.equipment import Equipment


class GetEquipmentService:
    def __init__(self, repository: EquipmentRepository) -> None:
        self._repository = repository

    def execute(self, equipment_id: str) -> Equipment | None:
        return self._repository.get_by_id(equipment_id)
