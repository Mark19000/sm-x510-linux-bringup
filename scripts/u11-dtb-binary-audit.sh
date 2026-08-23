#!/usr/bin/env bash
set -Eeuo pipefail

# Compara los DTB ya compilados. Esto es deliberadamente distinto de comparar
# el DTS fuente: escapes octales Samsung pueden cambiar de significado al pasar
# por dtc y sólo el blob final muestra los bytes que recibiría el kernel.

ROOT=$(cd "$(dirname "$0")/.." && pwd)
U11_DTB=${U11_DTB:-$ROOT/artifacts/u11/x510xxsbdzb4-u11-clang21-20260823/s5e8835.dtb}
EZE4_DTB=${EZE4_DTB:-$ROOT/artifacts/stock/dt/vendor_boot/fdt-00-offset-0113f040.dtb}
OUTPUT=${OUTPUT:-$ROOT/reports/generated/u11-dtb-binary}

command -v dtc >/dev/null || { echo "Falta dtc." >&2; exit 1; }
test -f "$U11_DTB" || { echo "Falta DTB U11: $U11_DTB" >&2; exit 1; }
test -f "$EZE4_DTB" || { echo "Falta DTB EZE4: $EZE4_DTB" >&2; exit 1; }

mkdir -p "$OUTPUT"
dtc -q -I dtb -O dts -o "$OUTPUT/u11-compiled.dts" "$U11_DTB"
dtc -q -I dtb -O dts -o "$OUTPUT/eze4-stock.dts" "$EZE4_DTB"

run_diff() {
    set +e
    python3 "$ROOT/tools/dts_semantic_diff.py" \
        "$OUTPUT/u11-compiled.dts" "$OUTPUT/eze4-stock.dts" "$@"
    status=$?
    set -e
    [ "$status" -le 1 ] || return "$status"
}
run_diff --format json --detail-limit 0 -o "$OUTPUT/semantic-base-compiled-u11-eze4.json"
run_diff --format markdown --detail-limit 0 -o "$OUTPUT/semantic-base-compiled-u11-eze4.md"

{
    printf '%s  %s\n' "$(shasum -a 256 "$U11_DTB" | cut -d' ' -f1)" 'u11:s5e8835.dtb'
    printf '%s  %s\n' "$(shasum -a 256 "$EZE4_DTB" | cut -d' ' -f1)" 'eze4:vendor_boot/fdt-00-offset-0113f040.dtb'
} > "$OUTPUT/INPUTS.sha256"

echo "Auditoría semántica de DTB compilados: $OUTPUT"
echo "Escritura física: NO-GO"
