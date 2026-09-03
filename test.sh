#!/usr/bin/env bash
# Run the pytest suite ensuring the current directory is in PYTHONPATH

export PYTHONPATH="."

if [ -f ".venv/Scripts/pytest" ]; then
    # Windows / Git Bash environment
    exec .venv/Scripts/pytest tests/ -v
elif [ -f ".venv/bin/pytest" ]; then
    # Linux / macOS environment (MangoLab's server)
    exec .venv/bin/pytest tests/ -v
else
    # Fallback to global pytest
    exec pytest tests/ -v
fi