import pytest

from fabcopilot.domain.equipment import Equipment, EquipmentType


def test_equipment_can_be_created_with_valid_id() -> None:
    equipment = Equipment(
        equipment_id="DF-01",
        equipment_type=EquipmentType.DIFFUSION_FURNACE,
    )

    assert equipment.equipment_id == "DF-01"


@pytest.mark.parametrize(
    "invalid_id",
    ["", "   "],
    ids=["empty", "whitespace"],
)
def test_equipment_rejects_blank_id(invalid_id: str) -> None:
    with pytest.raises(ValueError):
        Equipment(
            equipment_id=invalid_id,
            equipment_type=EquipmentType.DIFFUSION_FURNACE,
        )
