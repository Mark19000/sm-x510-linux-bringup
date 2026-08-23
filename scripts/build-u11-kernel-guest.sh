#!/usr/bin/env bash
set -Eeuo pipefail

# Trusted, fixed build recipe for the exact SM-X510 Android 16/U11 OSRC
# composite. This script runs only inside the Linux/ext4 Lima guest. It never
# creates a boot image, AVB signature or flash candidate.

usage() {
    cat >&2 <<'EOF'
Uso: build-u11-kernel-guest.sh --run-root DIR --kernel DIR --out DIR --dist DIR \
       --patch-dir DIR --patch-manifest FILE --fragment FILE [--jobs N]
EOF
}

RUN_ROOT=
KERNEL=
OUT=
DIST=
PATCH_DIR=
PATCH_MANIFEST=
FRAGMENT=
JOBS=4
while [ "$#" -gt 0 ]; do
    case "$1" in
        --run-root) shift; RUN_ROOT=${1:-} ;;
        --kernel) shift; KERNEL=${1:-} ;;
        --out) shift; OUT=${1:-} ;;
        --dist) shift; DIST=${1:-} ;;
        --patch-dir) shift; PATCH_DIR=${1:-} ;;
        --patch-manifest) shift; PATCH_MANIFEST=${1:-} ;;
        --fragment) shift; FRAGMENT=${1:-} ;;
        --jobs) shift; JOBS=${1:-} ;;
        -h|--help) usage; exit 0 ;;
        *) echo "Argumento U11 desconocido: $1" >&2; usage; exit 2 ;;
    esac
    shift
done

for required in RUN_ROOT KERNEL OUT DIST PATCH_DIR PATCH_MANIFEST FRAGMENT; do
    [ -n "${!required}" ] || { echo "Falta --$(printf '%s' "$required" | tr '_' '-' | tr '[:upper:]' '[:lower:]')" >&2; exit 2; }
done
case "$JOBS" in ''|*[!0-9]*) echo "--jobs debe ser un entero positivo" >&2; exit 2 ;; esac
[ "$JOBS" -ge 1 ] && [ "$JOBS" -le 64 ] || { echo "--jobs fuera de rango 1..64" >&2; exit 2; }
[ "$(uname -s)" = Linux ] || { echo "El perfil U11 sólo se ejecuta en Linux." >&2; exit 1; }

command -v realpath >/dev/null || { echo "Falta realpath en el guest." >&2; exit 1; }
command -v git >/dev/null || { echo "Falta git (se usa git apply sin checkout Git)." >&2; exit 1; }
command -v clang >/dev/null || { echo "Falta clang en el guest." >&2; exit 1; }
command -v sha256sum >/dev/null || { echo "Falta sha256sum en el guest." >&2; exit 1; }

RUN_ROOT=$(realpath -e "$RUN_ROOT")
KERNEL=$(realpath -e "$KERNEL")
PATCH_DIR=$(realpath -e "$PATCH_DIR")
PATCH_MANIFEST=$(realpath -e "$PATCH_MANIFEST")
FRAGMENT=$(realpath -e "$FRAGMENT")
OUT=$(realpath -m "$OUT")
DIST=$(realpath -m "$DIST")

inside_run() {
    case "$1/" in "$RUN_ROOT/"*) return 0 ;; *) return 1 ;; esac
}
for path in "$KERNEL" "$OUT" "$DIST" "$PATCH_DIR" "$PATCH_MANIFEST" "$FRAGMENT"; do
    inside_run "$path" || { echo "Ruta fuera del run U11 ext4: $path" >&2; exit 1; }
done
[ "$OUT" != "$DIST" ] || { echo "OUT y DIST deben ser distintos." >&2; exit 1; }
case "$OUT/" in "$DIST/"*) echo "OUT no puede estar dentro de DIST." >&2; exit 1 ;; esac
case "$DIST/" in "$OUT/"*) echo "DIST no puede estar dentro de OUT." >&2; exit 1 ;; esac
[ ! -e "$OUT" ] || { echo "OUT ya existe; cada build U11 requiere un run nuevo: $OUT" >&2; exit 1; }
[ ! -e "$DIST" ] || { echo "DIST ya existe; se rechaza sobrescribir: $DIST" >&2; exit 1; }
[ ! -L "$KERNEL" ] && [ ! -L "$PATCH_DIR" ] || { echo "Kernel y patchset no pueden ser symlinks." >&2; exit 1; }

