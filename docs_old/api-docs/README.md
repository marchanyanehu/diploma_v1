# Combined Markdown

> Generated: 2025-12-17 16:23:08

## API_REFERENCE.md

*(Modified: 2025-12-14 18:08:29)*

# API Reference

## Base URL
`http://localhost:8000` (development) or your deployed instance URL

## Authentication
All API endpoints (except `/auth/*` and `/health`) require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_access_token>
```

## Endpoints

### Health Endpoints

#### `GET /`
**Description**: Root endpoint providing basic API information

**Response**:
```json
{
  "message": "Intelligent Web Data Aggregator API",
  "version": "1.0.0",
  "status": "operational",
  "timestamp": "2025-08-08T12:00:00Z",
  "documentation": "/docs",
  "health_check": "/health"
}
```

#### `GET /health`
**Description**: Basic health check for monitoring and load balancers

**Response**:
```json
{
  "status": "healthy",
  "timestamp": "2025-08-08T12:00:00Z",
  "service": "api",
  "version": "1.0.0",
  "uptime": "operational"
}
```

#### `GET /api/v1/health`
**Description**: API v1 health check with database connectivity test

**Response**:
```json
{
  "api_version": "v1",
  "status": "healthy",
  "timestamp": "2025-08-08T12:00:00Z",
  "database": {
    "status": "connected",
    "tasks_count": 42,
    "parsers_count": 15
  },
  "endpoints": {
    "process": "/api/v1/process",
    "status": "/api/v1/status/{task_id}",
    "result": "/api/v1/result/{task_id}"
  }
}
```

### Authentication Endpoints

#### `POST /auth/register`
**Description**: Create new user account

**Rate Limit**: 5 requests per minute per IP

**Request Body**:
```json
{
  "username": "johndoe",
  "password": "securepassword123",
  "email": "john@example.com"
}
```

**Response**:
```json
{
  "id": 1,
  "username": "johndoe",
  "email": "john@example.com",
  "is_active": true
}
```

**Error Responses**:
- `400 Bad Request`: Username already registered
- `429 Too Many Requests`: Rate limit exceeded

#### `POST /auth/token`
**Description**: Login and obtain JWT access token

**Rate Limit**: 10 requests per minute per IP

**Request Body** (form data):
```
username=johndoe&password=securepassword123
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Error Responses**:
- `401 Unauthorized`: Incorrect username or password
- `429 Too Many Requests`: Rate limit exceeded

### Core API Endpoints (v1)

#### `POST /api/v1/process`
**Description**: Create a scraping task with URL and natural language prompt

**Authentication**: Required (Bearer token)

**Rate Limit**: 10 requests per minute per IP

**Request Body**:
```json
{
  "url": "https://example-jobs.com",
  "prompt": "I want all the job listings with their titles and locations"
}
```

**Response** (`202 Accepted`):
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "PENDING",
  "message": "Task created successfully"
}
```

**Error Responses**:
- `400 Bad Request`: Invalid URL format or prompt injection detected
- `401 Unauthorized`: Not authenticated
- `429 Too Many Requests`: Rate limit exceeded

#### `GET /api/v1/status/{task_id}`
**Description**: Check current status of a scraping task

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `task_id` (string): UUID of the task

**Response**:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "IN_PROGRESS",
  "progress": 40,
  "message": null,
  "created_at": "2025-08-08T12:00:00Z",
  "updated_at": "2025-08-08T12:00:20Z"
}
```

**Possible Status Values**:
- `PENDING`: Task created but not started
- `IN_PROGRESS`: Task is being processed
- `SUCCESS`: Task completed successfully
- `FAILED`: Task failed

**Error Responses**:
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Not authorized to access this task
- `404 Not Found`: Task not found

#### `GET /api/v1/result/{task_id}`
**Description**: Get final extracted data for a completed task

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `task_id` (string): UUID of the task

**Success Response** (`200 OK`):
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "SUCCESS",
  "url": "https://example-jobs.com",
  "prompt": "I want all the job listings with their titles and locations",
  "data": [
    {
      "text": "Senior Software Engineer — Berlin",
      "source": "//div[@class='job-card']/h2",
      "confidence": 0.92
    }
  ],
  "metadata": {
    "total_matches": 1,
    "used_cached_parser": false
  },
  "processing_time": 3.21,
  "created_at": "2025-08-08T12:00:00Z",
  "completed_at": "2025-08-08T12:00:03Z"
}
```

**Pending Response** (`202 Accepted`):
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "IN_PROGRESS",
  "progress": 75,
  "message": null,
  "created_at": "2025-08-08T12:00:00Z",
  "updated_at": "2025-08-08T12:00:10Z"
}
```

**Error Responses**:
- `400 Bad Request`: Task failed
- `401 Unauthorized`: Not authenticated
- `403 Forbidden`: Not authorized to access this task
- `404 Not Found`: Task not found

### Scheduler Endpoints

#### `POST /api/v1/jobs`
**Description**: Create a scheduled cron job

**Authentication**: Required (Bearer token)

**Request Body**:
```json
{
  "url": "https://example-jobs.com",
  "prompt": "Get latest job postings",
  "schedule_cron": "0 9 * * *"  // Daily at 9 AM
}
```

**Response**:
```json
{
  "id": 1,
  "url": "https://example-jobs.com",
  "prompt": "Get latest job postings",
  "schedule_cron": "0 9 * * *",
  "next_run_at": "2025-08-09T09:00:00Z",
  "last_run_at": null,
  "created_at": "2025-08-08T12:00:00Z"
}
```

#### `GET /api/v1/jobs`
**Description**: List all scheduled jobs for current user

**Authentication**: Required (Bearer token)

**Response**:
```json
[
  {
    "id": 1,
    "url": "https://example-jobs.com",
    "prompt": "Get latest job postings",
    "schedule_cron": "0 9 * * *",
    "next_run_at": "2025-08-09T09:00:00Z",
    "last_run_at": null,
    "created_at": "2025-08-08T12:00:00Z"
  }
]
```

#### `DELETE /api/v1/jobs/{job_id}`
**Description**: Delete a scheduled job

**Authentication**: Required (Bearer token)

**Path Parameters**:
- `job_id` (integer): ID of the job to delete

**Response**:
```json
{
  "message": "Job deleted"
}
```

**Error Responses**:
- `404 Not Found`: Job not found

#### `GET /api/v1/users/me/activity`
**Description**: Get current user's scheduled jobs and recent tasks

**Authentication**: Required (Bearer token)

**Response**:
**Response**:
```json
{
  "tasks": [
    {
      "task_id": "123e4567-e89b-89b-12d3-a456-426614174000",
      "status": "SUCCESS",
      "progress": 100,
      "message": null,
      "created_at": "2025-08-08T12:00:00Z",
      "updated_at": "2025-08-08-08T12:00:03Z"
    }
  ],
  "scheduled_jobs": [
    {
      "id": 1,
      "url": "https://example-jobs.com",
      "prompt": "Get latest job postings",
      "schedule_cron": "0 9 * * *",
      "next_run_at": "2025-08-09T09:00:00Z",
      "last_run_at": null,
      "created_at": "2025-08-08T12:00:00Z"
    }
  ]
}
```

### Testing Endpoints

#### `POST /api/v1/test-task`
**Description**: Create a test task for database connectivity verification

**Authentication**: Not required

**Response**:
```json
{
  "message": "Test task created successfully",
  "task": {
    "id": 42,
    "task_id": "test-2025-08-08T12:00:00Z",
    "url": "https://example.com",
    "user_prompt": "Test task for database verification",
    "status": "PENDING",
    "created_at": "2025-08-08T12:00:00Z"
  }
}
```

## HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 202 | Accepted (async operation) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (not authenticated) |
| 403 | Forbidden (no permission) |
| 404 | Not Found |
| 422 | Validation Error (Pydantic) |
| 429 | Rate Limit Exceeded |
| 500 | Internal Server Error |

## Correlation ID

All API responses include a `X-Correlation-
-Id` header for request tracing. You can provide your own correlation ID in the request headers:
- `X-Correlation-Id` or `Correlation-Id`

## Pagination

Currently, list endpoints return all results. Future versions may implement pagination with `limit` and `offset` parameters.

## Versioning

The API uses URL versioning (`/api/v1/`). Breaking changes will result in a new version (`/api/v2/`).

---

## GETTING_STARTED.md

*(Modified: 2025-12-14 18:09:10)*

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

---

## INTEGRATION_TUTORIAL.md

*(Modified: 2025-12-14 18:09:45)*

# Integration Tutorial

This tutorial provides a step-by-step guide for integrating the Intelligent Web Data Aggregator API into your application. We'll walk through a complete workflow from authentication to retrieving results.

## Tutorial Overview

We'll build a job monitoring application that:
1. Authenticates with the API
2. Creates a scraping task for job listings
3. Monitors task status
4. Retrieves and processes results
5. Sets up scheduled monitoring

## Prerequisites

- Python 3.9+ installed
- Access to a running API instance (localhost:8000 or deployed)
- Basic understanding of HTTP requests and JSON

## Step 1: Setting Up Your Client

### Python Client Setup

Create a new Python file `job_monitor.py`:

```python
import requests
import time
import json
from typing import Dict, Any, Optional

class JobMonitorClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.access_token = None
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with authentication if available."""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.get('headers', {})
        
        if self.access_token:
            headers['Authorization'] = f"Bearer {self.access_token}"
        
        kwargs['headers'] = headers
        
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
```

## Step 2: User Registration and Authentication

### Register a New User

```python
def register_user(self, username: str, password: str, email: Optional[str] = None) -> Dict[str, Any]:
    """Register a new user account."""
    data = {
        "username": username,
        "password": password
    }
    if email:
        data["email"] = email
    
    return self._make_request(
        "POST", 
        "/auth/register",
        json=data
    )

# Usage
client = JobMonitorClient()
try:
    user = client.register_user("job_monitor", "securepass123", "monitor@example.com")
    print(f"User created: {user['username']}")
except requests.exceptions.HTTPError as e:
    if e.response.status_code == 400:
        print("Username already exists, trying login instead...")
    else:
        raise
```

### Login and Get Access Token

```python
def login(self, username: str, password: str) -> str:
    """Login and store access token."""
    data = {
        "username": username,
        "password": password
    }
    
    response = self._make_request(
        "POST",
        "/auth/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    
    self.access_token = response["access_token"]
    print(f"Login successful, token expires in 30 minutes")
    return self.access_token

# Usage
token = client.login("job_monitor", "securepass123")
```

## Step 3: Creating a Scraping Task

### Define Job Search Parameters

```python
def create_job_search_task(self, url: str, prompt: str) -> str:
    """Create a task to search for job listings."""
    data = {
        "url": url,
        "prompt": prompt
    }
    
    response = self._make_request(
        "POST",
        "/api/v1/process",
        json=data
    )
    
    task_id = response["task_id"]
    print(f"Task created: {task_id}")
    print(f"Status: {response['status']}")
    print(f"Message: {response['message']}")
    
    return task_id

# Usage
task_id = client.create_job_search_task(
    url="https://example-jobs.com/careers",
    prompt="I want all software engineering job listings job listings with job titles, locations, and required skills"
)
```

## Step 4: Monitoring Task Status

### Poll Task Status**

### Poll Task Status

```python
def poll_task_status(self, task_id: str, interval: int = 5, max_attempts: int = 60) -> Dict[str, Any]:
    """Poll task status until completion or timeout."""
    for attempt in range(max_attempts):
        try:
            status = self._make_request("GET", f"/api/v1/status/{task_id}")
            
            print(f"Attempt {attempt + 1}: Status = {status['status']}, Progress = {status.get('progress', 'N/A')}%")
            
            if status['status['status'] in ["SUCCESS", "FAILED"]:
                return status
            
            time.sleep(interval)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                print(f"Task {task_id} not found")
                break
            raise
    
    raise TimeoutError(f"Task {task_id} did not complete within {max_attempts * interval} seconds")

# Usage
status = client.poll_task_status(task_id, interval=10, max_attempts=30)
```

## Step 5: Retrieving and Processing Results

### Get Task Results

```python
def get_task_results(self, task_id: str) -> Dict[str, Any]:
    """Get final results for a completed task."""
    try:
        results = self._make_request("GET", f"/api/v1/result/{task_id}")
        
        if results.get("status"] == "SUCCESS":
            print(f"Task completed successfully!")
            print(f"Processing time: {results.get('processing_time', 'N/A')} seconds")
            print(f"Total matches: {results.get('metadata', {}).get('total_matches', 0)}")
            
            # Process extracted data
            extracted_data = results.get("data", [])
            self._process_extracted_data(extracted_data)
            
        return results
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 202:
            print("Task still in progress, try again later")
            return e.response.json()
        raise

def _process_extracted_data(self, data: List[Dict[str, Any]]):
    """Process and display extracted job data."""
    print("\n=== Extracted Job Listings ===")
    for i, item in enumerate(data, 1):
        text = item.get("text", "")
        confidence = item.get("confidence", 0)
        source = item.get("source", "")
        
        print(f"{i}. {text}")
        print(f"   Confidence: {confidence:.2%}")
        print(f"   Source: {source}")
        print()
    
# Usage
results = client.get_task_results(task_id)
```

## Step 6: Setting Up Scheduled Monitoring

### Create Scheduled Job

```python
def create_scheduled_job(self, url: str, prompt: str, cron_expression: str) -> Dict[str, Any]:
    """Create a scheduled job for regular monitoring."""
    data = {
        "url": url,
        "prompt": prompt,
        "schedule_cron": cron_expression
    }
    
    response = self._make_request(
        "POST",
        "/api/v1/jobs",
        json=data
    )
    
    print(f"Scheduled job created: ID = {response['id']}")
    print(f"Next run: {response.get('next_run_at', 'N/A')}")
    
    return response

# Usage: Daily at 9 AM
scheduled_job = client.create_scheduled_job(
    url="https://example-jobs.com/careers",
    prompt="Get latest software engineering job postings",
    cron_expression="0 9 * * *"  # Daily at 9 AM
)
```

### List and Manage Scheduled Jobs

```python
def list_scheduled_jobs(self) -> List[Dict[str, Any]]:
    """List all scheduled jobs for the current user."""
    return self._make_request("GET", "/api/v1/jobs")

def delete_scheduled_job(self, job_id: int) -> Dict[str, Any]:
    """Delete a scheduled job."""
    return self._make_request("DELETE", f"/api/v1/jobs/{job_id}")

# Usage
jobs = client.list_scheduled_jobs()
print(f"You have {len(jobs)} scheduled jobs")
for job in jobs:
    print(f"  - Job {job['id']}: {job['schedule_cron']} (runs {job['schedule_cron']})")
```

## Step 7: Complete Workflow Example

Here's a complete example that ties everything together:

```python
def monitor_job_listings():
    """Complete workflow for monitoring job listings."""
    client = JobMonitorClient("http://localhost:8000")
    
    # 1. Authenticate
    try:
        client.login("job_monitor", "securepass123")
    except:
        # If login fails, register first
        client.register_user("job_monitor", "securepass123", "monitor@example.com")
        client.login("job_monitor", "securepass123")
    
    # 2. Create immediate task
    print("Creating immediate job search task...")
    task_id = client.create_job_search_task(
        url="https://example-jobs.com/careers",
        prompt="Extract software engineering job openings with titles, locations, and required skills"
    )
    
    # 3. Monitor task
    print("\nMonitoring task progress...")
    status = client.poll_task_status(task_id, interval=10)
    
    # 4. Get results
    if status["status"] == "SUCCESS":
        print("\nRetrieving results...")
        results = client.get_task_results(task_id)
        
        # Save results to file
        with open("job_listings.json", "w") as f:
            json.dump(results, f, indent=2)
        print("Results saved to job_listings.json")
    
    # 5. Set up scheduled monitoring
    print("\nSetting up scheduled monitoring...")
    scheduled_job = client.create_scheduled_job(
        url="https://example-jobs.com/careers",
        prompt="Get latest software engineering job postings",
        cron_expression="0 9 * * 1-5"  # Weekdays at 9 AM
    )
    
    print("\n=== Summary ===")
    print(f"Immediate task: {task_id} ({status['status']})")
    print(f"Scheduled job: {scheduled_job['id']} (runs {scheduled_job['schedule_cron']})")
    print(f"Next scheduled run: {scheduled_job.get('next_run_at', 'N/A')}")

if __name__ == "__main__":
    monitor_job_listings()
```

## Step 8: Error Handling and Best Practices

### Implement Retry Logic

```python
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class ResilientJobMonitorClient(JobMonitorClient):
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self.session = self._create_resilient_session()
    
    def _create_resilient_session(self) -> requests.Session:
        """Create session with retry logic."""
        session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=0.5,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Override with resilient session."""
        url = f"{self.base_url}{endpoint}"
        headers = kwargs.get('headers', {})
        
        if self.access_token:
            headers['Authorization'] = f"Bearer {self.access_token}"
        
        kwargs['headers'] = headers
        kwargs['timeout'] = kwargs.get('timeout', 30)
        
        response = self.session.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
```

### Handle Rate Limiting

```python
def create_task_with_backoff(self, url: str, prompt: str, max_retries: int = 3) -> str:
    """Create task creation with exponential backoff for rate limiting."""
    for retry in range(max_retries):
        try:
            return self.create_job_search_task(url, prompt)
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait_time = 2 ** (2 ** retry  # Exponential backoff
                print(f"Rate limited, waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise
    
    raise Exception(f"Failed after {max_retries} retries due to rate limiting")
```

## Step 9: Step 9: Production Considerations

### 1. Store Credentials Securely

```python
import os
from dotenv import load_dotenv

load_dotenv()

class ProductionClient(JobMonitorClient):
    def __init__(self):
        base_url = os.getenv("API_BASE_URL", "http://localhost:8000")
        super().__init__(base_url)
        
        # Load credentials from environment
        self.username = os.getenv("API_USERNAME")
        self.password = os.getenv("API_PASSWORD")
    
    def authenticate(self):
        """Authenticate using environment credentials."""
        if not self.username,
        if not self.username or not self.password:
            raise ValueError("API_USERNAME and API_PASSWORD must be set in environment")
        
        self.login(self.username, self.password)
```

### 2. Implement Logging

```python
import logging

logging.basicConfig(
    level=logging.INFO)
logger = logging.getLogger(__name__)

class LoggingClient(JobMonitorClient):
    def create_job_search_task(self, url: str, prompt: str) -> str:
        """Create task with logging."""
        logger.info(f"Creating task for URL: {url}")
        logger.info(f"Prompt: {prompt[:50]}...")
        
        try:
            task_id = super().create_job_search_task(url, prompt)
            logger.info(f"Task created successfully: {task_id}")
            return task_id
        except Exception as e:
            logger.error(f"Failed to create task: {str(e)}")
            raise
```

### 3. Add Metrics and Monitoring

```python
import time
from dataclasses import dataclass
from typing import Optional

@dataclass
class TaskMetrics:
    task_id: str
    creation_time: float
    completion_time: Optional[
    completion_time: Optional[float] = None
    success: Optional[bool] = None
    
    @property
    def processing_time(self) -> Optional[float]:
        if self.completion_time:
            return self.completion_time - self.creation_time
        return None

class MetricsClient(JobMonitorClient):
    def __init__(self, base_url: str = "http://localhost:8000"):
        super().__init__(base_url)
        self.metrics: Dict[str, TaskMetrics] = {}
    
    def create_job_search_task(self, url: str, prompt: str) -> str:
        """Create task with metrics tracking."""
        start_time = time.time()
        task_id = super().create_job_search_task(url, prompt)
        
        self.metrics[task_id] = TaskMetrics(
            task_id=task_id,
            creation_time=start_time
        )
        
        )
        
        return task_id
    
    def get_task_results(self, task_id: str) -> Dict[str, Any]:
        """Get results and update metrics."""
        results = super().get_task_results(task_id)
        
        if task_id in self.metrics:
            self.metrics[task_id].completion_time = time.time()
            self.metrics[task_id].success = results.get("status") == "SUCCESS"
        
        return results
```

## Next Steps

1. **Test with different websites**: Try various job boards or news sites
2. **Experiment with prompts**: Refine your natural language prompts for different types of data
3. **Implement webhook notifications**: Instead of polling, set up notifications for task completion
4. **Build a dashboard**: Create a web interface to visualize extracted data
5. **Scale up**: Consider implementing batch processing for multiple URLs

## Troubleshooting Common Issues

### Issue: Task

### Common Issues

1. **Task stuck in PENDING state**:
   - Check Celery workers are running
   - Verify Redis connection
   - Check logs in `logs/celery.log`

2. **Authentication errors**:
   - Verify token hasn't expired (30 minutes default)
   - Check user is active in database
   - Ensure correct Authorization header format

3. **Rate limiting**:
   - Implement exponential backoff
   - Reduce request frequency
   - Contact support for higher limits if needed

4. **No data extracted**:
   - Try simpler prompts
   - Check website structure
   - Adjust prompt to be more specific
   - Check if website blocks scraping

## Support Resources

- **API Documentation**: `/docs` endpoint for interactive testing
- **Error Reference**: See Error Handling guide for detailed error codes
- **Community**: Join the project discussion forum (if available)
- **Contact**: Email dadada.marchan@gmail.com for direct support

---

## AUTHENTICATION_GUIDE.md

*(Modified: 2025-12-14 18:28:53)*

# Authentication Guide

## Overview

The Intelligent Web Data Aggregator API uses **JSON Web Tokens (JWT)** for stateless authentication. This guide provides comprehensive details on authentication mechanisms, security best practices, and troubleshooting.

## Table of Contents

