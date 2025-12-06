"""
Add parser stats view and trigger to track parser reuse.

Revision ID: 0005_parser_stats
Revises: 0004_users_schedule
Create Date: 2025-12-06 12:00:05
"""
from __future__ import annotations

from alembic import op

# revision identifiers, used by Alembic.
revision = "0005_parser_stats"
down_revision = "0004_users_schedule"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Helper function: bump times_used / last_used_at when a parser is used
    op.execute(
        """
        CREATE OR REPLACE FUNCTION bump_parser_usage() RETURNS TRIGGER AS $$
        BEGIN
            IF NEW.used_parser_id IS NULL THEN
                RETURN NEW;
            END IF;

            UPDATE parsers_cache
            SET times_used = times_used + 1,
                last_used_at = NOW()
            WHERE id = NEW.used_parser_id;

            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )

    # Trigger on scraping_tasks for inserts/updates when a parser was used successfully
    op.execute(
        """
        DROP TRIGGER IF EXISTS trg_scraping_tasks_parser_usage ON scraping_tasks;
        CREATE TRIGGER trg_scraping_tasks_parser_usage
        AFTER INSERT OR UPDATE OF used_parser_id, used_cached_parser, status
        ON scraping_tasks
        FOR EACH ROW
        WHEN (NEW.status = 'SUCCESS' AND NEW.used_parser_id IS NOT NULL
              AND (TG_OP = 'INSERT'
                   OR NEW.used_parser_id IS DISTINCT FROM OLD.used_parser_id
                   OR (NEW.used_cached_parser IS TRUE AND (OLD.used_cached_parser IS DISTINCT FROM NEW.used_cached_parser))
                   OR NEW.status IS DISTINCT FROM COALESCE(OLD.status, '')))
        EXECUTE FUNCTION bump_parser_usage();
        """
    )

    # View to summarize parser performance and reuse
    op.execute(
        """
        CREATE OR REPLACE VIEW vw_parser_stats AS
        SELECT
            pc.id,
            pc.domain,
            pc.url_pattern,
            pc.target_data_type,
            pc.confidence_score,
            pc.success_rate,
            pc.times_used,
            pc.last_used_at,
            pc.created_at,
            COALESCE(SUM(CASE WHEN t.status = 'SUCCESS' THEN 1 ELSE 0 END), 0) AS successful_tasks,
            COALESCE(SUM(CASE WHEN t.used_cached_parser THEN 1 ELSE 0 END), 0) AS cached_hits,
            COALESCE(COUNT(t.id), 0) AS total_tasks
        FROM parsers_cache pc
        LEFT JOIN scraping_tasks t ON t.used_parser_id = pc.id
        GROUP BY pc.id, pc.domain, pc.url_pattern, pc.target_data_type, pc.confidence_score,
                 pc.success_rate, pc.times_used, pc.last_used_at, pc.created_at;
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS vw_parser_stats;")
    op.execute("DROP TRIGGER IF EXISTS trg_scraping_tasks_parser_usage ON scraping_tasks;")
    op.execute("DROP FUNCTION IF EXISTS bump_parser_usage;")

