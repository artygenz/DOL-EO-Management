"""edit task status

Revision ID: be040d1d12a0
Revises: af14a0baf535
Create Date: 2025-08-17 20:53:48.597752

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'be040d1d12a0'
down_revision: Union[str, Sequence[str], None] = 'af14a0baf535'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    op.alter_column('tasks', 'status',
                    existing_type=sa.String(length=11),
                    type_=sa.String(length=255),
                    existing_nullable=False)

    
def downgrade() -> None:
    """Downgrade schema."""
    