test -f "$KERNEL/Makefile" || { echo "Falta Makefile del kernel." >&2; exit 1; }
test -x "$KERNEL/scripts/kconfig/merge_config.sh" || { echo "Falta merge_config.sh." >&2; exit 1; }
DEFCONFIG=s5e8835-gts9fewifixx_defconfig
test -f "$KERNEL/arch/arm64/configs/$DEFCONFIG" || { echo "Falta $DEFCONFIG." >&2; exit 1; }

version=$(awk '$1=="VERSION" {v=$3} $1=="PATCHLEVEL" {p=$3} $1=="SUBLEVEL" {s=$3} END {print v "." p "." s}' "$KERNEL/Makefile")
[ "$version" = 5.15.180 ] || { echo "Kernel inesperado: $version (se exige 5.15.180)." >&2; exit 1; }

mapfile -t PATCHES < <(awk 'NF {print $2}' "$PATCH_MANIFEST")
[ "${#PATCHES[@]}" -eq 10 ] || { echo "El perfil U11 exige exactamente diez parches." >&2; exit 1; }
expected_patch_names=(
    0001-arm64-configs-gts9fewifi-enable-linux-early-userspace.patch
    0002-build-fix-modern-clang.patch
    0003-devfreq-add-missing-return-type.patch
    0004-vendor-drivers-fix-invalid-declarations.patch
    0005-gpu-qos-add-flag-check-return-type.patch
    0006-devfreq-remove-broken-dfs-id-fallback.patch
    0008-bringup-disable-crash-tests-and-init-charger-event.patch
    0009-input-novatek-return-valid-irq-status.patch
    0010-usb-typec-use-power-port-enum.patch
    0011-build-use-reproducible-kernel-vdso-build-ids.patch
)
[ "${PATCHES[*]}" = "${expected_patch_names[*]}" ] || { echo "Orden o nombres de parches U11 inesperados." >&2; exit 1; }
(cd "$PATCH_DIR" && sha256sum -c "$PATCH_MANIFEST")

patch_paths=()
for patch_name in "${PATCHES[@]}"; do patch_paths+=("$PATCH_DIR/$patch_name"); done
git -C "$KERNEL" apply --check "${patch_paths[@]}"
git -C "$KERNEL" apply "${patch_paths[@]}"

mkdir "$OUT" "$DIST"
export ARCH=arm64 LLVM=1 LLVM_IAS=1
export PLATFORM_VERSION=13 ANDROID_MAJOR_VERSION=t TARGET_SOC=s5e8835
export KBUILD_BUILD_USER=gts9fe-student
export KBUILD_BUILD_HOST=gts9fe-build
export KBUILD_BUILD_VERSION=1
export KBUILD_BUILD_TIMESTAMP='Thu Jan 1 00:00:00 UTC 1970'
export SOURCE_DATE_EPOCH=0 KCONFIG_NOTIMESTAMP=1 KCONFIG_SEED=0 TZ=UTC LC_ALL=C LANG=C PYTHONHASHSEED=0

clang_line=$(clang --version | sed -n '1p')
clang_major=$(printf '%s\n' "$clang_line" | sed -n 's/.*version \([0-9][0-9]*\).*/\1/p')
extra_kcflags=
if [ -n "$clang_major" ] && [ "$clang_major" -ge 21 ]; then
    extra_kcflags='-Wno-default-const-init-var-unsafe -Wno-default-const-init-field-unsafe -Wno-strict-prototypes -Wno-deprecated-non-prototype'
fi
prefix_flags="-fdebug-prefix-map=$RUN_ROOT=/build/u11 -ffile-prefix-map=$RUN_ROOT=/build/u11 -fmacro-prefix-map=$RUN_ROOT=/build/u11"
extra_kcflags="${extra_kcflags:+$extra_kcflags }$prefix_flags"
make_env=(ARCH=arm64 LLVM=1 LLVM_IAS=1 PLATFORM_VERSION=13 ANDROID_MAJOR_VERSION=t TARGET_SOC=s5e8835 DTC_FLAGS=-@ O="$OUT")
make_env+=(KCPPFLAGS="$prefix_flags" KCFLAGS="$extra_kcflags" KAFLAGS="$prefix_flags")

