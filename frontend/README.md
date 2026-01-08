# Web Data Aggregator - Frontend

A clean, simple frontend for the Intelligent Web Data Aggregator API.

## Features

- 🔐 **Authentication** - Login and registration
- 🔍 **Create Scraping Tasks** - Submit URLs with natural language prompts
- 📋 **Task History** - View all your scraping tasks and their results
- ⏰ **Scheduled Jobs** - Create and manage automated scraping schedules
- 📊 **Result Visualization** - View extracted data in tables or JSON format

## Running the Frontend

### Option 1: Simple HTTP Server (Python)

```bash
cd frontend
python -m http.server 3000
```

Then open http://localhost:3000 in your browser.

### Option 2: Using Live Server (VS Code)

1. Install the "Live Server" extension in VS Code
2. Right-click on `index.html`
3. Select "Open with Live Server"

### Option 3: Using Node.js

```bash
npx serve frontend -p 3000
```

## Configuration

The API base URL is configured in `app.js`:

```javascript
const CONFIG = {
    API_BASE_URL: 'http://localhost:8000',  // Change this to your API URL
    // ...
};
```

## API Requirements

The frontend expects the following API endpoints to be available:

- `POST /auth/register` - User registration
- `POST /auth/token` - User login (OAuth2 password flow)
- `POST /api/v1/process` - Create scraping task
- `GET /api/v1/status/{task_id}` - Get task status
- `GET /api/v1/result/{task_id}` - Get task result
- `GET /api/v1/users/me/activity` - Get user's tasks and scheduled jobs
- `POST /api/v1/jobs` - Create scheduled job
- `DELETE /api/v1/jobs/{job_id}` - Delete scheduled job

## CORS Configuration

Make sure your API allows CORS from your frontend origin. Example FastAPI configuration:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Screenshots

### Login Screen
Clean authentication with login/register toggle.

### Dashboard
- **New Scrape Tab**: Create scraping tasks with example prompts
- **Task History Tab**: View all tasks with status badges
- **Scheduled Jobs Tab**: Manage automated scraping schedules

### Results Display
- Tabular view for structured data
- JSON view for complex nested data
- Processing time and item count metadata
