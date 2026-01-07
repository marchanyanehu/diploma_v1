# API Reference

## Base URL

- **Development:** <http://localhost:8000>
- All endpoints are under the /api/v1 path (for versioning) or at the root for authentication and health.

## Authentication

The API uses JWT-based auth. Obtain a token via /auth/token and include it as:

Authorization: Bearer &lt;your_access_token&gt;

## Endpoints

### Auth & Health

- **POST /auth/register**  
    Create a new user account.  
    **Body:** {"username": "user", "password": "pass123", "email": "<a@b.com>"}.  
    **Success (200):** `{"id": 1, "username": "user", "email": "a@b.com", "is_active": true}`.  
    **Errors:** 400 if username exists; 429 if rate-limited.
- **POST /auth/token**  
    Obtain a JWT token.  
    **Form Data:** `username=user&password=pass123`.  
    **Success (200):** `{"access_token": "eyJ...","token_type":"bearer"}`.  
    **Errors:** 401 invalid credentials; 429 rate limit.
- **GET /**  
    Root endpoint. Returns basic API info (service name, version).  
    **Example Response (200):** `{"message":"Intelligent Web Data Aggregator API","version":"1.0.0","status":"operational", ...}`.
- **GET /health**  
    Liveness probe. **Response:** `{"status":"healthy","timestamp":"...","service":"api","version":"1.0.0","uptime":"operational"}`.
- **GET /api/v1/health**  
    Readiness with DB check. **Response:** includes `{"database": {"status":"connected", ...}}`.


### Core API (Tasks)

_(All below require Authorization: Bearer &lt;token&gt;)_

- **POST /api/v1/process**  
    Create a new scraping task.  
    **Body:** `{"url": "<target_url>", "prompt": "<what to extract>"}`.  
    **Rate-Limit:** 10/min per IP.  
    **Success (202):** `{"task_id":"<uuid>","status":"PENDING","message":"Task created successfully"}`.  
    **Errors:** 400 if bad URL or prompt (including injection detected); 401 if not authenticated; 429 rate-limit.
- **GET /api/v1/status/{task_id}**  
    Poll status of a task.  
    **Path Param:** `task_id` (string, UUID).  
    **Success (200):** JSON with task info, e.g.:  

```json
{  
    "task_id": "...",  
    "status": "IN_PROGRESS",  
    "progress": 40,  
    "message": null,  
    "created_at": "...",  
    "updated_at": "..."  
}
```

- Possible statuses: PENDING, IN_PROGRESS, SUCCESS, FAILED.  
    **Errors:** 401 if not auth; 403 if not owner; 404 if unknown ID.
- **GET /api/v1/result/{task_id}**  
    Retrieve results of a completed task.  
    **Path Param:** `task_id`.
- If status=SUCCESS (200): Returns full data, e.g.:  

```json
{  
    "task_id": "...",  
    "status": "SUCCESS",  
    "url": "https://example.com",  
    "prompt": "...",  
    "data": [  
        {"text": "...", "source": "...", "confidence": 0.92}  
    ],  
    "metadata": {"total_matches": 1, "used_cached_parser": false},  
    "processing_time": 3.21,  
    "created_at": "...", "completed_at": "..."  
}
```

- If still processing (202): same structure as status endpoint with `"status":"IN_PROGRESS"`.  
    **Errors:** 400 if task failed; 401/403 if unauthorized; 404 if not found.


### Scheduling

_(All below require auth)_

- **POST /api/v1/jobs**  
    Create a scheduled (cron) scraping job.  
    **Body:** `{"url": "...", "prompt": "...", "schedule_cron": "0 9 * * *"}`. Supports both 5-field (standard) and 6-field (sub-minute) cron expressions.  
    **Success (200):** JSON object of the new job, e.g.:  

```json
{  
    "id": 1,  
    "url": "https://example.com",  
    "prompt": "Get prices",  
    "schedule_cron": "*/30 * * * * *",  
    "next_run_at": "2025-08-08T12:00:30Z",  
    "last_run_at": null,  
    "created_at": "2025-08-08T12:00:00Z"  
}
```

- (Next run is computed by the scheduler; high-resolution tasks checked every 10s).
- **GET /api/v1/jobs**  
    List all jobs for the current user.  
    **Success (200):** JSON array of job objects (as above).
- **DELETE /api/v1/jobs/{job_id}**  
    Delete a scheduled job.  
    **Path Param:** `job_id` (integer).  
    **Success (200):** `{"message":"Job deleted"}`.  
    **Errors:** 404 if no such job or not owned by user.
- **GET /api/v1/users/me/activity**  
    (Optional) Returns current user's recent tasks and jobs.  
    **Success (200):** e.g.:  

```json
{  
    "tasks": [{ "task_id": "...", "status": "SUCCESS", ... }],  
    "scheduled_jobs": [{ "id":1, "url":"...", ...}]  
}
```

- (Not in minimal API; included as a helpful endpoint if implemented).


### Other Endpoints

- **POST /api/v1/test-task**  
    (For internal/test use) Creates a dummy task to verify DB connectivity.  
    **Response:** {"message":"Test task created successfully","task":{...}}. Typically not used by end users.

## Error Responses

The API uses standard HTTP error codes. Common errors include:

| Code | Description |
| --- | --- |
| 200 | OK - success |
| 202 | Accepted - processing (async task started) |
| 400 | Bad Request - validation failed |
| 401 | Unauthorized - missing/invalid token |
| 403 | Forbidden - no permission on this resource |
| 404 | Not Found - invalid endpoint or ID |
| 422 | Unprocessable - input validation (Pydantic) |
| 429 | Too Many Requests - rate limit exceeded |
| 500 | Internal Server Error - unexpected failure |

Rate limits are enforced per-IP: 10/min for /api/v1/process, 5/min for /auth/register, 10/min for /auth/token.

## Swagger/OpenAPI

Interactive API documentation is available at /docs (Swagger UI) once the service is running. The OpenAPI JSON is also exposed at /openapi.json for integration or client generation.
