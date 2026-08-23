#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/safety-paths.sh
source "$ROOT/scripts/safety-paths.sh"
VARIANT=${DEVICE_VARIANT:-wifi}
case "$VARIANT" in wifi|5g) ;; *) echo "DEVICE_VARIANT debe ser wifi o 5g" >&2; exit 2 ;; esac
STOCK=${1:-}
RAMDISK=${2:-$ROOT/artifacts/initramfs/$VARIANT/gts9fe-initramfs.cpio}
OUTPUT=${3:-$ROOT/artifacts/init_boot-UNSIGNED-gts9fe-linux-$VARIANT.img}
MAGISKBOOT=${MAGISKBOOT:-magiskboot}

if [ -z "$STOCK" ]; then
    echo "Uso: $0 init_boot-stock.img [initramfs.cpio] [salida.img]" >&2
    exit 2
fi
for file in "$STOCK" "$RAMDISK"; do
    test -f "$file" || { echo "Falta: $file" >&2; exit 1; }
done
mkdir -p "$(dirname "$OUTPUT")"
guard_output_file "$OUTPUT" "Salida init_boot"
output_path=$(cd "$(dirname "$OUTPUT")" && pwd -P)/$(basename "$OUTPUT")
for input in "$STOCK" "$RAMDISK"; do
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
rm -f -- "$OUTPUT"
if [ "$(uname -s)" != Linux ] && file "$MAGISKBOOT_BIN" | grep -q 'ELF'; then
    echo "El magiskboot indicado es ELF y no puede ejecutarse en $(uname -s)." >&2
    echo "Usa scripts/repack-reference-in-lima.sh o proporciona un binario nativo." >&2
    exit 1
fi

WORK=$(mktemp -d "${TMPDIR:-/tmp}/gts9fe-init-boot.XXXXXX")
PUBLISH=
cleanup() { rm -rf -- "$WORK"; rm -f -- "${PUBLISH:-}"; }
trap cleanup EXIT

cp "$STOCK" "$WORK/stock.img"
(
    cd "$WORK"
    "$MAGISKBOOT_BIN" unpack stock.img
)
test ! -f "$WORK/kernel" || {
    echo "La imagen contiene kernel; no parece el init_boot esperado." >&2
    exit 1
}
test -f "$WORK/ramdisk.cpio" || {
    echo "magiskboot no encontró ramdisk en init_boot." >&2
    exit 1
}

cp "$RAMDISK" "$WORK/ramdisk.cpio"
(
    cd "$WORK"
    "$MAGISKBOOT_BIN" repack stock.img new-init-boot.img
)
test -f "$WORK/new-init-boot.img"
mkdir "$WORK/verify"
(
    cd "$WORK/verify"
    "$MAGISKBOOT_BIN" unpack ../new-init-boot.img
)
test -f "$WORK/verify/ramdisk.cpio" || {
    echo "El control no recuperó ramdisk del candidato." >&2
    exit 1
}
cmp -s "$RAMDISK" "$WORK/verify/ramdisk.cpio" || {
    echo "El ramdisk cambió durante el reempaquetado." >&2
    exit 1
}
python3 "$ROOT/tools/bootimg_info.py" "$STOCK" "$WORK/new-init-boot.img"
stock_size=$(stat -c %s "$STOCK" 2>/dev/null || stat -f %z "$STOCK")
output_size=$(stat -c %s "$WORK/new-init-boot.img" 2>/dev/null || stat -f %z "$WORK/new-init-boot.img")
[ "$output_size" -le "$stock_size" ] || {
    echo "La imagen reempaquetada supera la partición stock ($output_size > $stock_size)." >&2
    exit 1
}
PUBLISH=$(mktemp "$(dirname "$OUTPUT")/.init-boot-candidate.XXXXXX")
cp "$WORK/new-init-boot.img" "$PUBLISH"
mv -f -- "$PUBLISH" "$OUTPUT"
PUBLISH=

if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$STOCK" "$OUTPUT"
else
    shasum -a 256 "$STOCK" "$OUTPUT"
fi
echo "Imagen creada en $OUTPUT"
echo "Round trip verificado: ramdisk recuperado byte a byte."
echo "NO FIRMADA / NO FLASHEAR: falta resolver AVB, compatibilidad exacta y método de recuperación."
