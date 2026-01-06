# Criterion: Security & Error Handling

## Architecture Decision Record

### Status
**Status:** Accepted
**Date:** 2025-01-05

### Context
Handling untrusted user input (URLs and prompts) and interacting with external LLM APIs poses significant security risks, including prompt injection and unauthorized access. Additionally, as an asynchronous system, robust error handling is critical to provide informative feedback to users.

### Decision
We implemented a multi-layered security and error handling strategy:
1.  **JWT Authentication:** All protected endpoints require a valid JSON Web Token.
2.  **Input Sanitization:** User prompts are scanned for injection patterns before being sent to the LLM.
3.  **Graceful Degeneracy:** Comprehensive error handlers in FastAPI and Celery ensure that failures are logged and returned as structured JSON rather than internal traces.

### Alternatives Considered
- **Session-based auth:** Less scalable for a microservices architecture.
- **Basic error responses:** Insufficient for debugging complex AI pipeline failures.

### Consequences
**Positive:**
- Secure access to user data and resources.
- Protection against common LLM-based attacks.
- Clear error messages help users refine their prompts.

**Negative:**
- Added latency due to input sanitization checks.
- Complexity in synchronizing auth secrets across multiple services.

## Implementation Details

### Key Implementation Decisions
- **Rate Limiting:** `slowapi` used to limit task submission to 10 requests/min per IP.
- **Structured Error Responses:** All exceptions are mapped to Pydantic-validated error schemas.
- **Worker Error Propagation:** Failures in background workers are captured and saved to the task record in the DB.

### Code Examples
```python
# Unified error handling middleware
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred", "type": "INTERNAL_ERROR"}
    )
```

## Requirements Checklist

| # | Requirement | Status | Evidence/Notes |
|---|-------------|--------|----------------|
| 1 | JWT Authentication | ✅ | Implemented via /auth/token and Bearer protection. |
| 2 | Prompt Sanitization | ✅ | Filters out common injection/jailbreak keywords. |
| 3 | API Rate Limiting | ✅ | Implemented per endpoint based on user role/IP. |
| 4 | DB Scoping | ✅ | Users can only access tasks and jobs they own. |
| 5 | Error Logging | ✅ | Centralized logging captures all failures with task context. |

## Known Limitations
- Password reset functionality is not yet implemented.
- Sanitization rules are baseline and may need updates for evolving injection techniques.

