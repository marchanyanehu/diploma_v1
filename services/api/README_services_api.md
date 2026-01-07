# FastAPI Service - Intelligent Web Data Aggregator

This is the main API service for the Intelligent Web Data Aggregator project. It exposes authenticated endpoints to create scraping tasks, poll their status/results, and manage user schedules.

## Features

- **JWT Auth**: `/auth/register` and `/auth/token` issue Bearer tokens.
- **Task lifecycle**: create, poll status, and fetch results for scraping tasks.
- **Scheduling**: per-user cron schedules via `/api/v1/jobs`.
- **Celery integration**: enqueues headless + AI workers (`shared/celery_app.py`).
- **Rate Limiting**: slowapi-based limits (10/min process, 5/min register, 10/min login).
- **Input Sanitization**: Prompt injection protection via `services/ai_worker/input_sanitization.py`.
- **FastAPI extras**: OpenAPI docs, CORS, error handlers, logging.

## Project Structure

```
services/api/
├── main.py              # FastAPI app, routes, rate limiting
├── auth.py              # JWT authentication helpers
├── config.py            # DEPRECATED: Re-exports from shared.config
├── models.py            # DEPRECATED: Re-exports from .schemas
├── schemas.py           # Pydantic request/response schemas (API contracts)
├── repositories.py      # DB repositories
├── services/            # task_service, auth_service, task_presenter
├── logging_config.py    # Structured logging
├── error_handlers.py    # Custom error responses
├── Dockerfile           # API container build
└── requirements.txt     # Python dependencies (now at repo root)

shared/                  # Shared infrastructure across all services
├── config.py            # Settings loader (env/.env) - used by all services
├── celery_app.py        # Celery configuration
└── database/            # Database layer (shared across services)
    ├── __init__.py      # Exports all DB components
    ├── connection.py    # Session & engine management
    ├── models.py        # ORM models (User, ScrapingTask, ParserCache, etc.)
    └── utils.py         # Database CRUD operations

services/ai_worker/      # AI worker service
├── input_sanitization.py# Prompt injection protection reused by API
├── llm_client.py        # LLM abstraction (DeepSeek/Gemini/OpenAI)
├── intent_extraction.py # User prompt → structured intent
├── regex_generation.py  # Iterative regex generation
├── workflows.py         # Schema extraction and caching
├── tasks.py             # Celery tasks for AI processing
└── utils.py             # Helper utilities

tests/                   # All test files
├── test_api_*.py        # API endpoint tests
├── test_auth.py         # Authentication tests
├── test_input_sanitization.py
├── test_intent_extraction.py
└── ...                  # Other module tests
```

## Quick Start

### Local Development

1. **Install Dependencies** (from repo root):
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables** (or copy `.env.example` to project root):
   ```bash
   export DEBUG=true
   export HOST=localhost
   export PORT=8000
   export LLM_PROVIDER=gemini   # or openai
   export GOOGLE_API_KEY=...    # or GEMINI_API_KEY / OPENAI_API_KEY
   export SECRET_KEY=...
   ```

