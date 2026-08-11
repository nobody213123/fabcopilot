from unittest.mock import MagicMock, Mock

from sqlalchemy.orm import Session

from fabcopilot.domain.equipment import Equipment, EquipmentType
from fabcopilot.infrastructure.models import EquipmentRecord
from fabcopilot.infrastructure.repositories.sqlalchemy_equipment_repository import (
    SqlAlchemyEquipmentRepository,
)


def test_repository_maps_domain_equipment_to_database_record() -> None:
    session = MagicMock(spec=Session)
    repository = SqlAlchemyEquipmentRepository(session)
    equipment = Equipment("DF-01", EquipmentType.DIFFUSION_FURNACE)

    repository.add(equipment)

    record = session.add.call_args.args[0]
    assert isinstance(record, EquipmentRecord)
    assert record.equipment_id == "DF-01"
    assert record.equipment_type == "diffusion_furnace"
    session.flush.assert_called_once_with()


def test_repository_maps_database_record_to_domain_equipment() -> None:
    session = Mock(spec=Session)
    session.get.return_value = EquipmentRecord(
        equipment_id="DF-01",
        equipment_type="diffusion_furnace",
    )
    repository = SqlAlchemyEquipmentRepository(session)

    equipment = repository.get_by_id("DF-01")

    assert equipment == Equipment("DF-01", EquipmentType.DIFFUSION_FURNACE)
    session.get.assert_called_once_with(EquipmentRecord, "DF-01")


def test_repository_returns_none_when_record_does_not_exist() -> None:
    session = Mock(spec=Session)
    session.get.return_value = None
    repository = SqlAlchemyEquipmentRepository(session)

    assert repository.get_by_id("missing") is None
