# Criterion: Requirements & Use Cases

## Architecture Decision Record

### Status
**Status:** Accepted
**Date:** 2025-01-05

### Context
The project required a clear definition of functional and non-functional requirements to ensure the Intelligent Web Data Aggregator meets user needs. The primary goal was to allow non-technical users to extract structured data using natural language, which necessitated a robust mapping from human prompts to technical extraction logic.

### Decision
We adopted a user-centric requirement engineering approach, breaking down the project into Epics and User Stories. Each story was defined with clear Acceptance Criteria (AC) and assigned a priority (Must, Should, Could). This ensured that the core extraction engine was prioritized over secondary features like a full UI.

### Alternatives Considered
- **Direct Scraper Generation:** Asking users to provide CSS selectors (too technical).
- **Hard-coded Templates:** Supporting only specific sites (not scalable).
- **Decision:** Natural Language Processing (NLP) via LLM was chosen for its flexibility across arbitrary websites.

### Consequences
**Positive:**
- Clear development roadmap based on prioritized stories.
- Accurate validation of features against Acceptance Criteria.
- High flexibility for users who don't know HTML/CSS.

**Negative:**
- Increased dependency on LLM API availability and accuracy.
- Complexity in handling ambiguous natural language prompts.

## Implementation Details

### Project Structure
```
docs/01-project-overview/
├── features.md            # Epics and User Stories
├── scope.md               # In/Out scope definitions
└── problem-and-goals.md   # Business context
```

### Key Implementation Decisions
- **Epic-based development:** Organized into 6 epics (Foundation, API, Acquisition, AI, Caching, QA).
- **Semantic Mapping:** Used LLMs to extract "intent" (fields, target, keywords) from raw strings.

## Requirements Checklist

| # | Requirement | Status | Evidence/Notes |
|---|-------------|--------|----------------|
| 1 | Natural language query support | ✅ | Implemented via AI worker and intent extraction. |
| 2 | Asynchronous task processing | ✅ | Handled by Celery and Redis. |
| 3 | Multi-field schema extraction | ✅ | Supported via the schema_extraction path. |
| 4 | Task status and result polling | ✅ | /status and /result endpoints implemented. |
| 5 | Scheduled jobs (CRON) | ✅ | Implemented using Celery Beat and ScheduledJob model. |

## Known Limitations
- Ambiguous prompts may lead to suboptimal selector generation.
- Very short prompts (<5 characters) are rejected to ensure context.

