# Intelligent Web Data Aggregator

**Diploma Project by Yan Marchan, 3rd-year student**

## 🎯 Project Overview

An intelligent service that accepts a URL and a natural language prompt (e.g., "I want all the job listings") and automatically extracts the requested data using web scraping and Large Language Models (LLMs). The system uses Playwright to gather page data, and an LLM to analyze the request, find the target data, and generate validated regular expressions to extract it. Successful parsers are cached for future use.

## 🛠️ Technology Stack

- **Backend:** Python, FastAPI
- **Web Scraping:** Playwright (async version)
- **Database:** PostgreSQL
- **ORM / Migrations:** SQLAlchemy, Alembic
- **Async Tasks:** Celery with Redis broker
- **Testing:** Pytest, pytest-cov
- **Containerization:** Docker, Docker Compose
- **AI:** Large Language Model APIs (OpenAI API)
- **CI/CD:** GitHub Actions

## 🏗️ Architecture

Microservice-based architecture with the following core services:
- **API Service** (FastAPI) - Main REST API for user interactions
- **Playwright Worker** - Celery worker for web scraping using Playwright
- **PostgreSQL Database** - Data persistence
- **Redis Broker** - Task queue and caching

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.11+
- Git

### Local Development Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd diploma
   ```

2. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start the services:**
   ```bash
   docker-compose up --build
   ```

4. **Access the API:**
   - API Documentation: http://localhost:8000/docs
   - API Endpoints: http://localhost:8000/api/v1/

## 📡 API Usage

### Process a URL with Natural Language Prompt

```bash
curl -X POST "http://localhost:8000/api/v1/process" \
     -H "Content-Type: application/json" \
     -d '{
       "url": "https://example-jobs.com",
       "prompt": "I want all the job listings with their titles and locations"
     }'
```

Response:
```json
{
  "task_id": "uuid-here",
  "status": "processing"
}
```

### Check Task Status

```bash
curl "http://localhost:8000/api/v1/status/{task_id}"
```

### Get Results

```bash
curl "http://localhost:8000/api/v1/result/{task_id}"
```

## 🧠 How It Works

1. **User Request:** Submit URL + natural language prompt
2. **Web Scraping:** Playwright captures page content and network requests
3. **LLM Analysis:** AI analyzes the prompt and identifies target data patterns
4. **Regex Generation:** LLM generates regular expressions to extract the data
5. **Validation:** System validates and refines the regex
6. **Caching:** Successful parsers are cached for future use
7. **Results:** Extracted data is returned to the user

## 📁 Project Structure

```
diploma/
├── services/
│   ├── api/                 # FastAPI application
│   └── playwright-worker/   # Celery worker with Playwright
├── shared/                  # Shared models and utilities
├── tests/                   # Test suites
├── migrations/              # Alembic database migrations
├── docker-compose.yml       # Service orchestration
├── .env.example            # Environment variables template
└── README.md               # This file
```

## 🧪 Testing

Run the test suite:
```bash
pytest --cov=. --cov-report=html
```

## 📚 Development

This project follows modern Python development practices:
- Type hints throughout the codebase
- SOLID principles
- Clean architecture
- Comprehensive testing
- Automated CI/CD

## 📄 License

This project is developed as part of a diploma thesis.

## 👨‍💻 Author

**Yan Marchan** - 3rd-year Computer Science Student
