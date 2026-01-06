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
| Repository | GitHub - marchanyanehu/diploma_v1 |
| API Docs | [Swagger UI](/docs) (Available at /docs on running server) |
| Design | (No external design documents) |

**Elevator Pitch**

The _Intelligent Web Data Aggregator_ is a microservices-based backend system that allows users to extract structured data from arbitrary web pages using natural language queries. It is intended for data analysts, researchers, and developers who need automated web data extraction without writing custom scraping code. The system accepts a URL and a human-friendly prompt (e.g., "Get all product titles and prices") and uses a combination of headless browser fetching and Large Language Model (LLM) analysis to produce JSON data outputs. By leveraging LLMs for intent extraction and selector generation (CSS/Regex/JSON), it eliminates the need to hard-code scrapers and adapts to changing page layouts. Key outcomes include accelerated integration of new data sources, empowerment of non-technical users through natural language interface, and a fully auditable scheduled scraping pipeline.

**Evaluation Criteria Checklist**

| #   | Criterion | Status | Documentation |
| --- | --- | --- | --- |
| 1   | Requirements & Use Cases | ✅   | criteria/requirements.md |
| 2   | Architecture & Design | ✅   | criteria/architecture.md |
| 3   | Implementation & Code Quality | ✅   | criteria/code-quality.md |
| 4   | Testing & Quality Assurance | ✅   | criteria/testing.md |
| 5   | Security & Error Handling | ✅   | criteria/security.md |
| 6   | Performance & Scalability | ✅   | criteria/performance.md |
| 7   | Documentation & Deployment | ✅   | criteria/documentation.md |

**Documentation Navigation**

- [Project Overview](01-project-overview/index.md) - Business context, goals, stakeholders, and features.
- [Technical Implementation](02-technical/index.md) - System architecture, tech stack, deployment, and design decisions.
- [User Guide](03-user-guide/index.md) - Instructions for using the system.
- [Retrospective](04-retrospective/index.md) - Lessons learned and future improvements.
- [Appendices](appendices/api-reference.md) - API Reference, Database Schema, and Glossary.


_Document created: 2025-01-05_  
_Last updated: 2025-01-05_
