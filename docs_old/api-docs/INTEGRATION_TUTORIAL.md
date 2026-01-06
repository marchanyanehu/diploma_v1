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