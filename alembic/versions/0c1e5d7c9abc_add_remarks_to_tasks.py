"""add remarks to tasks

Revision ID: 0c1e5d7c9abc
Revises: be040d1d12a0
Create Date: 2025-08-19 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '0c1e5d7c9abc'
down_revision: Union[str, Sequence[str], None] = 'be040d1d12a0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tasks",
        sa.Column("remarks", sa.Text(), nullable=True)
    )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("remarks") 