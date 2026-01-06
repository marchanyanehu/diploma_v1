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
