## **Project: Intellectual Web Data Aggregator**

### `EPIC #1: 🏗️ Project Foundation & Infrastructure Setup`

*Цель: Подготовить окружение для разработки, включая структуру проекта, контейнеризацию и базу данных.*

- **`Task #101`**: `[Setup]` Initialize Git repository with a clear README.md and .gitignore.
- **`Task #102`**: `[Architecture]` Define the project's microservice directory structure (e.g., `/services/api`, `/services/playwright-worker`, etc.).
- **`Task #103`**: `[Backend]` Initialize the FastAPI application for the main API service.
- **`Task #104`**: `[Database]` Define the initial database schema using SQLAlchemy models. Required tables: `scraping_tasks`, `parsers_cache`.
- **`Task #105`**: `[Database]` Set up Alembic for database migrations. Create the first migration.
- **`Task #106`**: `[Containerization]` Create initial `Dockerfile` for the FastAPI service.
- **`Task #107`**: `[Containerization]` Create a `docker-compose.yml` file to orchestrate the API service and a PostgreSQL database.
- **`Task #108`**: `[CI/CD]` Set up a basic CI pipeline (e.g., GitHub Actions) to run linters (Flake8/Ruff) and formatters (Black/Ruff) on every push.

---

### `EPIC #2: 📡 Core API & User Interaction`

*Цель: Реализовать основной эндпоинт для приёма запросов от пользователя и управления асинхронными задачами.*

- **`Task #201`**: `[API]` Implement `POST /api/v1/process` endpoint to accept `url` and `prompt`.
- **`Task #202`**: `[API]` Define Pydantic models for request validation (`ScrapeRequest`) and response (`TaskStatus`, `ScrapeResult`).
- **`Task #203`**: `[Async]` Integrate a task queue (e.g., Celery with Redis/RabbitMQ) to handle long-running scraping tasks asynchronously.
- **`Task #204`**: `[API]` The `POST /api/v1/process` endpoint should create a task and immediately return a `task_id`.
- **`Task #205`**: `[API]` Implement `GET /api/v1/status/{task_id}` endpoint to check the status of a task (e.g., `PENDING`, `IN_PROGRESS`, `SUCCESS`, `FAILED`).
- **`Task #206`**: `[API]` Implement `GET /api/v1/result/{task_id}` endpoint to retrieve the final data once the task is complete.
- **`Task #207`**: `[Docs]` Ensure all endpoints are well-documented in OpenAPI/Swagger with examples.

---

### `EPIC #3: 🌐 Web Data Acquisition Module (Playwright Worker)`

*Цель: Создать отдельный сервис, который будет выполнять "грязную" работу по запуску браузера и сбору данных со страницы.*

- **`Task #301`**: `[Worker]` Create a new service for the Playwright worker.
- **`Task #302`**: `[Containerization]` Create a `Dockerfile` for the Playwright worker service (it requires installing browser dependencies).
- **`Task #303`**: `[Worker]` Implement a Celery task that takes a URL as input.
- **`Task #304`**: `[Worker]` Inside the task, use Playwright to navigate to the URL in headless mode.
- **`Task #305`**: `[Worker]` Implement logic to capture and save `document.body.innerText`.
- **`Task #306`**: `[Worker]` Implement logic to intercept and save all network requests (especially XHR/Fetch) into a HAR-like structure or a simple list of responses.
- **`Task #307`**: `[Architecture]` Update `docker-compose.yml` to include the Playwright worker and the task queue broker (Redis/RabbitMQ).

---

### `EPIC #4: 🧠 LLM Integration & Intelligence Pipeline`

*Цель: Реализовать основную бизнес-логику, включающую взаимодействие с LLM для анализа, генерации и валидации.*

