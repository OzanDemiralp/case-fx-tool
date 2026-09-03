#!/usr/bin/env bash
# Start the FastAPI application respecting the PORT environment variable (default 8080)

PORT="${PORT:-8080}"

if [ -f ".venv/Scripts/uvicorn" ]; then
    # Windows / Git Bash environment
    exec .venv/Scripts/uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
elif [ -f ".venv/bin/uvicorn" ]; then
    # Linux / macOS environment (MangoLab's server)
    exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
else
    # Fallback to global uvicorn
    exec uvicorn app.main:app --host 0.0.0.0 --port "$PORT"
fi