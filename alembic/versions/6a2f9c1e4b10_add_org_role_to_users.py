"""add org_role to users

Revision ID: 6a2f9c1e4b10
Revises: 0c1e5d7c9abc
Create Date: 2025-08-19 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '6a2f9c1e4b10'
down_revision: Union[str, Sequence[str], None] = '0c1e5d7c9abc'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("org_role", sa.String(length=120), nullable=True)
    )
    op.create_index("ix_users_org_role", "users", ["org_role"]) 


def downgrade() -> None:
    op.drop_index("ix_users_org_role", table_name="users")
    with op.batch_alter_table("users") as batch:
        batch.drop_column("org_role") 