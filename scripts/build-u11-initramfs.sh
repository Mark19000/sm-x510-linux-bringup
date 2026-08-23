#!/usr/bin/env bash
set -euo pipefail

# Construye perfiles initramfs exclusivamente con módulos U11. Este script se
# ejecuta en Linux; en macOS usa build-u11-initramfs-in-lima.sh.

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/safety-paths.sh
source "$ROOT/scripts/safety-paths.sh"
# shellcheck source=configs/u11-x510xxsbdzb4.env
source "$ROOT/configs/u11-x510xxsbdzb4.env"

[ "$(uname -s)" = Linux ] || {
    echo "Este build requiere Linux; usa scripts/build-u11-initramfs-in-lima.sh." >&2
    exit 1
}

BUILD_ROOT=${U11_BUILD_ROOT:-$ROOT/$U11_BUILD_ARTIFACTS}
MODULES_ROOT=${U11_MODULES_ROOT:-$BUILD_ROOT/modules-installed/modules-root/lib/modules}
OUT_ROOT=${U11_INITRAMFS_OUT:-$ROOT/$U11_INITRAMFS_ARTIFACTS}
BUSYBOX=${BUSYBOX:-$ROOT/artifacts/busybox/busybox}
REPRO_CHECK=${U11_REPRO_CHECK:-1}

build_real=$(canonical_output_path "$BUILD_ROOT")
modules_real=$(canonical_output_path "$MODULES_ROOT")
out_real=$(canonical_output_path "$OUT_ROOT")
allowed_build=$(canonical_output_path "$ROOT/artifacts/u11")
allowed_output=$(canonical_output_path "$ROOT/artifacts/initramfs/u11")
case "$build_real/" in
    "$allowed_build/"*) ;;
    *) echo "U11_BUILD_ROOT debe permanecer bajo artifacts/u11: $build_real" >&2; exit 1 ;;
esac
case "$modules_real/" in
    "$build_real/"*) ;;
    *) echo "Los módulos U11 deben proceder del artefacto U11 elegido: $modules_real" >&2; exit 1 ;;
esac
case "$out_real/" in
    "$allowed_output/"*) ;;
    *) echo "La salida U11 debe permanecer bajo artifacts/initramfs/u11: $out_real" >&2; exit 1 ;;
esac

for forbidden in \
    "$ROOT/sources/wifi-kernel" \
    "$ROOT/artifacts/kernel/wifi" \
    "$ROOT/artifacts/stock" \
    "$ROOT/artifacts/candidates/reference"; do
    forbidden_real=$(canonical_output_path "$forbidden")
    case "$modules_real/|$out_real/" in
        *"$forbidden_real/"*) echo "Ruta U3/EZE4 prohibida en pipeline U11: $forbidden_real" >&2; exit 1 ;;
    esac
done

test -d "$MODULES_ROOT" || { echo "Faltan módulos U11: $MODULES_ROOT" >&2; exit 1; }
unexpected_module_entry=$(find "$BUILD_ROOT/modules-installed" ! -type d ! -type f -print -quit)
if [ -n "$unexpected_module_entry" ]; then
    echo "La extracción de módulos U11 contiene un tipo no regular: $unexpected_module_entry" >&2
    exit 1
fi
mapfile -t releases < <(find "$MODULES_ROOT" -mindepth 1 -maxdepth 1 -type d -print)
[ "${#releases[@]}" -eq 1 ] && [ "$(basename "${releases[0]}")" = "$U11_KERNEL_RELEASE" ] || {
    echo "Se esperaba exactamente el release U11 $U11_KERNEL_RELEASE bajo $MODULES_ROOT" >&2
    exit 1
}
module_count=$(find "${releases[0]}" -type f -name '*.ko' | wc -l)
[ "$module_count" -eq 282 ] || { echo "Se esperaban 282 módulos U11; encontrados: $module_count" >&2; exit 1; }

(
    cd "$BUILD_ROOT"
    sha256sum -c SHA256SUMS
)
source_manifest_sha256=$(sha256sum "$BUILD_ROOT/SHA256SUMS" | cut -d' ' -f1)
source_modules_archive_sha256=$(sha256sum "$BUILD_ROOT/modules-root.tar.gz" | cut -d' ' -f1)
source_modules_tree_sha256=$(
    cd "${releases[0]}"
    find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1
)

