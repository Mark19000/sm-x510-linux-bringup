#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/safety-paths.sh
source "$ROOT/scripts/safety-paths.sh"
VARIANT=${DEVICE_VARIANT:-wifi}
case "$VARIANT" in wifi|5g) ;; *) echo "DEVICE_VARIANT debe ser wifi o 5g" >&2; exit 2 ;; esac
STOCK=${1:-}
KERNEL=${2:-$ROOT/artifacts/kernel/$VARIANT/dist/Image}
OUTPUT=${3:-$ROOT/artifacts/boot-UNSIGNED-gts9fe-linux-$VARIANT.img}
MAGISKBOOT=${MAGISKBOOT:-magiskboot}

if [ -z "$STOCK" ]; then
    echo "Uso: $0 boot-stock.img [Image] [salida.img]" >&2
    exit 2
fi
for file in "$STOCK" "$KERNEL"; do
    test -f "$file" || { echo "Falta: $file" >&2; exit 1; }
done
mkdir -p "$(dirname "$OUTPUT")"
guard_output_file "$OUTPUT" "Salida boot"
output_path=$(cd "$(dirname "$OUTPUT")" && pwd -P)/$(basename "$OUTPUT")
for input in "$STOCK" "$KERNEL"; do
    input_path=$(cd "$(dirname "$input")" && pwd -P)/$(basename "$input")
    if [ "$output_path" = "$input_path" ] || \
       { [ -e "$OUTPUT" ] && [ "$OUTPUT" -ef "$input" ]; }; then
        echo "La salida no puede ser el mismo archivo que una entrada: $input" >&2
        exit 1
    fi
done
MAGISKBOOT_BIN=$(command -v "$MAGISKBOOT" 2>/dev/null) || {
    echo "Falta magiskboot. Define MAGISKBOOT=/ruta/al/binario oficial." >&2
    exit 1
}
case "$MAGISKBOOT_BIN" in
    /*) ;;
    *) MAGISKBOOT_BIN=$(cd "$(dirname "$MAGISKBOOT_BIN")" && pwd)/$(basename "$MAGISKBOOT_BIN") ;;
esac
# Una herramienta resuelta implica un intento real de reemplazo: invalida una
# salida anterior incluso si la plataforma resulta incompatible.
rm -f -- "$OUTPUT"
if [ "$(uname -s)" != Linux ] && file "$MAGISKBOOT_BIN" | grep -q 'ELF'; then
    echo "El magiskboot indicado es ELF y no puede ejecutarse en $(uname -s)." >&2
    echo "Usa scripts/repack-reference-in-lima.sh o proporciona un binario nativo." >&2
    exit 1
fi

WORK=$(mktemp -d "${TMPDIR:-/tmp}/gts9fe-repack.XXXXXX")
PUBLISH=
cleanup() { rm -rf -- "$WORK"; rm -f -- "${PUBLISH:-}"; }
trap cleanup EXIT

cp "$STOCK" "$WORK/stock.img"
(
    cd "$WORK"
    "$MAGISKBOOT_BIN" unpack stock.img
)

test -f "$WORK/kernel" || {
    echo "magiskboot no encontró un kernel dentro de la imagen stock." >&2
    exit 1
}
cp "$KERNEL" "$WORK/kernel"
(
    cd "$WORK"
    "$MAGISKBOOT_BIN" repack stock.img new-boot.img
)
test -f "$WORK/new-boot.img"
mkdir "$WORK/verify"
(
    cd "$WORK/verify"
    "$MAGISKBOOT_BIN" unpack ../new-boot.img
)
test -f "$WORK/verify/kernel" || {
    echo "El control no recuperó kernel del candidato." >&2
    exit 1
}
cmp -s "$KERNEL" "$WORK/verify/kernel" || {
    echo "El kernel cambió durante el reempaquetado." >&2
    exit 1
}
python3 "$ROOT/tools/bootimg_info.py" "$STOCK" "$WORK/new-boot.img"
stock_size=$(stat -c %s "$STOCK" 2>/dev/null || stat -f %z "$STOCK")
output_size=$(stat -c %s "$WORK/new-boot.img" 2>/dev/null || stat -f %z "$WORK/new-boot.img")
[ "$output_size" -le "$stock_size" ] || {
    echo "La imagen reempaquetada supera la partición stock ($output_size > $stock_size)." >&2
    exit 1
}
PUBLISH=$(mktemp "$(dirname "$OUTPUT")/.boot-candidate.XXXXXX")
cp "$WORK/new-boot.img" "$PUBLISH"
mv -f -- "$PUBLISH" "$OUTPUT"
PUBLISH=

if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$STOCK" "$OUTPUT"
else
    shasum -a 256 "$STOCK" "$OUTPUT"
fi
echo "Imagen creada en $OUTPUT"
echo "Round trip verificado: kernel recuperado byte a byte."
echo "NO FIRMADA / NO FLASHEAR: falta resolver AVB, compatibilidad exacta y método de recuperación."
