# Playwright worker Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Avoid interactive tzdata, etc.
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Workdir
WORKDIR /app

# Copy project
COPY . .

# Install project requirements (use top-level requirements from API to keep in sync)
COPY services/api/requirements.txt /tmp/requirements.txt
RUN pip install --upgrade pip && pip install -r /tmp/requirements.txt

# Copy entire repo (for shared modules and services)
COPY . /app

# Default environment values
ENV REDIS_URL=redis://redis:6379/0 \
    CELERY_BROKER_URL=redis://redis:6379/0 \
    CELERY_RESULT_BACKEND=redis://redis:6379/0

# Start Celery worker
CMD ["celery", "-A", "shared.celery_app.celery_app", "worker", "--loglevel=info", "-Q", "default"]
