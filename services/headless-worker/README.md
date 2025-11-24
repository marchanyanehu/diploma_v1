# Playwright Worker Service

This service runs the background scraping pipeline using Celery and Playwright. It subscribes to the default Celery queue and executes tasks defined in `services.playwright_worker.tasks`.

Key points:

- Base image: `mcr.microsoft.com/playwright/python` (includes browsers and Playwright Python bindings).
- Celery app is shared via `shared/celery_app.py` so API and worker use the same configuration.
- The worker connects to Redis as broker/result backend and to PostgreSQL to update task status.

Environment variables (see `.env.example`):

- REDIS_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND
- DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASSWORD
- PLAYWRIGHT_HEADLESS, PLAYWRIGHT_TIMEOUT (for future tasks)
- GOOGLE_API_KEY or GEMINI_API_KEY (for Gemini/AI Studio via LiteLLM)

Run with Docker Compose:

The root `docker-compose.yml` defines the `worker` service. When you start the stack, the worker will boot and listen for tasks enqueued by the API.
