from datetime import datetime

from pgvector.sqlalchemy import VECTOR
from sqlalchemy import CheckConstraint, Computed, DateTime, Index, String, Text, func
from sqlalchemy.dialects.postgresql import TSVECTOR
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
