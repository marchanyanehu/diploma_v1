# Criterion: Architecture & Design

## Architecture Decision Record

### Status
**Status:** Accepted
**Date:** 2025-01-05

### Context
The system needed to handle long-running, I/O-intensive tasks (web fetching) and CPU-intensive/Latency-sensitive tasks (LLM calls) concurrently while remaining scalable and maintainable. A traditional monolith would have been difficult to scale horizontally for these different workloads.

### Decision
A **Microservices Architecture** was chosen, utilizing Docker containers for isolation. The system is split into:
1.  **API Service:** Lightweight FastAPI frontend for user interaction.
2.  **Headless Worker:** Playwright-based service for web page acquisition.
3.  **AI Worker:** LLM-driven service for intent extraction and selector generation.
4.  **Scheduler:** Celery Beat for managing periodic tasks.

### Alternatives Considered
- **Monolithic API:** Easier to deploy but difficult to scale the browser fetching separately from the API.
- **Serverless (AWS Lambda):** Good for scaling but limited by execution time and environment constraints for Playwright.

### Consequences
**Positive:**
- Independent scaling of workers (more headless workers for high fetch volume).
- Clear separation of concerns and technical stacks (e.g., Playwright requirements isolated to one container).
- Robust asynchronous processing via Redis/Celery.

**Negative:**
- Increased complexity in deployment and networking.
- Overhead of managing multiple containers and inter-service communication.

## Implementation Details

### Project Structure
```
services/
├── api/               # FastAPI backend
├── headless_worker/   # Playwright fetching logic
├── ai_worker/         # LLM pipeline and regex/selector logic
└── scheduler/         # Cron job management
shared/                # Common models and database logic
```

### Key Implementation Decisions
- **Event-Driven Task Queue:** Used Celery to decouple API requests from background processing.
- **Unified Database:** PostgreSQL 15 used for all persistent state, from user accounts to cached selectors.

## Requirements Checklist

| # | Requirement | Status | Evidence/Notes |
|---|-------------|--------|----------------|
| 1 | Microservices separation | ✅ | Independent folders and Dockerfiles for each service. |
| 2 | Containerization | ✅ | Full docker-compose.yml configuration provided. |
| 3 | Scalable workers | ✅ | Celery allows scaling worker counts dynamically. |
| 4 | Shared database access | ✅ | All services use SQLAlchemy to connect to central Postgres. |
| 5 | Inter-service comms | ✅ | Handled via Redis broker and task queues. |

## Known Limitations
- Overhead of Docker on low-resource environments (~4GB RAM recommended).
- Single point of failure if Redis or Postgres goes down.

