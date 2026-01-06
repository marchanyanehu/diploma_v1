# Feature Walkthrough

## Feature 1: Submitting a Natural Language Query

**Overview:** Users can request data by sending a plain-English prompt. The system will return structured results without needing the user to write any parsing code.

### How to Use

- **Authentication**: Ensure you have a valid JWT token (see User Guide).
- **Submit Task**:

```bash
curl -X POST "http://localhost:8000/api/v1/process" \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{  
    "url": "https://news.example.com",  
    "prompt": "Find all article headlines and their publication dates"  
    }'
```

- A successful request returns `{"task_id": "...", "status": "PENDING", "message": "Task created successfully"}`.
- **Poll Status**:

```bash
curl -X GET "http://localhost:8000/api/v1/status/<task_id>" \
    -H "Authorization: Bearer YOUR_TOKEN"
```

- Repeat until status becomes SUCCESS or FAILED.
- Possible statuses: PENDING, IN_PROGRESS, SUCCESS, FAILED.
- **Get Results**:

```bash
curl -X GET "http://localhost:8000/api/v1/result/<task_id>" \
    -H "Authorization: Bearer YOUR_TOKEN"
```

- On success, receives JSON like:

```json
{  
    "task_id": "...",  
    "status": "SUCCESS",  
    "url": "https://news.example.com",  
    "prompt": "Find all article headlines and their dates",  
    "data": [  
        {"text": "Title 1", "source": "generated_regex", "confidence": 0.95},  
        {"text": "Title 2", "source": "generated_regex", "confidence": 0.93}  
    ],  
    "metadata": {"total_matches": 2, "used_cached_parser": false},  
    "processing_time": 4.2  
}
```

- The data array contains extracted items with their confidence scores.

**Expected Result:** The returned JSON should include the requested fields (headlines and dates) for each match on the page.

**Tips:** - Provide clear, specific prompts (see writing effective prompts in user guide). - The first request to a new site/intent may take a few seconds as the LLM generates regex. Subsequent similar requests may be faster due to caching.

## Feature 2: Scheduling Recurring Jobs

**Overview:** Users can automate data extraction on a schedule (cron-like). For example, daily price or news updates without manual intervention.

### How to Use

- **Create a Scheduled Job**:

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
    -H "Authorization: Bearer YOUR_TOKEN" \
    -H "Content-Type: application/json" \
    -d '{  
    "url": "https://prices.example.com/daily",  
    "prompt": "Get latest product prices",  
    "schedule_cron": "0 9 * * *"  
    }'
```

- `schedule_cron` uses standard cron syntax (minute hour day month weekday).
- Example `"0 9 * * *"` = every day at 9:00 AM.
- **List Scheduled Jobs**:

```bash
curl -X GET "http://localhost:8000/api/v1/jobs" \
    -H "Authorization: Bearer YOUR_TOKEN"
```

- Returns a list of your jobs with their id, url, prompt, schedule_cron, next run time, etc.
- **Delete a Scheduled Job**:

```bash
curl -X DELETE "http://localhost:8000/api/v1/jobs/1" \
    -H "Authorization: Bearer YOUR_TOKEN"
```

- Deletes job with ID 1. Returns confirmation message.

**Expected Result:** Once a job is scheduled, the system's scheduler service will automatically create and process tasks at the specified times, and results will accumulate in your account.

**Tips:** - Ensure cron expressions are valid (crontab.guru can help). - Monitor your jobs with GET /api/v1/jobs to see when they will run next.

### Keyboard Shortcuts

_(Not applicable: this is an API-based system; no keyboard shortcuts)_

### Feature Comparison

| Feature | Available to All Users |
| --- | --- |
| Single Extraction | ✅   |
| Multi-field Schema Extraction | ✅   |
| Scheduling Jobs | ✅   |
| Real-time Data | ✅ (subject to prompt and site behavior) |
