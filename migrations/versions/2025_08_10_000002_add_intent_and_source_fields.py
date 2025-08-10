"""
Add intent & chosen source columns to scraping_tasks

Revision ID: 0002_intent_source
Revises: 0001_initial
Create Date: 2025-08-10 00:00:02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '0002_intent_source'
down_revision = '0001_initial'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('scraping_tasks') as batch:
        batch.add_column(sa.Column('intent_target', sa.Text(), nullable=True))
        batch.add_column(sa.Column('intent_keywords', sa.JSON(), nullable=True))
        batch.add_column(sa.Column('chosen_source_url', sa.Text(), nullable=True))
        batch.add_column(sa.Column('chosen_source_type', sa.String(length=50), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table('scraping_tasks') as batch:
        batch.drop_column('chosen_source_type')
        batch.drop_column('chosen_source_url')
        batch.drop_column('intent_keywords')
        batch.drop_column('intent_target')
