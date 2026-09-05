#!/usr/bin/env bash
# One-command local run. Creates a venv on first use; restarts any instance already on port 8000.
set -e
cd "$(dirname "$0")"
if [ ! -d .venv ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
# stop a previous server on :8000 so this command is safe to re-run
existing=$(lsof -ti tcp:8000 2>/dev/null || true)
[ -n "$existing" ] && kill $existing 2>/dev/null && sleep 1
[ -f .env ] || echo "(no .env found - running with offline fixtures; copy .env.example to .env and add ANTHROPIC_API_KEY for free-text notes)"
echo "PlugPoint -> http://localhost:8000   (Ctrl+C stops it)"
exec .venv/bin/uvicorn plugpoint.app:app --reload --port 8000
