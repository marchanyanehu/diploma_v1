# Getting Started Guide

This guide will help you set up and start using the Intelligent Web Data Aggregator API.

## Prerequisites

- **Python 3.9+** (recommended 3.11+)
- **PostgreSQL 12+** (or compatible database)
- **Redis 6+** (for rate limiting and Celery)
- **Docker & Docker Compose** (optional, for containerized deployment)

## Installation Methods

### Method 1: Local Development (Recommended)

1. **Clone the repository** (if applicable):
   ```bash
   git clone <repository-url>
   cd diploma
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Copy the example environment file and configure it:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` with your configuration:
   ```bash
   # Database
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=diploma_db
   DB_USER=postgres
   DB_PASSWORD=your_password
   
   # Redis
   REDIS_URL=redis://localhost:6379/0
   
   # JWT Secret
   SECRET_KEY=your-secret-key-change-this-in-production
   
   # LLM Configuration
   LLM_PROVIDER=gemini  # or openai, baseten
   GOOGLE_API_KEY=your-gemini-api-key  # if using Gemini
   ```

4. **Initialize the database**:
   ```bash
   # Create database tables
   python -c "from shared.database.connection import create_tables; create_tables()"
   ```

5. **Start the API server**:
   ```bash
   uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000
   ```

6. **Start Celery workers** (in separate terminals):
   ```bash
   # Start headless worker (web scraping)
   celery -A shared.celery_app.celery_app worker -Q fetching_queue --loglevel=info
   
   # Start AI worker (LLM processing)
   celery -A shared.celery_app.celery_app worker -Q ai_queue --loglevel=info
   ```

### Method 2: Docker Deployment

1. **Build and run with Docker Compose**:
   ```bash
   docker-compose up --build
   ```

2. **Or build individual services**:
   ```bash
   # Build API service
   docker build -t diploma-api -f services/api/Dockerfile .
   
   # Run with environment variables
   docker run -p 8000:8000 --env-file .env diploma-api
   ```

## Quick Test

1. **Verify the API is running**:
   ```bash
   curl http://localhost:8000/health
   ```
   
   Expected response:
   ```json
   {
     "status": "healthy",
     "timestamp": "2025-08-08T12:00:00Z",
     "service": "api",
     "version": "1.0.0",
     "uptime": "operational"
   }
   ```

2. **Access interactive documentation**:
   Open your browser and navigate to:
   - Swagger UI: http://localhost:8000/docs
   - ReDoc: http://localhost:8000/redoc

## Creating Your First Task

### Step 1: Register a User

```bash
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "username": "testuser",
    "password": "testpassword123",
    "email": "test@example.com"
  }'
```

### Step 2: Get Authentication Token

```bash
curl -X POST http://localhost:8000/auth/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=testuser&password=testpassword123"
```

Save the `access_token` from the response.

### Step 3: Create a Scraping Task

```bash
curl -X POST http://localhost:8000/api/v1/process \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com",
    "prompt": "Extract all headings from the page"
  }'
```

Save the `task_id` from the response.

### Step 4: Check Task Status

```bash
curl -X GET "http://localhost:8000/api/v1/status/YOUR_TASK_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

### Step 5: Get Results (when task completes)

```bash
curl -X GET "http://localhost:8000/api/v1/result/YOUR_TASK_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Configuration Options

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `DEBUG` | `false` | Enable debug mode |
| `HOST` | `0.0.0.0` | Server host |
| `PORT` | `8000` | Server port |
| `DATABASE_URL` | - | PostgreSQL connection URL |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `SECRET_KEY` | - | JWT signing key (required) |
| `LLM_PROVIDER` | `baseten` | Primary LLM provider |
| `LLM_MODEL` | `baseten/deepseek-ai/DeepSeek-V3.2` | Primary model |
| `LLM_FALLBACK_PROVIDER` | `gemini` | Fallback provider |
| `CORS_ORIGINS` | `*` | Allowed CORS origins |

### Database Configuration

The API supports PostgreSQL with the following connection options:

1. **Individual parameters**:
   ```bash
   DB_HOST=localhost
   DB_PORT=5432
   DB_NAME=diploma_db
   DB_USER=postgres
   DB_PASSWORD=password
   ```

2. **Connection URL**:
   ```bash
   DATABASE_URL=postgresql://user:password@localhost:5432/diploma_db
   ```

### LLM Configuration

Configure your preferred LLM provider:

1. **Gemini (Google)**:
   ```bash
   LLM_PROVIDER=gemini
   GOOGLE_API_KEY=your-api-key
   ```

2. **OpenAI**:
   ```bash
   LLM_PROVIDER=openai
   OPENAI_API_KEY=your-api-key
   ```

3. **DeepSeek (via Baseten)**:
   ```bash
   LLM_PROVIDER=baseten
   BASETEN_API_KEY=your-api-key
   ```

## Common Issues & Troubleshooting

### Database Connection Issues

**Symptoms**: `500 Internal Server Error` on `/api/v1/health`

**Solutions**:
1. Verify PostgreSQL is running:
   ```bash
   psql -h localhost -U postgres -c "SELECT 1;"
   ```
2. Check environment variables:
   ```bash
   echo $DATABASE_URL
   ```
3. Ensure database exists:
   ```bash
   createdb diploma_db
   ```

### Redis Connection Issues

**Symptoms**: Rate limiting falls back to in-memory storage

**Solutions**:
1. Verify Redis is running:
   ```bash
   redis-cli ping
   ```
2. Check Redis URL format:
   ```bash
   redis://localhost:6379/0
   ```

### Authentication Issues

**Symptoms**: `401 Unauthor `401 Unauthorized` errors

**Solutions**:
1. Verify token format:
   ```bash
   Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   ```
2. Check token expiration (default: 30 minutes)
3. Ensure user is active in database

### Rate Limiting Issues

**Symptoms**: `429 Too Many Requests`

**Solutions**:
1. Check rate limits:
   - Registration: 5 requests/minute
   - Login: 10 requests/minute
   - Process: 10 requests/minute
2. Implement exponential backoff in your client
3. Use correlation ID for debugging

## Next Steps

1. **Explore the API**: Use the interactive documentation at `/docs`
2. **Review examples**: Check the Integration Tutorial for practical use cases
3. **Set up monitoring**: Configure logging and health checks for production
4. **Implement error handling**: Review the Error Handling Guide for best practices

## Support

If you encounter issues:

1. **Check logs**: API logs are available in `logs/api.log` (if configured)
2. **Review documentation**: All endpoints are documented in the API Reference
3. **Contact support**: Email dadada.marchan@gmail.com for assistance

## Contact support**: Email dadada.marchan@gmail.com for assistance