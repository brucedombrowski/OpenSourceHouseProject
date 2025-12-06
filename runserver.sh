#!/usr/bin/env bash
set -euo pipefail

# Start Django dev server on the first free port, default host/port: 127.0.0.1:8000

cd "$(dirname "$0")"

HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8000}

# Activate venv if present
if [ -d "venv" ]; then
  source venv/bin/activate
fi

# Find a free port starting at PORT
PORT=$(HOST="$HOST" PORT="$PORT" python - <<'PY'
import os, socket

host = os.environ["HOST"]
start = int(os.environ["PORT"])

def free_port(host, start, attempts=10):
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
            except OSError:
                continue
            return port
    return None

port = free_port(host, start)
if port is None:
    raise SystemExit("No free port found; adjust PORT env var.")
print(port)
PY
)

echo "Starting dev server on ${HOST}:${PORT}"
python manage.py runserver "${HOST}:${PORT}"
