# Architecture Overview

## Microservices Diagram

```mermaid
graph TD
    User[User / Client] -->|REST API| API[API Service]
    API -->|Auth & Tasks| DB[(PostgreSQL)]
    API -->|Queue Task| Redis[(Redis / Celery)]
    
    Scheduler[Scheduler Service] -->|Cron check (Celery Beat)| Redis
    Scheduler -->|Read Schedule| DB
    
    Redis -->|fetching_queue| Headless[Headless Worker]
    Redis -->|ai_queue| AI[AI Worker]
    
    Headless -->|Fetch Page| Web[Target Website]
    Headless -->|Raw Content| DB
    Headless -->|process_content -> ai_queue| Redis
    
    AI -->|Read Content & Cache| DB
    AI -->|Call LLM| LLM[LLM Provider]
    AI -->|Save Result| DB
```

## Data Flow (Optimized Pipeline)

1.  **Request**: User sends `url` + `prompt` to API.
2.  **Intent Extraction**: AI Worker extracts target, keywords, and schema fields from prompt.
3.  **Fetch**: Headless Worker (Celery `fetching_queue`) navigates to `url`.
    -   Captures `inner_text` (visible, up to 1MB) and `html` (structure), plus network preview.
4.  **AI Analysis (AI Worker, `ai_queue`)**:
    -   **Step 1**: Prepare content - truncate to 32KB for LLM, keep full for regex.
    -   **Step 2**: LLM finds *example values* in `inner_text` (e.g., specific prices/titles).
    -   **Step 3**: Worker searches `html` for these examples (no LLM) to find *candidate snippets*.
    -   **Step 4**: LLM selects best candidate from snippets (source disambiguation).
    -   **Step 5**: Extract focused micro-snippets (150 chars) around examples.
    -   **Step 6**: LLM generates RegEx using `shared/regex_generation.py`:
        - Iterative loop: Generate → Validate → Refine (up to 3 attempts)
        - Validation ensures pattern matches ALL examples
    -   **Cache**: Successful regex stored per domain/keywords for reuse.
5.  **Extraction**: Worker applies RegEx to full content (or uses cached parser).
6.  **Result**: Structured data saved to DB with `source` and `confidence` metadata.

### Snippet Strategy (Token Optimization)

The system uses layered snippets to handle large pages efficiently:

| Layer | Size | Purpose |
|-------|------|---------|
| Full content | 1MB max | Stored for regex application |
| LLM prompt content | 32KB max | Sent to LLM for example finding |
| Context snippet | 4000 chars | Fallback for regex generation |
| Micro-snippet | 150 chars | Focused HTML for precise regex |
| Line-aware snippet | 600 chars | Preserves example intact with context |

## Database Schema

-   **Users**: Authentication info.
-   **ScrapingTasks**: Tracks status, raw content, and final results.
-   **ScheduledJobs**: Cron schedules linked to users.
-   **ParserCache**: Stores successful RegEx patterns for reuse (optimization).

