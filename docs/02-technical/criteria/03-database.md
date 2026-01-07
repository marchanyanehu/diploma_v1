# Criterion: Database (PostgreSQL)

## Architecture Decision Record

### Status
**Status:** Accepted
**Date:** 2025-01-05

### Context
The system needs to store a variety of data types: structured metadata (users, tasks, schedules), large text blobs (HTML, semantic content), and cacheable patterns (RegEx, CSS selectors). Reliability, ACID compliance, and relational integrity are paramount.

### Decision
We chose **PostgreSQL 15** as the primary relational database. It is highly reliable, supports JSONB for flexible metadata, and integrates perfectly with SQLAlchemy ORM.

### Alternatives Considered
- **MySQL:** Good, but PostgreSQL offers better support for complex data types (JSONB) and advanced indexing.
- **NoSQL (MongoDB):** While good for blobs, the relational nature of users/tasks/schedules is better served by SQL.

### Consequences
**Positive:**
- Strong data consistency and transactional integrity.
- Flexible storage of extra metadata via JSONB.
- Mature ecosystem for migrations (Alembic).

**Negative:**
- Requires more management effort than a managed NoSQL solution if self-hosted.

## Implementation Details

### Key Implementation Decisions
- **Unified Schema:** All persistent state (users, tasks, results, schedules, cache) is kept in a single PostgreSQL instance.
- **Alembic Migrations:** Used to manage schema changes version-by-version.
- **Caching Logic:** The `parser_cache` table uses a unique index on (domain, prompt_hash) to quickly retrieve previously generated RegEx.

## Requirements Checklist

| # | Requirement | Status | Evidence/Notes |
|---|-------------|--------|----------------|
| 1 | PostgreSQL Storage | ✅ | Uses Postgres 15+ via SQLAlchemy. |
| 2 | HTML & Result Storage | ✅ | Stores raw HTML and final JSON results in the `scraping_tasks` table. |
| 3 | RegEx & Pattern Cache | ✅ | `parser_cache` table stores generated extraction patterns. |
| 4 | Scheduling Storage | ✅ | `scheduled_jobs` table stores cron definitions and job history. |

## Known Limitations
- Large HTML blobs can increase DB size rapidly; implemented cleanup policies for old tasks.

