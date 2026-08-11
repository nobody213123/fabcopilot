from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class EquipmentRecord(Base):
    __tablename__ = "equipment"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(equipment_id)) > 0",
            name="ck_equipment_equipment_id_not_blank",
        ),
    )

    equipment_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    equipment_type: Mapped[str] = mapped_column(String(50), nullable=False)
