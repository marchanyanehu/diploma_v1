#!/bin/bash
set -e

echo "Running database migrations..."
cd /app
alembic upgrade head || echo "Migrations may have already been applied or failed - continuing..."

echo "Starting API server..."
exec uvicorn services.api.main:app --host 0.0.0.0 --port 8000 --workers 1
