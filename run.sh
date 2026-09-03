#!/usr/bin/env bash
# Start the FastAPI application on port 8080
exec uvicorn app.main:app --host 0.0.0.0 --port 8080