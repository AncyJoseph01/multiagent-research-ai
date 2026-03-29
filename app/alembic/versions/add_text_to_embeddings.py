"""Add text column to embeddings table

Revision ID: add_text_column
Revises: 79e4affc14ec
Create Date: 2025-03-29

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'add_text_column'
down_revision: Union[str, None] = '79e4affc14ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add text column to embeddings table
    op.add_column('embeddings', sa.Column('text', sa.Text(), nullable=False, server_default=''))


def downgrade() -> None:
    # Remove text column from embeddings table
    op.drop_column('embeddings', 'text')
