#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VARIANT=${DEVICE_VARIANT:-wifi}
case "$VARIANT" in
    wifi) DEFAULT_KERNEL="$ROOT/sources/wifi-kernel" ;;
    5g) DEFAULT_KERNEL="$ROOT/sources/device-kernel" ;;
    *) echo "DEVICE_VARIANT debe ser wifi o 5g" >&2; exit 2 ;;
esac
KERNEL=${KERNEL_DIR:-$DEFAULT_KERNEL}
PATCH_DIR="$ROOT/patches/downstream/$VARIANT"

test -d "$KERNEL/.git" || { echo "No es un árbol Git: $KERNEL" >&2; exit 1; }

for patch in "$PATCH_DIR"/*.patch; do
    [ -e "$patch" ] || continue
    if git -C "$KERNEL" apply --reverse --check "$patch" >/dev/null 2>&1; then
        echo "Ya aplicado: $(basename "$patch")"
    else
        git -C "$KERNEL" apply --check "$patch"
        git -C "$KERNEL" apply "$patch"
        echo "Aplicado: $(basename "$patch")"
    fi
done

# Demuestra que todo cambio rastreado respecto a HEAD procede exactamente de
# la serie. Un segundo índice permite construir el diff esperado sin tocar el
# checkout ni depender de que los parches ya estuvieran aplicados.
expected_index=$(mktemp "${TMPDIR:-/tmp}/gts9fe-patch-index.XXXXXX")
rm -f -- "$expected_index"
cleanup() { rm -f -- "$expected_index"; }
trap cleanup EXIT
GIT_INDEX_FILE="$expected_index" git -C "$KERNEL" read-tree HEAD
for patch in "$PATCH_DIR"/*.patch; do
    [ -e "$patch" ] || continue
    GIT_INDEX_FILE="$expected_index" git -C "$KERNEL" apply --cached "$patch"
done
expected_diff=$(GIT_INDEX_FILE="$expected_index" git -C "$KERNEL" \
    diff --cached --binary HEAD | sha256sum | cut -d' ' -f1)
actual_diff=$(git -C "$KERNEL" diff --binary HEAD | sha256sum | cut -d' ' -f1)
if [ "$actual_diff" != "$expected_diff" ]; then
    echo "El árbol contiene cambios rastreados ajenos o distintos al patchset." >&2
    echo "diff esperado: $expected_diff" >&2
    echo "diff actual:   $actual_diff" >&2
    exit 1
fi
git -C "$KERNEL" diff --check
echo "Patchset verificado: el diff rastreado coincide exactamente con la serie."
