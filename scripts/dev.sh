#!/usr/bin/env bash
# Run the API and the Streamlit UI locally (requires a configured .env).
set -euo pipefail
cd "$(dirname "$0")/.."

if [ ! -f .env ]; then
  echo "ERROR: .env not found. Run scripts/setup.sh first." >&2
  exit 1
fi

if [ -d venv ]; then
  # shellcheck disable=SC1091
  source venv/bin/activate
fi

export PYTHONPATH="$(pwd)"

uvicorn backend.api.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!

echo "Waiting for the API..."
for _ in $(seq 1 30); do
  if curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
    echo "API ready."
    break
  fi
  sleep 1
done

BACKEND_URL="${BACKEND_URL:-http://localhost:8000}" streamlit run frontend/app.py --server.port 8501 &
FRONTEND_PID=$!

trap 'kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true' EXIT INT TERM

echo
echo "API:       http://localhost:8000"
echo "API docs:  http://localhost:8000/docs"
echo "Frontend:  http://localhost:8501"
echo "Press Ctrl+C to stop."
wait
