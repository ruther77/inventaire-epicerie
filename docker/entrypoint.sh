#!/usr/bin/env bash
set -euo pipefail

PROCESS=${APP_PROCESS:-streamlit}
PORT=${STREAMLIT_SERVER_PORT:-8501}

case "$PROCESS" in
  streamlit)
    exec streamlit run app.py --server.address=0.0.0.0 --server.port="${PORT}"
    ;;
  api)
    exec python -m uvicorn backend.main:app --host 0.0.0.0 --port "${API_PORT:-8000}"
    ;;
  worker)
    exec python -m telemetry
    ;;
  *)
    echo "Unknown APP_PROCESS '${PROCESS}'." >&2
    exit 1
    ;;
esac
