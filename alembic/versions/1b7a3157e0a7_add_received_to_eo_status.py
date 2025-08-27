"""add_received_to_eo_status

Revision ID: 1b7a3157e0a7
Revises: be424b166b13
Create Date: 2025-08-22 02:27:35.690024

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b7a3157e0a7'
down_revision: Union[str, Sequence[str], None] = 'be424b166b13'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Only update the EO status enum to include "received"
    op.alter_column('executive_orders', 'status',
               existing_type=sa.VARCHAR(length=255),
               type_=sa.Enum('processed', 'error', 'pending', 'received', name='eo_status', native_enum=False),
               existing_nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert the EO status enum to original values
    op.alter_column('executive_orders', 'status',
               existing_type=sa.Enum('processed', 'error', 'pending', 'received', name='eo_status', native_enum=False),
               type_=sa.VARCHAR(length=255),
               existing_nullable=False)
