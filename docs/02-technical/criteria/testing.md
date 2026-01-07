# Criterion: Automated Tests (≥ 70% Coverage)

## Architecture Decision Record

### Status
**Status:** Accepted
**Date:** 2025-01-05

### Context
Reliability in a complex microservices system with AI components is difficult to ensure manually. We need an automated way to verify that changes don't break core logic and that the system meets a high bar for code quality.

### Decision
We implemented a comprehensive suite of automated tests using **Pytest**. We set a strict requirement of **at least 70% code coverage** for the entire backend codebase (API and Workers).

### Alternatives Considered
- **Unittest:** Standard but less flexible and verbose compared to Pytest.
- **Manual Testing:** Not scalable and prone to human error in a distributed system.

### Consequences
**Positive:**
- High confidence in the correctness of core scraping and AI logic.
- Faster development cycles as regressions are caught early.
- Documentation of system behavior through test cases.

**Negative:**
- Writing and maintaining tests adds to development time.
- Mocking external APIs (Baseten, Gemini) is necessary for stable tests.

## Implementation Details

### Key Implementation Decisions
- **Pytest-Cov:** Used to generate and enforce coverage reports.
- **Tiered Testing:** Unit tests for utilities, integration tests for API-DB-Worker flows.
- **Mocking:** All third-party calls (LLMs, Playwright) are mocked in standard test runs to ensure stability and speed.

## Requirements Checklist

| # | Requirement | Status | Evidence/Notes |
|---|-------------|--------|----------------|
| 1 | Pytest Framework | ✅ | All tests written using modern Pytest standards. |
| 2 | Code Coverage ≥ 70% | ✅ | Coverage reports confirm >70% coverage across modules. |
| 3 | API Logic Testing | ✅ | Endpoints (process, jobs) tested with valid/invalid inputs. |
| 4 | Business Logic Testing | ✅ | Core AI and RegEx generation logic covered by unit tests. |

## Known Limitations
- Testing the actual quality of LLM-generated RegEx requires non-deterministic testing (partially covered in integration).

