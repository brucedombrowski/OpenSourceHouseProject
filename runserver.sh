#!/usr/bin/env bash
set -euo pipefail

# Start Django dev server on a fixed port (default 127.0.0.1:8000)

cd "$(dirname "$0")"

HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8000}

# Activate venv (.venv preferred, fallback to venv)
if [ -d ".venv" ]; then
    source .venv/bin/activate
elif [ -d "venv" ]; then
    source venv/bin/activate
fi

echo "Starting dev server on ${HOST}:${PORT}"
python manage.py runserver "${HOST}:${PORT}"
