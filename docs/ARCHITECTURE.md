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
2.  **Fetch**: Headless Worker (Celery `fetching_queue`) navigates to `url`.
    -   Captures `inner_text` (visible) and `html` (structure), plus network preview.
3.  **AI Analysis (AI Worker, `ai_queue`)**:
    -   **Step 1**: LLM analyzes `inner_text` to find *example values* (e.g., specific prices/titles).
    -   **Step 2**: Worker searches `html` for these example strings to find *candidate snippets*.
    -   **Step 3**: LLM compares candidates to decide which HTML structure is the "canonical" source.
    -   **Step 4**: LLM generates a RegEx based *only* on the chosen snippet.
    -   **Cache**: Successful regex is stored per domain/keywords for reuse.
4.  **Extraction**: Worker applies RegEx to the full content (or uses cached parser).
5.  **Result**: Structured data is saved to DB.

## Database Schema

-   **Users**: Authentication info.
-   **ScrapingTasks**: Tracks status, raw content, and final results.
-   **ScheduledJobs**: Cron schedules linked to users.
-   **ParserCache**: Stores successful RegEx patterns for reuse (optimization).

