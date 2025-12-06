# FastAPI Service - Intelligent Web Data Aggregator

This is the main API service for the Intelligent Web Data Aggregator project. It exposes authenticated endpoints to create scraping tasks, poll their status/results, and manage user schedules.

## Features

- **JWT Auth**: `/auth/register` and `/auth/token` issue Bearer tokens.
- **Task lifecycle**: create, poll status, and fetch results for scraping tasks.
- **Scheduling**: per-user cron schedules via `/api/v1/jobs`.
- **Celery integration**: enqueues headless + AI workers (`shared/celery_app.py`).
- **FastAPI extras**: OpenAPI docs, CORS, error handlers, logging.

## Project Structure

```
services/api/
├── main.py              # FastAPI app and routes
├── config.py            # Settings loader (env/.env)
├── database.py          # Session & engine
├── db_models.py         # ORM models
├── models.py            # Pydantic schemas
├── services/            # task/auth services
├── repositories.py      # DB repositories
├── logging_config.py    # Structured logging
├── error_handlers.py    # Custom error responses
└── tests/               # API and service tests
```

## Quick Start

### Local Development

1. **Install Dependencies**:
   ```bash
   cd services/api
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
- `POST /auth/register`
- `POST /auth/token` → `access_token`

### Tasks (auth required)
- `POST /api/v1/process` - Create scraping task (returns task_id)
- `GET /api/v1/status/{task_id}` - Poll task status
- `GET /api/v1/result/{task_id}` - Get final result (202 if not ready)

### Scheduling (auth required)
- `POST /api/v1/jobs` - Create cron job
- `GET /api/v1/jobs` - List jobs for current user
- `DELETE /api/v1/jobs/{job_id}` - Delete job

Background work is dispatched via Celery to `headless_worker` (fetching_queue) and `ai_worker` (ai_queue). See `shared/celery_app.py`, `services/headless_worker/tasks.py`, and `services/ai_worker/tasks.py`.

## Configuration

Key environment variables (root `.env` or process env):

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `DATABASE_URL` / `DB_*` | - | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis/Celery broker |
| `CELERY_BROKER_URL` | `${REDIS_URL}` | Celery broker |
| `CELERY_RESULT_BACKEND` | `${REDIS_URL}` | Celery backend |
| `GOOGLE_API_KEY`/`GEMINI_API_KEY` | - | Gemini LLM key |
| `OPENAI_API_KEY` | - | OpenAI LLM key |
| `LLM_PROVIDER` | `gemini` | LLM provider |
| `LLM_MODEL` | `gemini-2.0-flash` | Model name |
| `SECRET_KEY` | - | JWT signing key |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

## Testing

Run the test suite:

```bash
# Install test dependencies (included in requirements.txt)
pip install pytest pytest-asyncio pytest-cov

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

## Next Steps

This FastAPI application is ready for:

1. **Task #201**: Adding the `/api/v1/process` endpoint
2. **Task #202**: Implementing detailed Pydantic models
3. **Task #203**: Integrating Celery for async processing
4. **Database Integration**: Connecting to PostgreSQL
5. **LLM Integration**: Adding OpenAI API client

## License

This project is part of a diploma thesis and is for academic purposes.
