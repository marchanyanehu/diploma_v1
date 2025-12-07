# Data Dictionary & DB Operations

## Normalization (3NF)

This schema is normalized to Third Normal Form (3NF):
- **1NF**: All columns contain atomic values; no repeating groups.
- **2NF**: All non-key attributes depend on the entire primary key.
- **3NF**: No transitive dependencies; all non-key attributes depend only on the primary key.

Key normalization changes:
- Extracted `domain` from `parsers_cache` into separate `domains` table (eliminates derivable field).
- Moved large blobs (`page_content`, `network_requests`) from `scraping_tasks` to `task_sources` table.
- Extracted intent fields from `scraping_tasks` into `task_intents` table (logical grouping).
- Moved sample data from `parsers_cache` into `parser_samples` table (1:N relationship).

## Tables

### Core Tables

- `users`
  - `id` (PK, serial), `username` (varchar(50), unique, not null), `hashed_password` (varchar(255), not null), `email` (varchar(255), unique, null), `created_at` (timestamptz, default now), `is_active` (bool, default true).

- `domains`
  - `id` (PK, serial), `name` (varchar(255), unique, not null), `first_seen_at` (timestamptz, default now).
  - Purpose: Normalized domain storage for parser cache entries.

- `scraping_tasks`
  - `id` (PK), `task_id` (varchar(255), unique, not null), `url` (text, not null), `user_prompt` (text, not null), status/timestamp fields (`status`, `created_at`, `started_at`, `completed_at`, `processing_time_seconds`, `retry_count`), error/result fields (`error_message`, `extracted_data`, `total_matches`), parser linkage (`used_cached_parser`, `used_parser_id` → `parsers_cache.id`), intent linkage (`intent_id` → `task_intents.id`), ownership (`owner_id` → `users.id`, nullable).
  - Related tables: `task_source_data` (1:1), `task_intents` (N:1, allows reuse).

- `parsers_cache`
  - `id` (PK), `url_pattern`, `domain_id` (FK → `domains.id`), `user_intent`, `intent_keywords`, `target_data_type`, `generated_regex`, `source_type`, `source_identifier`, validation fields (`test_matches_count`, `confidence_score`, `success_rate`, `times_used`, `is_active`), metadata (`created_at`, `last_used_at`, `created_by_task_id`, `llm_model_used`, `generation_attempts`, `normalized_intent_hash`, `keyword_set`).
  - Related tables: `parser_samples` (1:1), `domains` (N:1).

- `scheduled_jobs`
  - `id` (PK), `url` (text, not null), `prompt` (text, not null), `schedule_cron` (varchar(100), not null), `is_active` (bool, default true), `last_run_at`, `next_run_at`, `owner_id` (FK → `users.id`, not null), `created_at` (timestamptz, default now).

### Normalized Extension Tables

- `task_source_data`
  - `id` (PK, serial), `task_id` (FK → `scraping_tasks.id`, unique, not null), `page_content` (text), `html_content` (text), `network_requests` (jsonb), `chosen_source_url` (text).
  - Purpose: Stores large page content and network request data separately from main task record.

- `task_intents`
  - `id` (PK, serial), `target` (text), `keywords` (jsonb), `schema_fields` (jsonb), `constraints` (jsonb), `output_shape` (text), `confidence` (float), `normalized_hash` (varchar(64)), `source_type` (varchar(50)), `target_attribute` (varchar(50)), `created_at` (timestamptz, default now).
  - Purpose: Normalized intent data extracted from user prompts; can be reused across tasks.

- `parser_samples`
  - `id` (PK, serial), `parser_id` (FK → `parsers_cache.id`, unique, not null), `sample_input` (text), `sample_output` (jsonb).
  - Purpose: Sample input/output pairs for parser validation.

## ER Diagram (Mermaid)

```mermaid
erDiagram
    users ||--o{ scraping_tasks : owns
    users ||--o{ scheduled_jobs : schedules
    parsers_cache ||--o{ scraping_tasks : reused_by
    domains ||--o{ parsers_cache : categorizes
    scraping_tasks ||--o| task_source_data : has_source
    task_intents ||--o{ scraping_tasks : defines_intent
    parsers_cache ||--o| parser_samples : has_sample

    users {
        int id PK
        varchar username UK
        varchar email UK
        bool is_active
        timestamptz created_at
    }

    domains {
        int id PK
        varchar name UK
        timestamptz created_at
    }

    scraping_tasks {
        int id PK
        varchar task_id UK
        text url
        text user_prompt
        varchar status
        int intent_id FK
        int used_parser_id FK
        int owner_id FK
    }

    task_source_data {
        int id PK
        int task_id FK_UK
        text page_content
        text html_content
        jsonb network_requests
        text chosen_source_url
    }

    task_intents {
        int id PK
        text target
        jsonb keywords
        jsonb schema_fields
        float confidence
        varchar normalized_hash
    }

    parsers_cache {
        int id PK
        varchar url_pattern
        int domain_id FK
        text user_intent
        text generated_regex
        int times_used
        timestamptz last_used_at
    }

    parser_samples {
        int id PK
        int parser_id FK_UK
        text sample_input
        jsonb sample_output
    }

    scheduled_jobs {
        int id PK
        text url
        text prompt
        varchar schedule_cron
        int owner_id FK
    }
```

