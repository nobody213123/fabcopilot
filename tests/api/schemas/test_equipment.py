import pytest
from pydantic import ValidationError

from fabcopilot.api.schemas.equipment import EquipmentCreateRequest
from fabcopilot.domain.equipment import EquipmentType


def test_equipment_create_request_parses_equipment_type() -> None:
    request = EquipmentCreateRequest.model_validate(
        {
            "equipment_id": "DF-01",
            "equipment_type": "diffusion_furnace",
        }
    )

    assert request.equipment_type is EquipmentType.DIFFUSION_FURNACE


def test_equipment_create_request_rejects_unknown_equipment_type() -> None:
    with pytest.raises(ValidationError):
        EquipmentCreateRequest.model_validate(
            {
                "equipment_id": "DF-01",
                "equipment_type": "etcher",
            }
        )
