# Technology Stack

## Stack Overview

| Layer | Technology | Version | Justification |
| --- | --- | --- | --- |
| **Backend Language** | Python | 3.11 | Widely supported for web and ML; used in microservices. |
| **Web Framework** | FastAPI | ~0.95 (latest) | High-performance, async, automatic OpenAPI docs. |
| **Async Tasks** | Celery + Redis | Celery 5.x, Redis 7 | Mature distributed task queue and in-memory broker for decoupling workloads. |
| **Database** | PostgreSQL | 15.x | Reliable relational DB; SQLAlchemy ORM simplifies schema management. |
| **ORM** | SQLAlchemy | 1.4+ | Robust for complex schemas and relations (tasks, caching, users). |
| **Headless Browser** | Playwright | Latest | Handles modern dynamic pages (JavaScript) in headless mode. |
| **LLM APIs** | DeepSeek, Gemini, OpenAI | Various | Provides intelligence without local model training. Fall back options configured. |
| **Containerization** | Docker, Docker Compose | (n/a) | Ensures consistent environments; defines multi-container setup (API, DB, Workers). |
| **CI/CD** | GitHub Actions (implied) | \-  | Automates testing, linting, and deployment pipelines. |
| **Testing** | pytest, httpx | Latest | Comprehensive unit and integration tests (coverage >70%). |
| **Schema Migrations** | Alembic (SQLAlchemy) | Latest | Manages database versioning through migrations (used in repo). |

## Key Technology Decisions

### Decision 1: Python & FastAPI

**Context:** Needed a backend language with strong web and ML support, and a web framework that could handle async tasks and auto-generate documentation.  
**Decision:** Use Python 3.11 with FastAPI.  
**Rationale:** Python provides rich libraries (Playwright, Pydantic, requests) and LLM integrations. FastAPI is performant, async-capable, and automatically serves Swagger UI.  
**Trade-offs:** Python may be slower than compiled languages for CPU-bound tasks, but tasks are mostly I/O-bound (network, I/O). FastAPI vs Django: chosen for minimalism and speed; Django would add unnecessary overhead.

### Decision 2: Microservices & Docker

**Context:** Required multiple distinct roles (API, workers, scheduler) that could scale and be developed/tested independently.  
**Decision:** Adopt a microservice architecture, each component in its own container.  
**Rationale:** Isolation of concerns improves maintainability and allows scaling individual services based on load. Docker ensures consistency across dev, test, and prod.  
**Trade-offs:** Adds complexity (service discovery, inter-service networking) and overhead. Simpler monolith could have been easier to start, but less scalable. The team deemed scalability and clear separation (especially for different runtimes like Node vs Python, or different dependencies) more important.

### Decision 3: Redis & Celery for Task Queue

**Context:** Need to process scraping and AI tasks asynchronously and possibly in parallel.  
**Decision:** Use Celery with Redis as broker.  
**Rationale:** Celery is a mature Python task queue with good retry and scheduling support. Redis is fast and supports pub/sub. Both are widely used and fit well in Docker.  
**Trade-offs:** Requires running Redis server. Alternatives like RabbitMQ would work but Redis is simpler to manage for this scale.

## Development Tools

| Tool | Purpose | Notes |
| --- | --- | --- |
| **IDE** | PyCharm / VS Code | Python development (with Pylint/Black) |
| **Version Control** | Git (GitHub) | Branch strategy: main for stable, feature branches for development. Pull requests with code review. |
| **Package Manager** | pip + venv | Dependency isolation; requirements.txt at repo root. |
| **Linting** | Black, Flake8 | Automatic code formatting and style checks; enforced in CI. |
| **Testing** | Pytest | Unit & integration tests; coverage goal 70%+. |
| **API Docs** | Swagger UI (FastAPI) | Auto-generated from code; available at /docs. |
| **Logging** | structlog or Python logging | Centralized structured logs; console output captured by Docker logging driver. |

## External Services & APIs

| Service | Purpose | Pricing Model |
| --- | --- | --- |
| **OpenAI/GPT** | LLM provider for prompt processing | Pay-as-you-go (per request) |
| **Gemini (Google)** | Alternative LLM provider | Free tier & paid options |
| **Baseten/DeepSeek** | Specialized AI model hosting | Subscription-based |
| **Email/SMS** (optional) | User notifications/alerts | Depends on chosen provider (Twilio, etc.) |
