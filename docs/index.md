# Intelligent Web Data Aggregator

**Project Information**

| Field | Value |
| --- | --- |
| **Student** | Yan Marchan |
| **Group** | Informatics, 3rd Year |
| **Supervisor** | Evgeniy Tretyak |
| **Date** | 2025-01-06 |

**Links**

| Resource | URL |
| --- | --- |
| Production | Internal API Service (Deployment pending) |
| Repository | GitHub - marchanyanehu/diploma_v1 |
| API Docs | [Swagger UI](/docs) (Available at /docs on running server) |
| Design | N/A (Local microservices architecture) |

**Elevator Pitch**

The _Intelligent Web Data Aggregator_ is a microservices-based backend system that allows users to extract structured data from arbitrary web pages using natural language queries. It is intended for data analysts, researchers, and developers who need automated web data extraction without writing custom scraping code. The system accepts a URL and a human-friendly prompt (e.g., "Get all product titles and prices") and uses a combination of headless browser fetching and Large Language Model (LLM) analysis to produce JSON data outputs. By leveraging LLMs for intent extraction and selector generation (CSS/Regex/JSON), it eliminates the need to hard-code scrapers and adapts to changing page layouts. Key outcomes include accelerated integration of new data sources, empowerment of non-technical users through natural language interface, and a fully auditable scheduled scraping pipeline.

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
- [Appendices](appendices/glossary.md) - API Reference, DB Schema, System Limitations, and Example Dialogs.

_Document created: 2025-01-05_  
_Last updated: 2025-01-05_