3. **Run the Application**:
   ```bash
   uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

4. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - Alternative Docs: http://localhost:8000/redoc
   - Health Check: http://localhost:8000/health
   - API Health: http://localhost:8000/api/v1/health

### Docker Deployment

1. **Build the Image**:
   ```bash
   docker build -t diploma-api .
   ```

2. **Run the Container**:
   ```bash
   docker run -p 8000:8000 diploma-api
   ```

## API Endpoints

### Health
- `GET /` - Root metadata
- `GET /health` - Service health
- `GET /api/v1/health` - API + DB health

### Auth (JWT)
- `POST /auth/register` - Create new user (rate limit: 5/min)
- `POST /auth/token` - Login, returns `access_token` (rate limit: 10/min)

### Tasks (auth required)
- `POST /api/v1/process` - Create scraping task (rate limit: 10/min)
- `GET /api/v1/status/{task_id}` - Poll task status
- `GET /api/v1/result/{task_id}` - Get final result (202 if not ready)

### Scheduling (auth required)
- `POST /api/v1/jobs` - Create cron job
- `GET /api/v1/jobs` - List jobs for current user
- `DELETE /api/v1/jobs/{job_id}` - Delete job

Background work is dispatched via Celery to `headless_worker` (fetching_queue) and `ai_worker` (ai_queue). See `shared/celery_app.py`, `services/headless_worker/tasks.py`, and `services/ai_worker/tasks.py`.

## Module Organization

The project follows microservices principles with shared infrastructure:

- **`shared/config.py`**: Application settings used by all services (database, Redis, LLM, security)
- **`shared/database/`**: Database layer accessible to all services (connection, models, utilities)
- **`services/api/schemas.py`**: Pydantic API contracts (request/response models)
- **`services/ai_worker/llm_client.py`**: LLM abstraction layer (DeepSeek/Gemini/OpenAI)
- **`services/api/config.py`**: Backward-compatible stub (re-exports from `shared.config`)
- **`services/api/models.py`**: Backward-compatible stub (re-exports from `.schemas`)

New code should:
- Import config from `shared.config`
- Import database from `shared.database`
- Import schemas from `services.api.schemas` (within API) or `.schemas` (relative)
- Import LLM client from `services.ai_worker.llm_client` (within AI worker)

## Security

### Rate Limiting
- Uses `slowapi` with Redis storage (falls back to in-memory if Redis unavailable)
- `/api/v1/process`: 10 requests/minute per IP
- `/auth/register`: 5 requests/minute per IP
- `/auth/token`: 10 requests/minute per IP

### Input Sanitization
User prompts are sanitized via `services/ai_worker/input_sanitization.py` before processing:
- Blocks prompt injection attempts ("ignore previous instructions", etc.)
- Blocks jailbreak patterns ("DAN mode", "no restrictions", etc.)
- Blocks system prompt extraction attempts
- Returns 400 Bad Request with explanation when blocked

### Authentication
- JWT tokens with configurable expiry (default: 30 minutes)
- Passwords hashed with bcrypt via passlib
- All `/api/v1/*` endpoints require valid Bearer token

## Configuration

Key environment variables (root `.env` or process env):

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `DATABASE_URL` / `DB_*` | - | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis/Celery broker + rate limit storage |
| `CELERY_BROKER_URL` | `${REDIS_URL}` | Celery broker |
| `CELERY_RESULT_BACKEND` | `${REDIS_URL}` | Celery backend |
| `BASETEN_API_KEY` | - | Baseten (DeepSeek) LLM key |
| `GOOGLE_API_KEY`/`GEMINI_API_KEY` | - | Gemini fallback LLM key |
| `OPENAI_API_KEY` | - | OpenAI LLM key (optional) |
| `LLM_PROVIDER` | `baseten` | Primary LLM provider |
| `LLM_MODEL` | `baseten/deepseek-ai/DeepSeek-V3.2` | Primary model name |
| `LLM_FALLBACK_PROVIDER` | `gemini` | Fallback provider |
| `LLM_FALLBACK_MODEL` | `gemini-3.0-flash` | Fallback model name |
| `LLM_REQUEST_TIMEOUT_S` | `60` | LLM request timeout |
| `SECRET_KEY` | - | JWT signing key |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |
| `TESTING` | `false` | Disables Redis for rate limiting in tests |

## Testing

Run the test suite:

```bash
# Install test dependencies (included in requirements.txt)
pip install -r requirements.txt

# Run tests
pytest

# Run with coverage
pytest --cov=. --cov-report=html
```

## Development

### Code Quality

The project uses the following tools for code quality:

- **Black**: Code formatting
- **Ruff**: Fast Python linter
- **Pytest**: Testing framework

Run code quality checks:

```bash
# Format code
black .

# Lint code
ruff check .

# Run tests
pytest
```

### Adding New Endpoints

1. Define Pydantic models in `models/__init__.py`
2. Add endpoint functions to `main.py`
3. Add corresponding tests in `tests/`
4. Update this README with endpoint documentation

## Error Handling

The API provides structured error responses:

```json
{
  "error": "Error Type",
  "message": "Human-readable error message",
  "details": {},
  "timestamp": "2025-08-03T14:30:00Z"
}
```

Common HTTP status codes:
- `200` - Success
- `202` - Accepted (for async operations)
- `400` - Bad Request
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error

## Monitoring

### Health Checks

The service provides multiple health check endpoints:

- `/health` - Basic health status
- `/api/v1/health` - API-specific health with endpoint information

### Logging

The application uses structured logging with uvicorn's built-in logging capabilities. In production, consider using structured logging libraries like `structlog`.

## Current Status

This FastAPI application includes:

- ✅ `/api/v1/process` endpoint with async task creation
- ✅ Pydantic models for all request/response schemas
- ✅ Celery integration with separate queues (fetching, AI)
- ✅ PostgreSQL with SQLAlchemy ORM
- ✅ LiteLLM integration (Gemini/OpenAI support)
- ✅ JWT authentication with user registration
- ✅ Rate limiting (slowapi with Redis/memory fallback)
- ✅ Prompt injection protection
- ✅ Scheduled jobs with cron expressions
- ✅ Parser caching for regex reuse

## License

This project is part of a diploma thesis and is for academic purposes.
