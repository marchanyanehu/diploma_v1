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
