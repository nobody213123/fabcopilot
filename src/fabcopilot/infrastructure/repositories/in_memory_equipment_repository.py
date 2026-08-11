from fabcopilot.domain.equipment import Equipment


class InMemoryEquipmentRepository:
    def __init__(self) -> None:
        self._equipment_by_id: dict[str, Equipment] = {}

    def add(self, equipment: Equipment) -> None:
        self._equipment_by_id[equipment.equipment_id] = equipment

    def get_by_id(self, equipment_id: str) -> Equipment | None:
        return self._equipment_by_id.get(equipment_id)
