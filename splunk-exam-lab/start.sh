#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
# Use the desktop app's bundled runtime when standard Node tools are absent.
lab_runtime="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies"
if ! command -v node >/dev/null && [ -x "$lab_runtime/node/bin/node" ]; then
  export PATH="$lab_runtime/node/bin:$lab_runtime/bin/fallback:$PATH"
fi
command -v python3 >/dev/null || { echo 'Install Python 3.10 or newer.'; exit 1; }
command -v node >/dev/null || { echo 'Install Node.js 20.19+ and pnpm.'; exit 1; }
command -v pnpm >/dev/null || { echo 'Install pnpm: npm install -g pnpm'; exit 1; }
if [ ! -d backend/.venv ]; then python3 -m venv backend/.venv; fi
backend/.venv/bin/python -m pip install -r backend/requirements.txt
(cd frontend && pnpm install --frozen-lockfile)
(cd backend && .venv/bin/python -m app.seed && exec .venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000) &
lab_backend_pid=$!
trap 'kill "$lab_backend_pid" 2>/dev/null || true' EXIT INT TERM
echo 'Open http://127.0.0.1:5173 in your browser.'
(cd frontend && pnpm dev)
