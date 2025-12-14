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
