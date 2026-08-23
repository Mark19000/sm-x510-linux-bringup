#!/usr/bin/env bash
set -euo pipefail
ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
exec python3 "$ROOT/tools/u11_modules_audit.py" --root "$ROOT" \
    --json "$ROOT/reports/generated/u11-modules/modules-audit.json" \
    --markdown "$ROOT/reports/generated/u11-modules/modules-audit.md"