- [Authentication Flow](#authentication-flow)
- [Registration](#registration)
- [Login and Token Generation](#login-and-token-generation)
- [Using Access Tokens](#using-access-tokens)
- [Token Management](#token-management)
- [Security Best Practices](#security-best-practices)
- [Password Requirements](#password-requirements)
- [Error Handling](#error-handling)
- [Advanced Topics](#advanced-topics)

## Authentication Flow

```
┌─────────────┐                                    ┌─────────────┐
│   Client    │                                    │   API       │
└──────┬──────┘                                    └──────┬──────┘
       │                                                  │
       │  1. POST /auth/register                         │
       │     (username, password, email)                 │
       ├─────────────────────────────────────────────────>│
       │                                                  │
       │  2. User Created (200 OK)                       │
       │<─────────────────────────────────────────────────┤
       │                                                  │
       │  3. POST /auth/token                            │
       │     (username, password)                        │
       ├─────────────────────────────────────────────────>│
       │                                                  │
       │  4. JWT Access Token (200 OK)                   │
       │<─────────────────────────────────────────────────┤
       │                                                  │
       │  5. API Request with Bearer Token               │
       │     Authorization: Bearer <token>               │
       ├─────────────────────────────────────────────────>│
       │                                                  │
       │  6. Protected Resource (200 OK)                 │
       │<─────────────────────────────────────────────────┤
       │                                                  │
```

## Registration

### Endpoint: `POST /auth/register`

Create a new user account with username, password, and optional email.

**Rate Limit**: 5 requests per minute per IP address

**Request**:
```http
POST /auth/register HTTP/1.1
Host: api.example.com
Content-Type: application/json

{
  "username": "john_doe",
  "password": "SecureP@ssw0rd!",
  "email": "john@example.com"
}
```

**Success Response** (200 OK):
```json
{
  "id": 42,
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true
}
```

**Error Responses**:

| Status | Error | Description |
|--------|-------|-------------|
| 400 | Username already registered | The username is already taken |
| 400 | Password too long | Password exceeds 72 bytes (bcrypt limit) |
| 422 | Validation Error | Invalid request format |
| 429 | Rate Limit Exceeded | Too many registration attempts |

**Example Error**:
```json
{
  "detail": "Username already registered"
}
```

### Registration Best Practices

1. **Unique Usernames**: Ensure usernames are unique across your application
2. **Strong Passwords**: Enforce password complexity requirements on the client side
3. **Email Verification**: Consider implementing email verification for production systems
4. **Rate Limiting**: The API automatically rate-limits registration to prevent abuse

## Login and Token Generation

### Endpoint: `POST /auth/token`

Authenticate with username and password to receive a JWT access token.

**Rate Limit**: 10 requests per minute per IP address

**Request**:
```http
POST /auth/token HTTP/1.1
Host: api.example.com
Content-Type: application/x-www-form-urlencoded

username=john_doe&password=SecureP@ssw0rd!
```

**cURL Example**:
```bash
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=john_doe&password=SecureP@ssw0rd!"
```

**Python Example**:
```python
import requests

response = requests.post(
    "http://localhost:8000/auth/token",
    data={
        "username": "john_doe",
        "password": "SecureP@ssw0rd!"
    }
)
token_data = response.json()
access_token = token_data["access_token"]
```

**Success Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huX2RvZSIsImV4cCI6MTY5MzQ4MjAwMH0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
  "token_type": "bearer"
}
```

**Error Responses**:

| Status | Error | Description |
|--------|-------|-------------|
| 401 | Incorrect username or password | Invalid credentials |
| 400 | Inactive user | User account is deactivated |
| 429 | Rate Limit Exceeded | Too many login attempts |

**Example Error**:
```json
{
  "detail": "Incorrect username or password"
}
```

### JWT Token Structure

The JWT token consists of three parts separated by dots:

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9    ← Header
.
eyJzdWIiOiJqb2huX2RvZSIsImV4cCI6MTY5M...  ← Payload
.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQ... ← Signature
```

**Header**:
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

**Payload**:
```json
{
  "sub": "john_doe",
  "exp": 1693482000
}
```

- `sub`: Subject (username)
- `exp`: Expiration time (Unix timestamp)

**Token Expiration**: Tokens expire after **30 minutes** by default.

## Using Access Tokens

### Authorization Header

Include the access token in the `Authorization` header for all protected endpoints:

```http
GET /api/v1/status/123e4567-e89b-12d3-a456-426614174000 HTTP/1.1
Host: api.example.com
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Header Format**:
```
Authorization: Bearer <access_token>
```

### Example Implementations

#### cURL
```bash
curl -X GET "http://localhost:8000/api/v1/process" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com", "prompt": "Extract headings"}'
```

#### Python (requests)
```python
import requests

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

response = requests.post(
    "http://localhost:8000/api/v1/process",
    headers=headers,
    json={
        "url": "https://example.com",
        "prompt": "Extract all headings"
    }
)
```

#### JavaScript (fetch)
```javascript
const response = await fetch('http://localhost:8000/api/v1/process', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    url: 'https://example.com',
    prompt: 'Extract all headings'
  })
});
```

#### Python (httpx - async)
```python
import httpx

async with httpx.AsyncClient() as client:
    response = await client.post(
        "http://localhost:8000/api/v1/process",
        headers={"Authorization": f"Bearer {access_token}"},
        json={"url": "https://example.com", "prompt": "Extract headings"}
    )
```

## Token Management

### Token Expiration

- **Default Expiration**: 30 minutes
- **Configuration**: Set via `ACCESS_TOKEN_EXPIRE_MINUTES` environment variable
- **Behavior**: Expired tokens return `401 Unauthorized`

### Token Refresh Strategy

Since tokens are stateless and expire after 30 minutes, implement one of these strategies:

#### 1. Proactive Refresh (Recommended)
```python
import time
from datetime import datetime, timedelta

class AuthClient:
    def __init__(self):
        self.access_token = None
        self.token_expires_at = None
    
    def login(self, username, password):
        response = requests.post(
            f"{self.base_url}/auth/token",
            data={"username": username, "password": password}
        )
        self.access_token = response.json()["access_token"]
        # Token expires in 30 minutes
        self.token_expires_at = datetime.now() + timedelta(minutes=30)
    
    def ensure_valid_token(self):
        """Refresh token if it expires in less than 5 minutes"""
        if not self.token_expires_at or \
           datetime.now() >= self.token_expires_at - timedelta(minutes=5):
            self.login(self.username, self.password)
    
    def make_request(self, method, endpoint, **kwargs):
        self.ensure_valid_token()
        headers = kwargs.get('headers', {})
        headers['Authorization'] = f"Bearer {self.access_token}"
        kwargs['headers'] = headers
        return requests.request(method, f"{self.base_url}{endpoint}", **kwargs)
```

#### 2. Reactive Refresh (Simple)
```python
def make_authenticated_request(url, method='GET', **kwargs):
    """Make request, re-authenticate on 401"""
    headers = kwargs.get('headers', {})
    headers['Authorization'] = f"Bearer {access_token}"
    kwargs['headers'] = headers
    
    response = requests.request(method, url, **kwargs)
    
    if response.status_code == 401:
        # Token expired, re-authenticate
        new_token = login(username, password)
        headers['Authorization'] = f"Bearer {new_token}"
        response = requests.request(method, url, **kwargs)
    
    return response
```

### Storing Tokens Securely

#### Web Browsers
**DO NOT** store tokens in:
- `localStorage` (vulnerable to XSS attacks)
- `sessionStorage` (same XSS vulnerability)

**RECOMMENDED** approach:
1. **httpOnly Cookies**: Store token in secure, httpOnly cookie
2. **Memory**: Store token in JavaScript memory (lost on refresh)
3. **Secure Storage API**: Use browser's credential management API

#### Mobile Applications
- **iOS**: Use Keychain
- **Android**: Use EncryptedSharedPreferences or KeyStore
- **React Native**: Use `react-native-keychain`

#### Server-to-Server
- **Environment Variables**: Store credentials in environment
- **Secret Management**: Use AWS Secrets Manager, HashiCorp Vault, etc.

**Example (Environment Variables)**:
```python
import os
from dotenv import load_dotenv

load_dotenv()

USERNAME = os.getenv("API_USERNAME")
PASSWORD = os.getenv("API_PASSWORD")
```

## Security Best Practices

### 1. Password Security

**Hashing Algorithm**: bcrypt with salt (work factor: 12)

**Password Requirements**:
- Minimum length: 8 characters (client-side validation recommended)
- Maximum length: 72 bytes (bcrypt limitation)
- Recommended: Mix of uppercase, lowercase, numbers, and symbols

**Password Validation Example**:
```python
import re

def validate_password(password: str) -> tuple[bool, str]:
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters"
    
    if len(password.encode('utf-8')) > 72:
        return False, "Password too long (max 72 bytes)"
    
    if not re.search(r"[a-z]", password):
        return False, "Password must contain lowercase letters"
    
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain uppercase letters"
    
    if not re.search(r"\d", password):
        return False, "Password must contain numbers"
    
    return True, "Password is valid"
```

### 2. HTTPS/TLS Enforcement

**ALWAYS** use HTTPS in production to prevent token interception:

```python
# Development
BASE_URL = "http://localhost:8000"

# Production
BASE_URL = "https://api.example.com"
```

### 3. Token Storage

**Never**:
- Log tokens in application logs
- Commit tokens to version control
- Share tokens between users
- Store tokens in URL parameters

**Always**:
- Use secure storage mechanisms
- Implement token rotation
- Clear tokens on logout
- Handle token expiration gracefully

### 4. Rate Limiting Compliance

Respect rate limits to avoid account suspension:

| Endpoint | Rate Limit |
|----------|------------|
| `/auth/register` | 5 requests/minute |
| `/auth/token` | 10 requests/minute |
| `/api/v1/process` | 10 requests/minute |

**Implement exponential backoff**:
```python
import time

def make_request_with_backoff(func, max_retries=3):
    """Retry with exponential backoff on rate limit"""
    for retry in range(max_retries):
        try:
            return func()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait_time = 2 ** retry
                print(f"Rate limited, waiting {wait_time} seconds...")
                time.sleep(wait_time)
            else:
                raise
    raise Exception("Max retries exceeded")
```

### 5. User Authorization

The API implements **user-scoped authorization**:
- Users can only access their own tasks
- Users can only manage their own scheduled jobs
- Attempting to access another user's resources returns `403 Forbidden`

## Password Requirements

### Technical Constraints

1. **Maximum Length**: 72 bytes (bcrypt limitation)
   - UTF-8 encoding means some characters consume multiple bytes
   - Example: "café" = 5 characters but 6 bytes

2. **Encoding**: UTF-8

### Recommended Client-Side Validation

```javascript
function validatePassword(password) {
  const errors = [];
  
  if (password.length < 8) {
    errors.push("Password must be at least 8 characters");
  }
  
  if (new Blob([password]).size > 72) {
    errors.push("Password too long (max 72 bytes)");
  }
  
  if (!/[a-z]/.test(password)) {
    errors.push("Must contain lowercase letters");
  }
  
  if (!/[A-Z]/.test(password)) {
    errors.push("Must contain uppercase letters");
  }
  
  if (!/\d/.test(password)) {
    errors.push("Must contain numbers");
  }
  
  if (!/[^a-zA-Z0-9]/.test(password)) {
    errors.push("Must contain special characters");
  }
  
  return {
    valid: errors.length === 0,
    errors: errors
  };
}
```

## Error Handling

### Common Authentication Errors

#### 401 Unauthorized

**Causes**:
- Token expired (>30 minutes old)
- Invalid token signature
- Token not provided
- User not found

**Response**:
```json
{
  "detail": "Could not validate credentials"
}
```

**Solution**: Re-authenticate with `/auth/token`

#### 403 Forbidden

**Cause**: User attempting to access another user's resources

**Response**:
```json
{
  "detail": "Not authorized to access this task"
}
```

**Solution**: Ensure you're accessing your own resources

#### 429 Rate Limit Exceeded

**Response**:
```json
{
  "error": "Too Many Requests"
}
```

**Solution**: Implement exponential backoff and respect rate limits

### Debugging Authentication Issues

#### 1. Verify Token Format
```python
import jwt

def decode_token(token):
    """Decode JWT without verification (for debugging only)"""
    try:
        header, payload, signature = token.split('.')
        decoded_payload = jwt.decode(
            token, 
            options={"verify_signature": False}
        )
        print(f"Username: {decoded_payload['sub']}")
        print(f"Expires: {decoded_payload['exp']}")
    except Exception as e:
        print(f"Invalid token: {e}")
```

#### 2. Check Token Expiration
```python
from datetime import datetime

def is_token_expired(token):
    """Check if token is expired"""
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        exp_timestamp = decoded['exp']
        return datetime.now().timestamp() > exp_timestamp
    except:
        return True
```

#### 3. Test Authentication Flow
```bash
# 1. Register
curl -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser","password":"Test123!@#"}'

# 2. Login
curl -X POST http://localhost:8000/auth/token \
  -d "username=testuser&password=Test123!@#"

# 3. Use token (replace YOUR_TOKEN)
curl -X GET http://localhost:8000/api/v1/health \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Advanced Topics

### Custom Token Expiration

While the API defaults to 30 minutes, administrators can configure token lifetime:

```bash
# .env file
ACCESS_TOKEN_EXPIRE_MINUTES=60  # 1 hour
```

### Multi-Device Authentication

The stateless JWT approach means:
- Users can be logged in on multiple devices simultaneously
- Each login creates an independent token
- Logging out on one device doesn't affect other devices
- Token revocation is not supported (by design)

### Security Considerations for Production

1. **Secret Key Rotation**: Periodically rotate `SECRET_KEY`
2. **HTTPS Only**: Enforce TLS 1.2+ in production
3. **IP Whitelisting**: Consider IP restrictions for sensitive operations
4. **Audit Logging**: Log all authentication attempts
5. **Account Lockout**: Implement temporary lockout after failed attempts
6. **Two-Factor Authentication**: Consider adding 2FA for enhanced security

### Future Authentication Features

Planned enhancements:
- Refresh tokens for extended sessions
- OAuth2 integration (Google, GitHub)
- API keys for server-to-server authentication
- Role-based access control (RBAC)
- Session management and revocation

## Support

For authentication-related issues:

1. **Check Logs**: Review API logs for detailed error messages
2. **Verify Configuration**: Ensure `SECRET_KEY` is set correctly
3. **Test Locally**: Use Swagger UI at `/docs` for interactive testing
4. **Contact Support**: Email dadada.marchan@gmail.com

## Related Documentation

- [API Reference](./API_REFERENCE.md) - Complete endpoint documentation
- [Error Handling](./ERROR_HANDLING.md) - Error codes and troubleshooting
- [Rate Limiting](./RATE_LIMITING.md) - Rate limit details and strategies
- [Security Best Practices](./BEST_PRACTICES.md) - Comprehensive security guide

---

## ERROR_HANDLING.md

*(Modified: 2025-12-14 18:28:53)*

# Error Handling Guide

## Overview

This guide provides comprehensive information about error handling in the Intelligent Web Data Aggregator API, including error codes, response formats, troubleshooting steps, and recovery strategies.

## Table of Contents

- [Error Response Format](#error-response-format)
- [HTTP Status Codes](#http-status-codes)
- [Error Taxonomy](#error-taxonomy)
- [Common Errors](#common-errors)
- [Validation Errors](#validation-errors)
- [Authentication Errors](#authentication-errors)
- [Rate Limiting Errors](#rate-limiting-errors)
- [Task Processing Errors](#task-processing-errors)
- [Error Recovery Strategies](#error-recovery-strategies)
- [Debugging Guide](#debugging-guide)
- [Best Practices](#best-practices)

## Error Response Format

### Standard Error Response

All API errors follow a consistent JSON format:

```json
{
  "error": "Error Type",
  "message": "Human-readable error description",
  "timestamp": "2025-08-08T12:00:00Z"
}
```

**Fields**:
- `error` (string): Error category or type
- `message` (string): Detailed error description
- `timestamp` (string): ISO 8601 timestamp when the error occurred

**Example**:
```json
{
  "error": "Not Found",
  "message": "Task not found",
  "timestamp": "2025-12-14T10:30:00Z"
}
```

### Validation Error Response

Pydantic validation errors have a different format:

```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "prompt"],
      "msg": "String should have at least 5 characters",
      "input": "hi",
      "ctx": {
        "min_length": 5
      }
    }
  ]
}
```

**Fields**:
- `detail` (array): List of validation errors
- `type` (string): Validation error type
- `loc` (array): Location of the error in the request
- `msg` (string): Human-readable message
- `input` (any): The input value that caused the error
- `ctx` (object): Additional context

## HTTP Status Codes

### Success Codes (2xx)

| Code | Status | Description | Usage |
|------|--------|-------------|-------|
| 200 | OK | Request succeeded | GET requests, successful operations |
| 202 | Accepted | Request accepted for processing | Async task creation |

### Client Error Codes (4xx)

| Code | Status | Description | Typical Causes |
|------|--------|-------------|----------------|
| 400 | Bad Request | Invalid request data | Malformed JSON, invalid parameters |
| 401 | Unauthorized | Authentication required or failed | Missing/invalid token |
| 403 | Forbidden | User lacks permission | Accessing another user's resources |
| 404 | Not Found | Resource doesn't exist | Invalid task ID, endpoint not found |
| 422 | Unprocessable Entity | Validation error | Invalid URL format, prompt too short |
| 429 | Too Many Requests | Rate limit exceeded | Too many requests in time window |

### Server Error Codes (5xx)

| Code | Status | Description | Typical Causes |
|------|--------|-------------|----------------|
| 500 | Internal Server Error | Unexpected server error | Database errors, unhandled exceptions |
| 502 | Bad Gateway | Upstream service unavailable | LLM service down, network issues |
| 503 | Service Unavailable | Service temporarily unavailable | Maintenance, overload |
| 504 | Gateway Timeout | Upstream service timeout | LLM processing timeout |

## Error Taxonomy

### 1. Authentication Errors (401, 403)

#### 401 Unauthorized

**Causes**:
- Missing Authorization header
- Invalid or expired JWT token
- Malformed token format
- Token signature verification failed

**Example Response**:
```json
{
  "detail": "Could not validate credentials"
}
```

**Recovery**:
1. Re-authenticate via `/auth/token`
2. Ensure correct Authorization header format: `Bearer <token>`
3. Check token hasn't expired (30 minutes default)

#### 403 Forbidden

**Causes**:
- User attempting to access another user's task
- User attempting to delete another user's scheduled job
- Inactive user account

**Example Response**:
```json
{
  "detail": "Not authorized to access this task"
}
```

**Recovery**:
1. Verify you're accessing your own resources
2. Check user account is active
3. Contact administrator if account is suspended

### 2. Validation Errors (400, 422)

#### 400 Bad Request

**Causes**:
- Prompt injection detected
- Invalid URL scheme
- Duplicate username during registration
- Password exceeds 72 bytes

**Examples**:

**Username Already Registered**:
```json
{
  "detail": "Username already registered"
}
```

**Prompt Injection Detected**:
```json
{
  "detail": "Invalid prompt: Potential injection detected"
}
```

**Password Too Long**:
```json
{
  "detail": "Password too long (max 72 bytes for bcrypt)"
}
```

#### 422 Unprocessable Entity

**Causes**:
- URL format validation failed
- Prompt too short (< 5 characters) or too long (> 1000 characters)
- Missing required fields
- Invalid data types

**Example**:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "prompt"],
      "msg": "String should have at least 5 characters",
      "input": "hi"
    },
    {
      "type": "url_parsing",
      "loc": ["body", "url"],
      "msg": "Input should be a valid URL, relative URL without a base",
      "input": "not-a-url"
    }
  ]
}
```

**Field Constraints**:

| Field | Constraint | Error Message |
|-------|-----------|---------------|
| `url` | Valid HTTP/HTTPS URL | "Input should be a valid URL" |
| `prompt` | 5-1000 characters | "String should have at least 5 characters" |
| `username` | Required | "Field required" |
| `password` | Required | "Field required" |

**Recovery**:
1. Validate input on client side before sending
2. Check field constraints
3. Ensure proper data types
4. Use valid URL format: `https://example.com`

### 3. Resource Not Found Errors (404)

**Causes**:
- Task ID doesn't exist
- Task belongs to another user
- Job ID doesn't exist
- Endpoint path is incorrect

**Examples**:

**Task Not Found**:
```json
{
  "error": "Not Found",
  "message": "Task not found",
  "timestamp": "2025-12-14T10:30:00Z"
}
```

**Job Not Found**:
```json
{
  "detail": "Job not found"
}
```

**Endpoint Not Found**:
```json
{
  "error": "Not Found",
  "message": "The requested resource was not found",
  "timestamp": "2025-12-14T10:30:00Z"
}
```

**Recovery**:
1. Verify task/job ID is correct
2. Check task/job belongs to authenticated user
3. Confirm endpoint path is correct
4. Task may have been deleted

### 4. Rate Limiting Errors (429)

**Response**:
```json
{
  "error": "Too Many Requests"
}
```

**Rate Limits**:

| Endpoint | Limit | Time Window |
|----------|-------|-------------|
| `/auth/register` | 5 requests | per minute |
| `/auth/token` | 10 requests | per minute |
| `/api/v1/process` | 10 requests | per minute |
| Global | 100 requests | per minute |

**Headers**:
```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1702550400
Retry-After: 60
```

**Recovery**:
1. Implement exponential backoff
2. Respect `Retry-After` header
3. Reduce request frequency
4. Cache responses where possible

**Exponential Backoff Example**:
```python
import time

def make_request_with_backoff(func, max_retries=5):
    for retry in range(max_retries):
        try:
            return func()
        except RateLimitError as e:
            if retry == max_retries - 1:
                raise
            wait_time = min(2 ** retry, 60)  # Cap at 60 seconds
            print(f"Rate limited. Waiting {wait_time}s...")
            time.sleep(wait_time)
```

### 5. Task Processing Errors

#### Task Failed (400)

When retrieving results for a failed task:

```json
{
  "detail": "Task failed: regex did not match"
}
```

**Common Failure Reasons**:

| Error Message | Cause | Solution |
|---------------|-------|----------|
| "regex did not match" | No content matched the generated regex | Try a more specific prompt |
| "Failed to fetch page" | Website unreachable or blocked scraping | Check URL is accessible |
| "Timeout during processing" | Task exceeded time limit | Simplify prompt or retry |
| "LLM service unavailable" | LLM provider is down | Retry later or contact support |
| "Invalid HTML structure" | Malformed HTML prevented parsing | Verify URL returns valid HTML |

**Example Response**:
```json
{
  "error": "Bad Request",
  "message": "Task failed: Failed to fetch page - Connection timeout",
  "timestamp": "2025-12-14T10:35:00Z"
}
```

**Recovery**:
1. Check task status via `/api/v1/status/{task_id}`
2. Review error message for specific failure reason
3. Adjust prompt to be more specific
4. Verify website is accessible
5. Retry with different parameters

#### Task Still Pending (202)

When requesting results for an incomplete task:

```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "IN_PROGRESS",
  "progress": 45,
  "message": null,
  "created_at": "2025-12-14T10:30:00Z",
  "updated_at": "2025-12-14T10:30:30Z"
}
```

**Status Values**:
- `PENDING`: Task created, not started
- `IN_PROGRESS`: Task being processed
- `SUCCESS`: Task completed successfully
- `FAILED`: Task failed (see error message)

**Recovery**:
1. Poll `/api/v1/status/{task_id}` periodically
2. Wait for status to become `SUCCESS` or `FAILED`
3. Implement polling with exponential backoff
4. Typical processing time: 5-30 seconds

### 6. Server Errors (500, 502, 503, 504)

#### 500 Internal Server Error

**Causes**:
- Database connection failure
- Unhandled exception
- Configuration error

**Example**:
```json
{
  "error": "Internal Server Error",
  "message": "An internal server error occurred",
  "timestamp": "2025-12-14T10:30:00Z"
}
```

**Recovery**:
1. Retry the request after a delay
2. Check system status page
3. Contact support if error persists
4. Include X-Correlation-Id in support request

#### 502 Bad Gateway

**Causes**:
- LLM service unavailable
- Celery worker not responding
- Network connectivity issues

**Recovery**:
1. Retry after 30-60 seconds
2. Check service status
3. Use exponential backoff
4. Switch to fallback endpoint if available

#### 503 Service Unavailable

**Causes**:
- System maintenance
- Temporary overload
- Service restart

**Recovery**:
1. Wait for service to recover
2. Check status page or announcements
3. Implement retry with backoff
4. Typical downtime: < 5 minutes

## Validation Errors

### URL Validation

**Valid Formats**:
```
https://example.com
http://example.com/path
https://subdomain.example.com:8080/path?query=value
```

**Invalid Formats**:
```
example.com              ← Missing scheme
ftp://example.com        ← Invalid scheme (only http/https)
//example.com            ← Relative URL
javascript:alert('xss')  ← Invalid scheme
```

**Error**:
```json
{
  "detail": [
    {
      "type": "url_scheme",
      "loc": ["body", "url"],
      "msg": "URL scheme should be 'http' or 'https'",
      "input": "ftp://example.com"
    }
  ]
}
```

### Prompt Validation

**Constraints**:
- Minimum: 5 characters
- Maximum: 1000 characters
- No prompt injection patterns

**Examples**:

**Too Short**:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "prompt"],
      "msg": "String should have at least 5 characters"
    }
  ]
}
```

**Too Long**:
```json
{
  "detail": [
    {
      "type": "string_too_long",
      "loc": ["body", "prompt"],
      "msg": "String should have at most 1000 characters"
    }
  ]
}
```

**Injection Detected**:
```json
{
  "detail": "Invalid prompt: Potential injection detected"
}
```

## Error Recovery Strategies

### 1. Retry with Exponential Backoff

```python
import time
import requests
from typing import Callable, Any

def retry_with_backoff(
    func: Callable,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    retry_statuses: set = {429, 500, 502, 503, 504}
) -> Any:
    """
    Retry function with exponential backoff.
    
    Args:
        func: Function to retry
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        backoff_factor: Multiplier for each retry
        max_delay: Maximum delay cap
        retry_statuses: HTTP status codes to retry on
    """
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            response = func()
            response.raise_for_status()
            return response
        except requests.exceptions.HTTPError as e:
            if e.response.status_code not in retry_statuses or attempt == max_retries:
                raise
            
            # Use Retry-After header if available
            retry_after = e.response.headers.get('Retry-After')
            if retry_after:
                wait_time = float(retry_after)
            else:
                wait_time = min(delay, max_delay)
                delay *= backoff_factor
            
            print(f"Attempt {attempt + 1} failed. Retrying in {wait_time}s...")
            time.sleep(wait_time)
```

### 2. Circuit Breaker Pattern

```python
import time
from enum import Enum

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, failure_threshold: int = 5, timeout: float = 60.0):
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    def call(self, func: Callable) -> Any:
        if self.state == CircuitState.OPEN:
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = func()
            self.on_success()
            return result
        except Exception as e:
            self.on_failure()
            raise
    
    def on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def on_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN

# Usage
breaker = CircuitBreaker(failure_threshold=5, timeout=60)

try:
    result = breaker.call(lambda: make_api_request())
except Exception as e:
    print(f"Request failed: {e}")
```

### 3. Graceful Degradation

```python
class APIClient:
    def __init__(self, primary_url: str, fallback_url: str = None):
        self.primary_url = primary_url
        self.fallback_url = fallback_url
    
    def make_request(self, endpoint: str, **kwargs):
        """Try primary, fall back to secondary on failure"""
        try:
            response = requests.get(f"{self.primary_url}{endpoint}", **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if self.fallback_url:
                print(f"Primary failed: {e}. Trying fallback...")
                response = requests.get(f"{self.fallback_url}{endpoint}", **kwargs)
                response.raise_for_status()
                return response.json()
            else:
                raise
```

### 4. Request Idempotency

```python
import uuid

def make_idempotent_request(client, endpoint: str, **kwargs):
    """
    Make request with idempotency key to safely retry.
    
    The API doesn't currently support idempotency keys,
    but this pattern is recommended for future implementation.
    """
    idempotency_key = str(uuid.uuid4())
    headers = kwargs.get('headers', {})
    headers['Idempotency-Key'] = idempotency_key
    kwargs['headers'] = headers
    
    return client.post(endpoint, **kwargs)
```

## Debugging Guide

### 1. Enable Verbose Logging

```python
import logging
import requests

# Enable detailed HTTP logging
logging.basicConfig(level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.DEBUG)
logging.getLogger("urllib3").setLevel(logging.DEBUG)

response = requests.post("http://localhost:8000/api/v1/process", ...)
```

### 2. Use Correlation IDs

Every API response includes an `X-Correlation-Id` header for request tracing:

```python
response = requests.post(
    "http://localhost:8000/api/v1/process",
    headers={"X-Correlation-Id": "my-custom-id-12345"},
    json={"url": "https://example.com", "prompt": "Extract data"}
)

correlation_id = response.headers.get("X-Correlation-Id")
print(f"Track this request: {correlation_id}")
```

**Include correlation ID when contacting support**.

### 3. Test in Swagger UI

Use the interactive documentation at `/docs`:

1. Navigate to http://localhost:8000/docs
2. Click "Authorize" and enter your token
3. Try endpoints interactively
4. View request/response details

### 4. Check API Health

```bash
# Basic health check
curl http://localhost:8000/health

# Detailed health check with database status
curl http://localhost:8000/api/v1/health
```

### 5. Inspect Error Details

```python
import requests

try:
    response = requests.post(
        "http://localhost:8000/api/v1/process",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": "invalid-url", "prompt": "test"}
    )
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    print(f"Status Code: {e.response.status_code}")
    print(f"Response Body: {e.response.text}")
    print(f"Headers: {dict(e.response.headers)}")
```

## Best Practices

### 1. Always Handle Errors Gracefully

```python
import requests
from typing import Optional, Dict, Any

def safe_api_call(
    url: str,
    method: str = "GET",
    **kwargs
) -> Optional[Dict[str, Any]]:
    """Make API call with comprehensive error handling"""
    try:
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        
        if status_code == 401:
            print("Authentication failed. Please login again.")
        elif status_code == 403:
            print("Access denied. Check permissions.")
        elif status_code == 404:
            print("Resource not found.")
        elif status_code == 429:
            retry_after = e.response.headers.get('Retry-After', 60)
            print(f"Rate limited. Retry after {retry_after} seconds.")
        elif 500 <= status_code < 600:
            print("Server error. Please try again later.")
        else:
            print(f"Request failed: {e.response.text}")
        
        return None
    
    except requests.exceptions.ConnectionError:
        print("Connection failed. Check network connectivity.")
        return None
    
    except requests.exceptions.Timeout:
        print("Request timed out.")
        return None
    
    except requests.exceptions.RequestException as e:
        print(f"Request error: {e}")
        return None
```

### 2. Validate Input Client-Side

```python
from pydantic import BaseModel, HttpUrl, Field, validator

class ScrapeRequestValidator(BaseModel):
    url: HttpUrl
    prompt: str = Field(min_length=5, max_length=1000)
    
    @validator('prompt')
    def validate_prompt(cls, v):
        # Additional custom validation
        prohibited_patterns = ['<script>', 'javascript:', 'eval(']
        if any(pattern in v.lower() for pattern in prohibited_patterns):
            raise ValueError("Prompt contains prohibited patterns")
        return v

# Usage
try:
    request_data = ScrapeRequestValidator(
        url="https://example.com",
        prompt="Extract all headings"
    )
    # Make API call
except ValidationError as e:
    print(f"Validation failed: {e}")
```

### 3. Monitor Error Rates

```python
from collections import defaultdict
import time

class ErrorTracker:
    def __init__(self):
        self.error_counts = defaultdict(int)
        self.start_time = time.time()
    
    def record_error(self, status_code: int):
        self.error_counts[status_code] += 1
    
    def get_error_rate(self) -> Dict[int, float]:
        elapsed = time.time() - self.start_time
        return {
            code: count / elapsed * 60  # Errors per minute
            for code, count in self.error_counts.items()
        }
    
    def alert_if_high_error_rate(self, threshold: float = 10.0):
        rates = self.get_error_rate()
        for code, rate in rates.items():
            if rate > threshold:
                print(f"ALERT: High error rate for {code}: {rate:.2f}/min")

tracker = ErrorTracker()
```

### 4. Log Errors for Analysis

```python
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)

def log_api_error(
    endpoint: str,
    method: str,
    status_code: int,
    response_body: str,
    correlation_id: str = None
):
    """Structured error logging"""
    error_data = {
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "method": method,
        "status_code": status_code,
        "response": response_body,
        "correlation_id": correlation_id
    }
    logger.error(f"API Error: {json.dumps(error_data)}")
```

### 5. Provide User-Friendly Messages

```python
ERROR_MESSAGES = {
    400: "The request was invalid. Please check your input.",
    401: "Please login to continue.",
    403: "You don't have permission to access this resource.",
    404: "The requested resource was not found.",
    422: "Please check that all required fields are filled correctly.",
    429: "Too many requests. Please wait a moment and try again.",
    500: "Something went wrong on our end. Please try again later.",
    502: "Service temporarily unavailable. Please try again.",
    503: "The service is currently under maintenance.",
}

def get_user_friendly_message(status_code: int) -> str:
    return ERROR_MESSAGES.get(
        status_code,
        "An unexpected error occurred. Please contact support."
    )
```

## Support and Resources

### Getting Help

1. **Check this guide**: Review error descriptions and recovery strategies
2. **Search logs**: Include X-Correlation-Id for tracking
3. **Test in Swagger**: Use `/docs` for interactive debugging
4. **Contact support**: Email dadada.marchan@gmail.com with:
   - Error message
   - Correlation ID
   - Steps to reproduce
   - Expected vs. actual behavior

### Related Documentation

- [API Reference](./API_REFERENCE.md) - Complete endpoint documentation
- [Authentication Guide](./AUTHENTICATION_GUIDE.md) - Auth error details
- [Rate Limiting](./RATE_LIMITING.md) - Rate limit specifics
- [Best Practices](./BEST_PRACTICES.md) - Error handling patterns
- [Integration Tutorial](./INTEGRATION_TUTORIAL.md) - Working examples

### Monitoring and Alerts

For production deployments, monitor:
- Error rates by status code
- P95/P99 latency
- Authentication failure rate
- Rate limiting events
- Task failure rate

Set up alerts for:
- Error rate > 5% of total requests
- Any 500 errors
- Authentication failure rate > 10%
- Task failure rate > 20%

---

## RATE_LIMITING.md

*(Modified: 2025-12-14 18:28:53)*

# Rate Limiting Guide

## Overview

The Intelligent Web Data Aggregator API implements rate limiting to ensure fair resource allocation, prevent abuse, and maintain service quality for all users. This guide explains rate limit policies, how to handle rate limits, and strategies for optimization.

## Table of Contents

- [Rate Limit Policies](#rate-limit-policies)
- [Rate Limit Headers](#rate-limit-headers)
- [Handling Rate Limits](#handling-rate-limits)
- [Best Practices](#best-practices)
- [Optimization Strategies](#optimization-strategies)
- [Monitoring and Debugging](#monitoring-and-debugging)
- [Enterprise Rate Limits](#enterprise-rate-limits)

## Rate Limit Policies

### Default Rate Limits

The API applies different rate limits based on endpoint sensitivity and resource intensity:

| Endpoint | Rate Limit | Time Window | Scope |
|----------|------------|-------------|-------|
| `/auth/register` | 5 requests | per minute | Per IP address |
| `/auth/token` | 10 requests | per minute | Per IP address |
| `/api/v1/process` | 10 requests | per minute | Per IP address |
| Global default | 100 requests | per minute | Per IP address |
| All other endpoints | 100 requests | per minute | Per IP address |

### Rate Limit Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Client Request                          │
└──────────────────────────────┬──────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                  Rate Limiter (SlowAPI)                     │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Redis Storage (Production)                           │  │
│  │  - Distributed rate limiting                          │  │
│  │  - Shared across API instances                        │  │
│  │                                                        │  │
│  │  In-Memory Storage (Development/Fallback)             │  │
│  │  - Per-instance rate limiting                         │  │
│  │  - Used when Redis unavailable                        │  │
│  └───────────────────────────────────────────────────────┘  │
└──────────────────────────────┬──────────────────────────────┘
                               │
                    Rate Limit Exceeded?
                    ┌──────────┴──────────┐
                   NO                    YES
                    │                      │
                    ▼                      ▼
         ┌──────────────────┐   ┌──────────────────┐
         │  Process Request │   │  429 Too Many    │
         │                  │   │  Requests        │
         └──────────────────┘   └──────────────────┘
```

### Rate Limit Identification

Rate limits are applied based on:

1. **IP Address** (primary): Client's source IP address
2. **Endpoint**: Specific endpoint being accessed
3. **Method**: HTTP method (GET, POST, etc.)

**Note**: Currently, rate limits are per-IP, not per-user. This means:
- Multiple users from the same IP share the same limit
- One user can make requests from multiple IPs (separate limits)
- Consider this for shared networks (offices, schools, etc.)

## Rate Limit Headers

### Response Headers

Every API response includes rate limit information in headers:

```http
HTTP/1.1 200 OK
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 7
X-RateLimit-Reset: 1702556400
```

**Header Descriptions**:

| Header | Type | Description | Example |
|--------|------|-------------|---------|
| `X-RateLimit-Limit` | Integer | Maximum requests allowed in window | `10` |
| `X-RateLimit-Remaining` | Integer | Requests remaining in current window | `7` |
| `X-RateLimit-Reset` | Unix timestamp | When the rate limit window resets | `1702556400` |

### Rate Limit Exceeded Response

When you exceed the rate limit, you'll receive a `429 Too Many Requests` response:

```http
HTTP/1.1 429 Too Many Requests
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1702556460
Retry-After: 60
Content-Type: application/json

{
  "error": "Too Many Requests"
}
```

**Additional Header**:
- `Retry-After`: Seconds until you can retry (integer)

### Parsing Headers Example

```python
import time
from datetime import datetime

def check_rate_limit(response):
    """Extract and display rate limit information"""
    limit = response.headers.get('X-RateLimit-Limit')
    remaining = response.headers.get('X-RateLimit-Remaining')
    reset_timestamp = response.headers.get('X-RateLimit-Reset')
    
    if reset_timestamp:
        reset_time = datetime.fromtimestamp(int(reset_timestamp))
        print(f"Rate Limit: {remaining}/{limit}")
        print(f"Resets at: {reset_time}")
        
        if int(remaining) < 2:
            print("WARNING: Approaching rate limit!")
    
    return int(remaining) if remaining else None

# Usage
response = requests.post("http://localhost:8000/api/v1/process", ...)
remaining = check_rate_limit(response)
```

## Handling Rate Limits

### 1. Exponential Backoff (Recommended)

Retry with exponentially increasing delays:

```python
import time
import requests
from typing import Callable, Any

def exponential_backoff_retry(
    func: Callable,
    max_retries: int = 5,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    backoff_factor: float = 2.0
) -> Any:
    """
    Retry function with exponential backoff on rate limit.
    
    Args:
        func: Function to execute
        max_retries: Maximum number of retries
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay cap
        backoff_factor: Multiplier for each retry
    
    Returns:
        Function result
    
    Raises:
        Exception: If max retries exceeded
    """
    delay = initial_delay
    
    for attempt in range(max_retries + 1):
        try:
            response = func()
            
            if response.status_code == 429:
                if attempt == max_retries:
                    raise Exception("Max retries exceeded due to rate limiting")
                
                # Use Retry-After header if available
                retry_after = response.headers.get('Retry-After')
                wait_time = int(retry_after) if retry_after else min(delay, max_delay)
                
                print(f"Rate limited. Retrying in {wait_time}s... (attempt {attempt + 1}/{max_retries})")
                time.sleep(wait_time)
                
                delay *= backoff_factor
                continue
            
            response.raise_for_status()
            return response
        
        except requests.exceptions.HTTPError as e:
            if e.response.status_code != 429:
                raise
    
    raise Exception("Unexpected exit from retry loop")

# Usage
def make_request():
    return requests.post(
        "http://localhost:8000/api/v1/process",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": "https://example.com", "prompt": "Extract data"}
    )

response = exponential_backoff_retry(make_request)
```

### 2. Adaptive Rate Limiting

Adjust request rate based on remaining quota:

```python
import time
from dataclasses import dataclass
from datetime import datetime

@dataclass
class RateLimitInfo:
    limit: int
    remaining: int
    reset_at: datetime

class AdaptiveRateLimiter:
    def __init__(self):
        self.rate_limit_info: RateLimitInfo = None
    
    def update_from_response(self, response):
        """Update rate limit info from response headers"""
        limit = response.headers.get('X-RateLimit-Limit')
        remaining = response.headers.get('X-RateLimit-Remaining')
        reset = response.headers.get('X-RateLimit-Reset')
        
        if limit and remaining and reset:
            self.rate_limit_info = RateLimitInfo(
                limit=int(limit),
                remaining=int(remaining),
                reset_at=datetime.fromtimestamp(int(reset))
            )
    
    def calculate_delay(self) -> float:
        """Calculate optimal delay before next request"""
        if not self.rate_limit_info:
            return 0.0
        
        now = datetime.now()
        if now >= self.rate_limit_info.reset_at:
            return 0.0
        
        remaining_seconds = (self.rate_limit_info.reset_at - now).total_seconds()
        
        # If close to limit, increase delay
        if self.rate_limit_info.remaining < 2:
            return remaining_seconds
        
        # Distribute remaining requests evenly
        if self.rate_limit_info.remaining > 0:
            return remaining_seconds / self.rate_limit_info.remaining
        
        return remaining_seconds
    
    def wait_if_needed(self):
        """Wait if approaching rate limit"""
        delay = self.calculate_delay()
        if delay > 0:
            print(f"Rate limit approaching. Waiting {delay:.2f}s...")
            time.sleep(delay)

# Usage
limiter = AdaptiveRateLimiter()

for task in tasks:
    limiter.wait_if_needed()
    
    response = requests.post(
        "http://localhost:8000/api/v1/process",
        headers={"Authorization": f"Bearer {token}"},
        json=task
    )
    
    limiter.update_from_response(response)
```

### 3. Request Queuing

Queue requests and process them respecting rate limits:

```python
import time
import queue
import threading
from datetime import datetime, timedelta

class RateLimitedQueue:
    def __init__(self, rate_limit: int, time_window: float = 60.0):
        """
        Args:
            rate_limit: Maximum requests per time window
            time_window: Time window in seconds
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.queue = queue.Queue()
        self.request_times = []
        self.lock = threading.Lock()
    
    def add_request(self, func, *args, **kwargs):
        """Add request to queue"""
        self.queue.put((func, args, kwargs))
    
    def process_queue(self):
        """Process queued requests respecting rate limits"""
        while not self.queue.empty():
            with self.lock:
                # Remove expired timestamps
                now = time.time()
                self.request_times = [
                    t for t in self.request_times
                    if now - t < self.time_window
                ]
                
                # Check if we can make a request
                if len(self.request_times) >= self.rate_limit:
                    # Calculate wait time
                    oldest_request = min(self.request_times)
                    wait_time = self.time_window - (now - oldest_request)
                    print(f"Rate limit reached. Waiting {wait_time:.1f}s...")
                    time.sleep(wait_time)
                    continue
                
                # Get next request
                func, args, kwargs = self.queue.get()
                
                # Execute request
                try:
                    result = func(*args, **kwargs)
                    self.request_times.append(time.time())
                    print(f"Request completed. {self.rate_limit - len(self.request_times)} remaining in window.")
                except Exception as e:
                    print(f"Request failed: {e}")

# Usage
rate_limiter = RateLimitedQueue(rate_limit=10, time_window=60.0)

# Add multiple requests
for i in range(20):
    rate_limiter.add_request(
        lambda i=i: requests.post(
            "http://localhost:8000/api/v1/process",
            headers={"Authorization": f"Bearer {token}"},
            json={"url": f"https://example{i}.com", "prompt": "Extract data"}
        )
    )

# Process queue
rate_limiter.process_queue()
```

### 4. Token Bucket Algorithm

Implement client-side rate limiting:

```python
import time
from threading import Lock

class TokenBucket:
    def __init__(self, capacity: int, refill_rate: float):
        """
        Token bucket rate limiter.
        
        Args:
            capacity: Maximum tokens (requests)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.tokens = capacity
        self.refill_rate = refill_rate
        self.last_refill = time.time()
        self.lock = Lock()
    
    def _refill(self):
        """Refill tokens based on elapsed time"""
        now = time.time()
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate
        self.tokens = min(self.capacity, self.tokens + tokens_to_add)
        self.last_refill = now
    
    def consume(self, tokens: int = 1) -> bool:
        """
        Attempt to consume tokens.
        
        Returns:
            True if tokens consumed, False if insufficient tokens
        """
        with self.lock:
            self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False
    
    def wait_for_token(self, tokens: int = 1):
        """Wait until enough tokens are available"""
        while not self.consume(tokens):
            time.sleep(0.1)

# Usage: 10 requests per minute = 10/60 = 0.167 tokens/second
bucket = TokenBucket(capacity=10, refill_rate=10/60)

for i in range(20):
    bucket.wait_for_token()
    response = requests.post(
        "http://localhost:8000/api/v1/process",
        headers={"Authorization": f"Bearer {token}"},
        json={"url": f"https://example{i}.com", "prompt": "Extract data"}
    )
    print(f"Request {i+1} completed")
```

## Best Practices

### 1. Always Check Headers

```python
def make_safe_request(url, **kwargs):
    """Make request with rate limit awareness"""
    response = requests.request(**kwargs)
    
    # Check rate limit
    remaining = response.headers.get('X-RateLimit-Remaining')
    if remaining and int(remaining) < 2:
        print("WARNING: Approaching rate limit!")
        # Consider adding delay before next request
        time.sleep(6)  # Wait 6 seconds
    
    return response
```

### 2. Implement Client-Side Rate Limiting

Don't rely solely on server rate limits:

```python
from datetime import datetime, timedelta

class ClientRateLimiter:
    def __init__(self, requests_per_minute: int):
        self.limit = requests_per_minute
        self.requests = []
    
    def wait_if_needed(self):
        """Wait if approaching rate limit"""
        now = datetime.now()
        
        # Remove requests older than 1 minute
        self.requests = [
            req_time for req_time in self.requests
            if now - req_time < timedelta(minutes=1)
        ]
        
        # If at limit, wait
        if len(self.requests) >= self.limit:
            oldest = min(self.requests)
            wait_until = oldest + timedelta(minutes=1)
            wait_seconds = (wait_until - now).total_seconds()
            
            if wait_seconds > 0:
                print(f"Client-side rate limit: waiting {wait_seconds:.1f}s")
                time.sleep(wait_seconds)
                self.requests = []
        
        # Record this request
        self.requests.append(now)

# Usage
limiter = ClientRateLimiter(requests_per_minute=10)

for task in tasks:
    limiter.wait_if_needed()
    response = make_request(task)
```

### 3. Batch Operations

Minimize API calls by batching when possible:

```python
# Instead of multiple individual requests
for url in urls:
    response = requests.post("/api/v1/process", json={
        "url": url,
        "prompt": "Extract data"
    })

# Consider scheduling multiple URLs as jobs
jobs = []
for url in urls:
    job = requests.post("/api/v1/jobs", json={
        "url": url,
        "prompt": "Extract data",
        "schedule_cron": "*/5 * * * *"  # Every 5 minutes
    })
    jobs.append(job.json())
```

### 4. Cache Responses

Cache results to reduce API calls:

```python
import hashlib
import json
from functools import lru_cache

class CachedAPIClient:
    def __init__(self):
        self.cache = {}
    
    def _cache_key(self, url: str, prompt: str) -> str:
        """Generate cache key from request parameters"""
        content = f"{url}:{prompt}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def create_task(self, url: str, prompt: str):
        """Create task with caching"""
        cache_key = self._cache_key(url, prompt)
        
        # Check cache
        if cache_key in self.cache:
            print("Returning cached result")
            return self.cache[cache_key]
        
        # Make API call
        response = requests.post(
            "http://localhost:8000/api/v1/process",
            headers={"Authorization": f"Bearer {token}"},
            json={"url": url, "prompt": prompt}
        )
        
        # Cache result
        result = response.json()
        self.cache[cache_key] = result
        
        return result
```

### 5. Graceful Degradation

Handle rate limits gracefully in user-facing applications:

```python
class APIClientWithFallback:
    def create_task(self, url: str, prompt: str, max_retries: int = 3):
        """Create task with user-friendly error handling"""
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    "http://localhost:8000/api/v1/process",
                    headers={"Authorization": f"Bearer {self.token}"},
                    json={"url": url, "prompt": prompt}
                )
                
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    
                    if attempt < max_retries - 1:
                        print(f"Rate limited. Retrying in {retry_after}s...")
                        time.sleep(retry_after)
                        continue
                    else:
                        return {
                            "success": False,
                            "message": "Service is busy. Please try again later."
                        }
                
                response.raise_for_status()
                return {
                    "success": True,
                    "data": response.json()
                }
            
            except Exception as e:
                if attempt == max_retries - 1:
                    return {
                        "success": False,
                        "message": f"Failed to create task: {str(e)}"
                    }
```

## Optimization Strategies

### 1. Parallel Requests with Rate Limiting

```python
import concurrent.futures
import time

class RateLimitedExecutor:
    def __init__(self, max_workers: int, requests_per_minute: int):
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.requests_per_minute = requests_per_minute
        self.request_times = []
    
    def submit(self, func, *args, **kwargs):
        """Submit task respecting rate limits"""
        # Enforce rate limit
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= self.requests_per_minute:
            wait_time = 60 - (now - min(self.request_times))
            time.sleep(wait_time)
        
        self.request_times.append(time.time())
        return self.executor.submit(func, *args, **kwargs)

# Usage
executor = RateLimitedExecutor(max_workers=3, requests_per_minute=10)

futures = []
for i in range(20):
    future = executor.submit(
        make_api_request,
        url=f"https://example{i}.com",
        prompt="Extract data"
    )
    futures.append(future)

# Wait for all requests
for future in concurrent.futures.as_completed(futures):
    try:
        result = future.result()
        print(f"Task completed: {result}")
    except Exception as e:
        print(f"Task failed: {e}")
```

### 2. Request Prioritization

Prioritize important requests:

```python
import heapq
from dataclasses import dataclass, field
from typing import Any

@dataclass(order=True)
class PrioritizedRequest:
    priority: int
    request_data: Any = field(compare=False)

class PriorityRateLimiter:
    def __init__(self, rate_limit: int):
        self.rate_limit = rate_limit
        self.heap = []
        self.request_times = []
    
    def add_request(self, priority: int, func, *args, **kwargs):
        """Add request with priority (lower = higher priority)"""
        request = PrioritizedRequest(
            priority=priority,
            request_data=(func, args, kwargs)
        )
        heapq.heappush(self.heap, request)
    
    def process_next(self):
        """Process highest priority request"""
        if not self.heap:
            return None
        
        # Check rate limit
        now = time.time()
        self.request_times = [t for t in self.request_times if now - t < 60]
        
        if len(self.request_times) >= self.rate_limit:
            oldest = min(self.request_times)
            wait_time = 60 - (now - oldest)
            time.sleep(wait_time)
        
        # Execute request
        request = heapq.heappop(self.heap)
        func, args, kwargs = request.request_data
        result = func(*args, **kwargs)
        self.request_times.append(time.time())
        
        return result

# Usage
limiter = PriorityRateLimiter(rate_limit=10)

# Add urgent requests with high priority (low number)
limiter.add_request(
    priority=1,
    func=make_request,
    url="https://urgent.com",
    prompt="Critical data"
)

# Add normal requests
limiter.add_request(
    priority=5,
    func=make_request,
    url="https://normal.com",
    prompt="Regular data"
)

# Process requests (urgent first)
while limiter.heap:
    result = limiter.process_next()
```

### 3. Smart Scheduling

Distribute requests over time:

```python
from datetime import datetime, timedelta

class SmartScheduler:
    def __init__(self, tasks: list, rate_limit: int, time_window: int = 60):
        """
        Schedule tasks to respect rate limits.
        
        Args:
            tasks: List of tasks to schedule
            rate_limit: Maximum requests per time_window
            time_window: Time window in seconds
        """
        self.tasks = tasks
        self.rate_limit = rate_limit
        self.time_window = time_window
    
    def calculate_schedule(self):
        """Calculate optimal execution times"""
        interval = self.time_window / self.rate_limit
        schedule = []
        
        start_time = datetime.now()
        for i, task in enumerate(self.tasks):
            execution_time = start_time + timedelta(seconds=i * interval)
            schedule.append((execution_time, task))
        
        return schedule
    
    def execute_schedule(self, schedule):
        """Execute tasks according to schedule"""
        for execution_time, task in schedule:
            now = datetime.now()
            if now < execution_time:
                wait_seconds = (execution_time - now).total_seconds()
                print(f"Waiting {wait_seconds:.1f}s for next task...")
                time.sleep(wait_seconds)
            
            try:
                result = self.execute_task(task)
                print(f"Task completed at {datetime.now()}")
            except Exception as e:
                print(f"Task failed: {e}")
    
    def execute_task(self, task):
        """Execute individual task"""
        return requests.post(
            "http://localhost:8000/api/v1/process",
            headers={"Authorization": f"Bearer {token}"},
            json=task
        )

# Usage
tasks = [
    {"url": f"https://example{i}.com", "prompt": "Extract data"}
    for i in range(20)
]

scheduler = SmartScheduler(tasks, rate_limit=10, time_window=60)
schedule = scheduler.calculate_schedule()
scheduler.execute_schedule(schedule)
```

## Monitoring and Debugging

### 1. Rate Limit Metrics

Track rate limit metrics:

```python
from collections import defaultdict
from datetime import datetime

class RateLimitMonitor:
    def __init__(self):
        self.rate_limit_hits = 0
        self.total_requests = 0
        self.rate_limit_by_endpoint = defaultdict(int)
        self.start_time = datetime.now()
    
    def record_request(self, endpoint: str, status_code: int):
        """Record request and check for rate limiting"""
        self.total_requests += 1
        
        if status_code == 429:
            self.rate_limit_hits += 1
            self.rate_limit_by_endpoint[endpoint] += 1
    
    def get_statistics(self):
        """Get rate limiting statistics"""
        elapsed = (datetime.now() - self.start_time).total_seconds()
        
        return {
            "total_requests": self.total_requests,
            "rate_limit_hits": self.rate_limit_hits,
            "rate_limit_percentage": (
                self.rate_limit_hits / self.total_requests * 100
                if self.total_requests > 0 else 0
            ),
            "requests_per_minute": self.total_requests / (elapsed / 60),
            "endpoints_with_limits": dict(self.rate_limit_by_endpoint)
        }
    
    def print_report(self):
        """Print monitoring report"""
        stats = self.get_statistics()
        print("\n=== Rate Limit Report ===")
        print(f"Total Requests: {stats['total_requests']}")
        print(f"Rate Limit Hits: {stats['rate_limit_hits']}")
        print(f"Rate Limit %: {stats['rate_limit_percentage']:.2f}%")
        print(f"Requests/min: {stats['requests_per_minute']:.2f}")
        
        if stats['endpoints_with_limits']:
            print("\nEndpoints with Rate Limits:")
            for endpoint, count in stats['endpoints_with_limits'].items():
                print(f"  {endpoint}: {count} hits")

# Usage
monitor = RateLimitMonitor()

for i in range(100):
    response = make_api_request()
    monitor.record_request("/api/v1/process", response.status_code)

monitor.print_report()
```

### 2. Debug Rate Limiting Issues

```python
import logging

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def debug_rate_limit(response):
    """Debug rate limit information"""
    logger.debug("=== Rate Limit Debug ===")
    logger.debug(f"Status: {response.status_code}")
    logger.debug(f"Limit: {response.headers.get('X-RateLimit-Limit')}")
    logger.debug(f"Remaining: {response.headers.get('X-RateLimit-Remaining')}")
    logger.debug(f"Reset: {response.headers.get('X-RateLimit-Reset')}")
    logger.debug(f"Retry-After: {response.headers.get('Retry-After')}")
    
    if response.status_code == 429:
        logger.warning("RATE LIMITED!")
        reset_time = response.headers.get('X-RateLimit-Reset')
        if reset_time:
            reset_dt = datetime.fromtimestamp(int(reset_time))
            logger.warning(f"Rate limit resets at: {reset_dt}")
```

## Enterprise Rate Limits

### Current Limitations

- All users share the same rate limits
- Limits are per-IP, not per-user
- No ability to purchase higher limits

### Future Enhancements

Planned features for enterprise users:

1. **User-based Rate Limiting**
   - Per-user instead of per-IP
   - Custom limits per user

2. **Rate Limit Tiers**
   - Free tier: 10 req/min
   - Basic tier: 60 req/min
   - Pro tier: 300 req/min
   - Enterprise: Custom limits

3. **Burst Allowance**
   - Allow short bursts above limit
   - Averaged over longer time period

4. **Dedicated Instances**
   - Isolated rate limits
   - Guaranteed capacity

### Requesting Higher Limits

To request higher rate limits:

1. Email: dadada.marchan@gmail.com
2. Include:
   - Use case description
   - Expected request volume
   - Business justification
3. Wait for approval and configuration

## Related Documentation

- [API Reference](./API_REFERENCE.md) - Endpoint documentation
- [Error Handling](./ERROR_HANDLING.md) - Error responses
- [Authentication Guide](./AUTHENTICATION_GUIDE.md) - Auth requirements
- [Best Practices](./BEST_PRACTICES.md) - Usage patterns
- [Integration Tutorial](./INTEGRATION_TUTORIAL.md) - Working examples

## Support

For rate limiting issues:

1. **Monitor Headers**: Track X-RateLimit-* headers
2. **Implement Backoff**: Use exponential backoff
3. **Client-Side Limiting**: Don't rely solely on server
4. **Contact Support**: Email dadada.marchan@gmail.com for limit increases

---

## BEST_PRACTICES.md

*(Modified: 2025-12-14 18:28:53)*

# API Best Practices

## Overview

This guide provides best practices, design patterns, and recommendations for using the Intelligent Web Data Aggregator API effectively. Following these guidelines will help you build robust, efficient, and maintainable integrations.

## Table of Contents

- [Authentication and Security](#authentication-and-security)
- [Request Management](#request-management)
- [Error Handling](#error-handling)
- [Performance Optimization](#performance-optimization)
- [Task Management](#task-management)
- [Code Organization](#code-organization)
- [Testing](#testing)
- [Monitoring and Logging](#monitoring-and-logging)
- [Production Considerations](#production-considerations)

## Authentication and Security

### 1. Never Hard-Code Credentials

**Bad**:
```python
username = "john_doe"
password = "MyPassword123"
api_key = "secret-key-12345"
```

**Good**:
```python
import os
from dotenv import load_dotenv

load_dotenv()

username = os.getenv("API_USERNAME")
password = os.getenv("API_PASSWORD")
```

**.env file**:
```bash
API_USERNAME=john_doe
API_PASSWORD=MySecurePassword123
API_BASE_URL=https://api.example.com
```

### 2. Implement Token Refresh Logic

**Pattern**:
```python
from datetime import datetime, timedelta
from typing import Optional

class AuthManager:
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
    
    def get_valid_token(self) -> str:
        """Get valid token, refreshing if necessary"""
        if self._token_needs_refresh():
            self._refresh_token()
        return self.token
    
    def _token_needs_refresh(self) -> bool:
        """Check if token needs refresh"""
        if not self.token or not self.token_expires_at:
            return True
        # Refresh 5 minutes before expiry
        return datetime.now() >= (self.token_expires_at - timedelta(minutes=5))
    
    def _refresh_token(self):
        """Refresh authentication token"""
        response = requests.post(
            f"{self.base_url}/auth/token",
            data={"username": self.username, "password": self.password}
        )
        response.raise_for_status()
        self.token = response.json()["access_token"]
        self.token_expires_at = datetime.now() + timedelta(minutes=30)
```

### 3. Use HTTPS in Production

**Development**:
```python
BASE_URL = "http://localhost:8000"  # OK for local dev
```

**Production**:
```python
BASE_URL = "https://api.example.com"  # Always use HTTPS
```

**Enforce in Code**:
```python
def validate_base_url(url: str):
    """Ensure production URLs use HTTPS"""
    if not url.startswith("http"):
        raise ValueError("Invalid URL scheme")
    
    # Warn if HTTP in production
    if os.getenv("ENVIRONMENT") == "production" and url.startswith("http://"):
        raise ValueError("Must use HTTPS in production")
    
    return url
```

### 4. Secure Token Storage

**Web Applications** - Use httpOnly cookies:
```javascript
// Server-side: Set httpOnly cookie
res.cookie('auth_token', token, {
  httpOnly: true,
  secure: true,  // HTTPS only
  sameSite: 'strict',
  maxAge: 30 * 60 * 1000  // 30 minutes
});

// Client-side: Cookie sent automatically
fetch('/api/v1/process', {
  method: 'POST',
  credentials: 'include',  // Include cookies
  body: JSON.stringify(data)
});
```

**Mobile Apps** - Use secure storage:
```python
# iOS: Keychain
# Android: EncryptedSharedPreferences
# React Native: react-native-keychain

from keyring import set_password, get_password

# Store token securely
set_password("api_service", "access_token", token)

# Retrieve token
token = get_password("api_service", "access_token")
```

## Request Management

### 1. Always Set Timeouts

**Bad**:
```python
response = requests.post(url, json=data)  # No timeout - can hang forever
```

**Good**:
```python
response = requests.post(
    url,
    json=data,
    timeout=30  # 30 second timeout
)
```

**Better** - Separate connect and read timeouts:
```python
response = requests.post(
    url,
    json=data,
    timeout=(5, 30)  # 5s connect, 30s read
)
```

### 2. Use Session Objects

**Bad** - Creates new connection each time:
```python
for i in range(100):
    response = requests.post(url, headers=headers, json=data[i])
```

**Good** - Reuses connections:
```python
session = requests.Session()
session.headers.update({"Authorization": f"Bearer {token}"})

for i in range(100):
    response = session.post(url, json=data[i])
```

**Best** - With context manager:
```python
with requests.Session() as session:
    session.headers.update({"Authorization": f"Bearer {token}"})
    
    for i in range(100):
        response = session.post(url, json=data[i])
```

### 3. Implement Request Retry Logic

```python
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

def create_resilient_session(
    retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: tuple = (500, 502, 503, 504)
) -> requests.Session:
    """Create session with retry logic"""
    session = requests.Session()
    
    retry_strategy = Retry(
        total=retries,
        backoff_factor=backoff_factor,
        status_forcelist=status_forcelist,
        allowed_methods=["GET", "POST", "PUT", "DELETE"]
    )
    
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    
    return session

# Usage
session = create_resilient_session()
response = session.post(url, json=data, timeout=30)
```

### 4. Use Correlation IDs

```python
import uuid
import logging

logger = logging.getLogger(__name__)

def make_request_with_correlation(url: str, **kwargs):
    """Make request with correlation ID for tracing"""
    correlation_id = str(uuid.uuid4())
    
    headers = kwargs.get('headers', {})
    headers['X-Correlation-Id'] = correlation_id
    kwargs['headers'] = headers
    
    logger.info(f"Request {correlation_id}: {url}")
    
    try:
        response = requests.request(**kwargs)
        logger.info(f"Response {correlation_id}: {response.status_code}")
        return response
    except Exception as e:
        logger.error(f"Request {correlation_id} failed: {e}")
        raise
```

## Error Handling

### 1. Handle All Error Cases

```python
def safe_api_call(func, *args, **kwargs):
    """Comprehensive error handling wrapper"""
    try:
        response = func(*args, **kwargs)
        response.raise_for_status()
        return response.json()
    
    except requests.exceptions.Timeout:
        logger.error("Request timed out")
        return {"error": "timeout", "message": "Request timed out"}
    
    except requests.exceptions.ConnectionError:
        logger.error("Connection failed")
        return {"error": "connection", "message": "Could not connect to server"}
    
    except requests.exceptions.HTTPError as e:
        status_code = e.response.status_code
        
        if status_code == 401:
            logger.error("Authentication failed")
            # Trigger re-authentication
            return {"error": "auth", "message": "Please login again"}
        
        elif status_code == 429:
            retry_after = e.response.headers.get('Retry-After', 60)
            logger.warning(f"Rate limited. Retry after {retry_after}s")
            return {"error": "rate_limit", "retry_after": int(retry_after)}
        
        elif status_code >= 500:
            logger.error(f"Server error: {status_code}")
            return {"error": "server", "message": "Server error, please retry"}
        
        else:
            logger.error(f"HTTP error: {status_code}")
            return {"error": "http", "message": e.response.text}
    
    except Exception as e:
        logger.exception("Unexpected error")
        return {"error": "unexpected", "message": str(e)}
```

### 2. Validate Before Sending

```python
from pydantic import BaseModel, HttpUrl, Field, ValidationError

class ScrapeRequestValidator(BaseModel):
    url: HttpUrl
    prompt: str = Field(min_length=5, max_length=1000)

def create_task_safely(url: str, prompt: str):
    """Validate before making API call"""
    try:
        # Validate input
        validated = ScrapeRequestValidator(url=url, prompt=prompt)
        
        # Make API call
        response = requests.post(
            f"{BASE_URL}/api/v1/process",
            headers={"Authorization": f"Bearer {token}"},
            json=validated.model_dump()
        )
        
        return response.json()
    
    except ValidationError as e:
        return {
            "error": "validation",
            "message": "Invalid input",
            "details": e.errors()
        }
```

### 3. Provide Context in Errors

```python
class APIError(Exception):
    """Custom exception with context"""
    def __init__(self, message: str, status_code: int = None, 
                 response_body: str = None, correlation_id: str = None):
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        self.correlation_id = correlation_id
        super().__init__(self.message)
    
    def __str__(self):
        parts = [self.message]
        if self.status_code:
            parts.append(f"Status: {self.status_code}")
        if self.correlation_id:
            parts.append(f"Correlation ID: {self.correlation_id}")
        return " | ".join(parts)

# Usage
try:
    response = requests.post(url, json=data)
    response.raise_for_status()
except requests.exceptions.HTTPError as e:
    correlation_id = e.response.headers.get('X-Correlation-Id')
    raise APIError(
        message="Task creation failed",
        status_code=e.response.status_code,
        response_body=e.response.text,
        correlation_id=correlation_id
    )
```

## Performance Optimization

### 1. Implement Client-Side Caching

```python
from functools import lru_cache
import hashlib
import json

class CachedAPIClient:
    def __init__(self, cache_ttl: int = 300):
        self.cache = {}
        self.cache_ttl = cache_ttl  # seconds
    
    def _cache_key(self, url: str, prompt: str) -> str:
        """Generate cache key"""
        content = json.dumps({"url": url, "prompt": prompt}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def create_task(self, url: str, prompt: str):
        """Create task with caching"""
        cache_key = self._cache_key(url, prompt)
        
        # Check cache
        if cache_key in self.cache:
            cached_time, result = self.cache[cache_key]
            if time.time() - cached_time < self.cache_ttl:
                logger.info("Returning cached result")
                return result
        
        # Make API call
        result = self._make_api_call(url, prompt)
        
        # Cache result
        self.cache[cache_key] = (time.time(), result)
        
        return result
```

### 2. Batch Operations

```python
def create_scheduled_jobs_batch(jobs: list):
    """Create multiple scheduled jobs efficiently"""
    results = []
    errors = []
    
    with requests.Session() as session:
        session.headers.update({"Authorization": f"Bearer {token}"})
        
        for job in jobs:
            try:
                response = session.post(
                    f"{BASE_URL}/api/v1/jobs",
                    json=job,
                    timeout=10
                )
                response.raise_for_status()
                results.append(response.json())
            except Exception as e:
                errors.append({"job": job, "error": str(e)})
    
    return {"created": results, "failed": errors}
```

### 3. Parallelize Independent Requests

```python
import concurrent.futures

def create_tasks_parallel(tasks: list, max_workers: int = 5):
    """Create multiple tasks in parallel"""
    def create_single_task(task_data):
        return requests.post(
            f"{BASE_URL}/api/v1/process",
            headers={"Authorization": f"Bearer {token}"},
            json=task_data,
            timeout=30
        )
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(create_single_task, task) for task in tasks]
        
        results = []
        for future in concurrent.futures.as_completed(futures):
            try:
                response = future.result()
                results.append(response.json())
            except Exception as e:
                logger.error(f"Task creation failed: {e}")
        
        return results
```

## Task Management

### 1. Implement Smart Polling

```python
import time

def wait_for_task_completion(
    task_id: str,
    initial_delay: float = 2.0,
    max_delay: float = 30.0,
    timeout: float = 300.0
) -> dict:
    """Poll task status with exponential backoff"""
    start_time = time.time()
    delay = initial_delay
    
    while True:
        # Check timeout
        if time.time() - start_time > timeout:
            raise TimeoutError(f"Task {task_id} timed out after {timeout}s")
        
        # Check status
        response = requests.get(
            f"{BASE_URL}/api/v1/status/{task_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        status_data = response.json()
        
        # Check completion
        if status_data["status"] in ["SUCCESS", "FAILED"]:
            return status_data
        
        # Log progress
        progress = status_data.get("progress", 0)
        logger.info(f"Task {task_id}: {progress}% complete")
        
        # Wait with exponential backoff
        time.sleep(delay)
        delay = min(delay * 1.5, max_delay)
```

### 2. Handle Task Failures Gracefully

```python
def create_task_with_retry(
    url: str,
    prompt: str,
    max_retries: int = 3
) -> dict:
    """Create task with retry on failure"""
    for attempt in range(max_retries):
        # Create task
        task_response = create_task(url, prompt)
        task_id = task_response["task_id"]
        
        # Wait for completion
        try:
            result = wait_for_task_completion(task_id)
            
            if result["status"] == "SUCCESS":
                return result
            
            # Task failed, retry if attempts remaining
            if attempt < max_retries - 1:
                logger.warning(f"Task failed, retrying... (attempt {attempt + 1})")
                time.sleep(5 * (attempt + 1))  # Increasing delay
            else:
                return result
        
        except TimeoutError:
            if attempt < max_retries - 1:
                logger.warning("Task timed out, retrying...")
            else:
                raise
    
    raise Exception("Max retries exceeded")
```

### 3. Clean Up Old Tasks

```python
from datetime import datetime, timedelta

def cleanup_old_tasks(older_than_days: int = 30):
    """Delete old completed tasks (if API supports it)"""
    cutoff_date = datetime.now() - timedelta(days=older_than_days)
    
    # Get user activity
    response = requests.get(
        f"{BASE_URL}/api/v1/users/me/activity",
        headers={"Authorization": f"Bearer {token}"}
    )
    activity = response.json()
    
    old_tasks = [
        task for task in activity["tasks"]
        if datetime.fromisoformat(task["created_at"].replace('Z', '+00:00')) < cutoff_date
        and task["status"] in ["SUCCESS", "FAILED"]
    ]
    
    logger.info(f"Found {len(old_tasks)} old tasks")
    # Note: API currently doesn't support task deletion
    # This is a placeholder for future functionality
```

## Code Organization

### 1. Use a Client Class

```python
class WebDataAggregatorClient:
    """Organized API client"""
    
    def __init__(self, base_url: str, username: str, password: str):
        self.base_url = base_url
        self.auth = AuthManager(base_url, username, password)
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create configured session"""
        session = create_resilient_session()
        session.timeout = 30
        return session
    
    def _get_headers(self) -> dict:
        """Get request headers with auth"""
        return {
            "Authorization": f"Bearer {self.auth.get_valid_token()}",
            "Content-Type": "application/json"
        }
    
    # Task operations
    def create_task(self, url: str, prompt: str) -> dict:
        """Create scraping task"""
        response = self.session.post(
            f"{self.base_url}/api/v1/process",
            headers=self._get_headers(),
            json={"url": url, "prompt": prompt}
        )
        response.raise_for_status()
        return response.json()
    
    def get_task_status(self, task_id: str) -> dict:
        """Get task status"""
        response = self.session.get(
            f"{self.base_url}/api/v1/status/{task_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    def get_task_result(self, task_id: str) -> dict:
        """Get task result"""
        response = self.session.get(
            f"{self.base_url}/api/v1/result/{task_id}",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()
    
    # Scheduler operations
    def create_scheduled_job(self, url: str, prompt: str, cron: str) -> dict:
        """Create scheduled job"""
        response = self.session.post(
            f"{self.base_url}/api/v1/jobs",
            headers=self._get_headers(),
            json={"url": url, "prompt": prompt, "schedule_cron": cron}
        )
        response.raise_for_status()
        return response.json()
    
    def list_scheduled_jobs(self) -> list:
        """List user's scheduled jobs"""
        response = self.session.get(
            f"{self.base_url}/api/v1/jobs",
            headers=self._get_headers()
        )
        response.raise_for_status()
        return response.json()

# Usage
client = WebDataAggregatorClient(
    base_url=os.getenv("API_BASE_URL"),
    username=os.getenv("API_USERNAME"),
    password=os.getenv("API_PASSWORD")
)

task = client.create_task("https://example.com", "Extract headings")
result = client.get_task_result(task["task_id"])
```

### 2. Separate Configuration

```python
# config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    api_base_url: str
    api_username: str
    api_password: str
    request_timeout: int = 30
    max_retries: int = 3
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"

settings = Settings()
```

## Testing

### 1. Mock API Responses

```python
import unittest
from unittest.mock import patch, Mock

class TestAPIClient(unittest.TestCase):
    @patch('requests.Session.post')
    def test_create_task(self, mock_post):
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "task_id": "test-123",
            "status": "PENDING",
            "message": "Task created"
        }
        mock_post.return_value = mock_response
        
        # Test
        client = WebDataAggregatorClient("http://test", "user", "pass")
        result = client.create_task("https://example.com", "Extract data")
        
        # Assertions
        self.assertEqual(result["task_id"], "test-123")
        self.assertEqual(result["status"], "PENDING")
```

### 2. Integration Tests

```python
import pytest

@pytest.fixture
def api_client():
    """Create test client"""
    return WebDataAggregatorClient(
        base_url=os.getenv("TEST_API_URL", "http://localhost:8000"),
        username=os.getenv("TEST_USERNAME"),
        password=os.getenv("TEST_PASSWORD")
    )

def test_full_task_workflow(api_client):
    """Test complete task workflow"""
    # Create task
    task = api_client.create_task(
        url="https://httpbin.org/html",
        prompt="Extract all headings"
    )
    assert "task_id" in task
    
    # Wait for completion
    result = wait_for_task_completion(task["task_id"])
    
    # Verify result
    assert result["status"] in ["SUCCESS", "FAILED"]
    if result["status"] == "SUCCESS":
        assert "data" in result
```

## Monitoring and Logging

### 1. Structured Logging

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON log formatter"""
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add extra fields
        if hasattr(record, 'correlation_id'):
            log_data['correlation_id'] = record.correlation_id
        if hasattr(record, 'task_id'):
            log_data['task_id'] = record.task_id
        
        return json.dumps(log_data)

# Configure logging
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.INFO)
```

### 2. Track Metrics

```python
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class APIMetrics:
    """Track API usage metrics"""
    requests_total: int = 0
    requests_success: int = 0
    requests_failed: int = 0
    rate_limit_hits: int = 0
    average_response_time: float = 0.0
    response_times: list = None
    
    def __post_init__(self):
        if self.response_times is None:
            self.response_times = []
    
    def record_request(self, success: bool, response_time: float, 
                      rate_limited: bool = False):
        """Record request metrics"""
        self.requests_total += 1
        
        if success:
            self.requests_success += 1
        else:
            self.requests_failed += 1
        
        if rate_limited:
            self.rate_limit_hits += 1
        
        self.response_times.append(response_time)
        self.average_response_time = sum(self.response_times) / len(self.response_times)
    
    def get_success_rate(self) -> float:
        """Calculate success rate"""
        if self.requests_total == 0:
            return 0.0
        return (self.requests_success / self.requests_total) * 100

# Usage
metrics = APIMetrics()

start = time.time()
try:
    response = make_api_request()
    metrics.record_request(success=True, response_time=time.time() - start)
except Exception:
    metrics.record_request(success=False, response_time=time.time() - start)

print(f"Success rate: {metrics.get_success_rate():.2f}%")
```

## Production Considerations

### 1. Health Checks

```python
def check_api_health() -> bool:
    """Check if API is healthy"""
    try:
        response = requests.get(
            f"{BASE_URL}/api/v1/health",
            timeout=5
        )
        return response.status_code == 200
    except:
        return False

# Periodic health check
if not check_api_health():
    logger.error("API health check failed")
    # Alert monitoring system
```

### 2. Graceful Shutdown

```python
import signal
import sys

class GracefulShutdown:
    """Handle graceful shutdown"""
    def __init__(self):
        self.shutdown_requested = False
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, sig, frame):
        """Handle shutdown signal"""
        logger.info("Shutdown requested, finishing current tasks...")
        self.shutdown_requested = True
    
    def should_continue(self) -> bool:
        """Check if should continue processing"""
        return not self.shutdown_requested

# Usage
shutdown = GracefulShutdown()

while shutdown.should_continue():
    # Process tasks
    pass

logger.info("Shutdown complete")
sys.exit(0)
```

### 3. Configuration Validation

```python
def validate_production_config():
    """Validate configuration for production"""
    errors = []
    
    # Check required environment variables
    required_vars = [
        "API_BASE_URL",
        "API_USERNAME",
        "API_PASSWORD"
    ]
    
    for var in required_vars:
        if not os.getenv(var):
            errors.append(f"Missing required environment variable: {var}")
    
    # Check HTTPS in production
    base_url = os.getenv("API_BASE_URL", "")
    if os.getenv("ENVIRONMENT") == "production":
        if not base_url.startswith("https://"):
            errors.append("Production must use HTTPS")
    
    if errors:
        raise ValueError(f"Configuration errors: {', '.join(errors)}")
    
    logger.info("Production configuration validated")

# Run at startup
if os.getenv("ENVIRONMENT") == "production":
    validate_production_config()
```

## Related Documentation

- [API Reference](./API_REFERENCE.md) - Complete endpoint documentation
- [Authentication Guide](./AUTHENTICATION_GUIDE.md) - Authentication details
- [Error Handling](./ERROR_HANDLING.md) - Error handling guide
- [Rate Limiting](./RATE_LIMITING.md) - Rate limit strategies
- [Integration Tutorial](./INTEGRATION_TUTORIAL.md) - Step-by-step examples

---

## DATA_MODELS.md

*(Modified: 2025-12-14 18:28:53)*

# Data Models and Schemas

## Overview

This guide provides comprehensive documentation of all data models, request/response schemas, and data structures used in the Intelligent Web Data Aggregator API. All models are validated using Pydantic for type safety and automatic validation.

## Table of Contents

- [Authentication Models](#authentication-models)
- [Task Models](#task-models)
- [Scheduler Models](#scheduler-models)
- [Error Models](#error-models)
- [Enums and Constants](#enums-and-constants)
- [Validation Rules](#validation-rules)
- [Examples and Use Cases](#examples-and-use-cases)
- [Database Models](#database-models)

## Authentication Models

### UserCreate

Request model for user registration.

**Schema**:
```json
{
  "username": "string",
  "password": "string",
  "email": "string (optional)"
}
```

**Field Specifications**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `username` | string | Yes | Unique, non-empty | User's unique identifier |
| `password` | string | Yes | ≤ 72 bytes | User's password (hashed server-side) |
| `email` | string | No | Valid email format | User's email address |

**Example**:
```json
{
  "username": "john_doe",
  "password": "SecureP@ssw0rd123",
  "email": "john@example.com"
}
```

**Python Model**:
```python
from pydantic import BaseModel
from typing import Optional

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None
```

**Validation Rules**:
- Username must be unique in the system
- Password will be hashed with bcrypt before storage
- Password must not exceed 72 bytes (bcrypt limitation)
- Email is validated for proper format if provided

### UserResponse

Response model for user information.

**Schema**:
```json
{
  "id": 1,
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true
}
```

**Field Specifications**:

| Field | Type | Description |
|-------|------|-------------|
| `id` | integer | Unique user ID |
| `username` | string | User's username |
| `email` | string \| null | User's email (optional) |
| `is_active` | boolean | Whether user account is active |

**Example**:
```json
{
  "id": 42,
  "username": "john_doe",
  "email": "john@example.com",
  "is_active": true
}
```

**Python Model**:
```python
from pydantic import BaseModel, ConfigDict
from typing import Optional

class UserResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    username: str
    email: Optional[str] = None
    is_active: bool
```

### Token

Response model for authentication token.

**Schema**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

**Field Specifications**:

| Field | Type | Description |
|-------|------|-------------|
| `access_token` | string | JWT access token |
| `token_type` | string | Token type (always "bearer") |

**Example**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJqb2huX2RvZSIsImV4cCI6MTcwMjU1NjQwMH0.abcdef123456",
  "token_type": "bearer"
}
```

**Token Format**: Standard JWT with:
- **Header**: Algorithm (HS256) and type
- **Payload**: Subject (username) and expiration
- **Signature**: HMAC SHA256 signature

**Usage**:
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Task Models

### ScrapeRequest

Request model for creating a scraping task.

**Schema**:
```json
{
  "url": "https://example.com",
  "prompt": "Extract all job listings with titles and locations"
}
```

**Field Specifications**:

| Field | Type | Required | Constraints | Description |
|-------|------|----------|-------------|-------------|
| `url` | HttpUrl | Yes | Valid HTTP/HTTPS URL, max 2083 chars | Target website URL |
| `prompt` | string | Yes | 5-1000 characters | Natural language extraction instruction |

**Example**:
```json
{
  "url": "https://jobs.example.com/careers",
  "prompt": "I want all software engineering positions with job title, location, required experience, and salary range"
}
```

**Python Model**:
```python
from pydantic import BaseModel, HttpUrl, Field

class ScrapeRequest(BaseModel):
    url: HttpUrl
    prompt: str = Field(..., min_length=5, max_length=1000)
```

**URL Validation**:
- Must start with `http://` or `https://`
- Must be a valid, well-formed URL
- Maximum length: 2083 characters (browser limit)

**Prompt Validation**:
- Minimum: 5 characters (must be meaningful)
- Maximum: 1000 characters (LLM context limit)
- Checked for injection patterns

**Good Prompt Examples**:
```json
"Extract all product names and prices"
"Get email addresses from the contact page"
"Find all article titles and publication dates"
"List all team member names and their roles"
```

**Bad Prompt Examples**:
```json
"hi"           // Too short
"data"         // Too vague
"<script>..."  // Injection attempt
```

### TaskResponse

Response model for task creation.

**Schema**:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "PENDING",
  "message": "Task created successfully"
}
```

**Field Specifications**:

| Field | Type | Description |
|-------|------|-------------|
| `task_id` | string (UUID) | Unique task identifier |
| `status` | string | Current task status |
| `message` | string | Human-readable status message |

**Status Values**:
- `PENDING`: Task created, awaiting processing
- `IN_PROGRESS`: Task is being processed
- `SUCCESS`: Task completed successfully
- `FAILED`: Task failed (see error message)

**Example**:
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "PENDING",
  "message": "Task created successfully"
}
```

### TaskStatusResponse

Response model for task status queries.

**Schema**:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "IN_PROGRESS",
  "progress": 45,
  "message": null,
  "created_at": "2025-12-14T10:30:00Z",
  "updated_at": "2025-12-14T10:30:30Z"
}
```

**Field Specifications**:

| Field | Type | Optional | Description |
|-------|------|----------|-------------|
| `task_id` | string | No | Unique task identifier |
| `status` | string | No | Current task status |
| `progress` | integer | Yes | Progress percentage (0-100) |
| `message` | string | Yes | Additional status information |
| `created_at` | datetime | No | Task creation timestamp (ISO 8601) |
| `updated_at` | datetime | No | Last update timestamp (ISO 8601) |

**Progress Tracking**:
- `0-25%`: Initial processing, intent extraction
- `26-50%`: Regex generation and validation
- `51-75%`: Web page fetching
- `76-100%`: Data extraction and validation

**Example Responses**:

**Pending Task**:
```json
{
  "task_id": "abc-123",
  "status": "PENDING",
  "progress": 0,
  "message": null,
  "created_at": "2025-12-14T10:30:00Z",
  "updated_at": "2025-12-14T10:30:00Z"
}
```

**In-Progress Task**:
```json
{
  "task_id": "abc-123",
  "status": "IN_PROGRESS",
  "progress": 65,
  "message": "Extracting data from page",
  "created_at": "2025-12-14T10:30:00Z",
  "updated_at": "2025-12-14T10:30:45Z"
}
```

**Completed Task**:
```json
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "progress": 100,
  "message": "Task completed successfully",
  "created_at": "2025-12-14T10:30:00Z",
  "updated_at": "2025-12-14T10:31:15Z"
}
```

### ScrapeResult

Response model for completed task results.

**Schema**:
```json
{
  "task_id": "123e4567-e89b-12d3-a456-426614174000",
  "status": "SUCCESS",
  "url": "https://example.com",
  "prompt": "Extract all headings",
  "data": [
    {
      "text": "Welcome to Example.com",
      "source": "//h1[@class='title']",
      "confidence": 0.95
    }
  ],
  "metadata": {
    "total_matches": 1,
    "used_cached_parser": false
  },
  "processing_time": 3.21,
  "created_at": "2025-12-14T10:30:00Z",
  "completed_at": "2025-12-14T10:30:03Z"
}
```

**Field Specifications**:

| Field | Type | Optional | Description |
|-------|------|----------|-------------|
| `task_id` | string | No | Unique task identifier |
| `status` | string | No | Task status ("SUCCESS") |
| `url` | string | No | Original target URL |
| `prompt` | string | No | Original extraction prompt |
| `data` | array | No | Extracted data items |
| `metadata` | object | No | Additional extraction metadata |
| `processing_time` | float | Yes | Processing duration in seconds |
| `created_at` | datetime | No | Task creation timestamp |
| `completed_at` | datetime | Yes | Task completion timestamp |

**Data Item Structure**:

Each item in the `data` array contains:

| Field | Type | Description |
|-------|------|-------------|
| `text` | string | Extracted text content |
| `source` | string | XPath or CSS selector used |
| `confidence` | float | Extraction confidence (0.0-1.0) |

**Metadata Structure**:

| Field | Type | Description |
|-------|------|-------------|
| `total_matches` | integer | Number of matches found |
| `used_cached_parser` | boolean | Whether cached parser was used |
| `parser_id` | integer | Parser ID (if cached) |
| `extraction_method` | string | Method used (xpath, css, regex) |

**Complete Example**:
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "SUCCESS",
  "url": "https://jobs.example.com/careers",
  "prompt": "Extract all job titles and locations",
  "data": [
    {
      "text": "Senior Software Engineer - San Francisco, CA",
      "source": "//div[@class='job-listing']/h2",
      "confidence": 0.92
    },
    {
      "text": "Product Manager - New York, NY",
      "source": "//div[@class='job-listing']/h2",
      "confidence": 0.89
    },
    {
      "text": "Data Scientist - Remote",
      "source": "//div[@class='job-listing']/h2",
      "confidence": 0.94
    }
  ],
  "metadata": {
    "total_matches": 3,
    "used_cached_parser": true,
    "parser_id": 42,
    "extraction_method": "xpath",
    "page_size_kb": 245
  },
  "processing_time": 2.87,
  "created_at": "2025-12-14T10:30:00.000Z",
  "completed_at": "2025-12-14T10:30:02.870Z"
}
```

## Scheduler Models

### ScheduledJobCreate

Request model for creating a scheduled job.

**Schema**:
```json
{
  "url": "https://example.com",
  "prompt": "Extract latest news",
  "schedule_cron": "0 9 * * *"
}
```

**Field Specifications**:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `url` | HttpUrl | Yes | Target website URL |
| `prompt` | string | Yes | Extraction instruction |
| `schedule_cron` | string | Yes | Cron expression for scheduling |

**Cron Expression Format**:
```
┌───────────── minute (0 - 59)
│ ┌───────────── hour (0 - 23)
│ │ ┌───────────── day of month (1 - 31)
│ │ │ ┌───────────── month (1 - 12)
│ │ │ │ ┌───────────── day of week (0 - 6) (Sunday to Saturday)
│ │ │ │ │
* * * * *
```

**Cron Examples**:

| Expression | Description |
|------------|-------------|
| `0 9 * * *` | Every day at 9:00 AM |
| `*/15 * * * *` | Every 15 minutes |
| `0 0 * * 0` | Every Sunday at midnight |
| `0 9 * * 1-5` | Weekdays at 9:00 AM |
| `30 14 1 * *` | 1st of every month at 2:30 PM |
| `0 */6 * * *` | Every 6 hours |

**Example**:
```json
{
  "url": "https://news.example.com",
  "prompt": "Extract top 10 news headlines",
  "schedule_cron": "0 */4 * * *"
}
```

### ScheduledJobResponse

Response model for scheduled job information.

**Schema**:
```json
{
  "id": 1,
  "url": "https://example.com",
  "prompt": "Extract latest news",
  "schedule_cron": "0 9 * * *",
  "next_run_at": "2025-12-15T09:00:00Z",
  "last_run_at": null,
  "created_at": "2025-12-14T10:30:00Z"
}
```

**Field Specifications**:

| Field | Type | Optional | Description |
|-------|------|----------|-------------|
| `id` | integer | No | Unique job identifier |
| `url` | string | No | Target website URL |
| `prompt` | string | No | Extraction instruction |
| `schedule_cron` | string | No | Cron schedule expression |
| `next_run_at` | datetime | Yes | Next scheduled execution time |
| `last_run_at` | datetime | Yes | Last execution time |
| `created_at` | datetime | No | Job creation timestamp |

**Example**:
```json
{
  "id": 5,
  "url": "https://jobs.example.com/careers",
  "prompt": "Get all new job postings",
  "schedule_cron": "0 9 * * 1-5",
  "next_run_at": "2025-12-15T09:00:00Z",
  "last_run_at": "2025-12-14T09:00:00Z",
  "created_at": "2025-12-01T10:00:00Z"
}
```

### UserActivityResponse

Combined response model for user's tasks and scheduled jobs.

**Schema**:
```json
{
  "tasks": [
    {
      "task_id": "abc-123",
      "status": "SUCCESS",
      "progress": 100,
      "message": null,
      "created_at": "2025-12-14T10:30:00Z",
      "updated_at": "2025-12-14T10:30:15Z"
    }
  ],
  "scheduled_jobs": [
    {
      "id": 1,
      "url": "https://example.com",
      "prompt": "Extract data",
      "schedule_cron": "0 9 * * *",
      "next_run_at": "2025-12-15T09:00:00Z",
      "last_run_at": null,
      "created_at": "2025-12-14T10:00:00Z"
    }
  ]
}
```

**Field Specifications**:

| Field | Type | Description |
|-------|------|-------------|
| `tasks` | array | Array of TaskStatusResponse objects |
| `scheduled_jobs` | array | Array of ScheduledJobResponse objects |

**Purpose**: Provides a complete view of user's activity in a single request, useful for dashboard views.

## Error Models

### ErrorResponse

Standard error response format.

**Schema**:
```json
{
  "error": "Not Found",
  "message": "Task not found",
  "timestamp": "2025-12-14T10:30:00Z"
}
```

**Field Specifications**:

| Field | Type | Description |
|-------|------|-------------|
| `error` | string | Error category/type |
| `message` | string | Human-readable error description |
| `timestamp` | datetime | When the error occurred (ISO 8601) |

**Common Error Types**:

| Error | HTTP Status | Description |
|-------|-------------|-------------|
| `Bad Request` | 400 | Invalid request data |
| `Unauthorized` | 401 | Authentication required/failed |
| `Forbidden` | 403 | Insufficient permissions |
| `Not Found` | 404 | Resource doesn't exist |
| `Too Many Requests` | 429 | Rate limit exceeded |
| `Internal Server Error` | 500 | Unexpected server error |

**Examples**:

**404 Not Found**:
```json
{
  "error": "Not Found",
  "message": "Task not found",
  "timestamp": "2025-12-14T10:30:00Z"
}
```

**400 Bad Request**:
```json
{
  "error": "Bad Request",
  "message": "Invalid prompt: Potential injection detected",
  "timestamp": "2025-12-14T10:30:00Z"
}
```

### ValidationError

Pydantic validation error format (422 status).

**Schema**:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "prompt"],
      "msg": "String should have at least 5 characters",
      "input": "hi",
      "ctx": {
        "min_length": 5
      }
    }
  ]
}
```

**Field Specifications**:

| Field | Type | Description |
|-------|------|-------------|
| `detail` | array | List of validation errors |
| `type` | string | Validation error type |
| `loc` | array | Location of error in request |
| `msg` | string | Human-readable message |
| `input` | any | The invalid input value |
| `ctx` | object | Additional error context |

**Common Validation Types**:

| Type | Description | Example Fix |
|------|-------------|-------------|
| `string_too_short` | String below minimum length | Add more characters |
| `string_too_long` | String exceeds maximum length | Shorten the input |
| `url_parsing` | Invalid URL format | Use valid HTTP/HTTPS URL |
| `url_scheme` | Invalid URL scheme | Use http:// or https:// |
| `missing` | Required field not provided | Include the field |

**Example - Multiple Errors**:
```json
{
  "detail": [
    {
      "type": "url_scheme",
      "loc": ["body", "url"],
      "msg": "URL scheme should be 'http' or 'https'",
      "input": "ftp://example.com"
    },
    {
      "type": "string_too_short",
      "loc": ["body", "prompt"],
      "msg": "String should have at least 5 characters",
      "input": "get"
    }
  ]
}
```

## Enums and Constants

### TaskStatus

Task status enumeration.

**Values**:
```python
class TaskStatus:
    PENDING = "PENDING"          # Task created, not started
    IN_PROGRESS = "IN_PROGRESS"  # Task being processed
    SUCCESS = "SUCCESS"          # Task completed successfully
    FAILED = "FAILED"            # Task failed
```

**State Transitions**:
```
PENDING ──→ IN_PROGRESS ──→ SUCCESS
                 │
                 └──────────→ FAILED
```

### HTTP Status Codes

Standard HTTP status codes used by the API:

| Code | Constant | Usage |
|------|----------|-------|
| 200 | OK | Successful request |
| 202 | ACCEPTED | Async task accepted |
| 400 | BAD_REQUEST | Invalid request |
| 401 | UNAUTHORIZED | Auth required |
| 403 | FORBIDDEN | Insufficient permissions |
| 404 | NOT_FOUND | Resource not found |
| 422 | UNPROCESSABLE_ENTITY | Validation error |
| 429 | TOO_MANY_REQUESTS | Rate limit exceeded |
| 500 | INTERNAL_SERVER_ERROR | Server error |

## Validation Rules

### URL Validation

**Rules**:
1. Must be valid HTTP or HTTPS URL
2. Maximum length: 2083 characters
3. Must be well-formed (scheme://host/path)
4. Special protocols blocked (javascript:, file:, data:)

**Valid Examples**:
```
https://example.com
http://subdomain.example.com:8080/path
https://example.com/path?query=value&foo=bar
```

**Invalid Examples**:
```
example.com                    // Missing scheme
ftp://example.com              // Invalid scheme
//example.com                  // Relative URL
javascript:alert('xss')        // Blocked scheme
```

### Prompt Validation

**Rules**:
1. Minimum length: 5 characters
2. Maximum length: 1000 characters
3. Must not contain injection patterns
4. UTF-8 encoding

**Injection Patterns Blocked**:
- `<script>` tags
- `javascript:` protocol
- `eval()` calls
- SQL injection patterns
- Command injection patterns

**Good Examples**:
```
"Extract all product names and prices"
"Get contact email addresses"
"Find all article titles published this week"
```

**Bad Examples**:
```
"hi"                                  // Too short
"<script>alert('xss')</script>"      // Injection attempt
[1000+ character prompt]              // Too long
```

### Cron Expression Validation

**Format**: Five fields separated by spaces
```
minute hour day_of_month month day_of_week
```

**Field Ranges**:
- minute: 0-59
- hour: 0-23
- day_of_month: 1-31
- month: 1-12
- day_of_week: 0-6 (0 = Sunday)

**Special Characters**:
- `*`: Any value
- `,`: List separator (e.g., `1,3,5`)
- `-`: Range (e.g., `1-5`)
- `/`: Step (e.g., `*/15`)

## Examples and Use Cases

### Creating and Monitoring a Task

**1. Create Task**:
```bash
curl -X POST "http://localhost:8000/api/v1/process" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://jobs.example.com",
    "prompt": "Extract all job titles and locations"
  }'
```

**Response**:
```json
{
  "task_id": "abc-123-def",
  "status": "PENDING",
  "message": "Task created successfully"
}
```

**2. Check Status**:
```bash
curl "http://localhost:8000/api/v1/status/abc-123-def" \
  -H "Authorization: Bearer $TOKEN"
```

**Response**:
```json
{
  "task_id": "abc-123-def",
  "status": "IN_PROGRESS",
  "progress": 60,
  "message": "Extracting data",
  "created_at": "2025-12-14T10:30:00Z",
  "updated_at": "2025-12-14T10:30:30Z"
}
```

**3. Get Results**:
```bash
curl "http://localhost:8000/api/v1/result/abc-123-def" \
  -H "Authorization: Bearer $TOKEN"
```

**Response**:
```json
{
  "task_id": "abc-123-def",
  "status": "SUCCESS",
  "url": "https://jobs.example.com",
  "prompt": "Extract all job titles and locations",
  "data": [
    {
      "text": "Senior Software Engineer - San Francisco",
      "source": "//div[@class='job']/h2",
      "confidence": 0.92
    }
  ],
  "metadata": {
    "total_matches": 1,
    "used_cached_parser": false
  },
  "processing_time": 3.5,
  "created_at": "2025-12-14T10:30:00Z",
  "completed_at": "2025-12-14T10:30:03Z"
}
```

### Scheduling Recurring Tasks

```python
import requests

# Create scheduled job for daily monitoring
job = {
    "url": "https://jobs.example.com",
    "prompt": "Extract new job postings",
    "schedule_cron": "0 9 * * *"  # Daily at 9 AM
}

response = requests.post(
    "http://localhost:8000/api/v1/jobs",
    headers={"Authorization": f"Bearer {token}"},
    json=job
)

job_data = response.json()
print(f"Job created: {job_data['id']}")
print(f"Next run: {job_data['next_run_at']}")
```

## Database Models

### Internal Database Schema

For reference, here are the underlying database models (not directly exposed via API):

**Users Table**:
- `id`: Primary key
- `username`: Unique username
- `hashed_password`: bcrypt hashed password
- `email`: Email address (optional)
- `is_active`: Account status
- `created_at`: Registration timestamp

**Scraping Tasks Table**:
- `id`: Primary key
- `task_id`: UUID for external reference
- `owner_id`: Foreign key to users
- `url`: Target URL
- `user_prompt`: Original prompt
- `status`: Current status
- `extracted_data`: JSON result data
- `error_message`: Error details (if failed)
- `created_at`: Creation timestamp
- `updated_at`: Last update timestamp

**Scheduled Jobs Table**:
- `id`: Primary key
- `owner_id`: Foreign key to users
- `url`: Target URL
- `prompt`: Extraction prompt
- `schedule_cron`: Cron expression
- `next_run_at`: Next execution time
- `last_run_at`: Last execution time
- `created_at`: Creation timestamp

## Related Documentation

- [API Reference](./API_REFERENCE.md) - Complete endpoint documentation
- [Authentication Guide](./AUTHENTICATION_GUIDE.md) - Authentication details
- [Error Handling](./ERROR_HANDLING.md) - Error responses
- [Integration Tutorial](./INTEGRATION_TUTORIAL.md) - Working examples
- [OpenAPI Specification](../openapi.json) - Machine-readable specification

## OpenAPI/Swagger Integration

All models are automatically documented in the OpenAPI specification available at:
- **Interactive UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **JSON**: http://localhost:8000/openapi.json

You can use these endpoints to:
- Explore all models interactively
- Generate client code automatically
- Validate requests before sending
- Test API endpoints

---

## VERSIONING.md

*(Modified: 2025-12-14 18:28:53)*

# API Versioning and Changelog

## Overview

This document describes the API versioning strategy, backward compatibility guarantees, and tracks changes across API versions.

## Table of Contents

- [Versioning Strategy](#versioning-strategy)
- [Current Version](#current-version)
- [Backward Compatibility](#backward-compatibility)
- [Breaking Changes Policy](#breaking-changes-policy)
- [Deprecation Policy](#deprecation-policy)
- [Version Migration Guide](#version-migration-guide)
- [Changelog](#changelog)

## Versioning Strategy

### URL-Based Versioning

The API uses **URL path versioning** for clear, explicit version identification:

```
https://api.example.com/api/v1/process
                           ^^^
                           Version identifier
```

**Benefits**:
- Clear and explicit
- Easy to understand and implement
- Simple routing
- Version-specific documentation

### Version Format

Versions follow the format: `v{MAJOR}`

- `v1`: Current stable version
- `v2`: Future version (when breaking changes are introduced)

### Versioning Principles

1. **Semantic Versioning Spirit**: While we use `v{MAJOR}` in URLs, changes follow semantic versioning principles
2. **Backward Compatibility**: Non-breaking changes are added to existing versions
3. **Deprecation Warnings**: Features are deprecated before removal
4. **Migration Period**: Overlapping version support during transitions

## Current Version

### Version 1.0.0 (v1)

**Release Date**: December 2025

**Status**: Stable

**Base URL**: `/api/v1`

**Features**:
- User authentication (JWT)
- Task creation and management
- Scheduled jobs
- Status tracking
- Rate limiting
- Input sanitization

**Supported Until**: At least December 2026 (minimum 12 months)

## Backward Compatibility

### What is Considered Backward Compatible

The following changes are **NOT considered breaking** and may be added to v1:

#### 1. Adding New Endpoints
```
✓ Adding /api/v1/new-feature
✓ Adding /api/v1/users/{id}/preferences
```

#### 2. Adding Optional Fields to Requests
```json
// Before
{
  "url": "https://example.com",
  "prompt": "Extract data"
}

// After (backward compatible)
{
  "url": "https://example.com",
  "prompt": "Extract data",
  "options": {              // ← New optional field
    "cache": true
  }
}
```

#### 3. Adding New Fields to Responses
```json
// Before
{
  "task_id": "abc-123",
  "status": "SUCCESS"
}

// After (backward compatible)
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "estimated_cost": 0.05    // ← New field
}
```

#### 4. Adding New Optional Headers
```http
X-Request-Priority: high   ← New optional header
```

#### 5. Adding New Status Codes for New Scenarios
```
200 OK (existing)
201 Created (new, for different endpoint)
```

#### 6. Adding New Error Types
```json
{
  "error": "New Error Type",
  "message": "Description"
}
```

### What is Considered Breaking

The following changes are **breaking** and require a new API version:

#### 1. Removing Endpoints
```
✗ Removing /api/v1/deprecated-endpoint
```

#### 2. Removing Request/Response Fields
```json
// Breaking: Removing "message" field
{
  "task_id": "abc-123",
  "status": "SUCCESS"
  // "message" removed ← Breaking!
}
```

#### 3. Changing Required Fields
```json
// Breaking: Making optional field required
{
  "url": "https://example.com",
  "prompt": "Extract data",
  "format": "json"  // ← Now required (was optional)
}
```

#### 4. Changing Field Types
```json
// Breaking: Changing type
{
  "task_id": 123,      // ← Was string, now integer
  "status": "SUCCESS"
}
```

#### 5. Renaming Fields
```json
// Breaking: Renaming field
{
  "id": "abc-123",     // ← Renamed from "task_id"
  "status": "SUCCESS"
}
```

#### 6. Changing Authentication Mechanism
```
✗ Changing from JWT to OAuth2 without supporting both
```

#### 7. Changing URL Structure
```
✗ Moving from /api/v1/process to /api/v1/tasks/create
```

## Breaking Changes Policy

### Introduction of Breaking Changes

When breaking changes are necessary:

1. **New Version Released**: Create v2 with breaking changes
2. **Parallel Support**: Both v1 and v2 supported simultaneously
3. **Deprecation Notice**: v1 marked as deprecated with end-of-life date
4. **Migration Period**: Minimum 6-12 months for migration
5. **Sunset**: v1 removed after migration period

### Timeline Example

```
Month 0:  v2 released, v1 still supported
Month 1:  v1 marked deprecated
Month 6:  v1 sunset warning (6 months remaining)
Month 9:  v1 sunset warning (3 months remaining)
Month 12: v1 removed (sunset)
```

### Communication Channels

Breaking changes announced via:
1. **API Response Headers**: `X-API-Deprecation` header
2. **Documentation**: Updated versioning page
3. **Email**: Direct notification to registered users
4. **Status Page**: Public announcements
5. **Changelog**: Detailed version history

## Deprecation Policy

### Deprecation Process

1. **Announcement**
   - Feature marked as deprecated in documentation
   - Deprecation header added to responses
   - Minimum 6 months notice before removal

2. **Deprecation Headers**
   ```http
   X-API-Deprecated: true
   X-API-Sunset: 2026-12-31
   X-API-Deprecation-Info: https://docs.example.com/migration
   ```

3. **Migration Guide**
   - Detailed migration instructions published
   - Code examples provided
   - Alternative approaches documented

4. **Support During Transition**
   - Both old and new versions supported
   - Technical support for migration
   - Tools/scripts for migration (if applicable)

### Deprecation Example

**Scenario**: Deprecating a response field

```json
// Current (v1)
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "old_field": "value"  // ← To be removed in v2
}

// Deprecation phase (v1 with warning)
Headers:
X-API-Deprecated-Fields: old_field
X-API-Sunset-Fields: old_field=2026-12-31

Response:
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "old_field": "value",       // ← Still present
  "new_field": "value"        // ← New field available
}

// Future (v2)
{
  "task_id": "abc-123",
  "status": "SUCCESS",
  "new_field": "value"        // ← Only new field
}
```

## Version Migration Guide

### Migrating from v1 to v2 (When Available)

**Note**: v2 is not yet released. This section will be updated when v2 is available.

#### Planned Changes for v2

Potential breaking changes being considered:

1. **Authentication**
   - Add OAuth2 support alongside JWT
   - Longer token expiration options

2. **Response Format**
   - Consistent error format
   - Standardized pagination

3. **Rate Limiting**
   - Per-user limits instead of per-IP
   - Tier-based limits

4. **New Features**
   - Webhook notifications
   - Batch operations
   - Improved filtering

#### Migration Checklist

When v2 is released:

- [ ] Review v2 changelog
- [ ] Test v2 endpoints in development
- [ ] Update client code
- [ ] Update error handling
- [ ] Update tests
- [ ] Deploy to staging
- [ ] Monitor for issues
- [ ] Deploy to production
- [ ] Verify all functionality
- [ ] Remove v1 dependencies

## Changelog

### Version 1.0.0 (2025-12-14)

**Initial Release**

**Features**:
- ✨ User registration and authentication
- ✨ JWT-based authentication with 30-minute expiration
- ✨ Task creation endpoint (`POST /api/v1/process`)
- ✨ Task status tracking (`GET /api/v1/status/{task_id}`)
- ✨ Task result retrieval (`GET /api/v1/result/{task_id}`)
- ✨ Scheduled jobs (cron-based)
- ✨ User activity endpoint
- ✨ Rate limiting (per-IP)
- ✨ Input sanitization (prompt injection protection)
- ✨ Correlation ID support for request tracing
- ✨ Health check endpoints
- ✨ OpenAPI specification

**Technical Stack**:
- FastAPI web framework
- PostgreSQL database
- Redis for caching and rate limiting
- Celery for async task processing
- JWT authentication
- bcrypt password hashing

**Rate Limits**:
- Registration: 5 requests/minute
- Login: 10 requests/minute
- Task creation: 10 requests/minute
- Global: 100 requests/minute

**Security**:
- JWT token authentication
- bcrypt password hashing
- Input sanitization
- Rate limiting
- CORS support

### Version 1.0.1 (Planned - Q1 2026)

**Enhancements**:
- 🚀 Performance optimization for cached parsers
- 🐛 Bug fixes for edge cases in regex generation
- 📝 Documentation improvements
- ⚡ Faster response times for status queries

**No Breaking Changes**

### Version 1.1.0 (Planned - Q2 2026)

**New Features** (Backward Compatible):
- ✨ Webhook notifications for task completion
- ✨ Task filtering and search
- ✨ Export results in multiple formats (JSON, CSV)
- ✨ Batch task creation
- ✨ Task tags and categorization

**No Breaking Changes**

### Version 2.0.0 (Planned - Q4 2026)

**Breaking Changes**:
- 🔧 Per-user rate limiting (instead of per-IP)
- 🔧 Standardized pagination format
- 🔧 Updated error response format
- 🔧 OAuth2 support (JWT still supported)
- 🔧 Renamed some response fields for consistency

**New Features**:
- ✨ Real-time WebSocket support
- ✨ Advanced filtering and querying
- ✨ Custom parser templates
- ✨ Multi-region support
- ✨ API usage analytics

**Migration Period**: 12 months (v1 supported until Q4 2027)

## Version Header

### Checking Current Version

```bash
curl -I https://api.example.com/api/v1/health
```

**Response Headers**:
```http
HTTP/1.1 200 OK
X-API-Version: 1.0.0
X-API-Supported-Versions: v1
```

### Future: Version Negotiation

When multiple versions exist:

```http
Accept-Version: v1
```

**Response**:
```http
X-API-Version: 1.0.0
X-API-Latest-Version: 2.0.0
```

## Best Practices for Version Management

### For API Consumers

1. **Explicit Versioning**
   ```python
   BASE_URL = "https://api.example.com/api/v1"  # ← Explicit version
   ```

2. **Monitor Deprecation Headers**
   ```python
   if 'X-API-Deprecated' in response.headers:
       logger.warning(f"Using deprecated API: {response.headers.get('X-API-Sunset')}")
   ```

3. **Test Before Migrating**
   - Test new version in staging
   - Gradually roll out to production
   - Monitor for issues

4. **Stay Updated**
   - Subscribe to changelog
   - Follow deprecation notices
   - Plan migrations early

### For API Maintainers

1. **Minimize Breaking Changes**
   - Prefer additive changes
   - Use optional fields
   - Support multiple formats

2. **Clear Communication**
   - Document all changes
   - Provide migration guides
   - Give advance notice

3. **Support Overlap**
   - Run multiple versions simultaneously
   - Provide migration tools
   - Offer technical support

## Version Support Matrix

| Version | Release Date | Status | EOL Date | Support Level |
|---------|--------------|--------|----------|---------------|
| v1.0.0  | 2025-12-14  | Stable | 2026-12+ | Full support  |
| v1.0.1  | 2026-Q1     | Planned| TBD      | -             |
| v1.1.0  | 2026-Q2     | Planned| TBD      | -             |
| v2.0.0  | 2026-Q4     | Planned| TBD      | -             |

**Support Levels**:
- **Full Support**: Active development, bug fixes, security updates
- **Maintenance**: Security updates only
- **Deprecated**: No updates, sunset date announced
- **Sunset**: No longer supported

## Contact and Support

For version-related questions:
- **Email**: dadada.marchan@gmail.com
- **Documentation**: [API Reference](./API_REFERENCE.md)
- **Changelog**: This document
- **Migration Help**: Contact support team

## Related Documentation

- [API Reference](./API_REFERENCE.md) - Current endpoint documentation
- [Integration Tutorial](./INTEGRATION_TUTORIAL.md) - Getting started
- [Best Practices](./BEST_PRACTICES.md) - Implementation guidelines
- [Breaking Changes Policy](#breaking-changes-policy) - Change management

---

## TESTING_GUIDE.md

*(Modified: 2025-12-14 18:28:53)*

# API Testing Guide

## Overview

This guide provides comprehensive information on testing the Intelligent Web Data Aggregator API, including contract testing, mock servers, integration testing, and automated testing strategies.

## Table of Contents

- [Testing Strategy](#testing-strategy)
- [Testing Pyramid](#testing-pyramid)
- [Unit Testing](#unit-testing)
- [Integration Testing](#integration-testing)
- [Contract Testing](#contract-testing)
- [Mock Servers](#mock-servers)
- [End-to-End Testing](#end-to-end-testing)
- [Performance Testing](#performance-testing)
- [Security Testing](#security-testing)
- [Test Automation](#test-automation)

## Testing Strategy

### Testing Levels

```
        /\
       /  \    E2E Tests (Few)
      /────\
     /      \  Integration Tests (Some)
    /────────\
   /          \ Unit Tests (Many)
  /────────────\
```

### Test Types

| Test Type | Purpose | Frequency | Scope |
|-----------|---------|-----------|-------|
| Unit | Test individual components | Every commit | Single function/class |
| Integration | Test API interactions | Every build | API client + endpoints |
| Contract | Verify API contracts | Every deployment | Request/response formats |
| E2E | Test full workflows | Nightly | Complete user journeys |
| Performance | Test under load | Weekly | System capacity |
| Security | Test for vulnerabilities | Release | Auth, injection, etc. |

## Testing Pyramid

### 1. Unit Tests (70%)

Test individual API client functions:

```python
import unittest
from unittest.mock import Mock, patch
from your_api_client import WebDataAggregatorClient

class TestAPIClient(unittest.TestCase):
    def setUp(self):
        self.client = WebDataAggregatorClient(
            "http://test", "user", "pass"
        )
    
    @patch('requests.Session.post')
    def test_create_task_success(self, mock_post):
        """Test successful task creation"""
        # Mock response
        mock_response = Mock()
        mock_response.status_code = 202
        mock_response.json.return_value = {
            "task_id": "test-123",
            "status": "PENDING",
            "message": "Task created successfully"
        }
        mock_post.return_value = mock_response
        
        # Execute
        result = self.client.create_task(
            "https://example.com",
            "Extract data"
        )
        
        # Assert
        self.assertEqual(result["task_id"], "test-123")
        self.assertEqual(result["status"], "PENDING")
        
        # Verify request
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        self.assertIn("url", call_args.kwargs["json"])
        self.assertIn("prompt", call_args.kwargs["json"])
    
    @patch('requests.Session.post')
    def test_create_task_authentication_error(self, mock_post):
        """Test authentication error handling"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = \
            requests.exceptions.HTTPError(response=mock_response)
        mock_post.return_value = mock_response
        
        # Execute and assert
        with self.assertRaises(requests.exceptions.HTTPError):
            self.client.create_task("https://example.com", "Extract data")
    
    def test_validate_url_format(self):
        """Test URL validation"""
        # Valid URLs
        valid_urls = [
            "https://example.com",
            "http://example.com/path",
            "https://sub.example.com:8080/path?query=value"
        ]
        
        for url in valid_urls:
            self.assertTrue(self.client._validate_url(url))
        
        # Invalid URLs
        invalid_urls = [
            "not-a-url",
            "ftp://example.com",
            "javascript:alert('xss')"
        ]
        
        for url in invalid_urls:
            self.assertFalse(self.client._validate_url(url))
```

### 2. Integration Tests (20%)

Test actual API interactions:

```python
import pytest
import os
from your_api_client import WebDataAggregatorClient

@pytest.fixture(scope="module")
def api_client():
    """Create API client for integration tests"""
    return WebDataAggregatorClient(
        base_url=os.getenv("TEST_API_URL", "http://localhost:8000"),
        username=os.getenv("TEST_USERNAME", "testuser"),
        password=os.getenv("TEST_PASSWORD", "testpass")
    )

@pytest.fixture(scope="module")
def test_user(api_client):
    """Create test user"""
    try:
        api_client.register("testuser", "testpass", "test@example.com")
    except Exception:
        pass  # User might already exist
    
    yield "testuser"

class TestAuthenticationEndpoints:
    """Test authentication endpoints"""
    
    def test_register_new_user(self, api_client):
        """Test user registration"""
        import uuid
        username = f"testuser_{uuid.uuid4().hex[:8]}"
        
        result = api_client.register(username, "testpass123", "test@example.com")
        
        assert "id" in result
        assert result["username"] == username
        assert result["is_active"] is True
    
    def test_register_duplicate_user(self, api_client, test_user):
        """Test registering duplicate username"""
        with pytest.raises(Exception) as exc_info:
            api_client.register(test_user, "testpass", "test@example.com")
        
        assert "already registered" in str(exc_info.value).lower()
    
    def test_login_success(self, api_client, test_user):
        """Test successful login"""
        token = api_client.login(test_user, "testpass")
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_login_invalid_credentials(self, api_client):
        """Test login with invalid credentials"""
        with pytest.raises(Exception) as exc_info:
            api_client.login("nonexistent", "wrongpass")
        
        assert "incorrect" in str(exc_info.value).lower() or \
               "unauthorized" in str(exc_info.value).lower()

class TestTaskEndpoints:
    """Test task creation and management"""
    
    def test_create_task(self, api_client, test_user):
        """Test task creation"""
        task = api_client.create_task(
            "https://httpbin.org/html",
            "Extract all headings"
        )
        
        assert "task_id" in task
        assert task["status"] == "PENDING"
        assert "message" in task
    
    def test_get_task_status(self, api_client, test_user):
        """Test getting task status"""
        # Create task
        task = api_client.create_task(
            "https://httpbin.org/html",
            "Extract data"
        )
        task_id = task["task_id"]
        
        # Get status
        status = api_client.get_task_status(task_id)
        
        assert status["task_id"] == task_id
        assert status["status"] in ["PENDING", "IN_PROGRESS", "SUCCESS", "FAILED"]
        assert "created_at" in status
        assert "updated_at" in status
    
    def test_get_nonexistent_task(self, api_client, test_user):
        """Test getting status of non-existent task"""
        with pytest.raises(Exception) as exc_info:
            api_client.get_task_status("nonexistent-task-id")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_task_result_after_completion(self, api_client, test_user):
        """Test getting result after task completes"""
        # Create task
        task = api_client.create_task(
            "https://httpbin.org/html",
            "Extract headings"
        )
        task_id = task["task_id"]
        
        # Wait for completion (with timeout)
        import time
        max_wait = 60
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            status = api_client.get_task_status(task_id)
            if status["status"] in ["SUCCESS", "FAILED"]:
                break
            time.sleep(5)
        
        # Get result
        if status["status"] == "SUCCESS":
            result = api_client.get_task_result(task_id)
            
            assert result["task_id"] == task_id
            assert result["status"] == "SUCCESS"
            assert "data" in result
            assert isinstance(result["data"], list)

class TestSchedulerEndpoints:
    """Test scheduled job endpoints"""
    
    def test_create_scheduled_job(self, api_client, test_user):
        """Test creating scheduled job"""
        job = api_client.create_scheduled_job(
            url="https://example.com",
            prompt="Extract data",
            cron="0 9 * * *"
        )
        
        assert "id" in job
        assert job["url"] == "https://example.com"
        assert job["schedule_cron"] == "0 9 * * *"
    
    def test_list_scheduled_jobs(self, api_client, test_user):
        """Test listing scheduled jobs"""
        jobs = api_client.list_scheduled_jobs()
        
        assert isinstance(jobs, list)
    
    def test_delete_scheduled_job(self, api_client, test_user):
        """Test deleting scheduled job"""
        # Create job
        job = api_client.create_scheduled_job(
            "https://example.com", "Extract data", "0 9 * * *"
        )
        job_id = job["id"]
        
        # Delete job
        api_client.delete_scheduled_job(job_id)
        
        # Verify deletion
        jobs = api_client.list_scheduled_jobs()
        job_ids = [j["id"] for j in jobs]
        assert job_id not in job_ids
```

### 3. End-to-End Tests (10%)

Test complete workflows:

```python
class TestCompleteWorkflow:
    """Test complete user workflows"""
    
    def test_full_scraping_workflow(self, api_client):
        """Test complete scraping workflow"""
        # Step 1: Register user
        import uuid
        username = f"e2e_user_{uuid.uuid4().hex[:8]}"
        user = api_client.register(username, "testpass123")
        assert user["username"] == username
        
        # Step 2: Login
        token = api_client.login(username, "testpass123")
        assert token is not None
        
        # Step 3: Create task
        task = api_client.create_task(
            "https://httpbin.org/html",
            "Extract all headings"
        )
        task_id = task["task_id"]
        
        # Step 4: Monitor task
        import time
        status = None
        for _ in range(12):  # Max 1 minute
            status = api_client.get_task_status(task_id)
            if status["status"] in ["SUCCESS", "FAILED"]:
                break
            time.sleep(5)
        
        # Step 5: Get result
        if status["status"] == "SUCCESS":
            result = api_client.get_task_result(task_id)
            assert "data" in result
            assert len(result["data"]) > 0
        
        # Step 6: Create scheduled job
        job = api_client.create_scheduled_job(
            "https://example.com",
            "Daily extraction",
            "0 9 * * *"
        )
        assert job["id"] is not None
        
        # Step 7: Clean up
        api_client.delete_scheduled_job(job["id"])
```

## Contract Testing

### Using Pact

Contract testing ensures API client and server stay compatible:

```python
import pytest
from pact import Consumer, Provider, Format

@pytest.fixture(scope='module')
def pact():
    """Setup Pact consumer"""
    pact = Consumer('APIClient').has_pact_with(
        Provider('APIServer'),
        pact_dir='pacts'
    )
    pact.start_service()
    yield pact
    pact.stop_service()

def test_create_task_contract(pact):
    """Test task creation contract"""
    # Define expected interaction
    (pact
     .given('user is authenticated')
     .upon_receiving('a request to create a task')
     .with_request(
         method='POST',
         path='/api/v1/process',
         headers={'Authorization': Format().regex('Bearer .+', 'Bearer token')},
         body={
             'url': Format().url('https://example.com'),
             'prompt': Format().string('Extract data')
         }
     )
     .will_respond_with(
         status=202,
         headers={'Content-Type': 'application/json'},
         body={
             'task_id': Format().uuid(),
             'status': 'PENDING',
             'message': Format().string('Task created successfully')
         }
     ))
    
    # Execute test
    with pact:
        client = WebDataAggregatorClient(pact.uri, 'user', 'pass')
        result = client.create_task('https://example.com', 'Extract data')
        
        assert 'task_id' in result
        assert result['status'] == 'PENDING'
```

### OpenAPI Validation

Validate requests and responses against OpenAPI spec:

```python
from openapi_core import create_spec
from openapi_core.validation.request import openapi_request_validator
from openapi_core.validation.response import openapi_response_validator
import yaml

# Load OpenAPI spec
with open('openapi.json') as f:
    spec_dict = json.load(f)
spec = create_spec(spec_dict)

def test_request_matches_openapi(api_client):
    """Test that request matches OpenAPI spec"""
    # Create request
    request = api_client._prepare_request(
        'POST',
        '/api/v1/process',
        json={'url': 'https://example.com', 'prompt': 'Extract data'}
    )
    
    # Validate against spec
    result = openapi_request_validator.validate(spec, request)
    assert not result.errors

def test_response_matches_openapi(api_client):
    """Test that response matches OpenAPI spec"""
    response = api_client.create_task('https://example.com', 'Extract data')
    
    # Validate against spec
    result = openapi_response_validator.validate(spec, response)
    assert not result.errors
```

## Mock Servers

### Using responses Library

Mock API responses for testing:

```python
import responses
import requests

@responses.activate
def test_with_mocked_api():
    """Test with mocked API responses"""
    # Mock registration
    responses.add(
        responses.POST,
        'http://localhost:8000/auth/register',
        json={
            'id': 1,
            'username': 'testuser',
            'email': 'test@example.com',
            'is_active': True
        },
        status=200
    )
    
    # Mock login
    responses.add(
        responses.POST,
        'http://localhost:8000/auth/token',
        json={
            'access_token': 'mock-token-123',
            'token_type': 'bearer'
        },
        status=200
    )
    
    # Mock task creation
    responses.add(
        responses.POST,
        'http://localhost:8000/api/v1/process',
        json={
            'task_id': 'mock-task-123',
            'status': 'PENDING',
            'message': 'Task created successfully'
        },
        status=202
    )
    
    # Test client with mocked responses
    client = WebDataAggregatorClient('http://localhost:8000', 'user', 'pass')
    task = client.create_task('https://example.com', 'Extract data')
    
    assert task['task_id'] == 'mock-task-123'
```

### Using Prism (OpenAPI Mock Server)

```bash
# Install Prism
npm install -g @stoplight/prism-cli

# Start mock server from OpenAPI spec
prism mock openapi.json --port 8080

# Test against mock server
curl http://localhost:8080/api/v1/process \
  -H "Authorization: Bearer mock-token" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","prompt":"Extract data"}'
```

**Python test with Prism**:
```python
def test_with_prism_mock():
    """Test with Prism mock server"""
    # Assumes Prism is running on port 8080
    client = WebDataAggregatorClient(
        'http://localhost:8080',
        'mock-user',
        'mock-pass'
    )
    
    task = client.create_task('https://example.com', 'Extract data')
    assert 'task_id' in task
```

## Performance Testing

### Using Locust

```python
from locust import HttpUser, task, between

class APIUser(HttpUser):
    """Simulated API user"""
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login when user starts"""
        response = self.client.post('/auth/token', data={
            'username': 'testuser',
            'password': 'testpass'
        })
        self.token = response.json()['access_token']
    
    @task(3)
    def create_task(self):
        """Create task (3x weight)"""
        self.client.post(
            '/api/v1/process',
            headers={'Authorization': f'Bearer {self.token}'},
            json={
                'url': 'https://example.com',
                'prompt': 'Extract data'
            }
        )
    
    @task(2)
    def check_status(self):
        """Check task status (2x weight)"""
        self.client.get(
            f'/api/v1/status/mock-task-id',
            headers={'Authorization': f'Bearer {self.token}'}
        )
    
    @task(1)
    def list_jobs(self):
        """List scheduled jobs (1x weight)"""
        self.client.get(
            '/api/v1/jobs',
            headers={'Authorization': f'Bearer {self.token}'}
        )

# Run: locust -f performance_test.py --host=http://localhost:8000
```

### Load Testing Metrics

```python
import time
import statistics
from concurrent.futures import ThreadPoolExecutor

def performance_test(num_requests: int = 100):
    """Simple performance test"""
    response_times = []
    errors = 0
    
    def make_request():
        start = time.time()
        try:
            response = client.create_task('https://example.com', 'Extract data')
            response_times.append(time.time() - start)
        except Exception:
            nonlocal errors
            errors += 1
    
    # Execute requests in parallel
    with ThreadPoolExecutor(max_workers=10) as executor:
        executor.map(lambda _: make_request(), range(num_requests))
    
    # Calculate metrics
    if response_times:
        print(f"Requests: {num_requests}")
        print(f"Errors: {errors}")
        print(f"Success Rate: {(1 - errors/num_requests) * 100:.2f}%")
        print(f"Average Response Time: {statistics.mean(response_times):.3f}s")
        print(f"Median Response Time: {statistics.median(response_times):.3f}s")
        print(f"95th Percentile: {statistics.quantiles(response_times, n=20)[18]:.3f}s")
        print(f"99th Percentile: {statistics.quantiles(response_times, n=100)[98]:.3f}s")
```

## Security Testing

### Authentication Testing

```python
class TestSecurityAuthentication:
    """Test authentication security"""
    
    def test_protected_endpoint_requires_auth(self):
        """Test endpoint requires authentication"""
        response = requests.post(
            'http://localhost:8000/api/v1/process',
            json={'url': 'https://example.com', 'prompt': 'Extract data'}
        )
        
        assert response.status_code == 401
    
    def test_invalid_token_rejected(self):
        """Test invalid token is rejected"""
        response = requests.post(
            'http://localhost:8000/api/v1/process',
            headers={'Authorization': 'Bearer invalid-token'},
            json={'url': 'https://example.com', 'prompt': 'Extract data'}
        )
        
        assert response.status_code == 401
    
    def test_expired_token_rejected(self):
        """Test expired token is rejected"""
        # Create token that expires immediately
        old_token = create_expired_token()
        
        response = requests.post(
            'http://localhost:8000/api/v1/process',
            headers={'Authorization': f'Bearer {old_token}'},
            json={'url': 'https://example.com', 'prompt': 'Extract data'}
        )
        
        assert response.status_code == 401

### Input Validation Testing

```python
class TestSecurityInputValidation:
    """Test input validation"""
    
    def test_prompt_injection_blocked(self):
        """Test prompt injection is blocked"""
        malicious_prompts = [
            "<script>alert('xss')</script>",
            "javascript:alert('xss')",
            "; DROP TABLE users;--"
        ]
        
        for prompt in malicious_prompts:
            with pytest.raises(Exception):
                client.create_task('https://example.com', prompt)
    
    def test_url_validation(self):
        """Test URL validation"""
        invalid_urls = [
            "javascript:alert('xss')",
            "file:///etc/passwd",
            "data:text/html,<script>alert('xss')</script>"
        ]
        
        for url in invalid_urls:
            with pytest.raises(Exception):
                client.create_task(url, 'Extract data')
```

## Test Automation

### CI/CD Integration

**GitHub Actions**:
```yaml
# .github/workflows/test.yml
name: API Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: testpass
          POSTGRES_DB: testdb
      redis:
        image: redis:7-alpine
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        env:
          TEST_API_URL: http://localhost:8000
          DATABASE_URL: postgresql://postgres:testpass@localhost/testdb
          REDIS_URL: redis://localhost:6379/0
        run: |
          pytest tests/ --cov=. --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Test Reporting

```python
# conftest.py - pytest configuration
import pytest
import json
from datetime import datetime

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Generate detailed test reports"""
    outcome = yield
    report = outcome.get_result()
    
    if report.when == 'call':
        # Log test result
        result = {
            'test': item.nodeid,
            'outcome': report.outcome,
            'duration': report.duration,
            'timestamp': datetime.now().isoformat()
        }
        
        # Save to file
        with open('test_results.json', 'a') as f:
            f.write(json.dumps(result) + '\n')
```

## Best Practices

1. **Test Isolation**: Each test should be independent
2. **Test Data**: Use fixtures for test data
3. **Cleanup**: Clean up test data after tests
4. **Assertions**: Use clear, specific assertions
5. **Documentation**: Document test purpose and setup
6. **Coverage**: Aim for 80%+ code coverage
7. **Fast Tests**: Keep tests fast and focused
8. **CI/CD**: Automate test execution

## Related Documentation

- [API Reference](./API_REFERENCE.md) - Endpoint documentation
- [Best Practices](./BEST_PRACTICES.md) - Implementation guidelines
- [Integration Tutorial](./INTEGRATION_TUTORIAL.md) - Getting started
- [Error Handling](./ERROR_HANDLING.md) - Error handling guide

---

## DOCUMENTATION_STRATEGY.md

*(Modified: 2025-12-14 18:28:53)*

# Documentation Strategy

## Overview

This document describes the comprehensive documentation strategy for the Intelligent Web Data Aggregator API, including the tools, standards, methodologies, and processes used to create, maintain, and deliver high-quality API documentation.

## Table of Contents

- [Documentation Philosophy](#documentation-philosophy)
- [Documentation Architecture](#documentation-architecture)
- [Tools and Technologies](#tools-and-technologies)
- [Standards and Conventions](#standards-and-conventions)
- [Documentation Types](#documentation-types)
- [Maintenance and Updates](#maintenance-and-updates)
- [Quality Assurance](#quality-assurance)
- [Known Gaps and Limitations](#known-gaps-and-limitations)
- [Future Improvements](#future-improvements)

## Documentation Philosophy

### Core Principles

1. **Developer-First**: Documentation designed for developers, by developers
2. **Completeness**: Cover all features, edge cases, and error scenarios
3. **Accuracy**: Keep documentation in sync with implementation
4. **Accessibility**: Multiple formats for different learning styles
5. **Maintainability**: Easy to update and version
6. **Searchability**: Well-organized with clear navigation

### Documentation Goals

- **Reduce time-to-first-request**: Get developers productive quickly
- **Minimize support requests**: Answer questions proactively
- **Improve API adoption**: Clear value proposition and examples
- **Enable self-service**: Comprehensive troubleshooting guides
- **Support multiple use cases**: From simple to advanced scenarios

## Documentation Architecture

### Information Architecture

```
docs_old/api-docs/
├── README.md                      # Documentation hub & navigation
├── GETTING_STARTED.md             # Quick start guide
├── API_REFERENCE.md               # Complete endpoint reference
├── INTEGRATION_TUTORIAL.md        # Step-by-step integration
├── AUTHENTICATION_GUIDE.md        # Auth details & security
├── ERROR_HANDLING.md              # Error codes & recovery
├── RATE_LIMITING.md               # Rate limit policies
├── DATA_MODELS.md                 # Request/response schemas
├── BEST_PRACTICES.md              # Usage patterns & guidelines
├── VERSIONING.md                  # Version management
├── ADVANCED_TOPICS.md             # Pagination, idempotency, etc.
├── TESTING_GUIDE.md               # Testing strategies
├── DOCUMENTATION_STRATEGY.md      # This document
├── ARCHITECTURE_OVERVIEW.md       # System architecture
└── ../openapi.json                # OpenAPI specification
```

### Documentation Layers

```
┌─────────────────────────────────────────────────────┐
│           Quick Start (Getting Started)             │
│  Goal: First successful API call in 5 minutes       │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│          Tutorial (Integration Tutorial)            │
│  Goal: Complete integration with working code       │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│         Reference (API Reference, Data Models)      │
│  Goal: Complete technical specification             │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│    Advanced (Best Practices, Advanced Topics)       │
│  Goal: Optimization and advanced patterns           │
└─────────────────────────────────────────────────────┘
```

## Tools and Technologies

### Documentation Generation

#### 1. FastAPI Auto-Documentation

**Tool**: FastAPI built-in OpenAPI generation

**Benefits**:
- Automatic OpenAPI spec generation from code
- Interactive Swagger UI (`/docs`)
- Alternative ReDoc UI (`/redoc`)
- Always in sync with implementation

**Configuration**:
```python
app = FastAPI(
    title="Intelligent Web Data Aggregator",
    description="API description...",
    version="1.0.0",
    openapi_tags=tags_metadata,
    contact={...},
    license_info={...}
)
```

**Endpoints**:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

#### 2. Markdown Documentation

**Tool**: GitHub-flavored Markdown

**Benefits**:
- Version-controlled alongside code
- Easy to read in raw form
- Renders well on GitHub, GitLab, etc.
- Supports code blocks, tables, and links

**Format Standards**:
```markdown
# Document Title

## Section
Description

### Subsection
Content with **bold** and *italic*

```python
# Code example
def example():
    pass
\```

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |
```

#### 3. Pydantic Models

**Tool**: Pydantic for schema validation and documentation

**Benefits**:
- Automatic validation
- Type safety
- Auto-generated JSON schemas
- OpenAPI integration

**Example**:
```python
from pydantic import BaseModel, Field

class ScrapeRequest(BaseModel):
    url: HttpUrl = Field(..., description="Target website URL")
    prompt: str = Field(
        ...,
        min_length=5,
        max_length=1000,
        description="Natural language extraction instruction"
    )
```

### Documentation Hosting

#### Current: File-Based

**Location**: `docs_old/api-docs/` directory

**Access**: Via repository (GitHub/GitLab)

**Benefits**:
- Simple and maintainable
- Version-controlled
- No additional infrastructure

#### Future: Documentation Portal

**Planned Tools**:
- **Docusaurus**: React-based documentation framework
- **GitBook**: Collaborative documentation platform
- **ReadTheDocs**: Automated documentation hosting

**Features**:
- Search functionality
- Version switching
- Dark mode
- Mobile-responsive
- Analytics

### Schema Validation

#### OpenAPI/Swagger Validation

**Tools**:
- **Swagger Editor**: Online OpenAPI editor with validation
- **Spectral**: OpenAPI linting tool
- **Redocly CLI**: OpenAPI validation and bundling

**Validation Example**:
```bash
# Install Spectral
npm install -g @stoplight/spectral-cli

# Validate OpenAPI spec
spectral lint docs_old/openapi.json

# Check for breaking changes
spectral lint --ruleset breaking-changes.yaml docs_old/openapi.json
```

**Spectral Ruleset** (`.spectral.yaml`):
```yaml
extends: spectral:oas
rules:
  operation-description: error
  operation-tags: error
  operation-operationId: error
  no-$ref-siblings: error
  oas3-schema: error
```

## Standards and Conventions

### Naming Conventions

#### Endpoints

- **URL Pattern**: `/api/v{version}/{resource}`
- **HTTP Methods**: Standard REST verbs (GET, POST, DELETE)
- **Plural Resources**: `/jobs`, `/tasks`, `/users`

**Examples**:
```
✓ POST /api/v1/process
✓ GET /api/v1/status/{task_id}
✓ GET /api/v1/jobs
✗ GET /api/v1/getStatus
✗ POST /api/v1/create-task
```

#### Fields

- **snake_case**: For JSON fields (`task_id`, `created_at`)
- **camelCase**: Avoided in favor of snake_case
- **Consistency**: Same field names across all endpoints

#### HTTP Status Codes

**Standard Usage**:
- `200 OK`: Successful GET/PUT/DELETE
- `202 Accepted`: Async operation accepted
- `400 Bad Request`: Client error (validation, etc.)
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `422 Unprocessable Entity`: Validation error
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

### Documentation Formatting

#### Code Examples

**Multi-Language Support**:
```markdown
**cURL**:
\```bash
curl -X POST "http://localhost:8000/api/v1/process"
\```

**Python**:
\```python
import requests
response = requests.post(...)
\```

**JavaScript**:
\```javascript
const response = await fetch(...);
\```
```

#### Response Examples

**Format**:
```markdown
**Success Response** (200 OK):
\```json
{
  "task_id": "abc-123",
  "status": "SUCCESS"
}
\```

**Error Response** (400 Bad Request):
\```json
{
  "error": "Bad Request",
  "message": "Invalid URL format",
  "timestamp": "2025-12-14T10:30:00Z"
}
\```
```

### Versioning

**Documentation Versions**:
- Each API version has its own documentation
- Breaking changes documented in VERSIONING.md
- Migration guides for major version changes

**File Organization**:
```
docs/
├── api-docs/           # v1 documentation
│   ├── README.md
│   ├── API_REFERENCE.md
│   └── ...
└── api-docs-v2/        # v2 documentation (future)
    ├── README.md
    └── ...
```

## Documentation Types

### 1. Reference Documentation

**Purpose**: Complete technical specification

**Includes**:
- All endpoints with parameters
- Request/response schemas
- HTTP status codes
- Authentication requirements
- Rate limits

**Audience**: Experienced developers needing details

**Examples**: API_REFERENCE.md, DATA_MODELS.md

### 2. Tutorial Documentation

**Purpose**: Step-by-step learning

**Includes**:
- Prerequisites
- Setup instructions
- Working code examples
- Common patterns
- Troubleshooting

**Audience**: New users getting started

**Examples**: GETTING_STARTED.md, INTEGRATION_TUTORIAL.md

### 3. Conceptual Documentation

**Purpose**: Explain how things work

**Includes**:
- Architecture overview
- Design decisions
- System diagrams
- Data flows

**Audience**: Architects and system designers

**Examples**: ARCHITECTURE_OVERVIEW.md

### 4. Procedural Documentation

**Purpose**: How to accomplish specific tasks

**Includes**:
- Authentication setup
- Error handling
- Rate limiting strategies
- Testing approaches

**Audience**: Developers implementing features

**Examples**: AUTHENTICATION_GUIDE.md, ERROR_HANDLING.md

### 5. Best Practices

**Purpose**: Recommended patterns and anti-patterns

**Includes**:
- Code organization
- Security practices
- Performance optimization
- Production considerations

**Audience**: Professional developers

**Examples**: BEST_PRACTICES.md

## Maintenance and Updates

### Update Process

1. **Code Change**: Feature or fix implemented
2. **Documentation Update**: Update relevant docs
3. **Review**: Technical writer or peer review
4. **Testing**: Verify examples still work
5. **Publish**: Commit to repository

### Update Triggers

**Automatic Updates**:
- OpenAPI spec regenerated on code changes
- Version numbers updated automatically
- Generated examples from tests

**Manual Updates**:
- New features
- Breaking changes
- Deprecations
- Tutorials and guides

### Change Management

**Change Log**:
- Document all API changes in VERSIONING.md
- Include version, date, and description
- Link to migration guides for breaking changes

**Deprecation Process**:
1. Mark feature as deprecated in docs
2. Add deprecation warnings to API responses
3. Provide migration guide
4. Remove in next major version

## Quality Assurance

### Documentation Review Checklist

**Accuracy**:
- [ ] Examples are tested and working
- [ ] Status codes match implementation
- [ ] Field names match API responses
- [ ] Type definitions are correct

**Completeness**:
- [ ] All endpoints documented
- [ ] All parameters described
- [ ] Error scenarios covered
- [ ] Examples for common use cases

**Clarity**:
- [ ] Clear, concise language
- [ ] No jargon without explanation
- [ ] Logical organization
- [ ] Good navigation

**Consistency**:
- [ ] Formatting is consistent
- [ ] Naming conventions followed
- [ ] Style guide adhered to
- [ ] Cross-references working

### Automated Testing

**Documentation Tests**:
```python
def test_documentation_examples():
    """Test that documentation examples work"""
    # Test example from GETTING_STARTED.md
    task = client.create_task(
        url="https://example.com",
        prompt="Extract all headings"
    )
    assert "task_id" in task
    
    # Test example from API_REFERENCE.md
    status = client.get_task_status(task["task_id"])
    assert "status" in status
```

**Link Validation**:
```bash
# Check for broken links
markdown-link-check docs_old/api-docs/*.md
```

**OpenAPI Validation**:
```bash
# Validate OpenAPI spec
spectral lint docs_old/openapi.json

# Check for breaking changes
openapi-diff docs/openapi-v1.json docs/openapi-v2.json
```

## Known Gaps and Limitations

### Current Limitations

1. **No Interactive Examples**: Documentation doesn't include runnable code playground
2. **Limited Diagrams**: Some complex flows could benefit from more visual diagrams
3. **No Video Tutorials**: No video content for visual learners
4. **Language Coverage**: Examples primarily in Python; limited JavaScript/Java/Go examples
5. **Search**: No full-text search across documentation (GitHub search only)
6. **Versioning**: Only v1 documented; no version switcher
7. **Offline Access**: No downloadable PDF/ePub versions
8. **Localization**: Documentation only in English

### Documentation Debt

**Areas Needing Improvement**:
1. More real-world use case examples
2. Performance tuning guide
3. Troubleshooting flowcharts
4. Architecture decision records (ADRs)
5. API design rationale documentation
6. Historical changelog (pre-v1.0.0)

## Future Improvements

### Short-Term (Q1 2026)

1. **Interactive Playground**
   - Embed Swagger UI in documentation site
   - Add "Try it" buttons to examples
   - Mock data for safe experimentation

2. **Enhanced Examples**
   - More language examples (JavaScript, Go, Java)
   - Real-world integration scenarios
   - Common error handling patterns

3. **Visual Content**
   - Sequence diagrams for complex flows
   - Infographics for rate limiting
   - Architecture diagrams

### Medium-Term (Q2-Q3 2026)

1. **Documentation Portal**
   - Deploy Docusaurus site
   - Full-text search
   - Version switcher
   - Dark mode

2. **Video Tutorials**
   - Getting started video
   - Common integration patterns
   - Troubleshooting guides

3. **SDK Documentation**
   - Official Python SDK with docs
   - JavaScript/TypeScript SDK
   - Auto-generated from OpenAPI

### Long-Term (Q4 2026+)

1. **Community Contributions**
   - Community examples repository
   - Integration showcases
   - User-contributed guides

2. **Localization**
   - Chinese documentation
   - Spanish documentation
   - Other major languages

3. **AI-Assisted Documentation**
   - Chatbot for documentation Q&A
   - Personalized tutorials
   - Code generation from docs

## Metrics and Success Criteria

### Documentation Quality Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Endpoint coverage | 100% | 100% ✓ |
| Example coverage | 100% | 100% ✓ |
| Error scenario coverage | 90%+ | 95% ✓ |
| Broken links | 0 | 0 ✓ |
| OpenAPI validation | Pass | Pass ✓ |
| User satisfaction | 4.5/5 | N/A |

### Usage Metrics (Future)

- Documentation page views
- Time to first API call
- Search queries and results
- Support ticket reduction
- Community contributions

## Conclusion

This documentation strategy provides a comprehensive foundation for maintaining high-quality API documentation. It follows industry best practices while being tailored to the specific needs of the Intelligent Web Data Aggregator API.

The strategy emphasizes:
- **Developer experience**: Making it easy to get started and succeed
- **Completeness**: Covering all aspects from basics to advanced topics
- **Accuracy**: Keeping documentation in sync with implementation
- **Maintainability**: Sustainable processes for long-term maintenance

As the API evolves, this strategy will be updated to reflect new tools, standards, and best practices.

## Related Documentation

- [API Reference](./API_REFERENCE.md) - Complete endpoint documentation
- [Getting Started](./GETTING_STARTED.md) - Quick start guide
- [Versioning](./VERSIONING.md) - Version management
- [Best Practices](./BEST_PRACTICES.md) - Usage guidelines

## Contact

For documentation feedback or contributions:
- **Email**: dadada.marchan@gmail.com
- **Repository**: Submit pull requests for documentation improvements
- **Issues**: Report documentation bugs or gaps

---

## ADVANCED_TOPICS.md

*(Modified: 2025-12-14 18:43:29)*

# Advanced Topics

## Overview

This guide covers advanced API usage patterns, including pagination strategies, idempotency, complex request flows, and advanced integration scenarios.

## Table of Contents

- [Pagination](#pagination)
- [Idempotency](#idempotency)
- [Complex Request Flows](#complex-request-flows)
- [WebHooks (Future)](#webhooks-future)
- [Batch Processing](#batch-processing)
- [Data Export and Integration](#data-export-and-integration)
- [Advanced Scheduling](#advanced-scheduling)
- [Performance Tuning](#performance-tuning)
- [Multi-Tenancy Considerations](#multi-tenancy-considerations)

## Pagination

### Current Implementation

**Note**: The current API version (v1.0.0) does not implement pagination. All list endpoints return complete results.

**Affected Endpoints**:
- `GET /api/v1/jobs` - Returns all scheduled jobs
- `GET /api/v1/users/me/activity` - Returns all tasks and jobs

### Future Pagination Support

**Planned for v1.1.0**: Standard pagination with limit/offset or cursor-based pagination.

#### Offset-Based Pagination (Planned)

```http
GET /api/v1/jobs?limit=10&offset=20 HTTP/1.1
```

**Response**:
```json
{
  "data": [...],
  "pagination": {
    "limit": 10,
    "offset": 20,
    "total": 50,
    "has_next": true,
    "has_previous": true
  }
}
```

#### Cursor-Based Pagination (Planned)

Better for large datasets with frequent updates:

```http
GET /api/v1/jobs?limit=10&cursor=eyJpZCI6MTIzfQ== HTTP/1.1
```

**Response**:
```json
{
  "data": [...],
  "pagination": {
    "next_cursor": "eyJpZCI6MTMzfQ==",
    "has_more": true
  }
}
```

### Client-Side Pagination Workaround

Until native pagination is available:

```python
def paginate_locally(items: list, page: int, page_size: int):
    """Client-side pagination"""
    start = (page - 1) * page_size
    end = start + page_size
    
    return {
        "data": items[start:end],
        "page": page,
        "page_size": page_size,
        "total": len(items),
        "total_pages": (len(items) + page_size - 1) // page_size
    }

# Usage
jobs = client.list_scheduled_jobs()  # Gets all jobs
page_1 = paginate_locally(jobs, page=1, page_size=10)
```

## Idempotency

### What is Idempotency?

Idempotency ensures that performing the same operation multiple times has the same effect as performing it once. This is crucial for reliable systems.

### Current Limitations

**v1.0.0 does not support idempotency keys**. Multiple identical requests will create duplicate tasks:

```python
# These will create TWO separate tasks
task1 = create_task("https://example.com", "Extract data")
task2 = create_task("https://example.com", "Extract data")

# task1["task_id"] != task2["task_id"]
```

### Planned Idempotency Support (v1.1.0)

Future support for idempotency keys:

```http
POST /api/v1/process HTTP/1.1
Authorization: Bearer <token>
Idempotency-Key: unique-key-12345
Content-Type: application/json

{
  "url": "https://example.com",
  "prompt": "Extract data"
}
```

**Behavior**:
- First request: Creates task, returns task_id
- Duplicate requests (within 24 hours): Returns same task_id
- After 24 hours: Creates new task

### Client-Side Idempotency Workaround

Implement idempotency tracking on the client:

```python
import hashlib
import json
from typing import Dict, Optional

class IdempotentClient:
    def __init__(self, client):
        self.client = client
        self.idempotency_cache: Dict[str, str] = {}
    
    def _generate_key(self, url: str, prompt: str) -> str:
        """Generate idempotency key from request"""
        content = json.dumps({"url": url, "prompt": prompt}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()
    
    def create_task_idempotent(
        self,
        url: str,
        prompt: str,
        force_new: bool = False
    ) -> dict:
        """Create task with client-side idempotency"""
        key = self._generate_key(url, prompt)
        
        # Check cache
        if not force_new and key in self.idempotency_cache:
            task_id = self.idempotency_cache[key]
            print(f"Using cached task: {task_id}")
            return self.client.get_task_status(task_id)
        
        # Create new task
        result = self.client.create_task(url, prompt)
        
        # Cache task ID
        self.idempotency_cache[key] = result["task_id"]
        
        return result

# Usage
idempotent_client = IdempotentClient(client)

# These will use the same task
task1 = idempotent_client.create_task_idempotent(
    "https://example.com", "Extract data"
)
task2 = idempotent_client.create_task_idempotent(
    "https://example.com", "Extract data"
)

assert task1["task_id"] == task2["task_id"]
```

## Complex Request Flows

### Sequential Task Processing

Process multiple URLs in sequence:

```python
def process_urls_sequentially(urls: list, prompt: str) -> list:
    """Process multiple URLs one after another"""
    results = []
    
    for url in urls:
        # Create task
        task = client.create_task(url, prompt)
        task_id = task["task_id"]
        
        # Wait for completion
        while True:
            status = client.get_task_status(task_id)
            if status["status"] in ["SUCCESS", "FAILED"]:
                break
            time.sleep(5)
        
        # Get result
        if status["status"] == "SUCCESS":
            result = client.get_task_result(task_id)
            results.append(result)
        else:
            results.append({"error": "Task failed", "task_id": task_id})
    
    return results
```

### Parallel Task Processing

Process multiple URLs concurrently:

```python
import concurrent.futures
from typing import List, Dict

def process_urls_parallel(
    urls: List[str],
    prompt: str,
    max_workers: int = 5
) -> List[Dict]:
    """Process multiple URLs in parallel"""
    
    def process_single_url(url: str) -> Dict:
        """Process a single URL"""
        try:
            # Create task
            task = client.create_task(url, prompt)
            task_id = task["task_id"]
            
            # Wait for completion
            result = wait_for_task_completion(task_id)
            
            if result["status"] == "SUCCESS":
                return client.get_task_result(task_id)
            else:
                return {"error": "Task failed", "task_id": task_id}
        
        except Exception as e:
            return {"error": str(e), "url": url}
    
    # Process URLs in parallel
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_single_url, urls))
    
    return results

# Usage
urls = [
    "https://example1.com",
    "https://example2.com",
    "https://example3.com"
]

results = process_urls_parallel(urls, "Extract headlines", max_workers=3)
```

### Conditional Processing

Process based on previous results:

```python
def conditional_processing(url: str, prompts: list) -> dict:
    """
    Execute prompts conditionally based on previous results.
    
    Example: Extract headlines, then extract details for each headline.
    """
    results = {}
    
    # Step 1: Extract headlines
    headlines_task = client.create_task(url, prompts[0])
    headlines_result = wait_for_task_completion(headlines_task["task_id"])
    results["headlines"] = headlines_result
    
    # Step 2: For each headline, extract details
    if headlines_result["status"] == "SUCCESS":
        details = []
        for item in headlines_result["data"]:
            # Create task for each headline
            detail_prompt = f"Extract details for: {item['text']}"
            detail_task = client.create_task(url, detail_prompt)
            detail_result = wait_for_task_completion(detail_task["task_id"])
            details.append(detail_result)
        
        results["details"] = details
    
    return results
```

### Pipeline Processing

Chain multiple processing steps:

```python
from typing import Callable, List, Any

class ProcessingPipeline:
    """Pipeline for multi-stage data processing"""
    
    def __init__(self, client):
        self.client = client
        self.stages: List[Callable] = []
    
    def add_stage(self, func: Callable) -> 'ProcessingPipeline':
        """Add processing stage"""
        self.stages.append(func)
        return self
    
    def execute(self, initial_data: Any) -> Any:
        """Execute pipeline"""
        data = initial_data
        
        for i, stage in enumerate(self.stages):
            print(f"Executing stage {i+1}/{len(self.stages)}")
            data = stage(data)
        
        return data

# Usage
def stage1_extract_urls(source_url: str) -> List[str]:
    """Stage 1: Extract URLs from source page"""
    task = client.create_task(source_url, "Extract all article URLs")
    result = wait_for_task_completion(task["task_id"])
    return [item["text"] for item in result["data"]]

def stage2_extract_content(urls: List[str]) -> List[Dict]:
    """Stage 2: Extract content from each URL"""
    return process_urls_parallel(urls, "Extract article title and content")

def stage3_summarize(articles: List[Dict]) -> List[Dict]:
    """Stage 3: Summarize each article"""
    summaries = []
    for article in articles:
        # Process with AI or external service
        summary = {"title": article.get("title"), "summary": "..."}
        summaries.append(summary)
    return summaries

# Execute pipeline
pipeline = ProcessingPipeline(client)
results = (pipeline
    .add_stage(stage1_extract_urls)
    .add_stage(stage2_extract_content)
    .add_stage(stage3_summarize)
    .execute("https://news-site.com"))
```

## WebHooks (Future)

### Planned WebHook Support (v2.0.0)

Instead of polling for task completion, receive notifications:

```http
POST /api/v2/webhooks HTTP/1.1
Authorization: Bearer <token>
Content-Type: application/json

{
  "url": "https://your-server.com/webhook",
  "events": ["task.completed", "task.failed"],
  "secret": "your-webhook-secret"
}
```

**WebHook Payload**:
```json
{
  "event": "task.completed",
  "task_id": "abc-123",
  "status": "SUCCESS",
  "timestamp": "2025-12-14T10:30:00Z",
  "signature": "sha256=..."
}
```

### Current Workaround: Long Polling

```python
def long_poll_task(task_id: str, callback: Callable, check_interval: int = 5):
    """Poll task status and call callback when complete"""
    while True:
        status = client.get_task_status(task_id)
        
        if status["status"] in ["SUCCESS", "FAILED"]:
            result = client.get_task_result(task_id)
            callback(result)
            break
        
        time.sleep(check_interval)

# Usage
def on_task_complete(result):
    print(f"Task completed: {result['task_id']}")
    # Process result

task = client.create_task("https://example.com", "Extract data")
long_poll_task(task["task_id"], on_task_complete)
```

## Batch Processing

### Batch Task Creation

Create multiple tasks efficiently:

```python
def create_tasks_batch(requests: List[Dict]) -> List[Dict]:
    """Create multiple tasks in batch"""
    results = []
    
    # Use session for connection pooling
    with requests.Session() as session:
        session.headers.update({
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        })
        
        for req in requests:
            try:
                response = session.post(
                    f"{BASE_URL}/api/v1/process",
                    json=req,
                    timeout=10
                )
                response.raise_for_status()
                results.append({
                    "success": True,
                    "data": response.json()
                })
            except Exception as e:
                results.append({
                    "success": False,
                    "error": str(e),
                    "request": req
                })
    
    return results

# Usage
batch_requests = [
    {"url": "https://example1.com", "prompt": "Extract data"},
    {"url": "https://example2.com", "prompt": "Extract data"},
    {"url": "https://example3.com", "prompt": "Extract data"}
]

results = create_tasks_batch(batch_requests)
successful = [r for r in results if r["success"]]
failed = [r for r in results if not r["success"]]

print(f"Created: {len(successful)}, Failed: {len(failed)}")
```

## Data Export and Integration

### Export to CSV

```python
import csv
from typing import List, Dict

def export_results_to_csv(results: List[Dict], filename: str):
    """Export task results to CSV"""
    if not results:
        return
    
    # Flatten data
    rows = []
    for result in results:
        for item in result.get("data", []):
            rows.append({
                "task_id": result["task_id"],
                "url": result["url"],
                "text": item.get("text"),
                "source": item.get("source"),
                "confidence": item.get("confidence")
            })
    
    # Write CSV
    with open(filename, 'w', newline='', encoding='utf-8') as f:
        if rows:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

# Usage
results = [client.get_task_result(task_id) for task_id in task_ids]
export_results_to_csv(results, "scraping_results.csv")
```

### Integration with Databases

```python
import sqlite3

def save_results_to_database(results: List[Dict], db_path: str):
    """Save results to SQLite database"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS scraping_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            url TEXT,
            text TEXT,
            source TEXT,
            confidence REAL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Insert data
    for result in results:
        for item in result.get("data", []):
            cursor.execute("""
                INSERT INTO scraping_results (task_id, url, text, source, confidence)
                VALUES (?, ?, ?, ?, ?)
            """, (
                result["task_id"],
                result["url"],
                item.get("text"),
                item.get("source"),
                item.get("confidence")
            ))
    
    conn.commit()
    conn.close()
```

## Advanced Scheduling

### Dynamic Scheduling

Adjust schedule based on conditions:

```python
def create_adaptive_schedule(url: str, prompt: str):
    """Create schedule that adapts to data freshness"""
    
    # Initial schedule: every hour
    job = client.create_scheduled_job(url, prompt, "0 * * * *")
    
    # Monitor for changes
    last_data = None
    stable_count = 0
    
    while True:
        # Get latest result
        status = client.get_user_activity()
        latest_result = status["tasks"][0]  # Most recent
        
        # Check if data changed
        if latest_result.get("data") == last_data:
            stable_count += 1
        else:
            stable_count = 0
            last_data = latest_result.get("data")
        
        # Adjust schedule if data is stable
        if stable_count >= 24:  # Stable for 24 hours
            # Delete current job
            client.delete_scheduled_job(job["id"])
            
            # Create new job with less frequent schedule
            job = client.create_scheduled_job(url, prompt, "0 */6 * * *")  # Every 6 hours
            print("Schedule adjusted to every 6 hours due to stable data")
            stable_count = 0
        
        time.sleep(3600)  # Check every hour
```

### Conditional Scheduling

```python
def schedule_if_condition(url: str, prompt: str, condition_func: Callable):
    """Schedule task only if condition is met"""
    
    if condition_func():
        job = client.create_scheduled_job(url, prompt, "0 9 * * *")
        print(f"Job scheduled: {job['id']}")
    else:
        print("Condition not met, task not scheduled")

# Usage
def business_hours() -> bool:
    """Check if currently business hours"""
    now = datetime.now()
    return 9 <= now.hour < 17 and now.weekday() < 5

schedule_if_condition(
    "https://example.com",
    "Extract data",
    business_hours
)
```

## Performance Tuning

### Connection Pooling

```python
from requests.adapters import HTTPAdapter

def create_optimized_session():
    """Create session with optimized connection pooling"""
    session = requests.Session()
    
    adapter = HTTPAdapter(
        pool_connections=10,   # Number of connection pools
        pool_maxsize=20,       # Max connections per pool
        max_retries=3,
        pool_block=False
    )
    
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    return session
```

### Request Compression

```python
# Enable compression
headers = {
    "Authorization": f"Bearer {token}",
    "Accept-Encoding": "gzip, deflate"
}

response = requests.post(url, headers=headers, json=data)
```

### Response Caching

```python
from requests_cache import CachedSession

# Create cached session
session = CachedSession(
    'api_cache',
    expire_after=300,  # 5 minutes
    allowable_methods=['GET'],
    allowable_codes=[200],
)

# Subsequent identical requests use cache
response1 = session.get(f"{BASE_URL}/api/v1/status/{task_id}")
response2 = session.get(f"{BASE_URL}/api/v1/status/{task_id}")  # From cache
```

## Multi-Tenancy Considerations

### Tenant Isolation

When building multi-tenant applications:

```python
class TenantAwareClient:
    """API client with tenant isolation"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.tenant_tokens = {}
    
    def login_tenant(self, tenant_id: str, username: str, password: str):
        """Login for specific tenant"""
        response = requests.post(
            f"{self.base_url}/auth/token",
            data={"username": username, "password": password}
        )
        token = response.json()["access_token"]
        self.tenant_tokens[tenant_id] = token
    
    def create_task_for_tenant(self, tenant_id: str, url: str, prompt: str):
        """Create task for specific tenant"""
        if tenant_id not in self.tenant_tokens:
            raise ValueError(f"Tenant {tenant_id} not logged in")
        
        response = requests.post(
            f"{self.base_url}/api/v1/process",
            headers={"Authorization": f"Bearer {self.tenant_tokens[tenant_id]}"},
            json={"url": url, "prompt": prompt}
        )
        
        return response.json()

# Usage
client = TenantAwareClient("https://api.example.com")
client.login_tenant("tenant1", "user1", "pass1")
client.login_tenant("tenant2", "user2", "pass2")

task1 = client.create_task_for_tenant("tenant1", url, prompt)
task2 = client.create_task_for_tenant("tenant2", url, prompt)
```

## Related Documentation

- [API Reference](./API_REFERENCE.md) - Complete endpoint documentation
- [Best Practices](./BEST_PRACTICES.md) - Implementation guidelines
- [Rate Limiting](./RATE_LIMITING.md) - Rate limit details
- [Integration Tutorial](./INTEGRATION_TUTORIAL.md) - Getting started
- [Versioning](./VERSIONING.md) - Version management

---

## ARCHITECTURE_OVERVIEW.md

*(Modified: 2025-12-17 16:18:28)*

# Architecture Overview

## System Architecture

The Intelligent Web Data Aggregator API is a microservices-based architecture that provides intelligent web data aggregation capabilities. The system combines web scraping, natural language processing, and machine learning to extract structured data from web pages based on natural language prompts.

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Applications                       │
│  (Web Apps, Mobile Apps, CLI Tools, Integrations)           │
└──────────────────────────────┬──────────────────────────────┘
                               │ HTTP/REST API
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    API Service (FastAPI)                    │
│  ├─ Authentication & Authorization (JWT)                    │
│  ├─ Request Validation & Rate Limiting                      │
│  ├─ Task Management & Status Tracking                       │
│  └─ Scheduling & User Management                            │
└──────────────────────────────┬──────────────────────────────┘
                               │ Celery Tasks
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Worker Services                          │
│  ┌────────────────────┐  ┌────────────────────┐            │
│  │  Headless Worker   │  │     AI Worker      │            │
│  │  (Web Scraping)    │  │ (LLM Processing)   │            │
│  └────────────────────┘  └────────────────────┘            │
└──────────────────────────────┬──────────────────────────────┘
                               │ Database & Cache
                               ▼
┌─────────────────────────────────────────────────────────────┐
│                    Data Layer                               │
│  ┌────────────────────┐  ┌────────────────────┐            │
│  │   PostgreSQL       │  │      Redis         │            │
│  │  (Primary Store)   │  │ (Cache & Queue)    │            │
│  └────────────────────┘  └────────────────────┘            │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. API Service (FastAPI)

**Purpose**: Main entry point for client requests, handles authentication, validation, and task orchestration.

**Key Components**:
- **FastAPI Application**: Main web server with OpenAPI endpoints
- **Authentication Middleware**: JWT token validation and user session management
- **Rate Limiting**: Request throttling using Redis or in-memory storage
- **Input Sanitization**: Protection against prompt injection attacks
- **Error Handling**: Structured error responses and logging
- **CORS Management**: Cross-origin resource sharing configuration

**Location**: `services/api/`

### 2. Headless Worker

**Purpose**: Performs web scraping and content extraction using headless browsers.

**Key Responsibilities**:
- Fetch web page content
- Execute JavaScript for dynamic content
- Extract HTML/JSON/XML data
- Handle anti-bot measures
- Capture network requests

**Location**: `services/headless_worker/`

### 3. AI Worker

**Purpose**: Processes natural language prompts and generates extraction rules using LLMs.

**Key Responsibilities**:
- Intent extraction from user prompts
- Regex pattern generation
-
- Regex pattern generation
- Schema extraction and validation
- Caching of successful parsers
- LLM integration (DeepSeek, Gemini, OpenAI)

**Location**: `services/ai_worker/`

### 4. Data Layer

#### PostgreSQL Database
**Purpose**: Primary data storage with 3NF normalized schema.

**Key Tables**:
- `users`: User authentication and profiles
- `scraping_tasks`: Task metadata and status
- `parsers_cache`: Cached regex patterns and extraction rules
- `task_intents`: Normalized intent data
- `scheduled_jobs`: Scheduled job definitions
- `domains`: Domain lookup table (3NF normalization)
- `parser_samples`: Sample input/output data

#### Redis
**Purpose**: Caching, rate limiting, and Celery message broker.

**Key Uses**:
- Rate limit storage
- Celery task queue
- Session caching of successful parsers
- Session storage (optional)

### 5. Shared Infrastructure

**Location**: `shared/`

**Components**:
- `shared/config.py`: Centralized configuration management
- `shared/database/`: Database connection and models
- `shared/celery_app.py`: Celery configuration and task queue configuration
- `shared/correlation.py`: Request correlation ID utilities
- `shared/logging_utils.py`: Structured logging configuration

## Data Flow

### 1. Task Creation Flow

```
1. Client → API: POST /api/v1/process
   │   - URL and prompt
   │   - JWT token
   │
2. API Validation:
   │   - Authentication check
   │   - Rate limiting
   │   - Input sanitization
   │   - Schema validation
   │
3. Database: Create task record (PENDING)
   │
4. API: Return task_id (202 Accepted)
   │
4. Celery: Enqueue task to ai_queue
   │
5. AI Worker: Process task
   │   - Intent extraction
   │   - Check parser cache
   │   - Generate/validate regex
   │   - Enqueue task to fetching_queue
   │
6. Headless Worker: Fetch web content
   │   - Execute in headless browser
   │   - Extract content
   │   - Return to AI worker
   │
7. AI Worker: Apply regex extraction
   │   - Validate results
   │   - Validate results
   │   - Update task status
   │
8. Database: Update task (SUCCESS/FAILED)
   │
9. Client: Poll /api/v1/status/{task_id}
```

### 2. Authentication Flow

```
1. Client → API: POST /auth/register
   │   - Username, password, email
   │
2. API: Validate input
   │   - Check username uniqueness
   │   - Hash password (bcrypt)
   │   - Create user record
   │
3. Client: POST /auth/token
   │   - Username & password
   │
4. API: Verify credentials
   │   - Check password hash
   │   - Generate JWT token
   │   - Return access_token
   │
5. Client: Use token in Authorization header
   │   Authorization: Bearer <token>
```

### 3. Scheduled Job Flow

```
1. Client: POST /api/v1/jobs
   │   - URL, prompt, cron schedule
   │
2. API: Create scheduled job record
   │
3. Scheduler: Monitor cron schedules
   │
4. On schedule: Create task automatically
   │   - Same flow as manual task creation
   │
5. Results: Available via /api/v1/result
```

## Database Schema (3NF Normalized)

### Normalization Principles

1. **First Normal Form (1NF)**:
   - Atomic values, unique rows
2. **Second Normal Form (2NF)**: All non-key attributes depend on full primary key
3. **Third Normal Form (3NF)**: No transitive dependencies

### Key Normalization Decisions

1. **Domain Separation**: Extracted domain from URL to separate `domains table
2. **Intent Normalization**: Separated intent data to task_intents table
3. **Source Data Separation**: Large blobs moved to task_source_data
4. **Parser Samples**: Sample data separated to parser_samples table

### Schema Relationships

```
users
 ├── scraping_tasks (one-to-many)
 ├── scheduled_jobs (one-to-many)
 │
scraping_tasks
 ├── task_intents (many-to-one)
 ├── parsers_cache (many-to-one)
 ├── task_source_data (one-to-one)
 │
parsers_cache
 ├── domains (many-to-one)
 ├── domains (many-to-one)
```

## Security Architecture

### 1. Authentication & Authorization

- **JWT Tokens**: Stateless authentication with configurable expiry
- **Password Hashing**: bcrypt with salt and work factor
- **Token Revocation**: Not implemented (stateless design)
- **User Roles**: Basic user model (future: admin roles)

### 2. Input Validation & Sanitization

- **Prompt Injection Protection**: Blocks common injection patterns
- **URL Validation**: Strict URL format validation
- **Schema Validation**: Pydantic models for all inputs
- **Rate Limiting**: Prevents abuse and DoS attacks

### 3. Data Protection

- **Database Encryption**: At-rest encryption (PostgreSQL)
- **Connection Security**: TLS for database connections
- **Environment Variables**: Sensitive data in .env files
- **Log Redaction**: PII data excluded from logs

## Scalability Considerations

### Horizontal Scaling

1. **API Service**: Stateless, can be scaled horizontally
2. **Celery Workers**: Multiple instances per queue type
3. **Database**: Read replicas for read-heavy workloads
4. **Redis**: Cluster mode for high availability

### Performance Optimizations

1. **Parser Caching**: Reuse successful regex patterns
2. **Intent Matching**: Hash-based intent matching
3. **Database Indexing**: Strategic indexes on frequently queried columns
4. **Connection Pooling**: SQLAlchemy connection pools
5. **Async Processing**: Non-blocking I/O operations

### Monitoring & Observability

1. **Health Checks**: `/health` and `/api/v1/health` endpoints
2. **Structured Logging**: JSON-formatted logs with correlation IDs
3. **Metrics**: Request timing, error rates, queue lengths
4. **Tracing**: Correlation ID propagation across services

## Deployment Options

### 1. Docker Compose (Development)

```yaml
version: '3.8'
services:
  api:
    build: ./services/api
    ports: ["8000:8000"]
    depends_on: [postgres, redis]
    environment:
      - DATABASE_URL=postgresql://postgres:password@db:5432/diploma_db
      - REDIS_URL=redis://redis:6379/0
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=diploma_db
  
  redis:
    image: redis:7-alpine
  
  celery-worker-ai:
    build: ./services/ai_worker
    command: celery -A shared.celery_app.celery_app worker -Q ai_queue --loglevelloglevel=info
    depends_on: [redis, db]
  
  celery-worker-headless:
    build: ./services/headless_worker
    command: celery -A shared.celery_app.celery_app worker -Q fetching_queue --loglevel=info
    command: celery -A shared.celery_app.celery_app worker -Q fetching_queue --loglevel=info
    depends_on: [redis, db]
```

### 2. Kubernetes (Production)

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: apiVersion: apps/v1
kind: Deployment
metadata:
  name: api-deployment
spec:
  replicas: 3
  selector:
    matchLabels:
      app: api
  template:
    metadata:
      labels:
        app: api
    spec:
      containers:
      - name: api
      containers:
      - name: api
        image: diploma-api:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: api-config
        - secretRef:
            name: api-secrets
```

### 3. Server Error: secretRef:
            name: api-secrets
```

### 3. Serverless (Future)

- **API Gateway**: AWS API Gateway or Google Cloud Endpoints
- **Functions**: AWS Lambda or Google Cloud Functions
- **Database**: Managed PostgreSQL (RDS, Cloud SQL)
- **Queue**: Managed Redis (ElastiCache, Memorystore)

## Technology Choices

### Why FastAPI?

- **Performance**: Built on Starlette and Pydantic, very fast
- **Async Support**: Native async/await support
- **Type Hints**: Full Python type hint support
- **Auto Docs**: Automatic Docs**: Automatic OpenAPI documentation generation
- **Dependency Injection**: Clean dependency management

### Why Celery?

- **Distributed Task Queue**: Reliable task execution
- **Redis Backend**: Fast and reliable message broker
- **Retry Mechanisms**: Built-in retry with exponential backoff
- **Monitoring**: Monitoring and management tools
- **Python Integration**: Native Python support

### Why PostgreSQL?

- **ACID Compliance**: Reliable transactions
- **JSON Support**: Native JSON/JSONB data types
- **Full-Text Search**: Advanced text search capabilities
- **Extensions**: Rich ecosystem of Extensions**: Rich ecosystem of extensions

## Future Architecture Considerations

### 1. Microservices Evolution

- **Service Mesh**: Istio or Linkerd for service-to-service communication
- **API Gateway**: Kong or Ambassador for API management
- **Event Sourcing**: Kafka or RabbitMQ for event-driven architecture
- **Service Discovery**: Consul or etcd for dynamic service discovery

### 2. Machine Learning Pipeline

- **Model Training**: Separate training pipeline for parser improvement
- **A/B Testing**: Canary deployments for new parser versions
- **Feedback Loop**: User feedback incorporation into model training
- **Model Versioning**: Automated model retraining and deployment

### 3. Multi-Tenancy

- **Data Isolation**: Schema-per-tenant or row-level security
- **Billing Integration**: Usage tracking and billing
- **Customization**: Tenant-specific configurations
- **Compliance**: GDPR, HIPAA, etc. **Compliance**: GDPR, CCPA, and other regulations

## Conclusion

The Intelligent Web Data Aggregator API is designed as a scalable, maintainable system that balances performance with developer experience. The microservices architecture allows independent scaling of components, while shared infrastructure ensures consistency across services.

Key architectural principles of the system is built with extensibility in mind, allowing for future enhancements like additional LLM providers, new data sources, and advanced analytics capabilities.

---

