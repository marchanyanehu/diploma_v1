# Project Scope

## In Scope ✅

| Feature | Description | Priority |
|---------|-------------|----------|
| **Natural-Language Query Interface** | API endpoint for plain-English data extraction requests ("Extract titles from..."). | Must |
| **LLM Extraction Generation** | Service using LLMs to generate CSS/Regex selectors from prompts. | Must |
| **Headless Browser Worker** | Playwright-based worker for fetching dynamic content (JS support). | Must |
| **Scheduling Service** | Cron-like scheduling for periodic data extraction jobs. | Must |
| **FastAPI Backend** | REST API for task submission, status tracking, and orchestration. | Must |
| **Frontend MVP** | Basic web interface (SPA) for task submission and monitoring. | Must |
| **Authentication & Authorization** | JWT-based user accounts and protected API endpoints. | Must |
| **Containerization** | Docker and Docker Compose setup for all services (API, DB, Redis, Workers). | Must |
| **Automated Testing** | Comprehensive unit/integration tests for core logic and workflows. | Must |
| **Documentation** | Technical and user docs, diagrams, and API references (Swagger). | Must |

## Out of Scope ❌

| Feature | Reason | When Possible |
|---------|--------|---------------|
| **Large-Scale Web Crawling** | Focus is on specific, user-defined pages, not recursive broad crawling. | Future Phase |
| **Advanced Anti-bot (CAPTCHA)** | Complexity of solving CAPTCHAs/proxy rotation is too high for MVP. | Future Phase |
| **Custom LLM Training** | Using pre-trained APIs (Baseten/Gemini) is sufficient and strictly defined. | Never (Cost/Time) |

| **Rich Report Generation** | PDF/Dashboard exports are secondary to raw data access (JSON/CSV). | Future Phase |
| **Third-Party Scraping APIs** | Dependency on external paid scraping services is avoided for learning purposes. | Never |

## Assumptions

| # | Assumption | Impact if Wrong | Probability |
|---|------------|-----------------|-------------|
| 1 | **LLM API Availability** | If Baseten or Gemini are down or change pricing, extraction fails. | Low |
| 2 | **Target Site Structure** | Sites allow some level of access (not 100% Cloudflare blocked). | Medium |
| 3 | **Hardware Resources** | Host machine has enough RAM for Playwright (headless browser). | Low |

## Dependencies

| Dependency | Type | Owner | Status |
|------------|------|-------|--------|
| **Baseten/Gemini API** | External | Baseten/Google | ✅ |
| **Playwright Browser** | Technical | Microsoft | ✅ |
| **PostgreSQL** | Technical | Network | ✅ |

## Constraints

| Constraint Type | Description | Mitigation |
|-----------------|-------------|------------|
| **Time** | Diploma submission deadline is strict. | Scope limited to "Must Have" features; "Nice to Have" dropped if needed. |
| **Budget** | Limited budget for API tokens (Baseten/DeepSeek) and hosting. | Caching generated selectors to minimize repetitive LLM calls. |
| **Technology** | Must use Python, Docker, and PostgreSQL. | Standard, well-supported stack chosen. |
| **Personnel** | Single developer (Solo Project). | Leveraging high-level libraries (FastAPI, Playwright) to speed dev. |
