"""add EO & Task constraints

Revision ID: 46b2c1b69e75
Revises: 2d54f2945195
Create Date: 2025-08-13 14:03:12.351039

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '46b2c1b69e75'
down_revision: Union[str, Sequence[str], None] = '2d54f2945195'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "executive_orders",
        sa.Column("message_id", sa.String(length=255), nullable=False)
    )
    
    op.create_unique_constraint(
        "uq_executive_orders_message_id", "executive_orders", ["message_id"]
    )
    op.create_unique_constraint(
        "uq_tasks_eo_id_title", "tasks", ["eo_id", "title"]
    )
    op.create_foreign_key(
        "fk_tasks_eo", "tasks", "executive_orders", ["eo_id"], ["id"], ondelete="CASCADE"
    )


def downgrade() -> None:
    op.drop_constraint("fk_tasks_eo", "tasks", type_="foreignkey")
    op.drop_constraint("uq_tasks_eo_id_title", "tasks", type_="unique")
    op.drop_constraint("uq_executive_orders_message_id", "executive_orders", type_="unique")
