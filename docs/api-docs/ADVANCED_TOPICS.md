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