- **`Task #401`**: `[LLM]` Create an abstraction layer/client for interacting with the LLM API (e.g., OpenAI, Anthropic). Handle API keys and retries.
- **`Task #402`**: `[LLM-Prompt]` **Prompt Engineering (Intent):** Design a prompt that takes the user's free-form text and extracts a structured intent (e.g., `{"target": "job links", "keywords": ["Software Engineer", "Senior"]}`).
- **`Task #403`**: `[Core Logic]` Implement the step to find examples of the target data within the captured `innerText` using the keywords from the LLM.
- **`Task #404`**: `[Core Logic]` Implement the logic to locate the origin of these examples within the captured network sources (main document HTML, JSON from an XHR, etc.).
- **`Task #405`**: `[Core Logic]` Implement a function to extract a small, relevant code snippet around the found example to use as context for the LLM.
- **`Task #406`**: `[LLM-Prompt]` **Prompt Engineering (Regex Generation):** Design a robust prompt for generating a regular expression. It should include the code snippet, the desired output, and rules for creating a good, non-greedy regex.
- **`Task #407`**: `[Core Logic]` Implement the validation step: test the generated regex against the full source content.
- **`Task #408`**: `[LLM-Prompt]` **Prompt Engineering (Refinement):** Design a "fix-it" prompt that takes the faulty regex, the incorrect results, and the source, and asks the LLM to provide a corrected version.
- **`Task #409`**: `[Core Logic]` Implement the iterative loop for regex refinement (Generate -> Test -> Refine -> Test).

---

### `EPIC #5: 💾 Caching & Persistence Layer`

*Цель: Сохранять успешные результаты работы LLM для повторного использования и ускорения будущих запросов.*

- **`Task #501`**: `[Database]` Finalize the `parsers_cache` table schema. It should include: `url_pattern`, `user_intent`, `generated_regex`, `source_type` (e.g., 'HTML', 'JSON'), `source_identifier` (e.g., URL of the XHR request), `created_at`.
- **`Task #502`**: `[Core Logic]` At the start of a new task, implement a check against the `parsers_cache` table. The check should match both the URL and the user intent.
- **`Task #503`**: `[Core Logic]` If a cached parser is found, the system should skip the entire LLM generation pipeline (EPIC #4) and directly use the cached regex.
- **`Task #504`**: `[Core Logic]` Upon successful generation and validation of a new regex, implement the logic to save it to the `parsers_cache` table.

---

### `EPIC #6: ✅ Quality Assurance & Documentation`

*Цель: Обеспечить стабильность и надежность системы через автоматизированное тестирование и качественную документацию.*

- **`Task #601`**: `[Tests]` Set up `pytest` and `pytest-cov` for test execution and coverage reports.
- **`Task #602`**: `[Tests]` Write unit tests for all Pydantic models and core utility functions (e.g., context snippet extractor).
- **`Task #603`**: `[Tests]` Write integration tests for the API endpoints. Use `httpx` and `TestClient` from FastAPI.
- **`Task #604`**: `[Tests]` Mock the LLM API calls during tests to avoid real API usage and ensure predictable results.
- **`Task #605`**: `[Tests]` Create mock data (sample HTML, JSON files) to test the Playwright worker and regex validation logic.
- **`Task #606`**: `[Tests]` Write an end-to-end test for a single, simple use case.
- **`Task #607`**: `[CI/CD]` Configure the CI pipeline to run the full test suite on every push to the main branch. Fail the build if tests fail or coverage drops below 70%.
- **`Task #608`**: `[Docs]` Thoroughly review and enhance the auto-generated Swagger documentation with clear descriptions and examples for each field and endpoint.

---

### `EPIC #7: 🚀 Deployment & Finalization`

*Цель: Подготовить проект к демонстрации и написать сопроводительную документацию для дипломной работы.*

- **`Task #701`**: `[Infra]` Create a `.env.example` file with all necessary environment variables (DB credentials, LLM API keys, etc.).
- **`Task #702`**: `[Containerization]` Finalize the `docker-compose.yml` file to ensure all services start correctly and can communicate with each other.
- **`Task #703`**: `[Docs]` Write a comprehensive `README.md` that explains the project's architecture, how to set it up locally using Docker Compose, and how to use the API.
- **`Task #704`**: `[Diploma]` Write the technical chapter of the diploma thesis, describing the architecture, technologies used, challenges faced, and solutions found.
- **`Task #705`**: `[Diploma]` Prepare a presentation and/or a live demo of the project.