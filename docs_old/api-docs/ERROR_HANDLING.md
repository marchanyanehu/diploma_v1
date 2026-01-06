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
