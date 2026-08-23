#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/safety-paths.sh
source "$ROOT/scripts/safety-paths.sh"
SRC=${BUSYBOX_SRC:-$ROOT/sources/busybox}
OUT=${BUSYBOX_OUT:-$ROOT/artifacts/busybox}
DIST=${BUSYBOX_DIST:-$OUT}
REF=${BUSYBOX_REF:-1_36_1}
EXPECTED_COMMIT=${BUSYBOX_EXPECTED_COMMIT:-1a64f6a20aaf6ea4dbba68bbfa8cc1ab7e5c57c4}
JOBS=${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}
CONFIG=${BUSYBOX_CONFIG:-$ROOT/configs/busybox-rescue.config}

if [ "$(uname -s)" != Linux ]; then
    echo "BusyBox ARM64 se construye en Linux; consulta docs/04-build.md." >&2
    exit 1
fi

case "$(uname -m)" in
    aarch64|arm64) CROSS=${CROSS_COMPILE:-} ;;
    *) CROSS=${CROSS_COMPILE:-aarch64-linux-gnu-} ;;
esac

if [ ! -d "$SRC/.git" ]; then
    git clone --depth 1 --branch "$REF" https://git.busybox.net/busybox "$SRC"
fi
expected_commit=$(git -C "$SRC" rev-parse "$REF^{commit}" 2>/dev/null) || {
    echo "El checkout no contiene la referencia BusyBox $REF" >&2
    exit 1
}
actual_commit=$(git -C "$SRC" rev-parse HEAD)
if [ "$expected_commit" != "$EXPECTED_COMMIT" ] || \
   [ "$actual_commit" != "$EXPECTED_COMMIT" ]; then
    echo "BusyBox no coincide con el commit fijado $EXPECTED_COMMIT." >&2
    echo "tag local=$expected_commit; HEAD=$actual_commit" >&2
    exit 1
fi
test -f "$CONFIG" || { echo "Falta la configuración $CONFIG" >&2; exit 1; }

mkdir -p "$OUT" "$DIST"
project_parent=$(dirname "$ROOT")
for generated in "$OUT" "$DIST"; do
    generated_real=$(cd "$generated" && pwd -P)
    guard_output_directory "$generated_real" "Ruta BusyBox"
    case "$generated_real" in
        /|/tmp|/var/tmp|"$ROOT"|"$project_parent"|"${HOME:-__no_home__}")
            echo "Ruta BusyBox demasiado amplia y rechazada: $generated_real" >&2
            exit 1
            ;;
    esac
done
rm -f -- "$DIST/busybox" "$DIST/SOURCE_COMMIT" "$DIST/SHA256SUMS"
mkdir -p "$OUT/obj"
KCONFIG_NOTIMESTAMP=1 make -C "$SRC" O="$OUT/obj" \
    ARCH=arm64 CROSS_COMPILE="$CROSS" allnoconfig >/dev/null
# Esta versión de BusyBox vuelve a forzar booleanos a `n` durante
# allnoconfig incluso después de leer KCONFIG_ALLCONFIG. Aplicamos después el
# pequeño fragmento y pedimos a Kconfig que resuelva las dependencias.
while IFS= read -r setting; do
    case "$setting" in
        CONFIG_*=y)
            symbol=${setting%%=*}
            if grep -q "^# $symbol is not set$" "$OUT/obj/.config"; then
                sed -i "s/^# $symbol is not set$/$setting/" "$OUT/obj/.config"
            elif grep -q "^$symbol=" "$OUT/obj/.config"; then
                sed -i "s/^$symbol=.*/$setting/" "$OUT/obj/.config"
            else
                echo "Opción BusyBox desconocida: $symbol" >&2
                exit 1
            fi
            ;;
        ""|'#'*) ;;
        *) echo "Formato no soportado en $CONFIG: $setting" >&2; exit 1 ;;
    esac
done < "$CONFIG"
set +o pipefail
yes '' | KCONFIG_NOTIMESTAMP=1 make -C "$SRC" O="$OUT/obj" \
    ARCH=arm64 CROSS_COMPILE="$CROSS" oldconfig >/dev/null
oldconfig_status=${PIPESTATUS[1]}
set -o pipefail
[ "$oldconfig_status" -eq 0 ] || exit "$oldconfig_status"
while IFS= read -r setting; do
    case "$setting" in
        CONFIG_*=y)
            grep -qxF "$setting" "$OUT/obj/.config" || {
                echo "Kconfig no pudo activar: $setting" >&2
                exit 1
            }
            ;;
    esac
done < "$CONFIG"
make -C "$SRC" O="$OUT/obj" ARCH=arm64 CROSS_COMPILE="$CROSS" -j"$JOBS"

file "$OUT/obj/busybox"
if ! file "$OUT/obj/busybox" | grep -Eq 'ARM aarch64|ARM64'; then
    echo "El BusyBox generado no es AArch64." >&2
    exit 1
fi
if ! file "$OUT/obj/busybox" | grep -q 'statically linked'; then
    echo "El BusyBox generado no es estático." >&2
    exit 1
fi

cp "$OUT/obj/busybox" "$DIST/busybox"
printf '%s\n' "$actual_commit" > "$DIST/SOURCE_COMMIT"
if command -v sha256sum >/dev/null 2>&1; then
    (cd "$DIST" && sha256sum busybox > SHA256SUMS)
else
    (cd "$DIST" && shasum -a 256 busybox > SHA256SUMS)
fi
echo "BusyBox listo: $DIST/busybox"
