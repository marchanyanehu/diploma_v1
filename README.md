# Intelligent Web Data Aggregator

A microservice-based web scraping system powered by LLMs to intelligently extract structured data from websites using natural language queries.

## Target Audience & Use Cases

### Who Is This For?

| Audience | Use Case |
|----------|----------|
| **Data Analysts** | Extract tabular data from websites without coding |
| **Market Researchers** | Collect competitor pricing, product listings |
| **Recruiters / HR** | Aggregate job postings from multiple career pages |
| **Journalists** | Gather public records, event listings, statistics |
| **Developers** | Build automated data pipelines via API integration |

### Example Scenarios

1. **E-commerce Monitoring**: "Extract all product names and prices from the sale section"
2. **Job Aggregation**: "Get job titles and locations for remote positions"
3. **News Collection**: "Find all article headlines with publication dates"
4. **Real Estate**: "Extract property prices and addresses from listings"
5. **Event Tracking**: "Get event names, dates, and venues from the calendar"

## Documentation

-   📐 [Architecture Overview](docs/ARCHITECTURE.md) - System design and data flow
-   🤖 [AI Prompts](docs/AI_PROMPTS.md) - Prompt engineering documentation
-   📖 [User Guide](docs/USER_GUIDE.md) - Step-by-step usage instructions
-   ⚠️ [System Limitations](docs/SYSTEM_LIMITATIONS.md) - What the system cannot do
-   💬 [Example Dialogs](docs/EXAMPLE_DIALOGS.md) - 15+ usage examples and test scenarios

## Architecture

Microservice layout with shared infrastructure (see `docs/ARCHITECTURE.md` for detailed diagram):

### Services

1. **API Service (`services/api/`)**
    - JWT auth (`/auth/register`, `/auth/token`)
    - Creates scraping tasks and exposes status/result endpoints
    - Manages user-owned schedules (CRUD on `/api/v1/jobs`)
2. **Scheduler Service (`services/scheduler/`)**
    - Celery Beat job that enqueues due schedules every minute
3. **Headless Worker (`services/headless_worker/`)**
    - Playwright fetcher; captures semantic content (structured text with markers) + full HTML
    - Uses smart content extraction with role markers: `[LINK: text]`, `[BUTTON: text]`, `##` headings, `•` lists, `|` tables
    - Runs on Celery `fetching_queue`
4. **AI Worker (`services/ai_worker/`)**
    - Intent extraction + dual-path extraction pipeline (schema vs single-field)
    - Uses LLM (DeepSeek/Gemini/OpenAI) for intent, extraction, and regex generation
    - Field-based caching with complete URL matching for fast reuse
    - Runs on Celery `ai_queue`
    - Input sanitization module (`services/ai_worker/input_sanitization.py`) reused by the API

### Shared Infrastructure (`shared/`)

- **`config.py`**: Application settings (database, Redis, LLM, security) used by all services
- **`database/`**: Database layer (connection, ORM models, CRUD utilities) shared across services
- **`celery_app.py`**: Celery configuration and task queues

## Key Features

-   **Natural Language Interface**: "Get me all prices from this page." or "Extract product title, price, and description"
-   **Semantic Content Extraction**: Structured text with role markers (`[LINK]`, `[BUTTON]`, `##` headings) for cleaner LLM prompts
-   **Dual Extraction Paths**: 
    - **Schema extraction**: Multi-field structured data (title + price + description) with proper field associations
    - **Single-field extraction**: Optimized pipeline with example finding and focused snippets
-   **Smart Caching**: Field-based regex cache per complete URL - reuses patterns for same URL + field combinations
-   **Token-Optimized AI**: LLM only sees 32KB snippets, regex runs on full content locally
-   **Auto-Invalidating Cache**: Patterns automatically validated and removed when they fail
-   **Automated Scheduling**: Cron-like schedules per user via `/api/v1/jobs`
-   **Robust Fetching**: Playwright worker with retry/backoff and stealth features
-   **Microservices**: Scalable and decoupled architecture
-   **JWT Auth**: All task and schedule endpoints require Bearer tokens
-   **Rate Limiting**: API endpoints are rate-limited to prevent abuse
-   **Prompt Injection Protection**: User inputs are sanitized against malicious patterns

## Security Features

-   **API Keys**: Stored in environment variables, never in code
-   **Rate Limiting**: 
    -   `/api/v1/process`: 10 requests/minute
    -   `/auth/register`: 5 requests/minute  
    -   `/auth/token`: 10 requests/minute
-   **Input Sanitization**: Dangerous prompt patterns are blocked (instruction override, jailbreak attempts)
-   **JWT Authentication**: All protected endpoints require valid Bearer tokens

## Setup & Installation

1.  **Prerequisites**: Docker and Docker Compose.
2.  **Environment Variables**:
    -   Copy `.env.example` to `.env`.
    -   Set your LLM keys (`BASETEN_API_KEY` for DeepSeek via Baseten; fallback `GOOGLE_API_KEY`/`GEMINI_API_KEY` for Gemini; optional `OPENAI_API_KEY`).
    -   Choose provider/model via `LLM_PROVIDER`/`LLM_MODEL` (default: baseten / baseten/deepseek-ai/DeepSeek-V3.2). Optional fallback via `LLM_FALLBACK_PROVIDER`/`LLM_FALLBACK_MODEL` (default: gemini / gemini-2.0-flash).
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
-   **Headless Worker** (`fetching_queue`): Playwright fetch with semantic content extraction → sends `scrape.process_content`
-   **AI Worker** (`ai_queue`): 
    - Intent extraction (target, keywords, schema_fields)
    - Schema extraction path for multi-field requests (returns LLM data with field associations)
    - Single-field extraction path with example finding and regex generation
    - Field-based caching with URL pattern matching
-   **Scheduler**: Celery Beat task `scheduler.check_due_jobs`

## Development

-   **Run Tests**:
    ```bash
    # Inside Docker
    docker-compose exec api pytest tests/
    
    # Or locally with virtual environment
    pytest tests/ -v
    ```
-   **Run Specific Test Files**:
    ```bash
    pytest tests/test_input_sanitization.py tests/test_intent_extraction.py -v
    ```
