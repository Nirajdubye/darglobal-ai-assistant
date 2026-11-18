#!/usr/bin/env bash
# Runs the FastAPI backend (internal, :8000) and the Streamlit UI (public, :$PORT) in one container.
set -euo pipefail
PORT="${PORT:-7860}"

uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 &
API_PID=$!

for i in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:8000/health >/dev/null 2>&1; then break; fi
  if ! kill -0 "$API_PID" 2>/dev/null; then echo "API failed to start"; exit 1; fi
  sleep 1
done

streamlit run app/frontend/streamlit_app.py --server.port "$PORT" --server.address 0.0.0.0 &
UI_PID=$!

# Exit (so the platform restarts us) if either process dies.
wait -n "$API_PID" "$UI_PID"
exit 1