base_dtb=exynos/s5e8835.dtb
dtbos=(
    samsung/gts9fewifi/gts9fewifi_eur_open_w00_r00.dtbo
    samsung/gts9fewifi/gts9fewifi_eur_open_w00_r01.dtbo
    samsung/gts9fewifi/gts9fewifi_eur_open_w00_r04.dtbo
)
for target in "${dtbos[@]}"; do
    test -f "$KERNEL/arch/arm64/boot/dts/${target%.dtbo}.dts" || { echo "Falta DTS obligatorio: ${target%.dtbo}.dts" >&2; exit 1; }
done

echo "1/4 Configuración U11 fija"
make -C "$KERNEL" "${make_env[@]}" "$DEFCONFIG"
"$KERNEL/scripts/kconfig/merge_config.sh" -m -O "$OUT" "$OUT/.config" "$FRAGMENT"
make -C "$KERNEL" "${make_env[@]}" olddefconfig
grep -qx '# CONFIG_IKHEADERS is not set' "$OUT/.config" || { echo "IKHEADERS sigue activo; se rechaza un Image no reproducible." >&2; exit 1; }
grep -qx '# CONFIG_MODULE_SIG is not set' "$OUT/.config" || { echo "La firma automática sigue activa; faltaría una clave reproducible." >&2; exit 1; }

echo "2/4 Image, DTB, DTBO y módulos"
make -C "$KERNEL" "${make_env[@]}" -j"$JOBS" Image "$base_dtb" modules "${dtbos[@]}"

echo "3/4 modules_install y recogida"
modules_stage="$RUN_ROOT/build-output/modules-stage"
[ ! -e "$modules_stage" ] || { echo "modules-stage ya existe." >&2; exit 1; }
mkdir "$modules_stage"
make -C "$KERNEL" "${make_env[@]}" INSTALL_MOD_PATH="$modules_stage" INSTALL_MOD_STRIP=1 modules_install
kernel_release=$(make -s -C "$KERNEL" "${make_env[@]}" kernelrelease)
[ "$kernel_release" = 5.15.180 ] || { echo "kernelrelease inesperado: $kernel_release" >&2; exit 1; }
module_root="$modules_stage/lib/modules/$kernel_release"
module_count=$(find "$module_root" -type f -name '*.ko' | wc -l | tr -d ' ')
[ "$module_count" = 282 ] || { echo "Se esperaban 282 módulos; obtenidos $module_count." >&2; exit 1; }
if grep -a -F -q "$RUN_ROOT" "$OUT/arch/arm64/boot/Image"; then
    echo "Image conserva la ruta real del run; faltó normalizar DWARF/BTF." >&2
    exit 1
fi
leak_list="$RUN_ROOT/build-output/module-path-leaks.txt"
module_scan_list="$RUN_ROOT/build-output/module-path-scan.list0"
# `find -exec grep ... +` returns 1 when grep correctly finds no matches.  Under
# `set -e` that made a clean build fail immediately after modules_install.  Keep
# discovery and matching separate so a find/read error is fatal while grep's
# ordinary "not found" status is handled explicitly.
find "$module_root" -type f -name '*.ko' -print0 > "$module_scan_list"
: > "$leak_list"
while IFS= read -r -d '' module; do
    if grep -a -F -q "$RUN_ROOT" "$module"; then
        printf '%s\n' "$module" >> "$leak_list"
    else
        grep_status=$?
        [ "$grep_status" -eq 1 ] || { echo "No se pudo inspeccionar el módulo: $module" >&2; exit "$grep_status"; }
    fi
done < "$module_scan_list"
if [ -s "$leak_list" ]; then
    echo "Algún módulo conserva la ruta real del run; se rechaza la distribución: $(sed -n '1p' "$leak_list")" >&2
    exit 1
fi

