"""Add background task processing fields

Revision ID: 002_background_tasks
Revises: c7033ca1ad0f
Create Date: 2025-06-19 10:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "002_background_tasks"
down_revision: Union[str, None] = "c7033ca1ad0f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add background processing fields to tasks table
    op.add_column(
        "tasks", sa.Column("background_task_id", sa.String(255), nullable=True)
    )
    op.add_column(
        "tasks",
        sa.Column(
            "queue_name", sa.String(100), nullable=False, server_default="default"
        ),
    )
    op.add_column("tasks", sa.Column("worker_id", sa.String(255), nullable=True))
    op.add_column(
        "tasks",
        sa.Column("processing_started_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("processing_completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "tasks",
        sa.Column("progress_details", sa.JSON(), nullable=False, server_default="{}"),
    )
    op.add_column(
        "tasks",
        sa.Column("estimated_completion_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("tasks", sa.Column("memory_usage_mb", sa.Integer(), nullable=True))
    op.add_column(
        "tasks", sa.Column("browser_session_id", sa.String(255), nullable=True)
    )
    op.add_column(
        "tasks", sa.Column("last_error_at", sa.DateTime(timezone=True), nullable=True)
    )

    # Add indexes for performance
    op.create_index("idx_tasks_background_task_id", "tasks", ["background_task_id"])
    op.create_index("idx_tasks_queue_name", "tasks", ["queue_name"])
    op.create_index(
        "idx_tasks_processing_started_at", "tasks", ["processing_started_at"]
    )


def downgrade() -> None:
    # Remove indexes
    op.drop_index("idx_tasks_background_task_id", table_name="tasks")
    op.drop_index("idx_tasks_queue_name", table_name="tasks")
    op.drop_index("idx_tasks_processing_started_at", table_name="tasks")

    # Remove columns
    op.drop_column("tasks", "last_error_at")
    op.drop_column("tasks", "browser_session_id")
    op.drop_column("tasks", "memory_usage_mb")
    op.drop_column("tasks", "estimated_completion_at")
    op.drop_column("tasks", "progress_details")
    op.drop_column("tasks", "processing_completed_at")
    op.drop_column("tasks", "processing_started_at")
    op.drop_column("tasks", "worker_id")
    op.drop_column("tasks", "queue_name")
    op.drop_column("tasks", "background_task_id")
