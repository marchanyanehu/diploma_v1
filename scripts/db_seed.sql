-- Seed/reference data for demo/testing (runs safely multiple times)
-- Usage:
--   psql -h <host> -p <port> -U app_admin -d diploma_db -f scripts/db_seed.sql
--   (app_admin role created via scripts/db_roles.sql)

\set ON_ERROR_STOP on

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

BEGIN;

-- Ensure demo user exists
WITH upsert_user AS (
    INSERT INTO users (username, hashed_password, email, is_active)
    VALUES (
        'demo_user',
        crypt('Password123!', gen_salt('bf')), -- bcrypt hash generated in DB
        'demo@example.com',
        true
    )
    ON CONFLICT (username)
    DO UPDATE SET email = EXCLUDED.email, is_active = EXCLUDED.is_active
    RETURNING id
)
-- Seed parser cache entry tied to demo task
, parser_ins AS (
    INSERT INTO parsers_cache (
        url_pattern,
        domain,
        user_intent,
        intent_keywords,
        target_data_type,
        generated_regex,
        source_type,
        source_identifier,
        test_matches_count,
        confidence_score,
        success_rate,
        times_used,
        created_by_task_id,
        llm_model_used,
        generation_attempts,
        sample_input,
        sample_output,
        normalized_intent_hash,
        keyword_set,
        is_active
    )
    SELECT
        'https://example.com/products',
        'example.com',
        'extract product titles and prices',
        '["product","price","title"]'::json,
        'product_prices',
        '(?P<title>[\\w\\s]+)\\s+-\\s+\\$(?P<price>\\d+\\.\\d{2})',
        'HTML',
        '//div[@class=\"product-card\"]',
        3,
        95,
        95,
        1,
        'seed-task-1',
        'baseten/deepseek-ai/DeepSeek-V3.2',
        1,
        '<div class=\"product-card\">Widget A - $19.99</div>',
        '[{\"title\": \"Widget A\", \"price\": 19.99}]'::json,
        'seed-intent-hash',
        '["product","price","title"]'::json,
        true
    WHERE NOT EXISTS (
        SELECT 1 FROM parsers_cache WHERE url_pattern = 'https://example.com/products' AND user_intent = 'extract product titles and prices'
    )
    RETURNING id
)
, parser_fail_ins AS (
    INSERT INTO parsers_cache (
        url_pattern,
        domain,
        user_intent,
        intent_keywords,
        target_data_type,
        generated_regex,
        source_type,
        source_identifier,
        test_matches_count,
        confidence_score,
        success_rate,
        times_used,
        created_by_task_id,
        llm_model_used,
        generation_attempts,
        sample_input,
        sample_output,
        normalized_intent_hash,
        keyword_set,
        is_active
    )
    SELECT
        'https://example.com/broken',
        'example.com',
        'extract failing sample for demo',
        '["product","price"]'::json,
        'product_prices',
        '(?P<name>.+)',
        'HTML',
        '//div[@class=\"product-card\"]',
        0,
        40,
        0,
        0,
        'seed-task-failed',
        'baseten/deepseek-ai/DeepSeek-V3.2',
        2,
        '<div class=\"product-card\">Bad Data</div>',
        '[]'::json,
        'seed-intent-hash-failed',
        '["product","price"]'::json,
        false
    WHERE NOT EXISTS (
        SELECT 1 FROM parsers_cache WHERE url_pattern = 'https://example.com/broken' AND user_intent = 'extract failing sample for demo'
    )
    RETURNING id
)
-- Seed scraping task owned by demo user
, task_ins AS (
    INSERT INTO scraping_tasks (
        task_id,
        url,
        user_prompt,
        status,
        created_at,
        used_cached_parser,
        used_parser_id,
        owner_id,
        extracted_data,
        total_matches
    )
    SELECT
        'seed-task-1',
        'https://example.com/products',
        'Extract product titles and prices',
        'SUCCESS',
        NOW(),
        true,
        (SELECT id FROM parser_ins),
        (SELECT id FROM upsert_user),
        '[{\"title\":\"Widget A\",\"price\":19.99}]'::json,
        1
    WHERE NOT EXISTS (SELECT 1 FROM scraping_tasks WHERE task_id = 'seed-task-1')
    RETURNING id
)
, task_fail_ins AS (
    INSERT INTO scraping_tasks (
        task_id,
        url,
        user_prompt,
        status,
        created_at,
        used_cached_parser,
        used_parser_id,
        owner_id,
        error_message,
        total_matches
    )
    SELECT
        'seed-task-failed',
        'https://example.com/broken',
        'Demonstrate failure handling for parser generation',
        'FAILED',
        NOW(),
        false,
        NULL,
        (SELECT id FROM upsert_user),
        'LLM regex generation failed validation',
        0
    WHERE NOT EXISTS (SELECT 1 FROM scraping_tasks WHERE task_id = 'seed-task-failed')
    RETURNING id
)
-- Seed scheduled job for the demo user
INSERT INTO scheduled_jobs (
    url,
    prompt,
    schedule_cron,
    is_active,
    owner_id,
    created_at,
    last_run_at,
    next_run_at
)
SELECT
    'https://example.com/products',
    'Refresh product prices nightly',
    '0 2 * * *',
    true,
    (SELECT id FROM upsert_user),
    NOW(),
    NULL,
    NULL
WHERE NOT EXISTS (SELECT 1 FROM scheduled_jobs WHERE url = 'https://example.com/products' AND owner_id = (SELECT id FROM upsert_user));

COMMIT;

