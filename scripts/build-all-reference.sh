#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
cd "$ROOT"

./scripts/setup-lima.sh
./scripts/fetch-image-tools.sh
./scripts/build-reference-in-lima.sh
./scripts/build-rescue-in-lima.sh
DEVICE_VARIANT=wifi DIST_DIR="$ROOT/artifacts/kernel/wifi/reference-dist" \
./scripts/build-dtbo.sh
./scripts/repack-reference-in-lima.sh

echo "Pipeline de referencia completado y auditado. Todo candidato sigue marcado UNSIGNED."
