"""
Add intent cache fields to parsers_cache

Revision ID: 0003_intent_cache
Revises: 0002_intent_source
Create Date: 2025-08-10 00:00:03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = '0003_intent_cache'
down_revision = '0002_intent_source'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('parsers_cache') as batch:
        batch.add_column(sa.Column('normalized_intent_hash', sa.String(length=64), nullable=True))
        batch.add_column(sa.Column('keyword_set', sa.JSON(), nullable=True))
        batch.add_column(sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')))
        batch.create_index('ix_parsers_cache_normalized_intent_hash', ['normalized_intent_hash'])


def downgrade() -> None:
    with op.batch_alter_table('parsers_cache') as batch:
        batch.drop_index('ix_parsers_cache_normalized_intent_hash')
        batch.drop_column('is_active')
        batch.drop_column('keyword_set')
        batch.drop_column('normalized_intent_hash')
