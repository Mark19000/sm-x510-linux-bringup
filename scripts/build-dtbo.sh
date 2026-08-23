#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/safety-paths.sh
source "$ROOT/scripts/safety-paths.sh"
VARIANT=${DEVICE_VARIANT:-wifi}
DIST=${DIST_DIR:-$ROOT/artifacts/kernel/$VARIANT/dist}
TEMPLATE=${DTBO_TEMPLATE:-$ROOT/artifacts/stock/dt/overlays/manifest.json}
OUTPUT=${DTBO_OUTPUT:-$DIST/dtbo-unsigned.img}

case "$VARIANT" in
    wifi)
        overlays=(
            "$DIST/dtbs/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r00.dtbo"
            "$DIST/dtbs/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r01.dtbo"
            "$DIST/dtbs/samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dtbo"
        )
        ;;
    5g)
        echo "El mapeo de revisiones de la X516 aún no se ha validado contra su DTBO stock." >&2
        exit 1
        ;;
    *) echo "DEVICE_VARIANT debe ser wifi o 5g" >&2; exit 2 ;;
esac

mkdir -p "$DIST" "$(dirname "$OUTPUT")"
guard_output_directory "$DIST" "DIST_DIR DTBO"
guard_output_file "$OUTPUT" "DTBO_OUTPUT"
output_path=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$OUTPUT")
for input in "$TEMPLATE" "${overlays[@]}"; do
    input_path=$(python3 -c 'import os,sys; print(os.path.realpath(sys.argv[1]))' "$input")
    if [ "$output_path" = "$input_path" ] || \
       { [ -e "$OUTPUT" ] && [ "$OUTPUT" -ef "$input" ]; }; then
        echo "DTBO_OUTPUT no puede sobrescribir una entrada: $input" >&2
        exit 1
    fi
done

# Si falta una entrada o falla el pack, no debe sobrevivir un candidato viejo.
rm -f -- "$OUTPUT" "$OUTPUT.sha256"
rm -rf -- "$DIST/dtbo-unsigned.entries"

test -f "$TEMPLATE" || { echo "Falta el manifiesto stock $TEMPLATE" >&2; exit 1; }
for overlay in "${overlays[@]}"; do
    test -s "$overlay" || { echo "Falta el overlay $overlay" >&2; exit 1; }
done

work=$(mktemp -d "$DIST/.dtbo-build.XXXXXX")
cleanup() { rm -rf -- "$work"; }
trap cleanup EXIT
packed="$work/dtbo.img"
extracted_dir="$work/entries"

python3 "$ROOT/tools/dtbo_pack.py" --template "$TEMPLATE" --output "$packed" \
    "${overlays[@]}"
python3 "$ROOT/tools/dtbo_extract.py" "$packed" "$extracted_dir"
extracted_files=()
while IFS= read -r filename; do
    extracted_files+=("$extracted_dir/$filename")
done < <(python3 -c \
    'import json,sys; [print(e["file"]) for e in json.load(open(sys.argv[1]))["entries"]]' \
    "$extracted_dir/manifest.json")
[ "${#extracted_files[@]}" -eq "${#overlays[@]}" ] || {
    echo "El número de entradas extraídas no coincide." >&2
    exit 1
}
for index in "${!overlays[@]}"; do
    extracted=${extracted_files[$index]}
    test -f "$extracted" || { echo "Falta la entrada extraída $extracted" >&2; exit 1; }
    cmp -s "${overlays[$index]}" "$extracted" || {
        echo "La entrada $index cambió durante pack/unpack" >&2
        exit 1
    }
done
echo "Round trip DTBO verificado: ${#overlays[@]} blobs idénticos."
cp "$packed" "$OUTPUT"
rm -rf -- "$DIST/dtbo-unsigned.entries"
mkdir -p "$DIST/dtbo-unsigned.entries"
cp -R "$extracted_dir"/. "$DIST/dtbo-unsigned.entries/"
output_dir=$(cd "$(dirname "$OUTPUT")" && pwd)
output_name=$(basename "$OUTPUT")
if command -v sha256sum >/dev/null 2>&1; then
    (cd "$output_dir" && sha256sum "$output_name" > "$output_name.sha256")
else
    (cd "$output_dir" && shasum -a 256 "$output_name" > "$output_name.sha256")
fi
echo "DTBO sin firma creado para análisis. No lo flashees: fuente y firmware no coinciden."
