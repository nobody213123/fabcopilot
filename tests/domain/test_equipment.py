import pytest

from fabcopilot.domain.equipment import Equipment, EquipmentType


def test_equipment_can_be_created_with_valid_id() -> None:
    equipment = Equipment(
        equipment_id="DF-01",
        equipment_type=EquipmentType.DIFFUSION_FURNACE,
    )

    assert equipment.equipment_id == "DF-01"


def test_equipment_rejects_empty_id() -> None:
    with pytest.raises(ValueError):
        Equipment(
            equipment_id="",
            equipment_type=EquipmentType.DIFFUSION_FURNACE,
        )