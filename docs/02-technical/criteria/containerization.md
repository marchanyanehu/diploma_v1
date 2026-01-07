# Criterion: Containerization (Docker)

## Architecture Decision Record

### Status
**Status:** Accepted
**Date:** 2025-01-05

### Context
Developing and deploying a multi-service system (API, workers, Redis, Postgres) is error-prone due to "it works on my machine" issues. Different components have specific runtime requirements (e.g., Playwright requires browser binaries and system libraries).

### Decision
We chose **Docker** for containerizing every component of the system. We use **Docker Compose** to orchestrate the entire stack for development and production environments.

### Alternatives Considered
- **Virtual Environments (venv):** Manage dependencies but don't isolate system libraries or binary requirements like browsers.
- **Bare Metal / Single VM:** Hard to scale and prone to library version conflicts.

### Consequences
**Positive:**
- **Consistency:** Same environment from development to production.
- **Dependency Isolation:** Browser workers don't interfere with API dependencies.
- **Ease of Deployment:** One command (`docker-compose up`) starts the whole system.

**Negative:**
- Overhead of running multiple containers.
- Image size management (especially for browser-heavy images).

## Implementation Details

### Key Implementation Decisions
- **Multi-stage Builds:** Used in Dockerfiles to keep production images small.
- **Docker Compose:** Defines the network, volumes, and environment variables for all services (API, Headless Worker, AI Worker, Redis, DB).
- **Environment Variables:** All secrets and configurations are injected via a `.env` file into the containers.

## Requirements Checklist

| # | Requirement | Status | Evidence/Notes |
|---|-------------|--------|----------------|
| 1 | Service Containerization | ✅ | Dockerfiles provided for all custom services. |
| 2 | Docker Compose | ✅ | Central `docker-compose.yml` orchestrates the stack. |
| 3 | Dependency Management | ✅ | `requirements.txt` used inside containers for Python libs. |
| 4 | Volume Persistence | ✅ | Docker volumes used for PostgreSQL data persistence. |

## Known Limitations
- Requires Docker installed on the host machine.
- Initial image pulls can be slow due to browser sizes.

