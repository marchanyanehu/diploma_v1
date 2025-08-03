# FastAPI Service - Intelligent Web Data Aggregator

This is the main API service for the Intelligent Web Data Aggregator project. It provides REST endpoints for processing web scraping requests using natural language prompts.

## Features

- **FastAPI Framework**: Modern, fast web framework for building APIs
- **Automatic Documentation**: Interactive API documentation with Swagger UI
- **Data Validation**: Request/response validation with Pydantic
- **Health Checks**: Built-in health monitoring endpoints
- **CORS Support**: Cross-origin resource sharing configuration
- **Error Handling**: Comprehensive error handling with custom responses
- **Configuration Management**: Environment-based configuration
- **Docker Support**: Containerized deployment with multi-stage builds

## Project Structure

```
services/api/
├── main.py              # Main FastAPI application
├── config.py            # Configuration settings
├── requirements.txt     # Python dependencies
├── Dockerfile          # Container configuration
├── run_dev.py          # Development runner
├── models/             # Pydantic models
│   └── __init__.py     # Request/response models
└── tests/              # Test suite
    ├── __init__.py
    ├── conftest.py     # Test configuration
    └── test_main.py    # Main application tests
```

## Quick Start

### Local Development

1. **Install Dependencies**:
   ```bash
   cd services/api
   pip install -r requirements.txt
   ```

2. **Set Environment Variables** (optional):
   ```bash
   export DEBUG=true
   export HOST=localhost
   export PORT=8000
   ```

3. **Run the Application**:
   ```bash
   # Option 1: Using the development runner
   python run_dev.py
   
   # Option 2: Using uvicorn directly
   uvicorn main:app --reload --host localhost --port 8000
   
   # Option 3: Using the main module
   python main.py
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

### Core Endpoints

- `GET /` - Root endpoint with API information
- `GET /health` - Health check endpoint
- `GET /api/v1/health` - API v1 health check

### Future Endpoints (Tasks #201-207)

- `POST /api/v1/process` - Process scraping request
- `GET /api/v1/status/{task_id}` - Check task status
- `GET /api/v1/result/{task_id}` - Get task results

## Configuration

The application supports configuration through environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `DATABASE_URL` | - | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string |
| `OPENAI_API_KEY` | - | OpenAI API key for LLM |
| `SECRET_KEY` | - | Application secret key |
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
