# Project Scope

## In-Scope

The following components and features will be developed:

- **Natural-Language Query Interface:** The system exposes an API endpoint (and optionally a minimal UI) where users can submit plain-English requests (e.g. "Extract all news headlines from example.com").
- **LLM Extraction Logic Generator:** A service that sends the user's query and page content to a Large Language Model (e.g. GPT/Gemini) which outputs extraction instructions (CSS selectors, XPath, or regex).
- **Headless Browser Worker:** A Playwright-based worker that fetches web pages (executing JavaScript if needed) and applies extraction logic to collect data.
- **Scheduling Service and History:** Ability for users to create cron-like schedules for periodic data extraction. Each run is logged in PostgreSQL for audit and tracking.
- **FastAPI Backend:** A Python/FastAPI web service that exposes the REST API for user interactions (task submission, status, result, schedule management) and orchestrates the above components.
- **Authentication & Authorization:** Implementation of JWT-based user accounts, with token issuance (/auth) and protected endpoints as per requirements.
- **Containerization:** All services (API, Scheduler, Workers, Redis, Postgres) will be containerized with Docker, orchestrated via Docker Compose for easy deployment.
- **Automated Testing:** Comprehensive test suite (unit/integration) covering models, services, and workflows to ensure correctness and quality.
- **Documentation:** Full technical and user documentation, including architecture diagrams, API references, user guide, and retrospective.

## Out-of-Scope

To keep the project focused, the following are explicitly excluded:

- **Large-Scale Distributed Crawling:** No massive web crawler or cluster setup for scraping the entire web. Only user-specified sites are targeted, not bulk crawl operations.
- **Advanced Anti-bot Measures:** Features like proxy rotation, CAPTCHA solving, or advanced bot evasion techniques are not included.
- **Custom ML Model Training:** We will not develop new LLM models; we integrate existing LLM APIs (e.g., OpenAI, Gemini) for prompt-based extraction.
- **User Interface (Frontend):** A full-featured web UI is out of scope. The focus is on a backend API (and possibly minimal admin pages) for data extraction.
- **Export Formats:** Only basic JSON results (and CSV via downstream tools) are provided; rich report generation (PDFs, dashboards) is not covered.
- **Third-Party Scraping APIs:** The system does not rely on external scraping services; it fetches pages directly via the headless worker.

This scoping ensures the diploma project emphasizes the core LLM-powered extraction and scheduling functionality without unnecessary features.
