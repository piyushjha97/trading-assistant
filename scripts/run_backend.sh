#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -f .env ]]; then
    cp .env.example .env
    echo "Created .env from .env.example. Add KITE_API_KEY and KITE_ACCESS_TOKEN, then run this script again."
    exit 1
fi

if grep -Eq '^KITE_API_KEY=replace-with-|^KITE_ACCESS_TOKEN=replace-with-|^KITE_API_KEY[[:space:]]*=[[:space:]]*$|^KITE_ACCESS_TOKEN[[:space:]]*=[[:space:]]*$' .env; then
    echo "Set KITE_API_KEY and KITE_ACCESS_TOKEN in .env, then run this script again."
    exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi

.venv/bin/python -m pip install -e '.[dev]'
exec .venv/bin/uvicorn trading_assistant.main:app --app-dir src --host 127.0.0.1 --port 8000
