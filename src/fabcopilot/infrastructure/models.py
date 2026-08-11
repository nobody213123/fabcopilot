from datetime import datetime

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import (
    CheckConstraint,
    Computed,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from fabcopilot.infrastructure.embeddings import EMBEDDING_DIMENSIONS


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


class KnowledgeDocumentRecord(Base):
    __tablename__ = "knowledge_document"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(document_id)) > 0",
            name="ck_knowledge_document_id_not_blank",
        ),
        CheckConstraint(
            "length(btrim(title)) > 0",
            name="ck_knowledge_document_title_not_blank",
        ),
        CheckConstraint(
            "length(btrim(content)) > 0",
            name="ck_knowledge_document_content_not_blank",
        ),
        Index(
            "ix_knowledge_document_search_vector",
            "search_vector",
            postgresql_using="gin",
        ),
        Index(
            "ix_knowledge_document_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    document_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    equipment_type: Mapped[str] = mapped_column(String(50), index=True)
    title: Mapped[str] = mapped_column(String(200))
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(500))
    embedding: Mapped[list[float]] = mapped_column(VECTOR(EMBEDDING_DIMENSIONS))
    search_vector: Mapped[str] = mapped_column(
        TSVECTOR,
        Computed(
            "to_tsvector('simple', coalesce(title, '') || ' ' || coalesce(content, ''))",
            persisted=True,
        ),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class ProcessRunRecord(Base):
    __tablename__ = "process_run"
    __table_args__ = (
        CheckConstraint(
            "yield_rate IS NULL OR (yield_rate >= 0 AND yield_rate <= 1)",
            name="ck_process_run_yield_rate_range",
        ),
        CheckConstraint(
            "ended_at IS NULL OR ended_at > started_at",
            name="ck_process_run_time_order",
        ),
        Index(
            "ix_process_run_equipment_started_at",
            "equipment_id",
            "started_at",
        ),
    )

    run_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    equipment_id: Mapped[str] = mapped_column(
        ForeignKey("equipment.equipment_id", ondelete="RESTRICT"),
    )
    lot_id: Mapped[str] = mapped_column(String(64), index=True)
    recipe: Mapped[str] = mapped_column(String(100))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    yield_rate: Mapped[float | None] = mapped_column(Numeric(6, 5))
    status: Mapped[str] = mapped_column(String(20))


class AlarmEventRecord(Base):
    __tablename__ = "alarm_event"
    __table_args__ = (
        CheckConstraint(
            "cleared_at IS NULL OR cleared_at >= occurred_at",
            name="ck_alarm_event_time_order",
        ),
        Index(
            "ix_alarm_event_equipment_occurred_at",
            "equipment_id",
            "occurred_at",
        ),
        Index(
            "ix_alarm_event_code_occurred_at",
            "alarm_code",
            "occurred_at",
        ),
    )

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    equipment_id: Mapped[str] = mapped_column(
        ForeignKey("equipment.equipment_id", ondelete="RESTRICT"),
    )
    alarm_code: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    message: Mapped[str] = mapped_column(String(500))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ApprovalRequestRecord(Base):
    __tablename__ = "approval_request"
    __table_args__ = (
        Index("ix_approval_request_status_requested_at", "status", "requested_at"),
    )

    approval_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    equipment_id: Mapped[str] = mapped_column(
        ForeignKey("equipment.equipment_id", ondelete="RESTRICT"),
    )
    action_type: Mapped[str] = mapped_column(String(50))
    reason: Mapped[str] = mapped_column(String(1000))
    parameters: Mapped[dict[str, object]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20))
    requested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    decided_by: Mapped[str | None] = mapped_column(String(100))
    decision_note: Mapped[str | None] = mapped_column(String(1000))
