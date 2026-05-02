#!/bin/sh
set -e

echo "Running Alembic migrations..."
alembic upgrade head

echo "Starting server on port ${PORT:-8000}..."
exec python -m uvicorn src.main:app \
    --host 0.0.0.0 \
    --port "${PORT:-8000}" \
    --workers 1
