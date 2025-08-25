"""add_approved_rejected_to_task_status

Revision ID: be424b166b13
Revises: 6a2f9c1e4b10
Create Date: 2025-08-21 18:16:18.631841

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be424b166b13'
down_revision: Union[str, Sequence[str], None] = '6a2f9c1e4b10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Only update the task status enum to include new values
    op.alter_column('tasks', 'status',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.Enum('pending', 'in_progress', 'completed', 'Pending PMO approval', 'approved', 'rejected', name='task_status', native_enum=False),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert the task status enum to original values
    op.alter_column('tasks', 'status',
               existing_type=sa.Enum('pending', 'in_progress', 'completed', 'Pending PMO approval', 'approved', 'rejected', name='task_status', native_enum=False),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)
