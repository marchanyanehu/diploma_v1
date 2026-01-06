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
