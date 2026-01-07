# 3\. User Guide

This section provides instructions for end users on how to use the application.

## Contents

- [Getting Started](#getting-started)
- [Features Walkthrough](features.md) - How to perform key tasks (via API).
- [FAQ & Troubleshooting](faq.md) - Common questions and issues.

## Getting Started

This project does not include a web UI. Users interact with the system via its REST API.

### Installation & Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/marchanyanehu/diploma_v1.git
   cd diploma_v1
   ```

2. **Configure Environment**:
   Copy `.env.example` to `.env` and fill in your API keys (Gemini/OpenAI) and database credentials.

3. **Start services**:
   ```bash
   docker-compose up --build
   ```

### First Task Example

1. **Register for an account**: 
   ```bash
   curl -X POST http://localhost:8000/auth/register \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "password": "yourpassword", "email": "test@example.com"}'
   ```

2. **Obtain a token**: 
   ```bash
   curl -X POST http://localhost:8000/auth/token \
     -d "username=testuser&password=yourpassword"
   ```

3. **Submit a scraping task**: 
   ```bash
   curl -X POST http://localhost:8000/api/v1/process \
     -H "Authorization: Bearer YOUR_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://example.com", "prompt": "Extract all headings"}'
   ```

4. **Poll status and retrieve results**: 
   Use `GET /api/v1/status/{task_id}` and `GET /api/v1/result/{task_id}`.

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