## Integrity & Constraints

- Primary keys on all tables; unique constraints on `users.username`, `users.email`, `scraping_tasks.task_id`, `domains.name`.
- Foreign keys:
  - `scraping_tasks.used_parser_id` → `parsers_cache.id`
  - `scraping_tasks.owner_id` → `users.id`
  - `scraping_tasks.intent_id` → `task_intents.id`
  - `scheduled_jobs.owner_id` → `users.id`
  - `parsers_cache.domain_id` → `domains.id`
  - `task_source_data.task_id` → `scraping_tasks.id` (unique, 1:1)
  - `parser_samples.parser_id` → `parsers_cache.id` (unique, 1:1)
- Default timestamps are UTC (`server_default NOW()`); boolean defaults enforce active rows.
- Engines/indices: per-model indexes added on ids, usernames, emails, owner ids, domain names for join performance.
- Consider CHECK/enum for `scraping_tasks.status` (`PENDING|IN_PROGRESS|SUCCESS|FAILED`) if/when stricter enforcement is required.

## Transactions & Integrity Handling

- Request-scope DB sessions via `services/api/database.py#get_db`; commit on success, rollback on exception. Celery tasks reuse the same pattern.
- Referential integrity is enforced in the DB (FKs on owner/parser), avoiding orphaned tasks or schedules.
- Defaults and NOT NULLs capture timestamps/activity flags; app code validates payloads before persistence.
- Trigger `trg_scraping_tasks_parser_usage` (with `bump_parser_usage`) fires only after successful tasks using a parser, updating `times_used` and `last_used_at` to align metadata with runtime behavior.
- Seeds include both success and failure cases to exercise constraints and error paths.

## Index Rationale

- `scraping_tasks.task_id`, `scraping_tasks.owner_id`, `scraping_tasks.intent_id`: task lookup by external ID, per-user views, and intent joins.
- `parsers_cache.domain_id`, `parsers_cache.url_pattern`, `parsers_cache.normalized_intent_hash`: fast reuse matching by domain/intent/keywords.
- `domains.name`: unique constraint creates implicit index for domain lookup.
- `users.username`, `users.email`: login uniqueness and quick authentication lookup.
- `scheduled_jobs.owner_id`: list schedules per user.
- `task_source_data.task_id`: unique FK index for 1:1 relationship join with scraping_tasks.
- `task_intents.normalized_hash`: intent matching for reuse.
- `parser_samples.parser_id`: unique FK index for 1:1 relationship join with parsers_cache.
- `parsers_cache.id`, `scraping_tasks.id`: primary key indexes for joins and admin operations.

## Views & Triggers

- View `vw_parser_stats`: aggregates parser reuse (`times_used`, cached hits, success counts) for reporting/defense.
- Trigger `trg_scraping_tasks_parser_usage` + function `bump_parser_usage`: updates `parsers_cache.times_used` and `last_used_at` on successful task completion with a parser.

## Seed & Test Data

- `scripts/db_seed.sql` loads:
  - Demo user (`demo_user` / `Password123!`).
  - Successful parser + successful task (`seed-task-1`) showing cached reuse and populated metrics.
  - Inactive/low-confidence parser for failure illustration (`https://example.com/broken`, `is_active=false`, `times_used=0`, `success_rate=0`).
  - Failed task (`seed-task-failed`) capturing error_message to demonstrate error handling paths.
  - Scheduled job for demo user (nightly cron).
- Seeds are idempotent (ON CONFLICT / NOT EXISTS guards) and rely on roles created via `scripts/db_roles.sql`.

## Setup & Deployment Notes

- Apply schema: `alembic upgrade head` (migrations tracked under `migrations/versions/`).
- Create roles/privileges: run `scripts/db_roles.sql` as `postgres` with provided vars.
- Load seeds: run `scripts/db_seed.sql` as `app_admin`.
- Service creds: use `app_write` in runtime `.env` (see `.env.example`); reserve `postgres/app_admin` for admin tasks only.

## Operational Queries (examples)

- Check parser stats: `SELECT * FROM vw_parser_stats ORDER BY times_used DESC;`
- List recent failed tasks: `SELECT task_id, url, error_message FROM scraping_tasks WHERE status='FAILED' ORDER BY created_at DESC LIMIT 10;`
- Inspect inactive parsers: `SELECT id, domain, url_pattern FROM parsers_cache WHERE is_active=false;`

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

