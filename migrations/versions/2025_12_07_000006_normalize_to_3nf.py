"""Normalize database schema to 3NF

Revision ID: 000006
Revises: 000005
Create Date: 2025-12-07

Changes:
- Create domains lookup table (eliminates derived domain from URL)
- Create task_intents table (normalizes intent data)
- Create task_source_data table (separates large blobs)
- Create parser_samples table (separates sample data)
- Add foreign keys to existing tables
- Migrate existing data
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '000006'
down_revision = '000005'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create domains table
    op.create_table(
        'domains',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_domains_id', 'domains', ['id'])
    op.create_index('ix_domains_name', 'domains', ['name'], unique=True)
    
    # 2. Create task_intents table
    op.create_table(
        'task_intents',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('target', sa.Text(), nullable=True),
        sa.Column('keywords', sa.JSON(), nullable=True),
        sa.Column('schema_fields', sa.JSON(), nullable=True),
        sa.Column('constraints', sa.JSON(), nullable=True),
        sa.Column('output_shape', sa.Text(), nullable=True),
        sa.Column('confidence', sa.Float(), nullable=True),
        sa.Column('normalized_hash', sa.String(64), nullable=True),
        sa.Column('source_type', sa.String(50), nullable=True),
        sa.Column('target_attribute', sa.String(50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_task_intents_id', 'task_intents', ['id'])
    op.create_index('ix_task_intents_normalized_hash', 'task_intents', ['normalized_hash'])
    
    # 3. Create task_source_data table
    op.create_table(
        'task_source_data',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('page_content', sa.Text(), nullable=True),
        sa.Column('html_content', sa.Text(), nullable=True),
        sa.Column('network_requests', sa.JSON(), nullable=True),
        sa.Column('chosen_source_url', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['task_id'], ['scraping_tasks.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('task_id')
    )
    op.create_index('ix_task_source_data_id', 'task_source_data', ['id'])
    
    # 4. Create parser_samples table
    op.create_table(
        'parser_samples',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('parser_id', sa.Integer(), nullable=False),
        sa.Column('sample_input', sa.Text(), nullable=True),
        sa.Column('sample_output', sa.JSON(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['parser_id'], ['parsers_cache.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('parser_id')
    )
    op.create_index('ix_parser_samples_id', 'parser_samples', ['id'])
    
    # 5. Migrate existing domains from parsers_cache
    op.execute("""
        INSERT INTO domains (name)
        SELECT DISTINCT domain FROM parsers_cache
        WHERE domain IS NOT NULL AND domain != ''
        ON CONFLICT (name) DO NOTHING
    """)
    
    # 6. Add domain_id to parsers_cache
    op.add_column('parsers_cache', sa.Column('domain_id', sa.Integer(), nullable=True))
    
    # 7. Update domain_id from existing domain values
    op.execute("""
        UPDATE parsers_cache pc
        SET domain_id = d.id
        FROM domains d
        WHERE pc.domain = d.name
    """)
    
    # 8. Add FK constraint (nullable for now due to potential missing domains)
    op.create_foreign_key(
        'fk_parsers_cache_domain_id',
        'parsers_cache', 'domains',
        ['domain_id'], ['id']
    )
    
    # 9. Migrate parser samples
    op.execute("""
        INSERT INTO parser_samples (parser_id, sample_input, sample_output)
        SELECT id, sample_input, sample_output
        FROM parsers_cache
        WHERE sample_input IS NOT NULL OR sample_output IS NOT NULL
    """)
    
    # 10. Add intent_id to scraping_tasks
    op.add_column('scraping_tasks', sa.Column('intent_id', sa.Integer(), nullable=True))
    op.create_foreign_key(
        'fk_scraping_tasks_intent_id',
        'scraping_tasks', 'task_intents',
        ['intent_id'], ['id']
    )
    
    # 11. Migrate existing intent data from scraping_tasks to task_intents
    op.execute("""
        INSERT INTO task_intents (target, keywords, source_type)
        SELECT DISTINCT intent_target, intent_keywords, chosen_source_type
        FROM scraping_tasks
        WHERE intent_target IS NOT NULL
    """)
    
    # 12. Link existing tasks to their intents
    op.execute("""
        UPDATE scraping_tasks st
        SET intent_id = ti.id
        FROM task_intents ti
        WHERE st.intent_target = ti.target
        AND (st.intent_keywords::text = ti.keywords::text OR (st.intent_keywords IS NULL AND ti.keywords IS NULL))
    """)
    
    # 13. Migrate source data from scraping_tasks to task_source_data
    op.execute("""
        INSERT INTO task_source_data (task_id, page_content, network_requests, chosen_source_url)
        SELECT id, page_content, network_requests, chosen_source_url
        FROM scraping_tasks
        WHERE page_content IS NOT NULL OR network_requests IS NOT NULL OR chosen_source_url IS NOT NULL
    """)
    
    # 14. Drop old columns from scraping_tasks (keep for now, can be removed in future migration)
    # op.drop_column('scraping_tasks', 'page_content')
    # op.drop_column('scraping_tasks', 'network_requests')
    # op.drop_column('scraping_tasks', 'intent_target')
    # op.drop_column('scraping_tasks', 'intent_keywords')
    # op.drop_column('scraping_tasks', 'chosen_source_url')
    # op.drop_column('scraping_tasks', 'chosen_source_type')
    
    # 15. Drop old columns from parsers_cache (keep for now, can be removed in future migration)
    # op.drop_column('parsers_cache', 'domain')
    # op.drop_column('parsers_cache', 'sample_input')
    # op.drop_column('parsers_cache', 'sample_output')


def downgrade() -> None:
    # Remove new FK from scraping_tasks
    op.drop_constraint('fk_scraping_tasks_intent_id', 'scraping_tasks', type_='foreignkey')
    op.drop_column('scraping_tasks', 'intent_id')
    
    # Remove new FK from parsers_cache
    op.drop_constraint('fk_parsers_cache_domain_id', 'parsers_cache', type_='foreignkey')
    op.drop_column('parsers_cache', 'domain_id')
    
    # Drop new tables
    op.drop_table('parser_samples')
    op.drop_table('task_source_data')
    op.drop_table('task_intents')
    op.drop_table('domains')
