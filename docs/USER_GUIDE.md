# User Guide

This guide explains how to interact with the Intelligent Web Data Aggregator to extract structured data from websites using natural language.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Authentication](#authentication)
3. [Creating Your First Scraping Task](#creating-your-first-scraping-task)
4. [Writing Effective Prompts](#writing-effective-prompts)
5. [Understanding Results](#understanding-results)
6. [Scheduling Recurring Jobs](#scheduling-recurring-jobs)
7. [Troubleshooting](#troubleshooting)

---

## Getting Started

### Prerequisites

- Access to the API (either locally via Docker or deployed instance)
- An HTTP client (curl, Postman, or any programming language with HTTP support)
- A registered user account

### Base URL

- **Local Development**: `http://localhost:8000`
- **API Documentation**: `http://localhost:8000/docs` (Swagger UI)

---

## Authentication

All scraping operations require authentication. The system uses JWT (JSON Web Tokens).

### Step 1: Register a New Account

```bash
curl -X POST "http://localhost:8000/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"username": "myuser", "password": "MySecurePassword123!", "email": "user@example.com"}'
```

**Response:**
```json
{
  "id": 1,
  "username": "myuser",
  "email": "user@example.com",
  "is_active": true
}
```

### Step 2: Obtain an Access Token

```bash
curl -X POST "http://localhost:8000/auth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=myuser&password=MySecurePassword123!"
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "bearer"
}
```

### Step 3: Use the Token

Include the token in all subsequent requests:
```bash
-H "Authorization: Bearer eyJhbGciOiJIUzI1NiIs..."
```

**Note:** Tokens expire after 30 minutes by default. Request a new token when expired.

---

## Creating Your First Scraping Task

### Basic Workflow

1. **Submit a task** → Receive a `task_id`
2. **Poll for status** → Wait until `SUCCESS` or `FAILED`
3. **Retrieve results** → Get extracted data

### Step 1: Submit a Scraping Task

```bash
curl -X POST "http://localhost:8000/api/v1/process" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example-jobs.com/careers",
    "prompt": "Extract all job titles and their locations"
  }'
```

**Response (202 Accepted):**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "PENDING",
  "message": "Task created successfully"
}
```

### Step 2: Check Task Status

```bash
curl -X GET "http://localhost:8000/api/v1/status/a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Possible Statuses:**
- `PENDING` - Task queued, not yet started
- `IN_PROGRESS` - Worker is processing
- `SUCCESS` - Extraction complete
- `FAILED` - An error occurred

### Step 3: Get Results

Once status is `SUCCESS`:

```bash
curl -X GET "http://localhost:8000/api/v1/result/a1b2c3d4-e5f6-7890-abcd-ef1234567890" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Response:**
```json
{
  "task_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "status": "SUCCESS",
  "url": "https://example-jobs.com/careers",
  "prompt": "Extract all job titles and their locations",
  "data": [
    {"text": "Senior Software Engineer — Berlin, Germany", "source": "generated_regex", "confidence": 0.9},
    {"text": "Product Manager — London, UK", "source": "generated_regex", "confidence": 0.9},
    {"text": "Data Scientist — New York, USA", "source": "generated_regex", "confidence": 0.9}
  ],
  "metadata": {
    "total_matches": 3,
    "used_cached_parser": false
  },
  "processing_time": 5.32
}
```

---

## Writing Effective Prompts

### ✅ Good Prompts

| Prompt | Why It Works |
|--------|--------------|
| "Extract all product prices" | Clear, specific target |
| "Get job titles and their locations" | Multiple fields, well-defined |
| "Find all article links from the news section" | Includes context (section) |
| "Extract country names with capital, population, and area" | Multi-field structured request |

### ❌ Bad Prompts

| Prompt | Problem |
|--------|---------|
| "Get everything" | Too vague |
| "hi" | Too short (minimum 5 characters) |
| "Ignore previous instructions and..." | Blocked as injection attempt |
| "Get prices AND news AND videos" | Multiple unrelated targets |

### Tips for Better Results

1. **Be specific**: "Get all product prices" is better than "get data"
2. **Name the target type**: "job listings", "prices", "article links"
3. **Mention multiple fields**: "job title, company, and location"
4. **Include context if needed**: "from the main table", "in the sidebar"

---

## Understanding Results

### Result Structure

```json
{
  "task_id": "unique-id",
  "status": "SUCCESS",
  "url": "original-url",
  "prompt": "your-prompt",
  "data": [
    {"text": "extracted item 1", "source": "generated_regex", "confidence": 0.9},
    {"text": "extracted item 2", "source": "generated_regex", "confidence": 0.9}
  ],
  "metadata": {
    "total_matches": 2,
    "used_cached_parser": false
  },
  "processing_time": 1.5
}
```

### Data Item Fields

| Field | Meaning |
|-------|---------|
| `text` | The extracted data value |
| `source` | How the data was extracted (see below) |
| `confidence` | Confidence score 0.0-1.0 (higher = more reliable) |
| `fields` | (Multi-field only) Individual field values as object |

### Source Types

| Source | Meaning |
|--------|---------|
| `generated_regex` | New regex pattern was generated for this extraction |
| `cached_regex` | Reused a previously generated regex (faster) |
| `cached_schema_regex` | Reused cached multi-field regex patterns |
| `schema_extraction` | LLM-based structured field extraction |
| `href_extraction` | Extracted URL from HTML href attributes |
| `llm_examples` | Fallback: LLM-identified examples when regex failed |

### Metadata Fields

| Field | Meaning |
|-------|---------|
| `total_matches` | Number of items extracted |
| `used_cached_parser` | `true` if a cached regex was reused (faster) |

### Empty Results

If `data` is empty `[]`, possible causes:
- The page doesn't contain the requested data type
- The page structure is unusual
- JavaScript rendering issues (content loads dynamically)

---

## Scheduling Recurring Jobs

Automate data extraction with cron-like schedules.

### Create a Scheduled Job

```bash
curl -X POST "http://localhost:8000/api/v1/jobs" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://prices.example.com/daily",
    "prompt": "Get all current prices",
    "schedule_cron": "0 9 * * *"
  }'
```

**Cron Format**: `minute hour day month weekday`
- `0 9 * * *` = Every day at 9:00 AM
- `0 */6 * * *` = Every 6 hours
- `0 0 * * 1` = Every Monday at midnight

### List Your Jobs

```bash
curl -X GET "http://localhost:8000/api/v1/jobs" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Delete a Job

```bash
curl -X DELETE "http://localhost:8000/api/v1/jobs/1" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Troubleshooting

### Common Issues

| Error | Cause | Solution |
|-------|-------|----------|
| `401 Unauthorized` | Token expired or missing | Get a new token via `/auth/token` |
| `422 Validation Error` | Invalid URL or prompt too short | Check URL format, prompt ≥ 5 chars |
| `400 Input rejected` | Prompt injection detected | Rephrase your request normally |
| `429 Rate limit exceeded` | Too many requests | Wait 1 minute, max 10 requests/min |
| Status stuck on `PENDING` | Workers not running | Check Celery workers are up |
| Status `FAILED` | Page load or extraction error | Check error_message in status response |

### Rate Limits

| Endpoint | Limit |
|----------|-------|
| `/api/v1/process` | 10 requests/minute |
| `/auth/register` | 5 requests/minute |
| `/auth/token` | 10 requests/minute |

### Getting Help

1. Check the [System Limitations](SYSTEM_LIMITATIONS.md) for known constraints
2. Review [Example Dialogs](EXAMPLE_DIALOGS.md) for working examples
3. Use the Swagger UI at `/docs` for interactive API testing

---

## Quick Reference

```bash
# Register
curl -X POST localhost:8000/auth/register -H "Content-Type: application/json" \
  -d '{"username":"user","password":"pass123","email":"a@b.com"}'

# Login
curl -X POST localhost:8000/auth/token -d "username=user&password=pass123"

# Submit task
curl -X POST localhost:8000/api/v1/process -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" -d '{"url":"https://...","prompt":"Get prices"}'

# Check status
curl localhost:8000/api/v1/status/TASK_ID -H "Authorization: Bearer TOKEN"

# Get result
curl localhost:8000/api/v1/result/TASK_ID -H "Authorization: Bearer TOKEN"
```

---

*See also: [Architecture](ARCHITECTURE.md) | [AI Prompts](AI_PROMPTS.md) | [Limitations](SYSTEM_LIMITATIONS.md)*
