# Intelligent Web Data Aggregator

A microservice-based web scraping system powered by LLMs to intelligently extract structured data from websites using natural language queries.

## Architecture

Microservice layout (see `docs/ARCHITECTURE.md` for the diagram):

1. **API Service (`api`)**
    - JWT auth (`/auth/register`, `/auth/token`)
    - Creates scraping tasks and exposes status/result endpoints
    - Manages user-owned schedules (CRUD on `/api/v1/jobs`)
2. **Scheduler Service (`scheduler`)**
    - Celery Beat job that enqueues due schedules every minute
3. **Headless Worker (`headless_worker`)**
    - Playwright fetcher; captures visible text + full HTML and forwards to AI
    - Runs on Celery `fetching_queue`
4. **AI Worker (`ai_worker`)**
    - Intent extraction + optimized regex pipeline
    - Uses LLM (Gemini/OpenAI) for intent, snippet choice, regex generation
    - Runs on Celery `ai_queue`

## Key Features

-   **Natural Language Interface**: "Get me all prices from this page."
-   **Token-Optimized AI**: Works on visible text, then focused HTML snippets to cut LLM cost.
-   **Regex + Cache**: Generated regex is cached per-domain/keywords for reuse.
-   **Automated Scheduling**: Cron-like schedules per user via `/api/v1/jobs`.
-   **Robust Fetching**: Playwright worker with retry/backoff knobs.
-   **Microservices**: Scalable and decoupled architecture.
-   **JWT Auth**: All task and schedule endpoints require Bearer tokens.

## Setup & Installation

1.  **Prerequisites**: Docker and Docker Compose.
2.  **Environment Variables**:
    -   Copy `.env.example` to `.env`.
    -   Set your LLM keys (`GOOGLE_API_KEY` or `GEMINI_API_KEY`, or `OPENAI_API_KEY`).
    -   Choose provider/model via `LLM_PROVIDER`/`LLM_MODEL` (default: gemini / gemini-2.0-flash).
    -   Set `SECRET_KEY` for JWT auth.
    -   Use least-privilege DB creds: `DB_USER=app_write`, `DB_PASSWORD=<strong>`, keep `POSTGRES_USER` only for admin/bootstrap.
3.  **Run**:
    ```bash
    docker-compose up --build
    ```

## Database Setup (roles, migrations, seeds)

- **Roles (once per environment, run as postgres):**
  ```bash
  psql -h <host> -p 5432 -U postgres -d diploma_db \
    -v app_read_pwd='<strong>' \
    -v app_write_pwd='<strong>' \
    -v app_admin_pwd='<strong>' \
    -f scripts/db_roles.sql
  ```
- **Migrations:** `alembic upgrade head` (or let the API start with the database available and alembic invoked separately).
- **Seeds (idempotent, run as app_admin):**
  ```bash
  psql -h <host> -p 5432 -U app_admin -d diploma_db -f scripts/db_seed.sql
  # demo credentials: demo_user / Password123!
  ```
- **Schema/roles reference:** see `reference_docs/DB/data_dictionary.md`.

## Services & API

Once running, visit: `http://localhost:8000/docs`.

### Auth
-   Register: `POST /auth/register`
-   Login: `POST /auth/token` -> returns `access_token`
-   Use `Authorization: Bearer <token>` for all `/api/v1/*` routes

### Authentication
-   Required for tasks and schedules.

### Core Endpoints
-   **Create Task**: `POST /api/v1/process`
-   **Check Status**: `GET /api/v1/status/{task_id}`
-   **Get Result**: `GET /api/v1/result/{task_id}`

### Scheduling
-   **Create Job**: `POST /api/v1/jobs`
-   **List Jobs**: `GET /api/v1/jobs`
-   **Delete Job**: `DELETE /api/v1/jobs/{job_id}`
-   Jobs enqueue tasks via Celery Beat every minute.

### Workers & Queues
-   **Headless Worker** (`fetching_queue`): Playwright fetch → sends `scrape.process_content`
-   **AI Worker** (`ai_queue`): Intent + regex pipeline; caches parsers
-   **Scheduler**: Celery Beat task `scheduler.check_due_jobs`

## Development

-   **Run Tests**:
    ```bash
    docker-compose exec api pytest tests/
    ```
-   **Linting**:
    ```bash
    ruff check .
    ```
