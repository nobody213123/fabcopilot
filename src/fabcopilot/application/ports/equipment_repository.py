from typing import Protocol

from fabcopilot.domain.equipment import Equipment


class EquipmentRepository(Protocol):
    def add(self, equipment: Equipment) -> None: ...

    def get_by_id(self, equipment_id: str) -> Equipment | None: ...
