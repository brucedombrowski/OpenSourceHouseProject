#!/usr/bin/env bash
set -euo pipefail

# Run from repo root; sets up venv, installs deps, creates admin, seeds sample data, starts server.

cd "$(dirname "$0")"

HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8000}

# Create or reuse venv
if [ ! -d "venv" ]; then
  python3 -m venv venv
fi
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Apply migrations
python manage.py migrate

# Create superuser if missing (defaults can be overridden via env vars)
python manage.py shell <<'PY'
import os
from django.contrib.auth import get_user_model

username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "adminpass")

User = get_user_model()
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
    print(f"Created superuser '{username}'")
else:
    print(f"Superuser '{username}' already exists; skipping create")
PY

# Optional seed data
python manage.py import_wbs_csv data/wbs_items_template.csv --update
python manage.py import_dependencies_csv data/wbs_dependencies_template.csv --update
python manage.py rollup_wbs_dates
python manage.py rollup_wbs_progress

# Pick a free port (defaults from PORT env; tries a small range)
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
