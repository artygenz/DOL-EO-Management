"""drop priority add category to tasks

Revision ID: af14a0baf535
Revises: 46b2c1b69e75
Create Date: 2025-08-13 20:05:40.939690

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'af14a0baf535'
down_revision: Union[str, Sequence[str], None] = '46b2c1b69e75'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1) Add category (string, indexed, nullable for now)
    op.add_column(
        "tasks",
        sa.Column("category", sa.String(length=255), nullable=True)
    )
    op.create_index("ix_tasks_category", "tasks", ["category"])

    # 2) Drop priority column
    # priority was Enum(*TASK_PRIORITY, name="task_priority", native_enum=False)
    # native_enum=False -> no PostgreSQL TYPE to drop, so this is enough.
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("priority")


def downgrade() -> None:
    # 1) Recreate priority (as it originally was)
    task_priority_enum = sa.Enum(
        "low", "medium", "high",
        name="task_priority",
        native_enum=False
    )
    with op.batch_alter_table("tasks") as batch:
        batch.add_column(
            sa.Column(
                "priority",
                task_priority_enum,
                nullable=False,
                server_default="medium",  # matches original default
            )
        )

    # 2) Drop category + index
    op.drop_index("ix_tasks_category", table_name="tasks")
    with op.batch_alter_table("tasks") as batch:
        batch.drop_column("category")