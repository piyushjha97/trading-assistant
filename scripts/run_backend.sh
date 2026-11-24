#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [[ ! -f .env ]]; then
    (umask 077; printf '%s\n' 'KITE_API_KEY=' 'KITE_API_SECRET=' > .env)
    echo "Created .env. Add KITE_API_KEY and KITE_API_SECRET, then run this script again."
    exit 1
fi

if grep -Eq '^KITE_API_KEY=replace-with-|^KITE_API_KEY[[:space:]]*=[[:space:]]*$' .env; then
    echo "Set KITE_API_KEY in .env, then run this script again."
    exit 1
fi

if [[ ! -x .venv/bin/python ]]; then
    python3 -m venv .venv
fi

.venv/bin/python -m pip install -e '.[dev]'
exec .venv/bin/uvicorn trading_assistant.main:app --app-dir src --host 127.0.0.1 --port 8000 --no-access-log
