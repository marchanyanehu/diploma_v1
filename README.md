# Intelligent Web Data Aggregator

A microservice-based web scraping system powered by LLMs to intelligently extract structured data from websites using natural language queries.

## Architecture

The system is composed of the following microservices:

1.  **API Service (`api`)**: 
    -   Entry point for users.
    -   Handles Authentication (JWT).
    -   Manages scraping tasks and scheduled jobs.
    -   Exposes REST endpoints.
2.  **Scheduler Service (`scheduler`)**:
    -   Runs periodic checks (Celery Beat) for due scheduled jobs.
    -   Triggers scraping tasks automatically.
3.  **Headless Worker (`headless_worker`)**:
    -   Handles actual web page fetching using Playwright.
    -   Captures visible text (for AI analysis) and full HTML (for extraction).
    -   Operates in a stealthy context.
4.  **AI Worker (`ai_worker`)**:
    -   **Intent Extraction**: Understands what the user wants (target, keywords).
    -   **Optimized Pipeline**:
        1.  Finds *examples* of data in the visible text (token-efficient).
        2.  Locates candidate snippets in the full HTML.
        3.  Uses LLM to *disambiguate* and select the best source snippet.
        4.  Generates a precise RegEx based on the snippet.
    -   Extracts data using the generated RegEx.

## Key Features

-   **Natural Language Interface**: "Get me all prices from this page."
-   **Token-Optimized AI**: Minimizes LLM costs by processing text/snippets instead of full HTML.
-   **Automated Scheduling**: Set up Cron-like schedules for recurring scrapes.
-   **Robust Fetching**: Uses Playwright to handle dynamic JS-heavy sites.
-   **Microservices**: Scalable and decoupled architecture.

## Setup & Installation

1.  **Prerequisites**: Docker and Docker Compose.
2.  **Environment Variables**:
    -   Copy `.env.example` to `.env`.
    -   Set your API keys (`GOOGLE_API_KEY` or `OPENAI_API_KEY`).
    -   Set `SECRET_KEY` for JWT auth.
3.  **Run**:
    ```bash
    docker-compose up --build
    ```

## API Documentation

Once running, visit: `http://localhost:8000/docs`

### Authentication
-   **Register**: `POST /auth/register`
-   **Login**: `POST /auth/token` -> returns `access_token`.
-   Use the token in the `Authorization: Bearer <token>` header for protected endpoints.

### Core Endpoints
-   **Create Task**: `POST /api/v1/process` (requires Auth)
-   **Check Status**: `GET /api/v1/status/{task_id}`
-   **Get Result**: `GET /api/v1/result/{task_id}`

### Scheduling
-   **Create Job**: `POST /api/v1/jobs`
-   **List Jobs**: `GET /api/v1/jobs`
-   **Delete Job**: `DELETE /api/v1/jobs/{job_id}`

## Development

-   **Run Tests**:
    ```bash
    docker-compose exec api pytest tests/
    ```
-   **Linting**:
    ```bash
    ruff check .
    ```
