&lt;!-- docs/index.md --&gt;

# Intelligent Web Data Aggregator

**Project Information**

| Field | Value |
| --- | --- |
| **Student** | Yan Marchan |
| **Group** | (Not applicable) |
| **Supervisor** | (Not applicable) |
| **Date** | 2025-01-05 |

**Links**

| Resource | URL |
| --- | --- |
| Production | (Not deployed) |
| Repository | [GitHub - marchanyanehu/diploma_v1](https://github.com/marchanyanehu/diploma_v1) |
| API Docs | [Swagger UI](/docs) (Available at /docs on running server) |
| Design | (No external design documents) |

**Elevator Pitch**

The _Intelligent Web Data Aggregator_ is a microservices-based backend system that allows users to extract structured data from arbitrary web pages using natural language queries[\[1\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L1-L5)[\[2\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L9-L17). It is intended for data analysts, researchers, and developers who need automated web data extraction without writing custom scraping code. The system accepts a URL and a human-friendly prompt (e.g., "Get all product titles and prices") and uses a combination of headless browser fetching and Large Language Model (LLM) analysis to produce JSON data outputs[\[1\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L1-L5)[\[3\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L28-L36). By leveraging LLMs for intent extraction and selector (CSS/Regex/JSON) generation, it eliminates the need to hard-code scrapers and adapts to changing page layouts. Key outcomes include accelerated integration of new data sources, empowerment of non-technical users through natural language interface, and a fully auditable scheduled scraping pipeline[\[2\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L9-L17)[\[4\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L70-L79).

**Evaluation Criteria Checklist**

| #   | Criterion | Status | Documentation |
| --- | --- | --- | --- |
| 1   | Back-end (FastAPI Service) | ✅   | criteria/01-backend.md |
| 2   | AI Assistant / Chatbot (LLM Integration) | ✅   | criteria/02-ai-assistant.md |
| 3   | Database (PostgreSQL) | ✅   | criteria/03-database.md |
| 4   | Microservices Architecture | ✅   | criteria/04-microservices.md |
| 5   | Automated Tests (≥ 70% coverage) | ✅   | criteria/05-testing.md |
| 6   | Containerization (Docker) | ✅   | criteria/06-containerization.md |
| 7   | API Documentation (Swagger/OpenAPI) | ✅   | criteria/07-api-docs.md |

**Documentation Navigation**

- [Project Overview](01-project-overview/index.md) - Business context, goals, stakeholders, and features.
- [Technical Implementation](02-technical/index.md) - System architecture, tech stack, deployment, and design decisions.
- [User Guide](03-user-guide/index.md) - Instructions for using the system.
- [Retrospective](04-retrospective/index.md) - Lessons learned and future improvements.

_Document created: 2025-01-05_  
_Last updated: 2025-01-05_

&lt;!-- docs/01-project-overview/index.md --&gt;

# 1\. Project Overview

This section covers the business context, goals, and requirements for the project.

## Executive Summary

The Intelligent Web Data Aggregator addresses the need for non-technical users (such as analysts and marketers) to extract data from websites without writing custom scraping code[\[2\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L9-L17)[\[1\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L1-L5). It provides a natural-language-driven API: users submit a target URL and a prompt describing what information they want, and the system returns structured results extracted from that page[\[1\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L1-L5)[\[5\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L30-L38). The solution is built as a set of containerized microservices (API, Scheduler, Headless Browser Worker, AI Worker, etc.) that collectively perform the task of navigating to web pages, processing content, and invoking LLMs for extraction logic[\[6\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L43-L51)[\[7\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L5-L13). Key outcomes include rapid onboarding of new web sources, enabling users without coding skills to get data on demand, and providing a fully automated, auditable data extraction pipeline[\[2\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L9-L17)[\[4\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L70-L79).

## Key Highlights

| Aspect | Description |
| --- | --- |
| **Problem** | Non-technical users and analysts struggle to extract web data; existing scrapers are brittle and labor-intensive[\[8\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L5-L13)[\[4\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L70-L79). |
| **Solution** | A Python/FastAPI backend with LLM-powered scraping. It uses a headless browser to fetch pages and an AI pipeline to interpret the prompt and generate extraction patterns[\[1\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L1-L5)[\[9\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L28-L37). |
| **Target Users** | Data Analysts, Market Researchers, HR/Recruiters, Journalists, and Developers who need web data in a structured form[\[10\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L9-L16). |
| **Key Features** | Natural language queries; Semantic content extraction; Intelligent extraction pipeline (CSS/Regex/JSON); Smart regex caching; Automated scheduling; Robust authentication and rate limiting[\[4\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L70-L79)[\[11\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L89-L96). |
| **Tech Stack** | Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery, Docker, Playwright, Baseten (DeepSeek) & Gemini LLM APIs[\[4\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L70-L79)[\[12\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L22-L30). |

&lt;!-- docs/01-project-overview/problem-and-goals.md --&gt;

# Problem Statement & Goals

## Context

Current web scraping solutions require engineers to hand-craft and frequently update parsers for each website, which is time-consuming and fragile[\[13\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L5-L14). Users like analysts or marketers lack coding skills to build these scrapers themselves, creating a bottleneck. The market for on-demand data (e.g. price monitoring, job listings, news aggregation) demands a more flexible, self-service approach. Our system operates in this domain of **automated web data extraction** and aims to make it accessible via simple natural language interfaces[\[2\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L9-L17)[\[4\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L70-L79).

## Problem Statement

**Who:** Non-technical users (business analysts, researchers, managers) and small teams who need web data but lack scraper engineering resources[\[13\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L5-L14)[\[10\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L9-L16).  
**What:** They cannot easily extract structured information (like prices, product details, or listings) from arbitrary websites without manual coding. Scrapers break whenever a page layout changes, requiring maintenance effort[\[13\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L5-L14)[\[3\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L28-L36).  
**Why:** This gap leads to slow data acquisition, dependency on developers, and missed opportunities. There is a need for an intuitive system that "understands" user queries and autonomously retrieves the data, so teams can focus on analysis rather than scraper development[\[13\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L5-L14)[\[2\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L9-L17).

### Pain Points

| #   | Pain Point | Severity | Current Workaround |
| --- | --- | --- | --- |
| 1   | Custom scrapers require coding and frequent updates | High[\[13\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L5-L14) | Developers write/maintain scripts manually |
| 2   | Scrapers break on site changes, causing downtime | High[\[13\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L5-L14) | Quick fixes or ignoring outdated data |
| 3   | Non-technical users can't self-serve data extraction | High[\[14\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L12-L20) | Rely on IT requests or third-party tools |
| 4   | Lack of scheduling/automation makes monitoring hard | Medium | Manual repeated data collection |

## Business Goals

| Goal | Description | Success Indicator |
| --- | --- | --- |
| Accelerate source onboarding | Reduce time to integrate a new website via LLM-generated extraction patterns | Time to first results < 1 day (vs. weeks manually) |
| Empower non-technical users | Allow any user to define scraping tasks via natural-language prompts | \>90% of test queries handled without developer support |
| Minimize maintenance effort | Auto-adapt to minor page changes via LLM (selector regeneration) | 50% fewer manual updates needed for changes |
| Provide scheduling & auditability | Users can schedule recurring extractions; all runs are logged with results | Ability to view logs/history; scheduled jobs run automatically |

&lt;!-- docs/01-project-overview/stakeholders.md --&gt;

# Stakeholders & Users

- **End Users (Data Analysts, Operations Staff):** Non-technical professionals who need data from various websites for analysis. They will directly use the API (or UI) to create scraping jobs and consume results. They value ease of use, reliability, and timely results[\[15\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L19-L28).
- **Business Sponsors (Product/Project Managers):** Decision-makers interested in business impact, such as faster time-to-insight and operational efficiency. They care about system delivering on promised goals (onboarding speed, maintenance reduction)[\[16\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L20-L28).
- **Technical Team (Backend Developers, Data Engineers, DevOps):** Responsible for building and maintaining the system. They design architecture (microservices, containers), ensure code quality (testing, CI/CD), and deploy infrastructure. Their concerns include scalability, reliability, and integration with external LLM APIs[\[17\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L27-L32)[\[6\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L43-L51).
- **Security/Compliance Officers:** Oversight for legal/ethical use of data. They ensure that scraping adheres to site policies (robots.txt, GDPR), and the system itself is secure against vulnerabilities. They insist on features like authentication (JWT), rate limiting, input sanitization, and audit logging[\[11\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L89-L96)[\[18\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L139-L147).
- **Administrator (Self-Service or Minimal UI):** Although the project is API-focused, if an admin or simple UI exists, that role could manage user accounts, view logs, and oversee scheduled jobs. (Currently, all management is via API endpoints.)

Each stakeholder contributes different perspectives: users define the functional needs (easy queries, scheduling), sponsors define success metrics (speed, cost savings), and technical/compliance teams define constraints (security, maintainability). Balancing these needs shaped the project design[\[15\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L19-L28)[\[19\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L99-L106).

&lt;!-- docs/01-project-overview/scope.md --&gt;

# Project Scope

## In-Scope

The following components and features will be developed:

- **Natural-Language Query Interface:** The system exposes an API endpoint (and optionally a minimal UI) where users can submit plain-English requests (e.g. "Extract all news headlines from example.com")[\[20\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L34-L43).
- **LLM Extraction Logic Generator:** A service that sends the user's query and page content to a Large Language Model (e.g. GPT/Gemini) which outputs extraction instructions (CSS selectors, XPath, or regex)[\[21\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L38-L41)[\[3\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L28-L36).
- **Headless Browser Worker:** A Playwright-based worker that fetches web pages (executing JavaScript if needed) and applies extraction logic to collect data[\[22\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L40-L43).
- **Scheduling Service and History:** Ability for users to create cron-like schedules for periodic data extraction. Each run is logged in PostgreSQL for audit and tracking[\[23\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L41-L44).
- **FastAPI Backend:** A Python/FastAPI web service that exposes the REST API for user interactions (task submission, status, result, schedule management) and orchestrates the above components[\[24\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L3-L11)[\[25\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L42-L45).
- **Authentication & Authorization:** Implementation of JWT-based user accounts, with token issuance (/auth) and protected endpoints as per requirements[\[26\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L12).
- **Containerization:** All services (API, Scheduler, Workers, Redis, Postgres) will be containerized with Docker, orchestrated via Docker Compose for easy deployment[\[27\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L33-L40).
- **Automated Testing:** Comprehensive test suite (unit/integration) covering models, services, and workflows to ensure correctness and quality[\[28\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md#L73-L82)[\[29\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TESTING_SUMMARY.md#L90-L99).
- **Documentation:** Full technical and user documentation, including architecture diagrams, API references, user guide, and retrospective[\[19\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L99-L106)[\[30\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/USER_GUIDE.md#L81-L90).

## Out-of-Scope

To keep the project focused, the following are explicitly excluded:

- **Large-Scale Distributed Crawling:** No massive web crawler or cluster setup for scraping the entire web. Only user-specified sites are targeted, not bulk crawl operations[\[31\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L48-L55).
- **Advanced Anti-bot Measures:** Features like proxy rotation, CAPTCHA solving, or advanced bot evasion techniques are not included[\[31\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L48-L55).
- **Custom ML Model Training:** We will not develop new LLM models; we integrate existing LLM APIs (e.g., Baseten, Gemini) for prompt-based extraction[\[32\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L50-L53).
- **User Interface (Frontend):** A full-featured web UI is out of scope. The focus is on a backend API (and possibly minimal admin pages) for data extraction.
- **Export Formats:** Only basic JSON results (and CSV via downstream tools) are provided; rich report generation (PDFs, dashboards) is not covered.
- **Third-Party Scraping APIs:** The system does not rely on external scraping services; it fetches pages directly via the headless worker.

This scoping ensures the diploma project emphasizes the core LLM-powered extraction and scheduling functionality without unnecessary features[\[31\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L48-L55).

&lt;!-- docs/01-project-overview/features.md --&gt;

# Features & Requirements

## Epics Overview

| Epic | Description | Status |
| --- | --- | --- |
| **E1: Project Foundation & Infrastructure** | Set up repository, containers, CI/CD, and initial database migrations to enable development[\[33\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md#L7-L15). | ✅   |
| **E2: Core API & User Interaction** | Implement FastAPI endpoints for task submission (/api/v1/process), status polling, result retrieval, user registration, and token-based authentication[\[34\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L13)[\[35\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L101-L110). | ✅   |
| **E3: Playwright-based Web Data Acquisition** | Develop a Celery worker using Playwright to fetch pages and extract text/HTML for processing[\[36\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md#L34-L43)[\[37\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L40-L44). | ✅   |
| **E4: LLM Intelligence Pipeline** | Integrate LLM for intent extraction and selector (CSS/Regex/JSON) generation. Implement a unified extraction flow with validation loops for arbitrary field sets[\[3\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L28-L36)[\[38\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md#L46-L55). | ✅   |
| **E5: Caching & Persistence** | Design parsers_cache schema. Reuse successful regex parsers to speed up future queries and implement cache invalidation[\[39\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md#L62-L70). | ✅   |
| **E6: QA & Documentation** | Write extensive automated tests (unit, integration, performance) and complete system documentation (API docs, user guide, architecture)[\[40\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TESTING_SUMMARY.md#L71-L80). | ✅   |

## User Stories

### Epic 2: Core API & User Interaction

| ID  | User Story | Acceptance Criteria | Priority | Status |
| --- | --- | --- | --- | --- |
| US-201 | **As a user**, I want to submit a scraping request (URL + prompt) via POST /api/v1/process, so that I receive a task ID immediately[\[41\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L110-L118). | \- Returns task_id and status PENDING (HTTP 202) on valid input.<br>- Rejects invalid URLs or injection with 400 error. | Must | ✅   |
| US-202 | **As a user**, I want to check the status of my task via GET /api/v1/status/{task_id}, so that I know when it's done. | \- Returns current status (PENDING, IN_PROGRESS, SUCCESS, or FAILED) in JSON[\[42\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L158-L167).<br>- Includes timestamps and progress percentage when in-progress. | Must | ✅   |
| US-203 | **As a user**, I want to retrieve the results of my scraping task via GET /api/v1/result/{task_id}, so that I get the extracted data once available. | \- If task is complete (status=SUCCESS), returns JSON with data, metadata (e.g. total matches, used cache)[\[43\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L197-L205)[\[44\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L240-L249).<br>- If still in-progress, returns 202 with status. | Must | ✅   |

### Epic 3: Web Data Acquisition

| ID  | User Story | Acceptance Criteria | Priority | Status |
| --- | --- | --- | --- | --- |
| US-301 | **As a developer**, I want a headless browser worker to fetch the target page in full (including JavaScript content), so that the system can extract data even from dynamic websites. | \- On task creation, a Celery worker on queue fetching_queue loads the URL using Playwright.<br>- Stores page text (innerText) and network requests in DB[\[45\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L40-L48). | Must | ✅   |

### Epic 4: LLM Integration & Extraction

| ID  | User Story | Acceptance Criteria | Priority | Status |
| --- | --- | --- | --- | --- |
| US-401 | **As a user**, I want the system to understand my natural-language prompt and generate appropriate extraction patterns, so that relevant data is returned correctly. | \- LLM extracts intent keywords and fields, and generates selectors (CSS/Regex/JSON) for target data[\[3\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L28-L36).<br>- Generated patterns are validated and, if successful, used for data extraction. | Must | ✅   |
| US-402 | **As a user**, I want commonly requested data (like "title, price, description") to be extracted as associated fields, so that relationships between fields are preserved. | \- Extracted data groups values under field names as objects[\[46\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L39-L47).<br>- Output JSON maintains structural associations. | Should | ✅   |

### Epic 5: Caching & Scheduling

| ID  | User Story | Acceptance Criteria | Priority | Status |
| --- | --- | --- | --- | --- |
| US-501 | **As a user**, I want repeated scraping of the same site/prompt to be faster by reusing previously learned patterns, so that I get quicker responses on repeat queries. | \- Before invoking LLM pipeline, system checks parsers_cache for matching URL and intent[\[47\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L200-L209).<br>- If found, uses cached selector and skips LLM calls (response time significantly faster). | Should | ✅   |
| US-502 | **As a user**, I want to schedule recurring scraping jobs (cron), so that I can automatically collect updated data over time. | \- Provides POST /api/v1/jobs to create a schedule with fields (URL, prompt, cron).<br>- Celery Beat enqueues tasks per schedule and new runs appear in user's job list. | Could | ✅   |

&lt;!-- docs/02-technical/index.md --&gt;

# 2\. Technical Implementation

This section covers the technical architecture, design decisions, and implementation details.

## Contents

- [Tech Stack](tech-stack.md) - Technologies and key decisions.
- [Criteria Documentation](criteria/) - Design rationale for each evaluation criterion.
- [Deployment & DevOps](deployment.md) - Infrastructure setup and deployment instructions.

## Solution Architecture

### High-Level Architecture

graph TD  
User\[User/Client\] -->|REST API| API\[FastAPI Service\]  
API -->|SQL/ORM| DB\[(PostgreSQL)\]  
API -->|Celery Queue| Redis\[(Redis Broker)\]  
<br/>Scheduler\[Scheduler Service (Beat)\] -->|Checks DB| DB  
Scheduler -->|Schedules Task| Redis  
<br/>Redis -->|fetching_queue| Headless\[Headless Worker\]  
Redis -->|ai_queue| AI\[AI Worker\]  
<br/>Headless -->|Fetch Page| Web\[Target Website\]  
Headless -->|Stores Content| DB  
<br/>Headless -->|→| Redis  
AI -->|Reads Content| DB  
AI -->|Calls LLM| LLM\[LLM Provider\]  
AI -->|Stores Results| DB

_Figure: High-level component interactions in the system._

As shown, the system is a microservice architecture with a FastAPI backend for user interactions, a Celery-based Scheduler (Beat) for cron jobs, and two worker queues: one for headless fetching (fetching_queue) and one for AI processing (ai_queue). A Redis instance serves as the message broker and the storage for rate-limiting, while a PostgreSQL database stores all persistent data (users, tasks, schedules, cache, results)[\[7\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L5-L13)[\[48\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L210-L219). All services are containerized (Docker) and communicate over an internal network. Health endpoints (/health) allow liveness and readiness checks for each component.

### System Components

| Component | Description | Technology |
| --- | --- | --- |
| **API Backend** | Handles authentication and task management (create task, check status/result, schedule jobs). Orchestrates workers via Celery. | Python 3.11, FastAPI, Uvicorn[\[34\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L13) |
| **Celery Workers** | Background services performing: |     |
| <br>- **Headless Worker**: Fetch web pages using Playwright, extract semantic page text and network data. |     |     |
| <br>- **AI Worker**: Interpret prompt, generate regex via LLM, apply regex for data extraction. | Python, Celery, Redis, Playwright[\[45\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L40-L48)[\[3\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L28-L36) |     |
| **Scheduler** | Cron-like service (Celery Beat) that enqueues tasks per user-defined schedule in the database. | Python, Celery Beat, Redis[\[27\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L33-L40)[\[45\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L40-L48) |
| **Database** | Central PostgreSQL database for all data: |     |
| <br>- _Users_: Auth info |     |     |
| <br>- _ScrapingTasks_: Task metadata and results |     |     |
| <br>- _ScheduledJobs_: Cron definitions |     |     |
| <br>- _ParserCache_: Regex patterns for reuse | PostgreSQL 15, SQLAlchemy ORM[\[19\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L99-L106)[\[49\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L30-L38) |     |
| **Cache/Broker** | Redis used both as a Celery broker/back-end and a short-term cache/rate-limit store. | Redis (In-memory data store) |
| **External LLMs** | Baseten (DeepSeek) as primary provider with Google (Gemini) as fallback. Used to interpret prompts and generate extraction patterns. | Baseten API, Gemini API |

### Data Flow

- **User Request:** A client sends a JSON request (url + prompt) to POST /api/v1/process[\[41\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L110-L118).
- **Task Creation:** API service validates input, creates a ScrapingTask record (status=PENDING) and enqueues a Celery task to fetching_queue.
- **Headless Fetch:** Headless Worker pulls the task, loads the page in Playwright (using configured headless browser flags), and captures:
- Semantic content (innerText with markers)
- Full HTML
- Network responses (XHR JSON, etc.) It stores this raw content linked to the task[\[45\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L40-L48)[\[3\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L28-L36).
- **AI Processing:** A Celery task on ai_queue is started. The worker:
- Extracts intent (target/keywords/fields) from the prompt using an LLM (intent extraction module).
- Checks the parsers_cache (by URL and intent) for a matching selector[\[48\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L210-L219).
- If cache hit: use selector on stored content, skip LLM calls. Otherwise, proceed.
- **Extraction Pipeline:** The system invokes the intelligent extraction flow, generating selectors (CSS/Regex/JSON) from LLM analysis[\[46\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L39-L47).
- Validate and possibly refine selector (iterative LLM prompts) until adequate accuracy.
- Save successful selector to parsers_cache.
- Apply selector to full content to produce structured results (with text, confidence, etc.).
- **Result Delivery:** Final results (JSON records) and metadata (match count, used cache flag, timing) are saved to the ScrapingTask record (status=SUCCESS or FAILED). The user can retrieve via GET /api/v1/result/{task_id}.
- **Scheduling:** If the request was a scheduled job, the Scheduler (Beat) enqueues new tasks at the specified cron times automatically.

### Key Technical Decisions

| Decision | Rationale | Alternatives Considered |
| --- | --- | --- |
| **Microservices Architecture** | Allows independent scaling of components (API, workers, scheduler). Improves modularity and maintainability[\[6\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L43-L51)[\[50\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L110-L118). | Monolithic app (simpler but less scalable) |
| **Python & FastAPI** | Python has rich web scraping and ML libraries; FastAPI offers async support and automatic docs[\[34\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L13). | Node.js/Express (less mature ML libs), Flask (slower performance) |
| **Celery with Redis** | Proven combo for distributed task queues. Redis is fast, and Celery supports retries and scheduling. | RabbitMQ (more overhead to set up), RQ (less feature-rich) |
| **Playwright for Headless Fetch** | Modern JS support, active browser automation features, and Python integration. | Selenium (heavier, less performant), requests-HTML (no JS) |
| **SQLAlchemy ORM** | Strong support for complex schemas and migrations in Python. Ease of writing queries. | Django ORM (heavy for this project), raw SQL (verbose) |
| **LLM Integration via API** | Leverages state-of-art LLMs (Baseten/DeepSeek + Gemini fallback) for intent interpretation without building our own model. | Building custom NLP models (too time-consuming) |

### Security Overview

| Aspect | Implementation |
| --- | --- |
| **Authentication** | JWT tokens for all protected endpoints (/auth/register, /auth/token, then Bearer tokens)[\[26\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L12). Passwords hashed (bcrypt). |
| **Authorization** | User-specific resources (tasks, jobs) are scoped to the authenticated user (owner_id field)[\[51\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L32-L40). |
| **Rate Limiting** | slowapi (Redis-backed) enforces limits: e.g. /api/v1/process: 10/minute per IP[\[26\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L12). |
| **Input Validation** | All inputs validated via Pydantic schemas. User prompts are sanitized against injection/jailbreak patterns before processing[\[26\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L12)[\[18\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L139-L147). |
| **Encryption** | TLS is recommended in production. JWT secret stored in environment (SECRET_KEY), never in code[\[27\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L33-L40). |
| **Secrets Management** | API keys and database credentials are loaded from environment variables (see .env example) and not hard-coded[\[27\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L33-L40)[\[34\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L13). |

&lt;!-- docs/02-technical/tech-stack.md --&gt;

# Technology Stack

## Stack Overview

| Layer | Technology | Version | Justification |
| --- | --- | --- | --- |
| **Backend Language** | Python | 3.11 | Widely supported for web and ML; used in microservices[\[34\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L13). |
| **Web Framework** | FastAPI | ~0.95 (latest) | High-performance, async, automatic OpenAPI docs[\[34\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L13). |
| **Async Tasks** | Celery + Redis | Celery 5.x, Redis 7 | Mature distributed task queue and in-memory broker for decoupling workloads. |
| **Database** | PostgreSQL | 15.x | Reliable relational DB; SQLAlchemy ORM simplifies schema management[\[51\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L32-L40). |
| **ORM** | SQLAlchemy | 1.4+ | Robust for complex schemas and relations (tasks, caching, users)[\[49\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L30-L38). |
| **Headless Browser** | Playwright | Latest | Handles modern dynamic pages (JavaScript) in headless mode[\[22\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L40-L43). |
| **LLM APIs** | Baseten (DeepSeek), Gemini | Various | Provides intelligence without local model training. Baseten is primary; Gemini is fallback. |
| **Containerization** | Docker, Docker Compose | (n/a) | Ensures consistent environments; defines multi-container setup (API, DB, Workers)[\[27\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L33-L40)[\[52\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L1-L8). |
| **CI/CD** | GitHub Actions (implied) | \-  | Automates testing, linting, and deployment pipelines. |
| **Testing** | pytest, httpx | Latest | Comprehensive unit and integration tests (coverage >70%)[\[53\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TESTING_SUMMARY.md#L91-L100). |
| **Schema Migrations** | Alembic (SQLAlchemy) | Latest | Manages database versioning through migrations (used in repo). |

## Key Technology Decisions

### Decision 1: Python & FastAPI

**Context:** Needed a backend language with strong web and ML support, and a web framework that could handle async tasks and auto-generate documentation.  
**Decision:** Use Python 3.11 with FastAPI.  
**Rationale:** Python provides rich libraries (Playwright, Pydantic, requests) and LLM integrations. FastAPI is performant, async-capable, and automatically serves Swagger UI[\[34\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L13).  
**Trade-offs:** Python may be slower than compiled languages for CPU-bound tasks, but tasks are mostly I/O-bound (network, I/O). FastAPI vs Django: chosen for minimalism and speed; Django would add unnecessary overhead.

### Decision 2: Microservices & Docker

**Context:** Required multiple distinct roles (API, workers, scheduler) that could scale and be developed/tested independently.  
**Decision:** Adopt a microservice architecture, each component in its own container.  
**Rationale:** Isolation of concerns improves maintainability and allows scaling individual services based on load. Docker ensures consistency across dev, test, and prod.  
**Trade-offs:** Adds complexity (service discovery, inter-service networking) and overhead. Simpler monolith could have been easier to start, but less scalable. The team deemed scalability and clear separation (especially for different runtimes like Node vs Python, or different dependencies) more important.

### Decision 3: Redis & Celery for Task Queue

**Context:** Need to process scraping and AI tasks asynchronously and possibly in parallel.  
**Decision:** Use Celery with Redis as broker.  
**Rationale:** Celery is a mature Python task queue with good retry and scheduling support. Redis is fast and supports pub/sub. Both are widely used and fit well in Docker.  
**Trade-offs:** Requires running Redis server. Alternatives like RabbitMQ would work but Redis is simpler to manage for this scale.

## Development Tools

| Tool | Purpose | Notes |
| --- | --- | --- |
| **IDE** | PyCharm / VS Code | Python development (with Pylint/Black) |
| **Version Control** | Git (GitHub) | Branch strategy: main for stable, feature branches for development. Pull requests with code review. |
| **Package Manager** | pip + venv | Dependency isolation; requirements.txt at repo root. |
| **Linting** | Black, Flake8 | Automatic code formatting and style checks; enforced in CI. |
| **Testing** | Pytest | Unit & integration tests; coverage goal 70%+[\[53\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TESTING_SUMMARY.md#L91-L100). |
| **API Docs** | Swagger UI (FastAPI) | Auto-generated from code; available at /docs. |
| **Logging** | structlog or Python logging | Centralized structured logs; console output captured by Docker logging driver. |

## External Services & APIs

| Service | Purpose | Pricing Model |
| --- | --- | --- |
| **Baseten/DeepSeek** | Primary LLM provider for prompt processing | Subscription-based |
| **Gemini (Google)** | Fallback LLM provider | Free tier & paid options |
| **Email/SMS** (optional) | User notifications/alerts | Depends on chosen provider (Twilio, etc.) |
| _(Others)_ | _(Any other required third-party)_ |     |

&lt;!-- docs/02-technical/deployment.md --&gt;

# Deployment & DevOps

## Infrastructure

The system is deployed as Docker containers (API, Redis, Postgres, Workers, Scheduler) connected via a Docker network. A high-level deployment architecture:

flowchart LR  
subgraph "Cloud/Server/VM"  
API\["API Container (FastAPI)"\]  
Redis\["Redis (Broker/Cache)"\]  
Postgres\["Postgres DB"\]  
Scheduler\["Scheduler Container (Celery Beat)"\]  
Headless\["Headless Worker Container"\]  
AIWorker\["AI Worker Container"\]  
Network\[(Docker Network)\]  
end  
Browser\["User (via HTTP)"\] -->|HTTP| API  
API -->|SQL| Postgres  
API -->|CELERY| Redis  
Scheduler -->|CELERY| Redis  
Redis -->|fetching_queue| Headless  
Redis -->|ai_queue| AIWorker  
Headless -->|Fetch Web| Internet\["Target Websites"\]  
AIWorker -->|(calls LLM API)| Internet

- **Containers:**
- **PostgreSQL** (diploma_postgres): on port 5432. Stores all data. Healthchecks ensure readiness[\[52\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L1-L8).
- **Redis** (diploma_redis): on port 6379. Acts as Celery broker/back-end and stores rate limit counters[\[54\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L21-L29).
- **API Service** (diploma_api): on port 8000. Exposes REST endpoints. Depends on Redis and Postgres (via depends_on healthcheck)[\[55\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L35-L43).
- **Headless Worker** (diploma_headless_worker): No host port (internal). Runs Celery worker for page fetching (queue=fetching_queue). Uses Playwright; has shm_size: 1gb for Chromium.
- **AI Worker** (diploma_ai_worker): No host port. Runs Celery worker for LLM regex generation (queue=ai_queue).
- **Scheduler** (diploma_scheduler): No host port. Runs Celery Beat to enqueue scheduled jobs into Redis[\[56\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L150-L159).
- **Network:** All containers use a Docker network (diploma_network) allowing inter-container communication[\[57\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L178-L185).
- **Volumes:**
- postgres_data for PostgreSQL persistence.
- redis_data for Redis persistence.

### Environments

| Environment | URL / Access | Branch |
| --- | --- | --- |
| **Development (Local)** | <http://localhost:8000> (API) | main or feature branches |
| **Staging** | (not configured) | develop |
| **Production** | (not deployed) | (N/A) |

Typically, running locally or in a cloud VM via Docker Compose is used. The example above uses localhost as the base.

## CI/CD Pipeline

A CI/CD pipeline (e.g., GitHub Actions) can automate builds and tests on each push:

- **Commit / PR** triggers pipeline.
- **Build**: Check out code, set up Python/Docker environment.
- **Lint**: Run black --check, flake8, etc. to enforce code style.
- **Test**: Run pytest (unit & integration tests) to ensure no regressions[\[53\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TESTING_SUMMARY.md#L91-L100).
- **Security Scan**: (Optional) Use tools like \[Bandit/Snyk\] for vulnerability scanning.
- **Build & Push Docker Images**: If on main branch, build Docker images and push to registry.
- **Deploy**: Automated or manual deployment to target environment (could be as simple as docker-compose up --build on a VM).

### Pipeline Configuration (Example: .github/workflows/ci.yml)

name: CI/CD Pipeline  
on: \[push, pull_request\]  
jobs:  
build-test:  
runs-on: ubuntu-latest  
steps:  
\- uses: actions/checkout@v3  
\- name: Set up Python 3.11  
uses: actions/setup-python@v4  
with: {python-version: 3.11}  
\- name: Install dependencies  
run: pip install -r requirements.txt  
\- name: Lint  
run: |  
black --check .  
flake8 .  
\- name: Run tests  
run: pytest --cov=./

## Environment Variables

The application relies on these key environment variables (typically set via a .env file):

| Variable | Description | Required | Example |
| --- | --- | --- | --- |
| DB_HOST, DB_PORT | Database connection host/port | Yes | postgres, 5432 |
| DB_NAME, DB_USER, DB_PASSWORD | Database credentials | Yes | diploma_db, app_write, \*\*\* |
| REDIS_URL | Redis connection string | Yes | redis://redis:6379/0 |
| SECRET_KEY | Secret key for JWT signing | Yes | yoursecretkey |
| LLM_PROVIDER | Primary LLM service (e.g. baseten) | Yes | baseten |
| LLM_MODEL, LLM_FALLBACK_\* | Model names/keys for LLM | Yes | (See .env.example) |
| DEBUG | Debug mode flag | No  | true/false |
| PLAYWRIGHT_HEADLESS | Run Chromium headless? | No  | true |
| (Other PLAYWRIGHT_\*) | (Timeouts/retry settings for headless) | No  | (Defaults as in .env.example) |

Secrets such as API keys (OPENAI_API_KEY, GOOGLE_API_KEY, etc.) should be kept out of source control (use .env or CI secrets). The provided docker-compose.yml references many of these via \${VAR} placeholders[\[58\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L42-L50)[\[59\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L54-L62).

## How to Run Locally

### Prerequisites

- **Docker & Docker Compose** installed.
- Optional: Python 3.11 (for running without Docker).

### Setup Steps

\# 1. Clone the repository  
git clone <https://github.com/marchanyanehu/diploma_v1.git>  
cd diploma_v1  
<br/>\# 2. Copy environment file  
cp .env.example .env  
\# Edit .env to configure credentials (database, JWT secret, API keys, etc.)  
<br/>\# 3. Start services with Docker Compose  
docker-compose up --build

This will build images and start all services (Postgres, Redis, API, workers). The API will be accessible at **<http://localhost:8000>**.

Alternatively, one can run the API directly with Uvicorn (for development):

pip install -r requirements.txt  
uvicorn services.api.main:app --reload --host 0.0.0.0 --port 8000

## Verify Installation

- Open <http://localhost:8000/docs> to see the live API documentation (Swagger UI).
- The root endpoint (GET /) returns basic service info.
- Test health: GET /health and GET /api/v1/health should report service and DB connectivity.
- Try registering a user (POST /auth/register) and creating a task to verify full end-to-end flow.

## Monitoring & Logging

| Aspect | Tool/Approach | Dashboard URL (if any) |
| --- | --- | --- |
| **Application Logs** | Console logs (structured JSON) | (No central dashboard) |
| **Error Tracking** | (Not integrated) | N/A |
| **Performance** | (Not integrated) | N/A |
| **Health Checks** | /health endpoints, Docker healthchecks | (See /health in API) |

Monitoring can be added (e.g., Prometheus, Grafana, or external logging) in future work. Currently, logs can be viewed via docker-compose logs and health endpoints indicate liveness.

&lt;!-- docs/03-user-guide/index.md --&gt;

# 3\. User Guide

This section provides instructions for end users on how to use the application.

## Contents

- [Getting Started](getting-started.md) _(not applicable/no UI)_
- [Features Walkthrough](features.md) - How to perform key tasks (via API).
- [FAQ & Troubleshooting](faq.md) - Common questions and issues.

## Getting Started

This project does not include a web UI. Users interact with the system via its REST API. To get started:

- **Register for an account**: Send POST /auth/register with JSON body {"username": "...", "password": "...", "email": "..."}[\[60\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L77-L85).
- **Obtain a token**: Send POST /auth/token with form data username & password to receive a JWT access token[\[61\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L105-L113).
- **Use the API**: Include the token in the Authorization: Bearer &lt;token&gt; header in subsequent requests[\[62\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L110-L119).
- **Submit a scraping task**: POST /api/v1/process with JSON {"url": "&lt;target_url&gt;", "prompt": "&lt;what to extract&gt;"}[\[63\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L129-L137).
- **Poll status**: GET /api/v1/status/{task_id} until status = SUCCESS[\[42\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L158-L167).
- **Retrieve results**: GET /api/v1/result/{task_id} to receive JSON data with extracted items[\[43\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L197-L205).

Swagger UI at /docs (e.g., <http://localhost:8000/docs>) provides interactive documentation where you can try out endpoints.

## System Requirements

- A web browser or API client (curl/Postman).
- Access to the API host (by default, localhost:8000 for development).
- Valid user credentials and JWT token.

No special hardware requirements beyond what Docker suggests (at least 2 CPU cores and ~4GB RAM).

## Accessing the Application

- Open your browser or HTTP client.
- Navigate to http://&lt;server-host&gt;:8000/docs to explore the API.
- Obtain a token (POST /auth/token).
- Use the token in the Authorization header for protected endpoints.

## First Task Example

- **Create a Task**  

- curl -X POST <http://localhost:8000/api/v1/process> \\  
    \-H "Authorization: Bearer YOUR_TOKEN" \\  
    \-H "Content-Type: application/json" \\  
    \-d '{"url": "<https://example.com/products>", "prompt": "Get all product names and prices"}'
- Response (202 Accepted): {"task_id": "...", "status": "PENDING", "message": "Task created successfully"}.

- **Check Status**  

- curl -X GET <http://localhost:8000/api/v1/status/&lt;task_id>&gt; \\  
    \-H "Authorization: Bearer YOUR_TOKEN"
- Response: e.g. {"task_id": "...", "status": "IN_PROGRESS", ...}.

- **Get Results** (when complete)  

- curl -X GET <http://localhost:8000/api/v1/result/&lt;task_id>&gt; \\  
    \-H "Authorization: Bearer YOUR_TOKEN"
- Response: JSON with extracted data records.

## User Roles

- **Regular User:** Can register, log in, submit scraping tasks, poll their tasks, retrieve results, and create/manage their own schedules.
- **(Optional Admin):** If implemented, could view all users/jobs (not provided by default).

&lt;!-- docs/03-user-guide/features.md --&gt;

# Feature Walkthrough

## Feature 1: Submitting a Natural Language Query

**Overview:** Users can request data by sending a plain-English prompt. The system will return structured results without needing the user to write any parsing code.

### How to Use

- **Authentication**: Ensure you have a valid JWT token (see User Guide).
- **Submit Task**:

- curl -X POST "<http://localhost:8000/api/v1/process>" \\  
    \-H "Authorization: Bearer YOUR_TOKEN" \\  
    \-H "Content-Type: application/json" \\  
    \-d '{  
    "url": "<https://news.example.com>",  
    "prompt": "Find all article headlines and their publication dates"  
    }'

- A successful request returns {"task_id": "...", "status": "PENDING", "message": "Task created successfully"}.
- **Poll Status**:

- curl -X GET "<http://localhost:8000/api/v1/status/&lt;task_id>&gt;" \\  
    \-H "Authorization: Bearer YOUR_TOKEN"

- Repeat until status becomes SUCCESS or FAILED.
- Possible statuses: PENDING, IN_PROGRESS, SUCCESS, FAILED[\[42\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L158-L167).
- **Get Results**:

- curl -X GET "<http://localhost:8000/api/v1/result/&lt;task_id>&gt;" \\  
    \-H "Authorization: Bearer YOUR_TOKEN"

- On success, receives JSON like:

- {  
    "task_id": "...",  
    "status": "SUCCESS",  
    "url": "<https://news.example.com>",  
    "prompt": "Find all article headlines and their dates",  
    "data": \[  
    {"text": "Title 1", "source": "generated_regex", "confidence": 0.95},  
    {"text": "Title 2", "source": "generated_regex", "confidence": 0.93}  
    \],  
    "metadata": {"total_matches": 2, "used_cached_parser": false},  
    "processing_time": 4.2  
    }

- The data array contains extracted items with their confidence scores[\[43\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L197-L205).

**Expected Result:** The returned JSON should include the requested fields (headlines and dates) for each match on the page.

**Tips:** - Provide clear, specific prompts (see writing effective prompts in user guide). - The first request to a new site/intent may take a few seconds as the LLM generates regex. Subsequent similar requests may be faster due to caching[\[48\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L210-L219).

## Feature 2: Scheduling Recurring Jobs

**Overview:** Users can automate data extraction on a schedule (cron-like). The system supports both standard cron syntax and high-resolution (sub-minute) scheduling with 6-field cron expressions. For example, tracking high-frequency changes every 30 seconds.

### How to Use

- **Create a Scheduled Job**:

- curl -X POST "<http://localhost:8000/api/v1/jobs>" \\  
    \-H "Authorization: Bearer YOUR_TOKEN" \\  
    \-H "Content-Type: application/json" \\  
    \-d '{  
    "url": "<https://prices.example.com/daily>",  
    "prompt": "Get latest product prices",  
    "schedule_cron": "*/30 * * * * *"  
    }'

- **schedule_cron** supports both standard 5-field syntax and 6-field syntax (including seconds).
- Example "0 9 \* \* \*" = every day at 9:00 AM.
- Example "*/30 * * * * *" = every 30 seconds.
- **List Scheduled Jobs**:

- curl -X GET "<http://localhost:8000/api/v1/jobs>" \\  
    \-H "Authorization: Bearer YOUR_TOKEN"

- Returns a list of your jobs with their id, url, prompt, schedule_cron, next run time, etc[\[64\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L241-L250)[\[65\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L253-L261).
- **Delete a Scheduled Job**:

- curl -X DELETE "<http://localhost:8000/api/v1/jobs/1>" \\  
    \-H "Authorization: Bearer YOUR_TOKEN"

- Deletes job with ID 1. Returns confirmation message.

**Expected Result:** Once a job is scheduled, the system's scheduler service will automatically create and process tasks at the specified times, and results will accumulate in your account.

**Tips:** - Ensure cron expressions are valid (crontab.guru can help). - Monitor your jobs with GET /api/v1/jobs to see when they will run next.

### Keyboard Shortcuts

_(Not applicable: this is an API-based system; no keyboard shortcuts)_

### Feature Comparison

| Feature | Available to All Users |
| --- | --- |
| Single Extraction | ✅   |
| Multi-field Schema Extraction | ✅   |
| Scheduling Jobs | ✅   |
| Real-time Data | ✅ (subject to prompt and site behavior) |

&lt;!-- docs/03-user-guide/faq.md --&gt;

# FAQ & Troubleshooting

## Frequently Asked Questions

### General

**Q: Who can use this service?**  
A: Any user with an account can use the API to extract data from websites. It is designed for analysts or developers who need data without writing scrapers[\[10\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L9-L16).

**Q: How do I authenticate?**  
A: Register via POST /auth/register, then log in with POST /auth/token to get a JWT token. Include Authorization: Bearer &lt;token&gt; in all protected requests[\[60\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L77-L85)[\[62\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L110-L119).

**Q: What kinds of websites can be scraped?**  
A: Both static and dynamic sites are supported (via Playwright). However, sites requiring login or behind heavy anti-bot measures may not work without additional configuration.

**Q: How fast are the results?**  
A: Initial tasks may take a few seconds (due to LLM calls). Subsequent requests on the same URL/fields may be faster via cached regex patterns[\[48\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L210-L219). There are no hard SLAs for response time; this is an experimental system.

### Account & Access

**Q: How do I reset my password?**  
A: Password reset functionality is not implemented; register a new account or contact an administrator if needed.

**Q: Can I delete my account?**  
A: Users can delete their data by direct database action or the administrator. (Not available via public API.)

### Features

**Q: What if my prompt is not specific enough?**  
A: The AI may return incorrect or empty results. For best results, be clear about what fields you want (e.g. include field names, avoid vague requests)[\[66\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/USER_GUIDE.md#L154-L163)[\[67\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/USER_GUIDE.md#L166-L171).

**Q: How do I know the data sources (HTML path) used?**  
A: Each result includes a source field indicating how it was extracted (e.g. generated_regex or schema_extraction)[\[68\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/USER_GUIDE.md#L214-L223). Source paths (XPaths) are shown in result objects.

### Error Troubleshooting

| Problem | Possible Cause | Solution |
| --- | --- | --- |
| **401 Unauthorized** | Invalid or expired token | Request a new token via POST /auth/token |
| **422 Validation Error** | Invalid URL format or prompt too short | Ensure URL begins with http/https and prompt ≥ 5 chars |
| **400 Input rejected** | Prompt injection or banned content detected | Modify your prompt to remove suspicious phrases[\[18\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L139-L147) |
| **429 Too Many Requests** | Rate limit exceeded (too many API calls) | Wait and retry (limits: /process:10/min, /token:10/min, /register:5/min)[\[34\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L13) |
| **Status remains PENDING** | Workers may be down or busy | Ensure Celery workers (headless and AI) are running |
| **Status = FAILED** | Extraction or page load error | Check error message in status response; try altering prompt or URL |
| **No results returned** | Page didn't contain requested info or dynamic load failed | Verify the prompt context; ensure the site doesn't require login. Try manual inspection. |

### Troubleshooting Steps

- Check the [System Limitations](SYSTEM_LIMITATIONS.md) for known constraints (e.g. request size limits).
- Review [Example Dialogs](EXAMPLE_DIALOGS.md) for sample successful prompts.
- Use the Swagger UI (/docs) to interactively test endpoints and view models.
- If problems persist, check service logs (if accessible) for errors in the backend.

&lt;!-- docs/04-retrospective/index.md --&gt;

# 4\. Retrospective

This section reflects on the project development process, lessons learned, and future improvements.

## What Went Well ✅

### Technical Successes

- **Microservices Architecture:** Decoupling the system into API, workers, and scheduler made it easier to develop and test each component independently[\[6\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L43-L51)[\[69\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L71-L80).
- **LLM Integration:** Successfully used LLMs for prompt interpretation and selector generation, achieving structured data extraction without hardcoding rules.
- **Automated Testing:** Achieved high test coverage across layers (unit, integration, contract) with organized Pytest suites[\[70\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TESTING_SUMMARY.md#L90-L100). The comprehensive tests helped ensure system reliability.
- **Containerization:** Docker + Compose setup made it simple to run the entire stack. This streamlined setup was documented in the README[\[27\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L33-L40).
- **Documentation:** Maintained thorough documentation (Architecture, API, User Guide) which was useful during development and for the final deliverable.

### Process Successes

- **Agile Task Breakdown:** The task-oriented epics (as in the TASKS.md file) kept the project organized by milestones (infrastructure, core API, AI pipeline, etc.)[\[71\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md#L2-L15).
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

&lt;!-- docs/appendices/api-reference.md --&gt;

# API Reference

## Base URL

- **Development:** <http://localhost:8000>
- All endpoints are under the /api/v1 path (for versioning) or at the root for authentication and health.

## Authentication

The API uses JWT-based auth. Obtain a token via /auth/token and include it as:

Authorization: Bearer &lt;your_access_token&gt;

## Endpoints

### Auth & Health

- **POST /auth/register**  
    Create a new user account[\[60\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L77-L85).  
    **Body:** {"username": "user", "password": "pass123", "email": "<a@b.com>"}.  
    **Success (200):** {"id": 1, "username": "user", "email": "<a@b.com>", "is_active": true}[\[72\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L82-L90).  
    **Errors:** 400 if username exists; 429 if rate-limited.
- **POST /auth/token**  
    Obtain a JWT token[\[61\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L105-L113).  
    **Form Data:** username=user&password=pass123.  
    **Success (200):** {"access_token": "eyJ...","token_type":"bearer"}[\[62\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L110-L119).  
    **Errors:** 401 invalid credentials; 429 rate limit.
- **GET /**  
    Root endpoint. Returns basic API info (service name, version).  
    **Example Response (200):** {"message":"Intelligent Web Data Aggregator API","version":"1.0.0","status":"operational", ...}[\[73\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L24-L32).
- **GET /health**  
    Liveness probe. **Response:** {"status":"healthy","timestamp":"...","service":"api","version":"1.0.0","uptime":"operational"}[\[74\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L39-L48).
- **GET /api/v1/health**  
    Readiness with DB check. **Response:** includes {"database": {"status":"connected", ...}}[\[75\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L53-L62).

### Core API (Tasks)

_(All below require Authorization: Bearer &lt;token&gt;)_

- **POST /api/v1/process**  
    Create a new scraping task[\[63\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L129-L137).  
    **Body:** {"url": "&lt;target_url&gt;", "prompt": "&lt;what to extract&gt;"}.  
    **Rate-Limit:** 10/min per IP[\[26\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L12).  
    **Success (202):** {"task_id":"&lt;uuid&gt;","status":"PENDING","message":"Task created successfully"}[\[76\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L144-L152).  
    **Errors:** 400 if bad URL or prompt (including injection detected); 401 if not authenticated; 429 rate-limit.
- **GET /api/v1/status/{task_id}**  
    Poll status of a task[\[42\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L158-L167).  
    **Path Param:** task_id (string, UUID).  
    **Success (200):** JSON with task info, e.g.:  

- {  
    "task_id": "...",  
    "status": "IN_PROGRESS",  
    "progress": 40,  
    "message": null,  
    "created_at": "...",  
    "updated_at": "..."  
    }
- Possible statuses: PENDING, IN_PROGRESS, SUCCESS, FAILED[\[77\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L178-L187).  
    **Errors:** 401 if not auth; 403 if not owner; 404 if unknown ID.
- **GET /api/v1/result/{task_id}**  
    Retrieve results of a completed task[\[43\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L197-L205).  
    **Path Param:** task_id.
- If status=SUCCESS (200): Returns full data, e.g.:  

- {  
    "task_id": "...",  
    "status": "SUCCESS",  
    "url": "<https://example.com>",  
    "prompt": "...",  
    "data": \[  
    {"text": "...", "source": "...", "confidence": 0.92}  
    \],  
    "metadata": {"total_matches": 1, "used_cached_parser": false},  
    "processing_time": 3.21,  
    "created_at": "...", "completed_at": "..."  
    }
- If still processing (202): same structure as status endpoint with "status":"IN_PROGRESS" (see \[23†L157-L166\]).  
    **Errors:** 400 if task failed; 401/403 if unauthorized; 404 if not found.

### Scheduling

_(All below require auth)_

- **POST /api/v1/jobs**  
    Create a scheduled (cron) scraping job[\[44\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L240-L249).  
    **Body:** {"url": "...", "prompt": "...", "schedule_cron": "0 9 \* \* \*"}.  
    **Success (200):** JSON object of the new job, e.g.:  

- {  
    "id": 1,  
    "url": "<https://example.com>",  
    "prompt": "Get prices",  
    "schedule_cron": "0 9 \* \* \*",  
    "next_run_at": "2025-08-09T09:00:00Z",  
    "last_run_at": null,  
    "created_at": "2025-08-08T12:00:00Z"  
    }
- (Next run is computed by the scheduler)[\[78\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L246-L254)[\[79\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L255-L265).
- **GET /api/v1/jobs**  
    List all jobs for the current user[\[80\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L268-L285).  
    **Success (200):** JSON array of job objects (as above)[\[81\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L268-L276)[\[82\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L277-L285).
- **DELETE /api/v1/jobs/{job_id}**  
    Delete a scheduled job.  
    **Path Param:** job_id (integer).  
    **Success (200):** {"message":"Job deleted"}[\[83\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L288-L297).  
    **Errors:** 404 if no such job or not owned by user.
- **GET /api/v1/users/me/activity**  
    (Optional) Returns current user's recent tasks and jobs.  
    **Success (200):** e.g.:  

- {  
    "tasks": \[{ "task_id": "...", "status": "SUCCESS", ... }\],  
    "scheduled_jobs": \[{ "id":1, "url":"...", ...}\]  
    }
- (Not in minimal API; included as a helpful endpoint if implemented)[\[84\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L306-L315).

### Other Endpoints

- **POST /api/v1/test-task**  
    (For internal/test use) Creates a dummy task to verify DB connectivity[\[85\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L339-L348).  
    **Response:** {"message":"Test task created successfully","task":{...}}. Typically not used by end users.

## Error Responses

The API uses standard HTTP error codes. Common errors include:

| Code | Description |
| --- | --- |
| 200 | OK - success |
| 202 | Accepted - processing (async task started) |
| 400 | Bad Request - validation failed |
| 401 | Unauthorized - missing/invalid token |
| 403 | Forbidden - no permission on this resource |
| 404 | Not Found - invalid endpoint or ID |
| 422 | Unprocessable - input validation (Pydantic) |
| 429 | Too Many Requests - rate limit exceeded |
| 500 | Internal Server Error - unexpected failure |

Rate limits are enforced per-IP: 10/min for /api/v1/process, 5/min for /auth/register, 10/min for /auth/token[\[26\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L12).

## Swagger/OpenAPI

Interactive API documentation is available at /docs (Swagger UI) once the service is running. The OpenAPI JSON is also exposed at /openapi.json for integration or client generation[\[86\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L119-L128).

&lt;!-- docs/appendices/db-schema.md --&gt;

# Database Schema

## Overview

- **Database:** PostgreSQL 15 (managed via Docker container)[\[52\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L1-L8).
- **ORM:** SQLAlchemy (models defined in shared/database/models.py)[\[12\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L22-L30).
- **Schema Management:** Alembic is used for migrations (initial setup and subsequent changes).

## Entity Relationship Diagram

erDiagram  
    USERS ||--o{ SCRAPING_TASKS : owns  
    USERS ||--o{ SCHEDULED_JOBS : owns  
    SCRAPING_TASKS }o--|| TASK_SOURCE_DATA : has  
    SCRAPING_TASKS }o--|| TASK_INTENTS : has  
    SCRAPING_TASKS }o--|| PARSERS_CACHE : uses

_Figure: Simplified ER diagram showing core relationships (User-Tasks-Jobs, and task dependencies)._

## Tables

### users

Stores user credentials and status[\[49\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L30-L38).

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| id  | INTEGER | PK, AUTOINCREMENT | Unique user ID |
| username | VARCHAR(50) | NOT NULL, UNIQUE | Login name |
| hashed_password | VARCHAR(255) | NOT NULL | Bcrypt hashed password |
| email | VARCHAR(255) | UNIQUE | User's email (optional) |
| is_active | BOOLEAN | DEFAULT TRUE | Whether account is active |
| created_at | TIMESTAMP | DEFAULT NOW() | Account creation timestamp |

**Indexes:** on username, email[\[49\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L30-L38).

### scraping_tasks

Main table for tracking each scraping task[\[87\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L134-L144).

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| id  | INTEGER | PK, AUTOINCREMENT | Primary key |
| task_id | VARCHAR | UNIQUE, NOT NULL | External task UUID |
| url | TEXT | NOT NULL | Target page URL |
| user_prompt | TEXT | NOT NULL | Original user prompt |
| status | VARCHAR | NOT NULL DEFAULT 'PENDING' | Task status (PENDING/IN_PROGRESS/SUCCESS/FAILED) |
| error_message | TEXT | NULLABLE | Error text if failed |
| extracted_data | JSON | NULLABLE | Final data array (on SUCCESS) |
| total_matches | INTEGER | NULLABLE | Number of items extracted |
| processing_time_seconds | INTEGER | NULLABLE | Time taken (seconds) |
| used_cached_parser | BOOLEAN | NOT NULL DEFAULT FALSE | Whether a cached regex was used |
| created_at, started_at, completed_at | TIMESTAMP |     | Timestamps for creation, start, completion |
| owner_id | INTEGER | FK -> users.id | Ownering user (nullable if anonymous tasks) |
| intent_id | INTEGER | FK -> task_intents.id | Intent details (for query reuse) |
| used_parser_id | INTEGER | FK -> parsers_cache.id | Cached parser used (if any) |

**Relationships:** Each task optionally links to one TaskIntent (normalized prompt data) and one ParserCache entry (if cached regex was used)[\[88\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L157-L165)[\[48\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L210-L219).

### task_intents

Normalizes the components of user prompts[\[89\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L64-L73). Each task may reference one intent.

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| id  | INTEGER | PK, AUTOINCREMENT | PK  |
| target | TEXT | NULLABLE | Main object (e.g. "job listings") |
| keywords | JSON | NULLABLE | Array of keywords |
| schema_fields | JSON | NULLABLE | Array of requested field names |
| constraints | JSON | NULLABLE | Additional conditions (e.g. filters) |
| output_shape | TEXT | NULLABLE | Human-readable description of output |
| normalized_hash | VARCHAR | NULLABLE INDEX | Hash for intent matching |

_(plus timestamps and other columns for processing hints)※_[_\[89\]_](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L64-L73)_._

### task_source_data

Holds large source data for a task to keep scraping_tasks slim[\[90\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L94-L103).

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| id  | INTEGER | PK  | PK  |
| task_id | INTEGER | FK -> scraping_tasks.id (1:1) | Associated scraping task |
| page_content | TEXT | NULLABLE | innerText of page (structured text) |
| html_content | TEXT | NULLABLE | Full HTML of the page |
| network_requests | JSON | NULLABLE | Captured XHR/fetch responses (as JSON) |
| chosen_source_url | TEXT | NULLABLE | URL of content used (if multiple) |

### parsers_cache

Caches successful regex parsers to reuse[\[48\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L210-L219).

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| id  | INTEGER | PK  | PK  |
| url_pattern | VARCHAR | NOT NULL | Pattern (domain or URL regex) |
| domain_id | INTEGER | FK -> domains.id | Foreign key to domains table |
| user_intent | TEXT | NOT NULL | Normalized prompt text |
| intent_keywords | JSON | NULLABLE | Keywords for matching |
| target_data_type | VARCHAR | NULLABLE | e.g. "job_listings" |
| generated_regex | TEXT | NOT NULL | The regex pattern string |
| source_type | VARCHAR | NOT NULL | e.g. "HTML", "JSON", "SCHEMA" |
| source_identifier | TEXT | NULLABLE | e.g. XHR URL or HTML context |
| test_matches_count | INTEGER | NOT NULL | \# of matches found during test |
| confidence_score | INTEGER | NOT NULL DEFAULT 100 | Match percentage (0-100) |
| times_used | INTEGER | NOT NULL DEFAULT 0 | Usage count |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | If parser is still valid |
| created_at, last_used_at | TIMESTAMP | DEFAULT NOW() | Timestamps |

Each cached parser links one-to-many to scraping_tasks that used it[\[48\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L210-L219).

### scheduled_jobs

Stores user-defined cron tasks[\[91\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L258-L266).

| Column | Type | Constraints | Description |
| --- | --- | --- | --- |
| id  | INTEGER | PK  | PK  |
| url | TEXT | NOT NULL | Target page URL |
| prompt | TEXT | NOT NULL | User's extraction prompt |
| schedule_cron | VARCHAR | NOT NULL | Cron expression |
| is_active | BOOLEAN | NOT NULL DEFAULT TRUE | If the job is active |
| last_run_at | TIMESTAMP | NULLABLE | Timestamp of last execution |
| next_run_at | TIMESTAMP | NULLABLE | Next scheduled run time |
| owner_id | INTEGER | FK -> users.id (NOT NULL) | Owning user |
| created_at | TIMESTAMP | DEFAULT NOW() | Job creation time |

## Relationships

- **User → ScrapingTasks:** One-to-many (a user can have multiple tasks)[\[51\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L32-L40).
- **User → ScheduledJobs:** One-to-many (a user's jobs)[\[92\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L38-L41)[\[91\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L258-L266).
- **ScrapingTask → TaskIntent:** Many tasks can share one intent (the normalized prompt)[\[93\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L160-L169).
- **ScrapingTask → ParserCache:** (Optional) Many tasks can reuse the same parser entry[\[48\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L210-L219).
- **ScheduledJobs → (ScrapingTask):** Jobs spawn new tasks on schedule (history in separate log table, not shown).

_(For full schema details, see the source: shared/database/models.py_[_\[94\]_](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L22-L38)[_\[48\]_](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L210-L219)_.)_

## Migrations

Schema migrations are managed by Alembic. The first migration created all tables above. Subsequent migrations (if any) update columns or add indexes.

## Seeding

No default seed data is required. A test user and tasks can be added via scripts or directly in SQL for testing.

&lt;!-- docs/appendices/glossary.md --&gt;

# Glossary

| Term | Definition |
| --- | --- |
| **API** | Application Programming Interface - The set of HTTP endpoints provided by the backend for communication between the client and server[\[95\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L99-L108). |
| **LLM** | Large Language Model - An AI model (like GPT-4 or Gemini) that understands and generates text; used here to interpret user prompts and generate data extraction logic. |
| **Regex** | Regular Expression - A sequence of characters defining a search pattern. Used to extract structured data from HTML content. |
| **Semantic Content** | Structured page text with role markers (e.g. \[LINK:\], ## headings) produced by the headless browser for cleaner LLM input[\[96\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L31-L39). |
| **Celery** | An asynchronous task queue/job queue based on distributed message passing. Used to process scraping and AI tasks. |
| **Redis** | In-memory data store used as a message broker for Celery and as a cache for rate-limiting. |
| **JWT** | JSON Web Token - A compact, URL-safe means of representing claims to be transferred between two parties. Used here for stateless API authentication. |
| **Pydantic** | A Python library for data validation using type annotations. FastAPI uses it to define request/response schemas (models). |
| **Swagger UI** | Automatically generated web interface for interacting with the API; provided by FastAPI at /docs. |
| **Rate Limiting** | Technique to limit the number of requests a user or IP can make in a time period, to prevent abuse. Implemented via slowapi in the API[\[26\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L12). |
| **Playwright** | A headless browser automation library used to fetch and render web pages (even with JavaScript). |
| **Docker Compose** | A tool for defining and running multi-container Docker applications. Used to orchestrate services (API, DB, Redis, etc.). |
| **Prompt Injection** | A form of attack where malicious input attempts to alter the instructions given to the LLM. The system sanitizes prompts to prevent this. |
| **Parser Cache** | A store of previously generated regex patterns (parsers) for reuse on repeated tasks, improving performance[\[48\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L210-L219). |

## Acronyms

| Acronym | Full Form | Description |
| --- | --- | --- |
| **API** | Application Programming Interface | A set of endpoints for programmatic interaction with the backend. |
| **UI** | User Interface | The part of the system the user interacts with (none provided in this project). |
| **CSV** | Comma-Separated Values | A common text format for tabular data (can be generated from JSON results). |
| **JSON** | JavaScript Object Notation | A lightweight data-interchange format. Used for all API requests/responses. |
| **ORM** | Object-Relational Mapping | Technique for mapping database tables to code classes (SQLAlchemy is the ORM here). |

## Domain-Specific Terms

### Web Scraping

- **Scraping Task:** A user-request to extract data from a URL based on a prompt. Represented by a ScrapingTask record.
- **Extraction Pattern:** The regex or selectors generated by the LLM to find the requested data on the page.

### Data Extraction

- **Single-field Extraction:** The pipeline used when the prompt asks for one field; involves finding example text and generating a focused regex.
- **Intelligent Extraction:** The pipeline for structured requests; LLM returns structured output for all fields at once with relationships preserved.

_Document created: 2025-01-05_

[\[1\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L1-L5) [\[4\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L70-L79) [\[6\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L43-L51) [\[10\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L9-L16) [\[11\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L89-L96) [\[27\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md#L33-L40) README.md

<https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/README.md>

[\[2\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L9-L17) [\[8\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L5-L13) [\[13\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L5-L14) [\[14\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L12-L20) [\[15\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L19-L28) [\[16\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L20-L28) [\[17\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L27-L32) [\[20\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L34-L43) [\[21\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L38-L41) [\[22\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L40-L43) [\[23\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L41-L44) [\[25\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L42-L45) [\[31\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L48-L55) [\[32\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L50-L53) [\[37\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt#L40-L44) BA_reqs-Yan_Marchan.txt

<https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/reference_docs/BA/BA_reqs-Yan_Marchan.txt>

[\[3\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L28-L36) [\[5\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L30-L38) [\[7\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L5-L13) [\[9\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L28-L37) [\[19\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L99-L106) [\[46\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L39-L47) [\[50\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L110-L118) [\[69\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L71-L80) [\[86\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L119-L128) [\[96\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md#L31-L39) ARCHITECTURE.md

<https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/ARCHITECTURE.md>

[\[12\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L22-L30) [\[47\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L200-L209) [\[48\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L210-L219) [\[49\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L30-L38) [\[51\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L32-L40) [\[87\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L134-L144) [\[88\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L157-L165) [\[89\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L64-L73) [\[90\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L94-L103) [\[91\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L258-L266) [\[92\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L38-L41) [\[93\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L160-L169) [\[94\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py#L22-L38) models.py

<https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/shared/database/models.py>

[\[18\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L139-L147) [\[24\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L3-L11) [\[26\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L12) [\[34\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L5-L13) [\[35\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L101-L110) [\[41\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L110-L118) [\[45\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L40-L48) [\[95\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md#L99-L108) README_services_api.md

<https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/services/api/README_services_api.md>

[\[28\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md#L73-L82) [\[33\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md#L7-L15) [\[36\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md#L34-L43) [\[38\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md#L46-L55) [\[39\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md#L62-L70) [\[71\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md#L2-L15) TASKS.md

<https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TASKS.md>

[\[29\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TESTING_SUMMARY.md#L90-L99) [\[40\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TESTING_SUMMARY.md#L71-L80) [\[53\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TESTING_SUMMARY.md#L91-L100) [\[70\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TESTING_SUMMARY.md#L90-L100) TESTING_SUMMARY.md

<https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/TESTING_SUMMARY.md>

[\[30\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/USER_GUIDE.md#L81-L90) [\[66\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/USER_GUIDE.md#L154-L163) [\[67\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/USER_GUIDE.md#L166-L171) [\[68\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/USER_GUIDE.md#L214-L223) USER_GUIDE.md

<https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/USER_GUIDE.md>

[\[42\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L158-L167) [\[43\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L197-L205) [\[44\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L240-L249) [\[60\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L77-L85) [\[61\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L105-L113) [\[62\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L110-L119) [\[63\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L129-L137) [\[64\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L241-L250) [\[65\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L253-L261) [\[72\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L82-L90) [\[73\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L24-L32) [\[74\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L39-L48) [\[75\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L53-L62) [\[76\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L144-L152) [\[77\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L178-L187) [\[78\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L246-L254) [\[79\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L255-L265) [\[80\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L268-L285) [\[81\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L268-L276) [\[82\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L277-L285) [\[83\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L288-L297) [\[84\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L306-L315) [\[85\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md#L339-L348) README.md

<https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docs/api-docs/README.md>

[\[52\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L1-L8) [\[54\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L21-L29) [\[55\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L35-L43) [\[56\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L150-L159) [\[57\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L178-L185) [\[58\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L42-L50) [\[59\]](https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml#L54-L62) docker-compose.yml

<https://github.com/marchanyanehu/diploma_v1/blob/931c2980c9a459ade00ebf5706ce779450939e39/docker-compose.yml>