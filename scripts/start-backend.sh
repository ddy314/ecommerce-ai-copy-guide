#!/bin/sh
set -eu

alembic upgrade head
exec gunicorn \
  --bind "0.0.0.0:${APP_PORT:-8000}" \
  --workers "${WEB_CONCURRENCY:-1}" \
  --threads "${GUNICORN_THREADS:-4}" \
  --access-logfile - \
  --error-logfile - \
  backend.app:app
