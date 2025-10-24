"""Initial schema

Revision ID: 79e4affc14ec
Revises: 
Create Date: 2025-10-11 15:20:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision: str = '79e4affc14ec'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("email", sa.String(), unique=True, nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
    )

    # Create papers table
    op.create_table(
        "papers",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("abstract", sa.Text(), nullable=True),
        sa.Column("authors", sa.Text(), nullable=True),
        sa.Column("arxiv_id", sa.String(), nullable=True),
        sa.Column("url", sa.Text(), nullable=True),
        sa.Column("published_at", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("status", sa.String(), server_default="pending"),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.UniqueConstraint("user_id", "arxiv_id", name="unique_user_arxiv"),
    )

    # Create summaries table
    op.create_table(
        "summaries",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("summary_type", sa.String(), nullable=True),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("paper_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE")),
    )

    # Create chat table
    op.create_table(
        "chat",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("chat_session_id", sa.Integer(), nullable=False),
        sa.Column("query", sa.String(), nullable=False),
        sa.Column("answer", sa.String(), nullable=False),
        sa.Column("cot_transcript", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("user_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
    )
    op.create_index("ix_chat_chat_session_id", "chat", ["chat_session_id"], unique=False)

    # Create embeddings table
    op.create_table(
        "embeddings",
        sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("chunk_id", sa.Integer(), nullable=True),
        sa.Column("vector", Vector(768)),  # pgvector column
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP")),
        sa.Column("paper_id", sa.dialects.postgresql.UUID(as_uuid=True), sa.ForeignKey("papers.id", ondelete="CASCADE")),
    )


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("embeddings")
    op.drop_index("ix_chat_chat_session_id", table_name="chat")
    op.drop_table("chat")
    op.drop_table("summaries")
    op.drop_table("papers")
    op.drop_table("users")
