# Data Dictionary & DB Operations

## Tables

- `users`
  - `id` (PK, serial), `username` (varchar(50), unique, not null), `hashed_password` (varchar(255), not null), `email` (varchar(255), unique, null), `created_at` (timestamptz, default now), `is_active` (bool, default true).
- `scraping_tasks`
  - `id` (PK), `task_id` (varchar(255), unique, not null), `url` (text, not null), `user_prompt` (text, not null), status/timestamp fields (`status`, `created_at`, `started_at`, `completed_at`, `processing_time_seconds`, `retry_count`), error/result fields (`error_message`, `extracted_data`, `total_matches`, `page_content`, `network_requests`), parser linkage (`used_cached_parser`, `used_parser_id` → `parsers_cache.id`), intent fields (`intent_target`, `intent_keywords`, `chosen_source_url`, `chosen_source_type`), ownership (`owner_id` → `users.id`, nullable).
- `parsers_cache`
  - `id` (PK), `url_pattern`, `domain`, `user_intent`, `intent_keywords`, `target_data_type`, `generated_regex`, `source_type`, `source_identifier`, validation fields (`test_matches_count`, `confidence_score`, `success_rate`, `times_used`, `is_active`), metadata (`created_at`, `last_used_at`, `created_by_task_id`, `llm_model_used`, `generation_attempts`, `sample_input`, `sample_output`, `normalized_intent_hash`, `keyword_set`).
- `scheduled_jobs`
  - `id` (PK), `url` (text, not null), `prompt` (text, not null), `schedule_cron` (varchar(100), not null), `is_active` (bool, default true), `last_run_at`, `next_run_at`, `owner_id` (FK → `users.id`, not null), `created_at` (timestamptz, default now).

## Integrity & Constraints

- Primary keys on all tables; unique constraints on `users.username`, `users.email`, `scraping_tasks.task_id`.
- Foreign keys:
  - `scraping_tasks.used_parser_id` → `parsers_cache.id`
  - `scraping_tasks.owner_id` → `users.id`
  - `scheduled_jobs.owner_id` → `users.id`
- Default timestamps are UTC (`server_default NOW()`); boolean defaults enforce active rows.
- Engines/indices: per-model indexes added on ids, usernames, emails, owner ids for join performance.

## Roles & Access

- Superuser (`postgres`) retained for administration only.
- Application roles created by `scripts/db_roles.sql`:
  - `app_read`: `SELECT` only.
  - `app_write`: CRUD on tables (used by services).
  - `app_admin`: full DML/DDL on public schema; inherits `app_write`.
- Privileges are granted via default privileges to cover future tables.

## Migration & DDL

- All schema changes tracked in Alembic under `migrations/versions/`. Latest revision adds `users`, `scheduled_jobs`, and ownership FK on `scraping_tasks`.
- Avoid running `Base.metadata.create_all` in production; prefer Alembic (`alembic upgrade head`).

## Seeds & Test Data

- Run `scripts/db_seed.sql` with `app_admin` to load demo user, sample parser cache, task, and scheduled job. Script is idempotent (checks existing keys).
- Seed password is generated in-DB with bcrypt (`crypt(..., gen_salt('bf'))`); demo login: `demo_user` / `Password123!`.

## Operational Notes

- Set service credentials to `app_write` (see `.env` and `docker-compose.yml`).
- For manual reads use `app_read`; for maintenance use `app_admin` or `postgres`.
- When adding new tables, extend Alembic migrations and update this dictionary.