build_profiles() {
    local destination=$1
    DEVICE_VARIANT=wifi BUSYBOX="$BUSYBOX" MODULES_MODE=none \
        INITRAMFS_OUT="$destination/minimal" INITRAMFS_STAGE_PARENT="${TMPDIR:-/tmp}" SOURCE_DATE_EPOCH=0 \
        "$ROOT/scripts/build-initramfs.sh"
    DEVICE_VARIANT=wifi BUSYBOX="$BUSYBOX" MODULES_MODE=deps \
        MODULES_ROOT="$MODULES_ROOT" MODULES_LIST="$ROOT/configs/initramfs-modules.conf" \
        INITRAMFS_OUT="$destination/ufs" INITRAMFS_STAGE_PARENT="${TMPDIR:-/tmp}" SOURCE_DATE_EPOCH=0 \
        "$ROOT/scripts/build-initramfs.sh"
    DEVICE_VARIANT=wifi BUSYBOX="$BUSYBOX" MODULES_MODE=deps \
        MODULES_ROOT="$MODULES_ROOT" MODULES_LIST="$ROOT/configs/initramfs-modules-usb.conf" \
        INITRAMFS_OUT="$destination/usb" INITRAMFS_STAGE_PARENT="${TMPDIR:-/tmp}" SOURCE_DATE_EPOCH=0 \
        "$ROOT/scripts/build-initramfs.sh"
}

snapshot() {
    local destination=$1 profile file
    for profile in minimal ufs usb; do
        for file in gts9fe-initramfs.cpio gts9fe-initramfs.cpio.gz gts9fe-initramfs.cpio.lz4; do
            sha256sum "$destination/$profile/$file" | sed "s#  $destination/#  #"
        done
    done
}

mkdir -p "$OUT_ROOT"
build_profiles "$OUT_ROOT"
first=$(snapshot "$OUT_ROOT")

reproducible=not-checked
if [ "$REPRO_CHECK" = 1 ]; then
    scratch=$(mktemp -d "${TMPDIR:-/tmp}/gts9fe-u11-initramfs.XXXXXX")
    cleanup() { rm -rf -- "$scratch"; }
    trap cleanup EXIT
    build_profiles "$scratch"
    second=$(snapshot "$scratch")
    [ "$first" = "$second" ] || {
        echo "Los initramfs U11 no son byte-reproducibles entre dos builds." >&2
        diff -u <(printf '%s\n' "$first") <(printf '%s\n' "$second") >&2 || true
        exit 1
    }
    reproducible=yes
fi

stock_limit=$(python3 - "$ROOT/artifacts/stock/boot-layout.json" <<'PY'
import json
import sys
with open(sys.argv[1], encoding="utf-8") as stream:
    layout = json.load(stream)
print(next(item["ramdisk_size"] for item in layout if item.get("path", "").endswith("init_boot.img")))
PY
)

{
    printf 'source_ap_version=%s\n' "$U11_SOURCE_AP_VERSION"
    printf 'source_base_version=%s\n' "$U11_SOURCE_BASE_VERSION"
    printf 'kernel_release=%s\n' "$U11_KERNEL_RELEASE"
    printf 'module_count=%s\n' "$module_count"
    printf 'source_build_manifest_sha256=%s\n' "$source_manifest_sha256"
    printf 'source_modules_archive_sha256=%s\n' "$source_modules_archive_sha256"
    printf 'source_modules_tree_sha256=%s\n' "$source_modules_tree_sha256"
    printf 'source_date_epoch=0\n'
    printf 'byte_reproducible=%s\n' "$reproducible"
    printf 'stock_init_boot_ramdisk_bytes=%s\n' "$stock_limit"
    for profile in minimal ufs usb; do
        size=$(stat -c %s "$OUT_ROOT/$profile/gts9fe-initramfs.cpio.lz4")
        printf '%s_lz4_bytes=%s\n' "$profile" "$size"
        printf '%s_margin_bytes=%s\n' "$profile" "$((stock_limit - size))"
    done
    printf 'physical_write_gate=NO-GO\n'
} > "$OUT_ROOT/BUILD-METADATA"

printf '%s\n' "$first" > "$OUT_ROOT/SHA256SUMS"
echo "Initramfs U11 construidos y verificados en $OUT_ROOT"
echo "Puerta física: NO-GO. Este comando no empaqueta ni escribe particiones."
