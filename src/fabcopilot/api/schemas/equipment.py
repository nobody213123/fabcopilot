from pydantic import BaseModel

from fabcopilot.domain.equipment import EquipmentType


class EquipmentCreateRequest(BaseModel):
    equipment_id: str
    equipment_type: EquipmentType
