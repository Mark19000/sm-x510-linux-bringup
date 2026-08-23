#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
AVBTOOL=${AVBTOOL:-$ROOT/sources/toolchain/avb-android16/avbtool.py}
STOCK_DIR=${STOCK_DIR:-$ROOT/artifacts/stock/images}
CANDIDATE_DIR=${CANDIDATE_DIR:-$ROOT/artifacts/candidates/reference}

test -f "$AVBTOOL" || { echo "Falta avbtool: $AVBTOOL" >&2; exit 1; }

work=$(mktemp -d "${TMPDIR:-/tmp}/gts9fe-avb-check.XXXXXX")
cleanup() { rm -rf -- "$work"; }
trap cleanup EXIT

for partition in boot init_boot; do
    stock="$STOCK_DIR/$partition.img"
    candidate="$CANDIDATE_DIR/$partition-UNSIGNED.img"
    test -f "$stock" || { echo "Falta $stock" >&2; exit 1; }
    test -f "$candidate" || { echo "Falta $candidate" >&2; exit 1; }
    stock_size=$(wc -c < "$stock" | tr -d '[:space:]')
    candidate_size=$(wc -c < "$candidate" | tr -d '[:space:]')
    if [ "$candidate_size" -eq 0 ] || [ "$candidate_size" -gt "$stock_size" ]; then
        echo "[$partition] candidato fuera del límite de partición: $candidate_size > $stock_size" >&2
        exit 1
    fi

    echo "[$partition] verificando imagen stock"
    python3 "$AVBTOOL" verify_image --image "$stock"

    # El descriptor busca <partition>.img en el mismo directorio; el nombre
    # UNSIGNED provocaría un falso 'file not found'. Copiamos con el nombre
    # semántico correcto dentro de un directorio temporal.
    partition_work="$work/$partition"
    mkdir -p "$partition_work"
    cp "$candidate" "$partition_work/$partition.img"
    python3 "$AVBTOOL" info_image \
        --image "$partition_work/$partition.img" > "$partition_work/info.txt"

    set +e
    verify_output=$(python3 "$AVBTOOL" verify_image \
        --image "$partition_work/$partition.img" 2>&1)
    verify_status=$?
    set -e
    if [ "$verify_status" -eq 0 ]; then
        echo "PELIGRO: el candidato $partition verificó inesperadamente." >&2
        exit 1
    fi
    if ! printf '%s\n' "$verify_output" | grep -q \
        'does not match digest in descriptor'; then
        echo "$verify_output" >&2
        echo "El candidato falló por una razón AVB no reconocida." >&2
        exit 1
    fi
    if ! printf '%s\n' "$verify_output" | grep -q \
        'Successfully verified footer and SHA256_RSA4096 vbmeta struct'; then
        echo "$verify_output" >&2
        echo "No se pudo confirmar la estructura/firma VBMeta embebida." >&2
        exit 1
    fi
    echo "[$partition] esperado: firma VBMeta válida, hash de contenido inválido"
done

echo "Puerta AVB superada: stock válido; candidatos modificados detectados como NO flasheables."
