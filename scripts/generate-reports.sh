#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VARIANT=${DEVICE_VARIANT:-wifi}
case "$VARIANT" in
    wifi)
        VENDOR="$ROOT/sources/wifi-kernel"
        BOARD_REL=arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dts
        REV_PREFIX=arch/arm64/boot/dts/samsung/gts9fewifi/gts9fewifi_eur_open_w00_
        REVISIONS="r00 r01"
        ;;
    5g)
        VENDOR="$ROOT/sources/device-kernel"
        BOARD_REL=arch/arm64/boot/dts/samsung/gts9fe/gts9fe_eur_open_w00_r04.dts
        REV_PREFIX=arch/arm64/boot/dts/samsung/gts9fe/gts9fe_eur_open_w00_
        REVISIONS="r00 r01 r02"
        ;;
    *) echo "DEVICE_VARIANT debe ser wifi o 5g" >&2; exit 2 ;;
esac
MAINLINE="$ROOT/sources/mainline-kernel"
OUT="$ROOT/reports/generated/$VARIANT"
BASE="$VENDOR/arch/arm64/boot/dts/exynos/s5e8835.dts"
BOARD="$VENDOR/$BOARD_REL"

test -f "$BASE" || { echo "Faltan fuentes; ejecuta make fetch." >&2; exit 1; }
test -d "$MAINLINE/drivers" || { echo "Falta mainline; ejecuta make fetch." >&2; exit 1; }
mkdir -p "$OUT"

python3 "$ROOT/tools/compatible_report.py" \
    --dts "$BASE" --dts "$BOARD" --vendor "$VENDOR" --mainline "$MAINLINE" \
    --output "$OUT/compatibles.md"

{
    echo '# Diferencias entre revisiones de placa'
    echo
    echo 'Resumen de `diff --stat` respecto a r04 (no implica que r04 sea tu hardware):'
    echo
    echo '```text'
    for revision in $REVISIONS; do
        candidate="$VENDOR/${REV_PREFIX}${revision}.dts"
        echo "$revision -> r04"
        (diff -u "$candidate" "$BOARD" || true) | diffstat 2>/dev/null || \
            echo "$revision: instala diffstat para el resumen detallado"
    done
    echo '```'
} > "$OUT/revisiones.md"

echo "Informes generados en $OUT"
