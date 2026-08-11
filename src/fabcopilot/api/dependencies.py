from collections.abc import Iterator
from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from fabcopilot.application.ports.equipment_repository import EquipmentRepository
from fabcopilot.application.services.create_equipment import CreateEquipmentService
from fabcopilot.application.services.get_equipment import GetEquipmentService
from fabcopilot.config import Settings
from fabcopilot.infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from fabcopilot.infrastructure.repositories.sqlalchemy_equipment_repository import (
    SqlAlchemyEquipmentRepository,
)


@lru_cache
def get_engine() -> Engine:
    return create_database_engine(Settings().database_url)


@lru_cache
def get_session_factory() -> sessionmaker[Session]:
    return create_session_factory(get_engine())


def get_session() -> Iterator[Session]:
    with get_session_factory().begin() as session:
        yield session


def get_equipment_repository(
    session: Annotated[Session, Depends(get_session)],
) -> EquipmentRepository:
    return SqlAlchemyEquipmentRepository(session)


def get_create_equipment_service(
    repository: Annotated[EquipmentRepository, Depends(get_equipment_repository)],
) -> CreateEquipmentService:
    return CreateEquipmentService(repository)


def get_get_equipment_service(
    repository: Annotated[EquipmentRepository, Depends(get_equipment_repository)],
) -> GetEquipmentService:
    return GetEquipmentService(repository)
