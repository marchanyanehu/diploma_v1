# Presentation Outline (18-24 Slides)

## Structure
- **Title Slide** (1 slide)
- **Problem & Goals** (2-3 slides)
- **Solution Overview / Architecture** (2-3 slides)
- **Technical Implementation** (7 slides - 1 per criterion)
- **Demo / Screenshots** (2-3 slides)
- **Results / Retrospective** (1-2 slides)
- **Key Takeaways / Questions** (1 slide)

## Detailed Slide Plan

1.  **Title Slide**: Project Name, Student Name, Date.
2.  **Context**: The need for web data extraction in business.
3.  **Problem**: Manual scraping is brittle; Commercial tools are expensive.
4.  **Goals**: Build an LLM-powered, resilient, schedule-based extraction API.
5.  **Solution Architecture**: High-level diagram (FastAPI, Playwright, LLM Agent, Postgres).
6.  **Criterion 1: Backend (FastAPI)**: Async architecture, Pydantic models.
7.  **Criterion 2: Scraping (Playwright)**: Headless browser, dynamic content handling.
8.  **Criterion 3: AI Extraction**: Prompt engineering, CSS selector generation.
9.  **Criterion 4: Data Storage (Postgres)**: Schema design, JSONB for flexible data.
10. **Criterion 5: Scheduling (APScheduler)**: Recurring jobs logic.
11. **Criterion 6: Infrastructure (Docker)**: Containerization, docker-compose.
12. **Criterion 7: Quality Assurance**: Testing strategy (unit/integration).
13. **Key Features**: Natural language queries, self-healing selectors.
14. **Demo Scenarios**: extracting from a news site, scheduling a job.
15. **Results**: Success rate comparison (Regex vs LLM).
16. **Challenges & Solutions**: Managing LLM costs, anti-bot detection.
17. **Retrospective**: What went well, what could be improved.
18. **Conclusion & Q&A**.
