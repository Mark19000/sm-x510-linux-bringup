#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
"$ROOT/scripts/u11-modules-audit.sh" >/dev/null
exec python3 "$ROOT/tools/u11_preflight.py" \
    --root "$ROOT" \
    --identity "$ROOT/configs/u11-x510xxsbdzb4.env" \
    --json "$ROOT/reports/generated/u11-preflight/preflight.json" \
    --markdown "$ROOT/reports/generated/u11-preflight/preflight.md"
