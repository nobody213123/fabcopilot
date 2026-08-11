from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from fabcopilot.application.exceptions import EquipmentAlreadyExistsError
from fabcopilot.domain.equipment import Equipment, EquipmentType
from fabcopilot.infrastructure.models import EquipmentRecord


class SqlAlchemyEquipmentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def add(self, equipment: Equipment) -> None:
        record = EquipmentRecord(
            equipment_id=equipment.equipment_id,
            equipment_type=equipment.equipment_type.value,
        )
        try:
            with self._session.begin_nested():
                self._session.add(record)
                self._session.flush()
        except IntegrityError as exc:
            if getattr(exc.orig, "sqlstate", None) == "23505":
                raise EquipmentAlreadyExistsError(equipment.equipment_id) from exc
            raise

    def get_by_id(self, equipment_id: str) -> Equipment | None:
        record = self._session.get(EquipmentRecord, equipment_id)
        if record is None:
            return None

        return Equipment(
            equipment_id=record.equipment_id,
            equipment_type=EquipmentType(record.equipment_type),
        )
