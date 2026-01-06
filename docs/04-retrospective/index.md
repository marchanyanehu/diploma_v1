# 4\. Retrospective

This section reflects on the project development process, lessons learned, and future improvements.

## What Went Well ✅

### Technical Successes

- **Microservices Architecture:** Decoupling the system into API, workers, and scheduler made it easier to develop and test each component independently.
- **LLM Integration:** Successfully used GPT/Gemini for prompt interpretation and regex generation, achieving multi-field extraction without hardcoding rules.
- **Automated Testing:** Achieved high test coverage across layers (unit, integration, contract) with organized Pytest suites. The comprehensive tests helped ensure system reliability.
- **Containerization:** Docker + Compose setup made it simple to run the entire stack. This streamlined setup was documented in the README.
- **Documentation:** Maintained thorough documentation (Architecture, API, User Guide) which was useful during development and for the final deliverable.

### Process Successes

- **Agile Task Breakdown:** The task-oriented epics (as in the TASKS.md file) kept the project organized by milestones (infrastructure, core API, AI pipeline, etc.).
- **Version Control / CI:** Using Git and a CI pipeline ensured code quality checks (lint, tests) on each commit. This prevented regressions.
- **Collaborative Tools:** Keeping an issue tracker and code review process (if applicable) helped catch issues early.

### Personal Achievements

- **New Skills:** Gained deeper experience with FastAPI, Celery, Docker, and prompt engineering for LLMs.
- **Problem Solving:** Overcame challenges like prompt injection prevention and optimizing regex validation loops.
- **Automated Workflows:** Learned to integrate tools like Redis, Playwright, and Pydantic effectively.

## What Didn't Go As Planned ⚠️

| Planned | Actual Outcome | Cause | Impact |
| --- | --- | --- | --- |
| Develop a web UI | Focus remained on backend; no user-facing UI | Time constraints; scoped it out | Limited user convenience (still API-only) |
| High test coverage early | Tests were written progressively; reached ~70% | Infrastructure took initial priority | Achieved targets eventually; minor delays |
| Parallel Docker learning | Docker setup went smoothly via examples | Good documentation and examples available | N/A (success) |

### Challenges Encountered

- **LLM Prompt Engineering:** Crafting effective prompts for schema vs. regex generation required trial and error. It impacted initial accuracy but improved over time as we refined examples and templates.
- **Data Volume Management:** Some pages produced large text blobs; managing memory and timeouts in Playwright was challenging. We mitigated by limiting snippet size and using rate limits.
- **Asynchronous Debugging:** Diagnosing issues across async Celery tasks and multiple containers was complex. Logging and health-checks helped, but some bugs (e.g. missing env var) took time to trace.
- **Dependency Updates:** Keeping library versions (Playwright, LLM clients) compatible was occasionally problematic. Pinning versions and using requirements.txt helped maintain stability.

## Technical Debt & Known Issues

| ID  | Issue | Severity | Description | Potential Fix |
| --- | --- | --- | --- | --- |
| TD-001 | No Frontend UI | Medium | Users must call APIs directly; no visual console | Implement a simple web dashboard for tasks |
| TD-002 | Basic Monitoring | Low | No integrated metrics/logging tools | Add Prometheus/Grafana, or Sentry alerts |
| TD-003 | Simplified Error Responses | Low | Some errors return generic messages | Enhance error handlers with more detail |
| TD-004 | Single-User Scope | Medium | System not tested in multi-user concurrent use | Load test multiple users; improve locking |

### Code Quality Issues

- Some utility modules (e.g. in shared) could be refactored for clarity.
- Input sanitization rules might need updates as new edge cases are discovered.
- While coverage is good, adding tests for rare failure modes (e.g. obscure HTML inputs) could strengthen robustness.

## Future Improvements (Backlog)

Given more time, the following would be prioritized:

### High Priority

- **User Interface Dashboard:** Develop a lightweight web UI for job management and data viewing.
- _Value:_ Greatly improves end-user usability.
- _Effort:_ Moderate (could use React or a simple templating framework).
- **Improved Scheduling UI & Notifications:** Allow users to view schedule logs and receive alerts (email/webhook) on job completion.
- _Value:_ Completes the automation loop.
- _Effort:_ Moderate.
- **Enhanced LLM Caching & Validation:** Cache more context (e.g., similar prompts) and refine regex validation (e.g., avoid overfitting).
- _Value:_ Faster responses; improved accuracy.
- _Effort:_ Moderate.

### Medium Priority

- **Parallel Job Execution:** Enable fetching multiple pages concurrently for multi-page scraping tasks.
- _Value:_ Reduces total processing time for batch jobs.
- _Effort:_ Moderate (requires task splitting logic).
- **Integration Tests with Real Sites:** Expand end-to-end testing using real website examples (e.g., popular news or e-commerce pages).
- _Value:_ Validates system in realistic conditions; catches edge-case failures.
- _Effort:_ Moderate to High.

### Nice to Have

- Additional extraction modes (e.g., handling image data or PDFs).
- Support for API key management and user roles (admin vs regular user).
- Model fine-tuning for domain-specific prompts.

## Lessons Learned

- **Lesson:** Clear API contracts and consistent data models are crucial.  
    **Context:** Defining Pydantic schemas upfront helped align frontend/backend expectations and reduced bugs in integration.  
    **Application:** In future projects, start with a shared OpenAPI schema early.
- **Lesson:** Automate everything (tests, lint, build).  
    **Context:** Setting up CI/CD early avoided code drift.  
    **Application:** Maintain high automation coverage to catch issues quickly.
- **Lesson:** Keep prompt templates simple and iterative.  
    **Context:** Complex prompts initially yielded unreliable LLM outputs; simplifying the approach improved consistency.  
    **Application:** For NLP tasks, use minimal prompts and test incrementally.

### What Would Be Done Differently

| Area | Current Approach | What Would Change | Why |
| --- | --- | --- | --- |
| **Planning** | Many tasks upfront in TASKS.md | More agile, incremental planning | Adapt to changing requirements more easily |
| **Technology** | Single-threaded Python workers | Explore Go/Rust for performance | Could handle high-load scraping faster |
| **Process** | End-to-end integration late | Frequent integration demos | Early validation of component interplay |
| **Scope** | Broader (scheduling + caching + all) | Focus on core scraping first | Ensure core functionality is rock-solid |

## Personal Growth

### Skills Developed

| Skill | Before Project | After Project |
| --- | --- | --- |
| API Design | Intermediate | Advanced |
| Asynchronous Python | Beginner | Intermediate |
| Docker & Deployment | Beginner | Intermediate |
| LLM Prompt Engineering | Beginner | Intermediate |
| Automated Testing | Beginner | Advanced |

### Key Takeaways

- **Decompose large projects into microservices** to manage complexity and facilitate parallel development.
- **Automate testing and deployment** early to maintain quality and confidence in changes.
- **Clear communication between system parts** (via message queues and well-defined contracts) is critical for reliability.

_Retrospective completed: 2025-01-05_
