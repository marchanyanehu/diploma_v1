# Criterion: Microservices Architecture

## Architecture Decision Record

### Status
**Status:** Accepted
**Date:** 2025-01-05

### Context
The project involves diverse workloads: I/O-heavy web fetching, CPU/latency-sensitive AI processing, and real-time API handling. A monolithic application would be difficult to scale and maintain as these components have different scaling needs and dependencies (e.g., Playwright requires specific system libraries).

### Decision
We adopted a **Microservices Architecture**. The system is decomposed into specialized services that communicate via a message broker (Redis) and a shared database (Postgres).

### Alternatives Considered
- **Monolith:** Easier to deploy initially but would couple the heavy browser-fetching environment with the lightweight API.
- **Serverless (Lambda):** Excellent for scaling but difficult to manage the state and long execution times of browser scraping.

### Consequences
**Positive:**
- **Isolation:** Each service (API, Worker, Scheduler) has its own dependencies and environment.
- **Scalability:** We can scale the number of scraping workers independently of the API.
- **Resilience:** A failure in the AI worker doesn't crash the API.

**Negative:**
- Increased complexity in inter-service communication and deployment (requires Docker Compose).

## Implementation Details

### Key Implementation Decisions
1.  **API Service:** Handles HTTP requests and task orchestration.
2.  **Headless Worker:** Uses Playwright to fetch pages in background queues.
3.  **AI Worker:** Handles LLM calls and Selector (CSS/Regex/JSON) generation.
4.  **Scheduler:** Manages periodic cron tasks via Celery Beat.

## Requirements Checklist

| # | Requirement | Status | Evidence/Notes |
|---|-------------|--------|----------------|
| 1 | Service Separation | ✅ | Separate folders and logic for API, Workers, and Scheduler. |
| 2 | Async Broker | ✅ | Redis used as the central message broker (Celery). |
| 3 | Independent Scaling | ✅ | Workers can be scaled horizontally via Docker. |
| 4 | Selector Generation Service | ✅ | Dedicated worker handles pattern generation logic. |

## Known Limitations
- Overhead of running multiple containers on low-resource machines.

