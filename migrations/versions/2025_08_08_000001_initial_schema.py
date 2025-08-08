"""
Initial database schema: scraping_tasks and parsers_cache

Revision ID: 0001_initial
Revises: 
Create Date: 2025-08-08 00:00:01
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create table: parsers_cache
    op.create_table(
        'parsers_cache',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('url_pattern', sa.String(length=500), nullable=False),
        sa.Column('domain', sa.String(length=255), nullable=False),
        sa.Column('user_intent', sa.Text(), nullable=False),
        sa.Column('intent_keywords', sa.JSON(), nullable=True),
        sa.Column('target_data_type', sa.String(length=100), nullable=True),
        sa.Column('generated_regex', sa.Text(), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_identifier', sa.Text(), nullable=True),
        sa.Column('test_matches_count', sa.Integer(), nullable=False),
        sa.Column('confidence_score', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('success_rate', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('times_used', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_task_id', sa.String(length=255), nullable=False),
        sa.Column('llm_model_used', sa.String(length=100), nullable=True),
        sa.Column('generation_attempts', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('sample_input', sa.Text(), nullable=True),
        sa.Column('sample_output', sa.JSON(), nullable=True),
    )
    op.create_index('ix_parsers_cache_id', 'parsers_cache', ['id'], unique=False)
    op.create_index('ix_parsers_cache_url_pattern', 'parsers_cache', ['url_pattern'], unique=False)
    op.create_index('ix_parsers_cache_domain', 'parsers_cache', ['domain'], unique=False)

    # Create table: scraping_tasks
    op.create_table(
        'scraping_tasks',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('task_id', sa.String(length=255), nullable=False, unique=True, index=True),
        sa.Column('url', sa.Text(), nullable=False),
        sa.Column('user_prompt', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, server_default='PENDING'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('NOW()'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('extracted_data', sa.JSON(), nullable=True),
        sa.Column('total_matches', sa.Integer(), nullable=True),
        sa.Column('processing_time_seconds', sa.Integer(), nullable=True),
        sa.Column('used_cached_parser', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('page_content', sa.Text(), nullable=True),
        sa.Column('network_requests', sa.JSON(), nullable=True),
        sa.Column('used_parser_id', sa.Integer(), sa.ForeignKey('parsers_cache.id'), nullable=True),
    )
    op.create_index('ix_scraping_tasks_id', 'scraping_tasks', ['id'], unique=False)
    op.create_index('ix_scraping_tasks_task_id', 'scraping_tasks', ['task_id'], unique=True)


def downgrade() -> None:
    op.drop_index('ix_scraping_tasks_task_id', table_name='scraping_tasks')
    op.drop_index('ix_scraping_tasks_id', table_name='scraping_tasks')
    op.drop_table('scraping_tasks')

    op.drop_index('ix_parsers_cache_domain', table_name='parsers_cache')
    op.drop_index('ix_parsers_cache_url_pattern', table_name='parsers_cache')
    op.drop_index('ix_parsers_cache_id', table_name='parsers_cache')
    op.drop_table('parsers_cache')
