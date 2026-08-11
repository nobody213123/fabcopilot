"""add multilingual trigram search

Revision ID: bc42f447db2b
Revises: d51a31dabd71
Create Date: 2026-08-11 23:50:00

"""

from typing import Sequence, Union

from alembic import op

revision: str = "bc42f447db2b"
down_revision: Union[str, Sequence[str], None] = "d51a31dabd71"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.create_index(
        "ix_knowledge_document_title_trgm",
        "knowledge_document",
        ["title"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
    op.create_index(
        "ix_knowledge_document_content_trgm",
        "knowledge_document",
        ["content"],
        unique=False,
        postgresql_using="gin",
        postgresql_ops={"content": "gin_trgm_ops"},
    )


def downgrade() -> None:
    op.drop_index(
        "ix_knowledge_document_content_trgm",
        table_name="knowledge_document",
        postgresql_using="gin",
        postgresql_ops={"content": "gin_trgm_ops"},
    )
    op.drop_index(
        "ix_knowledge_document_title_trgm",
        table_name="knowledge_document",
        postgresql_using="gin",
        postgresql_ops={"title": "gin_trgm_ops"},
    )
