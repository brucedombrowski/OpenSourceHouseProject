#!/usr/bin/env bash
# Stop common dev servers (Django runserver, ASGI servers, and listeners on common ports)
# Usage: ./stopAllServers.sh
# Optional env vars:
#   PORTS="8000 8001"   # space-separated ports to check
#   KILL_SIGNAL="TERM"  # signal to send (TERM or KILL)
set -euo pipefail

PORTS=${PORTS:-"8000 8001"}
KILL_SIGNAL=${KILL_SIGNAL:-TERM}

kill_listeners() {
  for port in $PORTS; do
    # Find listeners on the port (LISTEN state only)
    if pids=$(lsof -ti tcp:"${port}" -sTCP:LISTEN 2>/dev/null | tr '\n' ' '); then
      if [[ -n "${pids}" ]]; then
        echo "Stopping processes on port ${port} with SIG${KILL_SIGNAL}: ${pids}"
        # shellcheck disable=SC2086
        kill -s "${KILL_SIGNAL}" ${pids} || true
        # Give it a moment to exit gracefully
        sleep 0.5
        # If still running and TERM was used, force kill
        if [[ "${KILL_SIGNAL}" == "TERM" ]]; then
          remaining=$(lsof -ti tcp:"${port}" -sTCP:LISTEN 2>/dev/null | tr '\n' ' ' || true)
          if [[ -n "${remaining}" ]]; then
            echo "Forcefully killing remaining processes: ${remaining}"
            # shellcheck disable=SC2086
            kill -9 ${remaining} || true
          fi
        fi
      fi
    fi
  done
}

kill_by_pattern() {
  local patterns=(
    "manage.py runserver"
    "daphne"
    "uvicorn"
    "gunicorn"
    "hypercorn"
    "asgi.py"
  )
  for pat in "${patterns[@]}"; do
    if pids=$(pgrep -f "$pat" 2>/dev/null | tr '\n' ' '); then
      # Avoid killing this script if it somehow matches
      pids=$(echo "${pids}" | tr ' ' '\n' | grep -v "^$$$" || true)
      if [[ -n "${pids}" ]]; then
        echo "Stopping processes matching '${pat}' with SIG${KILL_SIGNAL}: ${pids}"
        # shellcheck disable=SC2086
        kill -s "${KILL_SIGNAL}" ${pids} || true
      fi
    fi
  done
}

kill_listeners
kill_by_pattern

echo "Done. If anything is still running, rerun with KILL_SIGNAL=KILL or add ports via PORTS=\"8000 8001 3000\" ./stopAllServers.sh"
