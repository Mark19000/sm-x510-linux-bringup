#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/safety-paths.sh
source "$ROOT/scripts/safety-paths.sh"
INPUT=${1:-}
OUT=${2:-$ROOT/artifacts/stock}

if [ -z "$INPUT" ]; then
    echo "Uso: $0 firmware.zip|AP_....tar.md5 [directorio-salida]" >&2
    exit 2
fi
test -f "$INPUT" || { echo "No existe: $INPUT" >&2; exit 1; }

case "$INPUT" in
    *.zip)
        exec "$ROOT/scripts/extract-firmware-zip.sh" "$INPUT" "$OUT"
        ;;
esac

command -v lz4 >/dev/null || { echo "Falta lz4." >&2; exit 1; }

# Evita analizar o reempaquetar por accidente un AP de otra revisión.
"$ROOT/scripts/target-info.sh" "$INPUT" >/dev/null

mkdir -p "$OUT"
out_real=$(cd "$OUT" && pwd -P)
guard_output_directory "$out_real" "Directorio de extracción"
project_parent=$(dirname "$ROOT")
case "$out_real" in
    /|/tmp|/var/tmp|"$ROOT"|"$project_parent"|"${HOME:-__no_home__}")
        echo "Directorio de extracción demasiado amplio: $out_real" >&2
        exit 1
        ;;
esac
if [ -n "$(find "$OUT" -mindepth 1 -maxdepth 1 -print -quit)" ]; then
    if [ "${REPLACE_STOCK_OUTPUT:-0}" != 1 ]; then
        echo "La salida $OUT no está vacía; se rechaza mezclar dos extracciones." >&2
        echo "Usa otro directorio o REPLACE_STOCK_OUTPUT=1 para sustituir sólo los artefactos generados." >&2
        exit 1
    fi
    rm -rf -- "$OUT/raw" "$OUT/images" "$OUT/dt"
    rm -f -- "$OUT/SHA256SUMS" "$OUT/FIRMWARE_SHA256SUM" "$OUT/firmware-metadata.txt"
fi

mkdir -p "$OUT/raw" "$OUT/images" "$OUT/dt"
echo "Extrayendo el AP sin modificar el original..."
PARTITIONS=(
    boot.img.lz4 init_boot.img.lz4 vendor_boot.img.lz4
    dtbo.img.lz4 recovery.img.lz4 vbmeta.img.lz4
)
python3 "$ROOT/tools/safe_tar_extract.py" "$INPUT" "$OUT/raw" "${PARTITIONS[@]}"

for packed in "${PARTITIONS[@]}"; do
    name=${packed%.lz4}
    lz4 -d -f "$OUT/raw/$packed" "$OUT/images/$name"
done

if [ -f "$OUT/images/dtbo.img" ]; then
    python3 "$ROOT/tools/dtbo_extract.py" "$OUT/images/dtbo.img" "$OUT/dt/overlays"
    if command -v dtc >/dev/null 2>&1; then
        find "$OUT/dt/overlays" -type f -name '*.dtbo' -print0 | \
        while IFS= read -r -d '' blob; do
            dtc -I dtb -O dts -o "${blob%.dtbo}.dts" "$blob" || true
        done
    fi
fi

for image in boot.img vendor_boot.img dtb.img; do
    if [ -f "$OUT/images/$image" ]; then
        python3 "$ROOT/tools/fdt_scan.py" "$OUT/images/$image" "$OUT/dt/${image%.img}" || true
    fi
done

if command -v sha256sum >/dev/null 2>&1; then
    (cd "$OUT"; for packed in "${PARTITIONS[@]}"; do sha256sum "images/${packed%.lz4}"; done) \
        > "$OUT/SHA256SUMS"
else
    (cd "$OUT"; for packed in "${PARTITIONS[@]}"; do shasum -a 256 "images/${packed%.lz4}"; done) \
        > "$OUT/SHA256SUMS"
fi

echo "Extracción terminada en $OUT"
echo "No se ha escrito nada en la tablet. Conserva el AP original y SHA256SUMS."
