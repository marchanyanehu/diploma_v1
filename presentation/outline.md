# Presentation Outline (18 Slides)

This outline matches `presentation/slides.html` and focuses on **accurate, defensible** claims from the implemented repo (FastAPI + Celery + Playwright + Postgres/Redis + LLM-assisted extraction with caching/validation).

## Slide-by-slide plan

1. **Title**: Intelligent Web Data Aggregator — Diploma Project (student, supervisor, date).
2. **Motivation / Problem**: Why web data extraction is hard (dynamic pages, layout changes, manual effort).
3. **Goal & Scope**: What the system solves + explicit scope boundaries (async API, public pages, no CAPTCHA solving).
4. **Key Contributions**: Semantic content extraction, dual extraction paths, parser caching + auto-invalidation, security & ops basics.
5. **Architecture**: Microservices diagram (API, AI worker, headless worker, scheduler, Redis, Postgres, LLM).
6. **End-to-End Flow**: Request → intent extraction → fetch → extraction → cache → result.
7. **API Interface**: Auth + main endpoints; example request/response structure.
8. **Headless Worker (Playwright)**: JS rendering, semantic text + HTML capture, network signal capture, basic stealth.
9. **Intent & Safety**: LLM intent extraction + field normalization; prompt-injection sanitization.
10. **Extraction Pipeline**: Schema extraction vs single-field extraction; parser types (regex/CSS/JSONPath) + validation loop.
11. **Caching Strategy**: Per-domain + full URL + fields; cache hit path; auto-invalidation on failure.
12. **Scheduling**: Cron jobs per user via `/api/v1/jobs`; Celery Beat enqueues tasks.
13. **Persistence Model**: Users, scraping tasks, scheduled jobs, parser cache; JSONB intent/results.
14. **Reliability & Observability**: Correlation IDs, retries/timeouts, health endpoints, logs.
15. **Security Controls**: JWT auth, rate limiting, safe input handling, secrets via env.
16. **Testing & Quality**: Test layers; coverage report snapshot (total 78%).
17. **Demo Walkthrough**: Single extraction + scheduled extraction (what to show during defense).
18. **Conclusion & Next Steps**: Summary + future work (UI/dashboard, richer navigation, target-site auth, captcha strategy) + Q&A.
