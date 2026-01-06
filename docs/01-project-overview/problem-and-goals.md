# Problem Statement & Goals

## Context

Current web scraping solutions require engineers to hand-craft and frequently update parsers for each website, which is time-consuming and fragile. Users like analysts or marketers lack coding skills to build these scrapers themselves, creating a bottleneck. The market for on-demand data (e.g. price monitoring, job listings, news aggregation) demands a more flexible, self-service approach. Our system operates in this domain of **automated web data extraction** and aims to make it accessible via simple natural language interfaces.

## Problem Statement

**Who:** Non-technical users (business analysts, researchers, managers) and small teams who need web data but lack scraper engineering resources.  
**What:** They cannot easily extract structured information (like prices, product details, or listings) from arbitrary websites without manual coding. Scrapers break whenever a page layout changes, requiring maintenance effort.  
**Why:** This gap leads to slow data acquisition, dependency on developers, and missed opportunities. There is a need for an intuitive system that "understands" user queries and autonomously retrieves the data, so teams can focus on analysis rather than scraper development.

### Pain Points

| #   | Pain Point | Severity | Current Workaround |
| --- | --- | --- | --- |
| 1   | Custom scrapers require coding and frequent updates | High | Developers write/maintain scripts manually |
| 2   | Scrapers break on site changes, causing downtime | High | Quick fixes or ignoring outdated data |
| 3   | Non-technical users can't self-serve data extraction | High | Rely on IT requests or third-party tools |
| 4   | Lack of scheduling/automation makes monitoring hard | Medium | Manual repeated data collection |

## Business Goals

| Goal | Description | Success Indicator |
| --- | --- | --- |
| Accelerate source onboarding | Reduce time to integrate a new website via LLM-generated extraction patterns | Time to first results < 1 day (vs. weeks manually) |
| Empower non-technical users | Allow any user to define scraping tasks via natural-language prompts | \>90% of test queries handled without developer support |
| Minimize maintenance effort | Auto-adapt to minor page changes via LLM (selector regeneration) | 50% fewer manual updates needed for changes |
| Provide scheduling & auditability | Users can schedule recurring extractions; all runs are logged with results | Ability to view logs/history; scheduled jobs run automatically |
