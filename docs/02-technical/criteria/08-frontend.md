# Criterion: Frontend (MVP)

## Description
The system includes a minimal, functional web interface to allow users to interact with the innovative backend capabilities (LLM extraction, querying) without using raw API calls.

## Component: `diploma_frontend`
- **Type**: Single Page Application (SPA).
- **Technology**: HTML5, CSS3, Vanilla JavaScript.
- **Serving**: Served as static files via Nginx container (`diploma_frontend`).
- **Integration**: Communicates with the Backend API via REST.

## Core Features
1. **User Registration/Login**: JWT-based authentication flow.
2. **Dashboard**: View active tasks and jobs.
3. **Query Interface**: Input form for natural language scraping requests.
4. **Results View**: Display of extracted JSON data and status updates.

## Design Rationale
A "Basic MVP" approach was chosen to strictly limit scope and focus effort on the Backend/LLM complexity, while still providing a usable interface for demonstration and testing.
