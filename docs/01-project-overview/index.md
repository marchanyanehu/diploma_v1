# 1\. Project Overview

This section covers the business context, goals, and requirements for the project.

## Executive Summary

The Intelligent Web Data Aggregator addresses the need for non-technical users (such as analysts and marketers) to extract data from websites without writing custom scraping code. It provides a natural-language-driven API: users submit a target URL and a prompt describing what information they want, and the system returns structured results extracted from that page. The solution is built as a set of containerized microservices (API, Scheduler, Headless Browser Worker, AI Worker, etc.) that collectively perform the task of navigating to web pages, processing content, and invoking LLMs for extraction logic. Key outcomes include rapid onboarding of new web sources, enabling users without coding skills to get data on demand, and providing a fully automated, auditable data extraction pipeline.

## Key Highlights

| Aspect | Description |
| --- | --- |
| **Problem** | Non-technical users and analysts struggle to extract web data; existing scrapers are brittle and labor-intensive. |
| **Solution** | A Python/FastAPI backend with LLM-powered scraping. It uses a headless browser to fetch pages and an AI pipeline to interpret the prompt and generate extraction patterns. |
| **Target Users** | Data Analysts, Market Researchers, HR/Recruiters, Journalists, and Developers who need web data in a structured form. |
| **Key Features** | Natural language queries; Semantic content extraction; Intelligent extraction pipeline (CSS/Regex/JSON); Smart regex caching; Automated scheduling; Robust authentication and rate limiting. |
| **Tech Stack** | Python 3.11, FastAPI, SQLAlchemy, PostgreSQL, Redis, Celery, Docker, Playwright, Baseten (DeepSeek) & Gemini LLM APIs. |
