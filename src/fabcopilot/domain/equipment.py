from dataclasses import dataclass
from enum import StrEnum


class EquipmentType(StrEnum):
    DIFFUSION_FURNACE = "diffusion_furnace"


@dataclass(frozen=True)
class Equipment:
    equipment_id: str
    equipment_type: EquipmentType

    def __post_init__(self) -> None:
        if not self.equipment_id.strip():
            raise ValueError("equipment_id must not be blank")