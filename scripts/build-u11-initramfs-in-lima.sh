#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VM=${LIMA_INSTANCE:-gts9fe-build}

command -v limactl >/dev/null || { echo "Falta limactl." >&2; exit 1; }
limactl shell "$VM" -- env HOST_PROJECT="$ROOT" bash -lc '
set -euo pipefail
exec "$HOST_PROJECT/scripts/build-u11-initramfs.sh"
'
