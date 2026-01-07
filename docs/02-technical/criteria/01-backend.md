# Criterion: Back-end (FastAPI Service)

## Architecture Decision Record

### Status
**Status:** Accepted
**Date:** 2025-01-05

### Context
The system required a robust, high-performance web framework to handle API requests, coordinate background workers for scraping, and manage the generation of extraction patterns (RegEx). The backend needs to be asynchronous to handle multiple concurrent tasks efficiently.

### Decision
We chose **FastAPI** (Python 3.11) as the core backend framework. It provides native `async/await` support, high performance (comparable to Go or Node.js), and automatic validation of data using Pydantic.

### Alternatives Considered
- **Django:** Too heavy for a microservices architecture; adds unnecessary overhead for simple API endpoints.
- **Flask:** Lacks native async support and automatic documentation, making it harder to build highly concurrent microservices.

### Consequences
**Positive:**
- Fast development with Pydantic for data schemas.
- Excellent performance for I/O-bound tasks.
- Clean integration with Celery and SQLAlchemy.

**Negative:**
- Requires careful management of async/sync code boundaries (e.g., when calling sync DB drivers).

## Implementation Details

### Key Implementation Decisions
- **RESTful Orchestration:** The API service manages the lifecycle of a ScrapingTask, from initial request to result delivery.
- **Async Endpoints:** All public endpoints are async to maximize throughput.
- **RegEx Management:** Centralized logic for storing and retrieving generated regular expressions from the database.

## Requirements Checklist

| # | Requirement | Status | Evidence/Notes |
|---|-------------|--------|----------------|
| 1 | FastAPI Framework | ✅ | Project uses FastAPI 0.95+ for all API services. |
| 2 | Request Processing | ✅ | Implemented via `POST /api/v1/process` with Pydantic validation. |
| 3 | RegEx Generation | ✅ | Managed via coordination with AI Worker and stored in DB. |
| 4 | Task Management | ✅ | Celery used to offload and monitor scraping tasks. |

## Known Limitations
- Heavy CPU tasks should be moved to workers to avoid blocking the event loop.

