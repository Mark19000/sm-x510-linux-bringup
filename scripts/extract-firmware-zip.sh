#!/usr/bin/env bash
set -euo pipefail

# Extrae sólo las particiones de arranque del AP contenido en un firmware
# Samsung completo. El AP se transmite ZIP -> tar y nunca se duplica en disco.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/safety-paths.sh
source "$ROOT/scripts/safety-paths.sh"
INPUT=${1:-}
OUT=${2:-$ROOT/artifacts/stock}

if [ -z "$INPUT" ]; then
    echo "Uso: $0 firmware-SM-X510.zip [directorio-salida]" >&2
    exit 2
fi
test -f "$INPUT" || { echo "No existe: $INPUT" >&2; exit 1; }
for command_name in unzip lz4 python3; do
    command -v "$command_name" >/dev/null || {
        echo "Falta la herramienta: $command_name" >&2
        exit 1
    }
done

"$ROOT/scripts/target-info.sh" "$INPUT" >/dev/null

ap_entries=$(unzip -Z1 "$INPUT" | grep -E '^AP_.*\.tar\.md5$' || true)
ap_count=$(printf '%s\n' "$ap_entries" | sed '/^$/d' | wc -l | tr -d ' ')
if [ "$ap_count" != 1 ]; then
    echo "Se esperaba un único AP_*.tar.md5 dentro del ZIP; encontrados: $ap_count" >&2
    printf '%s\n' "$ap_entries" >&2
    exit 1
fi
AP_ENTRY=$ap_entries
case "$(basename "$AP_ENTRY")" in
    *X510XXUCEZE4*) ;;
    *)
        echo "El AP interno no corresponde a X510XXUCEZE4: $AP_ENTRY" >&2
        exit 1
        ;;
esac

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

# Esta lista se obtuvo inspeccionando el AP EZE4. No se extrae super.img.
PARTITIONS=(
    boot.img.lz4
    init_boot.img.lz4
    vendor_boot.img.lz4
    dtbo.img.lz4
    recovery.img.lz4
    vbmeta.img.lz4
)

echo "AP interno: $AP_ENTRY"
echo "Extracción en streaming; el AP de 11+ GB no se escribirá en disco."
unzip -p "$INPUT" "$AP_ENTRY" | \
    python3 "$ROOT/tools/safe_tar_extract.py" - "$OUT/raw" "${PARTITIONS[@]}"

for packed in "${PARTITIONS[@]}"; do
    source_path="$OUT/raw/$packed"
    test -f "$source_path" || { echo "Falta la partición esperada: $packed" >&2; exit 1; }
    image_name=${packed%.lz4}
    lz4 -d -f "$source_path" "$OUT/images/$image_name"
done

python3 "$ROOT/tools/dtbo_extract.py" "$OUT/images/dtbo.img" "$OUT/dt/overlays"

for image_name in boot.img init_boot.img vendor_boot.img recovery.img; do
    python3 "$ROOT/tools/fdt_scan.py" \
        "$OUT/images/$image_name" "$OUT/dt/${image_name%.img}" || true
done

if command -v dtc >/dev/null 2>&1; then
    find "$OUT/dt" -type f \( -name '*.dtb' -o -name '*.dtbo' \) -print0 | \
    while IFS= read -r -d '' blob; do
        dtc -I dtb -O dts -o "${blob%.*}.dts" "$blob" || true
    done
else
    echo "AVISO: falta dtc; se conservaron los DTB/DTBO binarios." >&2
fi

if command -v sha256sum >/dev/null 2>&1; then
    hash_file() { sha256sum "$1"; }
else
    hash_file() { shasum -a 256 "$1"; }
fi

hash_file "$INPUT" > "$OUT/FIRMWARE_SHA256SUM"
(
    cd "$OUT"
    for packed in "${PARTITIONS[@]}"; do
        image_path="images/${packed%.lz4}"
        hash_file "$image_path"
    done
) > "$OUT/SHA256SUMS"

printf '%s\n' \
    "outer_zip=$(basename "$INPUT")" \
    "ap_entry=$AP_ENTRY" \
    "target_model=SM-X510" \
    "target_ap=X510XXUCEZE4" \
    "target_csc=EUX" \
    "target_csc_version=X510OXMCEZE4" > "$OUT/firmware-metadata.txt"

echo "Particiones de arranque extraídas en $OUT/images"
echo "Hashes y metadatos guardados en $OUT"
echo "No se ha escrito nada en la tablet."
