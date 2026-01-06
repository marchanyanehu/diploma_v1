# 2\. Technical Implementation

This section covers the technical architecture, design decisions, and implementation details.

## Contents

- [Tech Stack](tech-stack.md) - Technologies and key decisions.
- [Criteria Documentation](criteria/) - Design rationale for each evaluation criterion.
- [Deployment & DevOps](deployment.md) - Infrastructure setup and deployment instructions.

## Solution Architecture

### High-Level Architecture

graph TD  
User\[User/Client\] -->|REST API| API\[FastAPI Service\]  
API -->|SQL/ORM| DB\[(PostgreSQL)\]  
API -->|Celery Queue| Redis\[(Redis Broker)\]  
<br/>Scheduler\[Scheduler Service (Beat)\] -->|Checks DB| DB  
Scheduler -->|Schedules Task| Redis  
<br/>Redis -->|fetching_queue| Headless\[Headless Worker\]  
Redis -->|ai_queue| AI\[AI Worker\]  
<br/>Headless -->|Fetch Page| Web\[Target Website\]  
Headless -->|Stores Content| DB  
<br/>Headless -->|→| Redis  
AI -->|Reads Content| DB  
AI -->|Calls LLM| LLM\[LLM Provider\]  
AI -->|Stores Results| DB

_Figure: High-level component interactions in the system._

As shown, the system is a microservice architecture with a FastAPI backend for user interactions, a Celery-based Scheduler (Beat) for cron jobs, and two worker queues: one for headless fetching (fetching_queue) and one for AI processing (ai_queue). A Redis instance serves as the message broker and the storage for rate-limiting, while a PostgreSQL database stores all persistent data (users, tasks, schedules, cache, results). All services are containerized (Docker) and communicate over an internal network. Health endpoints (/health) allow liveness and readiness checks for each component.

### System Components

| Component | Description | Technology |
| --- | --- | --- |
| **API Backend** | Handles authentication and task management (create task, check status/result, schedule jobs). Orchestrates workers via Celery. | Python 3.11, FastAPI, Uvicorn |
| **Celery Workers** | Background services performing: |     |
| &lt;br&gt;- **Headless Worker**: Fetch web pages using Playwright, extract semantic page text and network data. |     |     |
| &lt;br&gt;- **AI Worker**: Interpret prompt, generate regex via LLM, apply regex for data extraction. | Python, Celery, Redis, Playwright |     |
| **Scheduler** | Cron-like service (Celery Beat) that enqueues tasks per user-defined schedule in the database. | Python, Celery Beat, Redis |
| **Database** | Central PostgreSQL database for all data: |     |
| &lt;br&gt;- _Users_: Auth info |     |     |
| &lt;br&gt;- _ScrapingTasks_: Task metadata and results |     |     |
| &lt;br&gt;- _ScheduledJobs_: Cron definitions |     |     |
| &lt;br&gt;- _ParserCache_: Regex patterns for reuse | PostgreSQL 15, SQLAlchemy ORM |     |
| **Cache/Broker** | Redis used both as a Celery broker/back-end and a short-term cache/rate-limit store. | Redis (In-memory data store) |
| **External LLMs** | Third-party Large Language Models (OpenAI/Gemini/DeepSeek) used to interpret prompts and generate extraction patterns. | e.g. OpenAI API, Gemini API, DeepSeek (Baseten) |

### Data Flow

- **User Request:** A client sends a JSON request (url + prompt) to POST /api/v1/process.
- **Task Creation:** API service validates input, creates a ScrapingTask record (status=PENDING) and enqueues a Celery task to fetching_queue.
- **Headless Fetch:** Headless Worker pulls the task, loads the page in Playwright (using configured headless browser flags), and captures:
- Semantic content (innerText with markers)
- Full HTML
- Network responses (XHR JSON, etc.) It stores this raw content linked to the task.
- **AI Processing:** A Celery task on ai_queue is started. The worker:
- Extracts intent (target/keywords/fields) from the prompt using an LLM (intent extraction module).
- Checks the parsers_cache (by URL and intent) for a matching regex.
- If cache hit: use regex on stored content, skip LLM calls. Otherwise, proceed.
- **Schema Path:** If multiple fields requested, LLM extracts all fields simultaneously (schema_extraction).
- **Single-Field Path:** LLM finds examples of target data, regex is generated to match those examples.
- Validate and possibly refine regex (iterative LLM prompts) until adequate accuracy.
- Save successful regex to parsers_cache.
- Apply regex to full HTML content to produce structured results (with text, confidence, etc.).
- **Result Delivery:** Final results (JSON records) and metadata (match count, used cache flag, timing) are saved to the ScrapingTask record (status=SUCCESS or FAILED). The user can retrieve via GET /api/v1/result/{task_id}.
- **Scheduling:** If the request was a scheduled job, the Scheduler (Beat) enqueues new tasks at the specified cron times automatically.

### Key Technical Decisions

| Decision | Rationale | Alternatives Considered |
| --- | --- | --- |
| **Microservices Architecture** | Allows independent scaling of components (API, workers, scheduler). Improves modularity and maintainability. | Monolithic app (simpler but less scalable) |
| **Python & FastAPI** | Python has rich web scraping and ML libraries; FastAPI offers async support and automatic docs. | Node.js/Express (less mature ML libs), Flask (slower performance) |
| **Celery with Redis** | Proven combo for distributed task queues. Redis is fast, and Celery supports retries and scheduling. | RabbitMQ (more overhead to set up), RQ (less feature-rich) |
| **Playwright for Headless Fetch** | Modern JS support, active browser automation features, and Python integration. | Selenium (heavier, less performant), requests-HTML (no JS) |
| **SQLAlchemy ORM** | Strong support for complex schemas and migrations in Python. Ease of writing queries. | Django ORM (heavy for this project), raw SQL (verbose) |
| **LLM Integration via API** | Leverages state-of-art LLMs (like OpenAI/Gemini) for intent interpretation without building our own model. | Building custom NLP models (too time-consuming) |

### Security Overview

| Aspect | Implementation |
| --- | --- |
| **Authentication** | JWT tokens for all protected endpoints (/auth/register, /auth/token, then Bearer tokens). Passwords hashed (bcrypt). |
| **Authorization** | User-specific resources (tasks, jobs) are scoped to the authenticated user (owner_id field). |
| **Rate Limiting** | slowapi (Redis-backed) enforces limits: e.g. /api/v1/process: 10/minute per IP. |
| **Input Validation** | All inputs validated via Pydantic schemas. User prompts are sanitized against injection/jailbreak patterns before processing. |
| **Encryption** | TLS is recommended in production. JWT secret stored in environment (SECRET_KEY), never in code. |
| **Secrets Management** | API keys and database credentials are loaded from environment variables (see .env example) and not hard-coded. |