cp "$OUT/arch/arm64/boot/Image" "$DIST/Image"
cp "$OUT/arch/arm64/boot/dts/$base_dtb" "$DIST/s5e8835.dtb"
for target in "${dtbos[@]}"; do cp "$OUT/arch/arm64/boot/dts/$target" "$DIST/$(basename "$target")"; done
cp "$OUT/.config" "$DIST/kernel.config"
cp "$OUT/System.map" "$DIST/System.map"
cp "$OUT/Module.symvers" "$DIST/Module.symvers"
for metadata in modules.order modules.builtin modules.builtin.modinfo; do cp "$OUT/$metadata" "$DIST/$metadata"; done
for cfg in vendor_boot_module_order_s5e8835.cfg vendor_module_list_s5e8835.cfg vendor_module_list_s5e8835_gts9fewifi.cfg; do
    test -f "$KERNEL/$cfg" || { echo "Falta metadata Samsung: $cfg" >&2; exit 1; }
    cp "$KERNEL/$cfg" "$DIST/$cfg"
done

(cd "$modules_stage" && find . -type f -print0 | LC_ALL=C sort -z | \
    tar --null --no-recursion --sort=name --mtime='@0' --owner=0 --group=0 --numeric-owner -cf - --files-from=- | \
    gzip -n > "$DIST/modules-root.tar.gz")

echo "4/4 Provenance y hashes"
cp "$PATCH_MANIFEST" "$DIST/PATCHES.sha256"
cp "$FRAGMENT" "$DIST/gts9fe-linux.fragment"
{
    echo 'schema=1'
    echo 'artifact_class=offline-reference-only'
    echo 'flash_authorized=no'
    echo 'source_release=X510XXSBDZB4'
    echo 'source_base=X510XXU8DYJ4'
    echo 'target_stock=X510XXUCEZE4'
    echo 'source_bootloader_revision=11'
    echo 'target_bootloader_revision=12'
    echo 'android_major=16'
    echo "kernel_release=$kernel_release"
    echo "defconfig=$DEFCONFIG"
    echo "compiler=$clang_line"
    echo "jobs=$JOBS"
    echo "modules=$module_count"
    echo "kbuild_build_user=$KBUILD_BUILD_USER"
    echo "kbuild_build_host=$KBUILD_BUILD_HOST"
    echo "kbuild_build_version=$KBUILD_BUILD_VERSION"
    echo "kbuild_build_timestamp=$KBUILD_BUILD_TIMESTAMP"
    echo "source_date_epoch=$SOURCE_DATE_EPOCH"
    echo "kconfig_seed=$KCONFIG_SEED"
    echo 'reproducibility_ikheaders=disabled-for-bringup'
    echo 'reproducibility_module_signing=disabled-for-bringup'
    echo 'debug_prefix_map=/build/u11'
    echo 'build_id_policy=fixed-recipe-v3-debug-labels'
    echo 'vmlinux_build_id=57058a4418ab06afd938fd0e9e8cb64a2d5d3933'
    echo 'vdso64_build_id=49cfa25babcb893702da3c382a03fe6a58c52915'
    echo 'vdso32_build_id=6f8c2ce3d766f486c5868124814b838d6496e533'
    echo "fragment_sha256=$(sha256sum "$FRAGMENT" | cut -d' ' -f1)"
    echo "defconfig_sha256=$(sha256sum "$KERNEL/arch/arm64/configs/$DEFCONFIG" | cut -d' ' -f1)"
    echo "patch_manifest_sha256=$(sha256sum "$PATCH_MANIFEST" | cut -d' ' -f1)"
    echo 'build_targets=Image,s5e8835.dtb,r00.dtbo,r01.dtbo,r04.dtbo,modules'
    echo 'boot_image_created=no'
    echo 'avb_signature_created=no'
} > "$DIST/BUILD-METADATA"
(cd "$DIST" && find . -type f ! -name SHA256SUMS -print0 | LC_ALL=C sort -z | xargs -0 sha256sum) > "$DIST/SHA256SUMS"

echo "Build U11 offline terminado: $DIST"
echo "NO-GO físico: este perfil no genera ni autoriza imágenes para flash."
