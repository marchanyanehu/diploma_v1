# Playwright Headless Worker

This service fetches pages with Playwright and extracts semantic content with role markers for the AI pipeline.

Key points:

- Runs Celery worker on `fetching_queue` (see `shared/celery_app.py`).
- Tasks live in `services/headless_worker/tasks.py`.
- Captures **semantic content** (structured text with role markers: `[LINK:]`, `[BUTTON:]`, `##` headings, `•` lists, `|` tables).
- Captures full HTML and network events for complete context.
- Enqueues `scrape.process_content` to `ai_queue` with both semantic and HTML content.
- Base image: `mcr.microsoft.com/playwright/python` (browsers included).
- Connects to Redis (broker/backend) and Postgres for task status updates.

Environment variables (see root `.env.example`):

- `REDIS_URL`, `CELERY_BROKER_URL`, `CELERY_RESULT_BACKEND`
- `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`
- `PLAYWRIGHT_HEADLESS`, `PLAYWRIGHT_NAV_TIMEOUT_MS`, `PLAYWRIGHT_SETTLE_DELAY_MS`, `PLAYWRIGHT_MAX_RETRIES`
- `GOOGLE_API_KEY` / `GEMINI_API_KEY` or `OPENAI_API_KEY` (used downstream by AI worker)

Run with Docker Compose:

The root `docker-compose.yml` defines `headless_worker`. `docker-compose up --build` starts the API, workers, Redis, Postgres, and scheduler together.
