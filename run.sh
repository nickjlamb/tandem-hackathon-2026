#!/usr/bin/env bash
# One-command local run. Creates a venv on first use.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
[ -f .env ] || echo "(no .env found - running with offline fixtures; copy .env.example to .env and add ANTHROPIC_API_KEY for free-text notes)"
echo "PlugPoint -> http://localhost:8000"
exec .venv/bin/uvicorn plugpoint.app:app --reload --port 8000
