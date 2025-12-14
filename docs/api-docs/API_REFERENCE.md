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