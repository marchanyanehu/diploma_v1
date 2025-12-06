"""
Add users and scheduled_jobs tables; link scraping_tasks to users.

Revision ID: 0004_users_schedule
Revises: 0003_intent_cache
Create Date: 2025-12-06 00:00:04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_users_schedule"
down_revision = "0003_intent_cache"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("username", sa.String(length=50), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True, unique=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )
    op.create_index("ix_users_id", "users", ["id"], unique=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    with op.batch_alter_table("scraping_tasks") as batch:
        batch.add_column(sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=True))
        batch.create_index("ix_scraping_tasks_owner_id", ["owner_id"])

    op.create_table(
        "scheduled_jobs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("schedule_cron", sa.String(length=100), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("owner_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("NOW()"),
            nullable=False,
        ),
    )
    op.create_index("ix_scheduled_jobs_id", "scheduled_jobs", ["id"], unique=False)
    op.create_index("ix_scheduled_jobs_owner_id", "scheduled_jobs", ["owner_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_scheduled_jobs_owner_id", table_name="scheduled_jobs")
    op.drop_index("ix_scheduled_jobs_id", table_name="scheduled_jobs")
    op.drop_table("scheduled_jobs")

    with op.batch_alter_table("scraping_tasks") as batch:
        batch.drop_index("ix_scraping_tasks_owner_id")
        batch.drop_column("owner_id")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_index("ix_users_id", table_name="users")
    op.drop_table("users")

