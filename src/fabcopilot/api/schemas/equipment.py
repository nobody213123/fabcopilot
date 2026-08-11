from pydantic import BaseModel, field_validator

from fabcopilot.domain.equipment import EquipmentType


class EquipmentCreateRequest(BaseModel):
    equipment_id: str
    equipment_type: EquipmentType

    @field_validator("equipment_id")
    @classmethod
    def validate_equipment_id(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("equipment_id must not be blank")
        return value


class EquipmentResponse(BaseModel):
    equipment_id: str
    equipment_type: EquipmentType
