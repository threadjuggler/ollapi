#!/bin/sh
set -e

echo "Running database migrations..."
n=0
until alembic upgrade head; do
  n=$((n + 1))
  if [ "$n" -ge 10 ]; then echo "Migrations failed after retries"; exit 1; fi
  echo "DB not ready / migration failed, retrying in 3s ($n/10)..."
  sleep 3
done

echo "Starting ollapi..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
