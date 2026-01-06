# Features & Requirements

## Epics Overview

| Epic | Description | Status |
| --- | --- | --- |
| **E1: Project Foundation & Infrastructure** | Set up repository, containers, CI/CD, and initial database migrations to enable development. | ✅   |
| **E2: Core API & User Interaction** | Implement FastAPI endpoints for task submission (/api/v1/process), status polling, result retrieval, user registration, and token-based authentication. | ✅   |
| **E3: Playwright-based Web Data Acquisition** | Develop a Celery worker using Playwright to fetch pages and extract text/HTML for processing. | ✅   |
| **E4: LLM Intelligence Pipeline** | Integrate LLM for intent extraction and selector generation (CSS/Regex/JSON). Implement multi-field (schema) and single-field extraction flows with validation loops. | ✅   |
| **E5: Caching & Persistence** | Design parsers_cache schema. Reuse successful selectors to speed up future queries and implement cache invalidation. | ✅   |
| **E6: QA & Documentation** | Write extensive automated tests (unit, integration, performance) and complete system documentation (API docs, user guide, architecture). | ✅   |

## User Stories

### Epic 2: Core API & User Interaction

| ID  | User Story | Acceptance Criteria | Priority | Status |
| --- | --- | --- | --- | --- |
| US-201 | **As a user**, I want to submit a scraping request (URL + prompt) via POST /api/v1/process, so that I receive a task ID immediately. | \- Returns task_id and status PENDING (HTTP 202) on valid input.&lt;br&gt;- Rejects invalid URLs or injection with 400 error. | Must | ✅   |
| US-202 | **As a user**, I want to check the status of my task via GET /api/v1/status/{task_id}, so that I know when it's done. | \- Returns current status (PENDING, IN_PROGRESS, SUCCESS, or FAILED) in JSON.&lt;br&gt;- Includes timestamps and progress percentage when in-progress. | Must | ✅   |
| US-203 | **As a user**, I want to retrieve the results of my scraping task via GET /api/v1/result/{task_id}, so that I get the extracted data once available. | \- If task is complete (status=SUCCESS), returns JSON with data, metadata (e.g. total matches, used cache).&lt;br&gt;- If still in-progress, returns 202 with status. | Must | ✅   |

### Epic 3: Web Data Acquisition

| ID  | User Story | Acceptance Criteria | Priority | Status |
| --- | --- | --- | --- | --- |
| US-301 | **As a developer**, I want a headless browser worker to fetch the target page in full (including JavaScript content), so that the system can extract data even from dynamic websites. | \- On task creation, a Celery worker on queue fetching_queue loads the URL using Playwright.&lt;br&gt;- Stores page text (innerText) and network requests in DB. | Must | ✅   |

### Epic 4: LLM Integration & Extraction

| ID  | User Story | Acceptance Criteria | Priority | Status |
| --- | --- | --- | --- | --- |
| US-401 | **As a user**, I want the system to understand my natural-language prompt and generate appropriate extraction patterns, so that relevant data is returned correctly. | \- LLM extracts intent keywords and fields, and generates regex or selectors for target data.&lt;br&gt;- Generated patterns are validated and, if successful, used for data extraction. | Must | ✅   |
| US-402 | **As a user**, I want commonly requested data (like "title, price, description") to be extracted as separate fields, so that relationships between fields are preserved. | \- Multi-field queries trigger the "schema extraction" path.&lt;br&gt;- Output JSON groups values under field names as objects. | Should | ✅   |

### Epic 5: Caching & Scheduling

| ID  | User Story | Acceptance Criteria | Priority | Status |
| --- | --- | --- | --- | --- |
| US-501 | **As a user**, I want repeated scraping of the same site/prompt to be faster by reusing previously learned patterns, so that I get quicker responses on repeat queries. | \- Before invoking LLM pipeline, system checks parsers_cache for matching URL and intent.&lt;br&gt;- If found, uses cached selector and skips LLM calls (response time significantly faster). | Should | ✅   |
| US-502 | **As a user**, I want to schedule recurring scraping jobs (cron), so that I can automatically collect updated data over time. | \- Provides POST /api/v1/jobs to create a schedule with fields (URL, prompt, cron).&lt;br&gt;- Celery Beat enqueues tasks per schedule and new runs appear in user's job list. | Could | ✅   |
