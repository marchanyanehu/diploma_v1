# Video Demo Script (30s - 2m)

## Preparation
- Have the API running (`docker-compose up`).
- Open Swagger UI (`http://localhost:8000/docs`).
- Have a sample query ready (e.g., "Extract product names and prices from [URL]").

## Script

**0:00 - 0:10: Introduction**
"Hello, this is [Name]. This is a demo of my diploma project: an AI-Powered Web Scraper API."

**0:10 - 0:40: Creating a Scraping Job**
"Here in the Swagger UI, I'm creating a new scraping job. I simply provide the URL and a natural language description of what I want to extract."
*(Action: Execute POST /scrape endpoint)*

**0:40 - 1:00: Behind the Scenes (Logs/Console)**
"The system uses an LLM to analyze the page and generate CSS selectors. The headless browser then fetches the content."
*(Action: Show logs in terminal or simple UI response)*

**1:00 - 1:30: Viewing Results**
"The job is complete. Let's retrieve the data."
*(Action: Execute GET /jobs/{id} endpoint and show the JSON output)*

**1:30 - 1:45: Scheduling**
"We can also schedule this to run daily."
*(Action: Show POST /schedules endpoint)*

**1:45 - 2:00: Conclusion**
"This system solves the problem of brittle scrapers by adapting dynamically using AI. Thank you."
