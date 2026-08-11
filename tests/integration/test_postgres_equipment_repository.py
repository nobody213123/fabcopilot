import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from fabcopilot.application.exceptions import EquipmentAlreadyExistsError
from fabcopilot.config import Settings
from fabcopilot.domain.equipment import Equipment, EquipmentType
from fabcopilot.infrastructure.database import create_database_engine
from fabcopilot.infrastructure.repositories.sqlalchemy_equipment_repository import (
    SqlAlchemyEquipmentRepository,
)

pytestmark = pytest.mark.integration


@pytest.fixture
def database_engine() -> Engine:
    engine = create_database_engine(Settings().database_url)
    yield engine
    engine.dispose()


def test_repository_round_trip_uses_postgresql(database_engine: Engine) -> None:
    connection = database_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        repository = SqlAlchemyEquipmentRepository(session)
        equipment = Equipment("DF-INTEGRATION-01", EquipmentType.DIFFUSION_FURNACE)

        repository.add(equipment)

        assert repository.get_by_id(equipment.equipment_id) == equipment
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


def test_repository_translates_duplicate_primary_key(database_engine: Engine) -> None:
    connection = database_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)

    try:
        repository = SqlAlchemyEquipmentRepository(session)
        equipment = Equipment("DF-INTEGRATION-02", EquipmentType.DIFFUSION_FURNACE)
        repository.add(equipment)

        with pytest.raises(EquipmentAlreadyExistsError):
            repository.add(equipment)
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()
