#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VM=${LIMA_INSTANCE:-gts9fe-build}
TEMPLATE="$ROOT/lima/gts9fe-build.yaml.in"

[ "$(uname -s)" = Darwin ] || {
    echo "Este helper es sólo para macOS; en Linux instala las dependencias de docs/04-build.md." >&2
    exit 1
}
command -v limactl >/dev/null || {
    echo "Falta Lima. Instálalo con: brew install lima" >&2
    exit 1
}

if limactl list --format '{{.Name}}' 2>/dev/null | grep -qx "$VM"; then
    echo "La VM $VM ya existe. Arrancándola si estaba detenida..."
    limactl start "$VM"
    exit 0
fi

CONFIG=$(mktemp "${TMPDIR:-/tmp}/gts9fe-lima.XXXXXX.yaml")
cleanup() { rm -f -- "$CONFIG"; }
trap cleanup EXIT
escaped_root=$(printf '%s' "$ROOT" | sed 's/[&|]/\\&/g')
sed "s|__PROJECT_ROOT__|$escaped_root|g" "$TEMPLATE" > "$CONFIG"
limactl start --name "$VM" "$CONFIG"
echo "VM $VM preparada. Continúa con scripts/build-reference-in-lima.sh."
