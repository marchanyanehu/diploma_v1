# Criterion: Testing & Quality Assurance

## Architecture Decision Record

### Status
**Status:** Accepted
**Date:** 2025-01-05

### Context
Ensuring the reliability of a microservices-based system with AI components is challenging. The non-deterministic nature of LLMs and the dynamic nature of web pages required a comprehensive testing strategy that covers both predictable code and variable AI outputs.

### Decision
A tiered testing strategy was implemented using `pytest`. This includes:
1.  **Unit Tests:** For individual components and utilities.
2.  **Integration Tests:** Testing the interaction between services (e.g., API to Redis to Worker).
3.  **End-to-End (E2E) Tests:** Verifying the full pipeline from prompt submission to result retrieval.

### Alternatives Considered
- **Manual Testing only:** Too slow and prone to human error.
- **Mock-heavy testing:** Risk of missing real-world integration issues.

### Consequences
**Positive:**
- High confidence in core logic changes.
- Automated verification of deployment readiness.
- Early detection of breaking changes in third-party APIs (Playwright, LLM).

**Negative:**
- Tests for AI components can be slower and occasionally flaky due to network/LLM latency.
- Maintenance overhead for keeping E2E tests in sync with web changes.

## Implementation Details

### Key Implementation Decisions
- **Pytest Suite:** Organized into `tests/` with specialized marks for unit and integration.
- **Coverage Tracking:** `pytest-cov` used to ensure a minimum of 70% code coverage.
- **Async Testing:** Leveraged `pytest-asyncio` for testing FastAPI and async worker tasks.

## Requirements Checklist

| # | Requirement | Status | Evidence/Notes |
|---|-------------|--------|----------------|
| 1 | Automated Unit Tests | ✅ | Extensive tests for models, schemas, and utils. |
| 2 | Integration Tests | ✅ | Verifies full task flow with Redis and PostgreSQL. |
| 3 | Code Coverage > 70% | ✅ | Monitored and enforced in CI pipelines. |
| 4 | Test Documentation | ✅ | Summary of testing strategy provided in `TESTING_SUMMARY.md`. |
| 5 | Mocking Third-Party APIs | ✅ | LLM and Playwright mocked in unit tests for stability. |

## Known Limitations
- E2E tests against real websites are excluded from regular CI runs to avoid dependency on external site stability.
- Coverage for complex LLM validation loops is focused on logic rather than output accuracy.

