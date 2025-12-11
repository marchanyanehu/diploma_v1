# Playwright worker Dockerfile
FROM mcr.microsoft.com/playwright/python:v1.44.0-jammy

# Avoid interactive tzdata, etc.
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Workdir
WORKDIR /app

# Install project requirements (shared root requirements)
COPY requirements.txt /tmp/requirements.txt
RUN python -m pip install --upgrade pip \
    && pip install --no-cache-dir -r /tmp/requirements.txt \
    # Ensure playwright python package is present (base image usually has it)
    && pip install --no-cache-dir "playwright==1.44.0" \
    # Explicitly install browsers and system dependencies for reliability
    && python -m playwright install --with-deps chromium

# Copy repository code
COPY . /app

# Default environment values
ENV REDIS_URL=redis://redis:6379/0 \
    CELERY_BROKER_URL=redis://redis:6379/0 \
    CELERY_RESULT_BACKEND=redis://redis:6379/0

# Start Celery worker
CMD ["celery", "-A", "shared.celery_app.celery_app", "worker", "--loglevel=info", "-Q", "default"]
