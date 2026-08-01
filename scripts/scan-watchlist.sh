#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

if [[ -d ".venv" ]]; then
  source ".venv/bin/activate"
fi

python3 run.py >> logs/scanner.log 2>&1
