#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
# shellcheck source=scripts/safety-paths.sh
source "$ROOT/scripts/safety-paths.sh"
VARIANT=${DEVICE_VARIANT:-wifi}
case "$VARIANT" in
    wifi)
        DEFAULT_KERNEL="$ROOT/sources/wifi-kernel"
        DEFAULT_DEFCONFIG=s5e8835-gts9fewifixx_defconfig
        SOURCE_AP_VERSION=X510XXU3BXDG
        BOARD_DTS_DIR=samsung/gts9fewifi
        ;;
    5g)
        DEFAULT_KERNEL="$ROOT/sources/device-kernel"
        DEFAULT_DEFCONFIG=s5e8835-gts9fexx_defconfig
        SOURCE_AP_VERSION=X516BXXU7CYE1
        BOARD_DTS_DIR=samsung/gts9fe
        ;;
    *) echo "DEVICE_VARIANT debe ser wifi o 5g" >&2; exit 2 ;;
esac
KERNEL=${KERNEL_DIR:-$DEFAULT_KERNEL}
OUT=${KERNEL_OUT:-$ROOT/artifacts/kernel/$VARIANT/obj}
DIST=${DIST_DIR:-$ROOT/artifacts/kernel/$VARIANT/dist}
FRAGMENT="$ROOT/configs/gts9fe-linux.fragment"
PATCH_DIR="$ROOT/patches/downstream/$VARIANT"
JOBS=${JOBS:-$(getconf _NPROCESSORS_ONLN 2>/dev/null || echo 4)}
DEFCONFIG=${DEFCONFIG:-$DEFAULT_DEFCONFIG}
TARGET_SOC=${TARGET_SOC:-s5e8835}
BASE_DTB_TARGET=exynos/s5e8835.dtb

TARGET_FILE=${TARGET_FILE:-$ROOT/configs/target-sm-x510.env}
if [ -f "$TARGET_FILE" ]; then
    # shellcheck source=/dev/null
    source "$TARGET_FILE"
    if [ "$VARIANT" != "$TARGET_VARIANT" ] && [ "${ALLOW_REFERENCE_BUILD:-0}" != 1 ]; then
        echo "BLOQUEADO: el objetivo es $TARGET_MODEL ($TARGET_VARIANT), no '$VARIANT'." >&2
        echo "Para compilar sólo como referencia: ALLOW_REFERENCE_BUILD=1 $0" >&2
        exit 1
    fi
    if [ "$VARIANT" = "$TARGET_VARIANT" ] && \
       [ "$SOURCE_AP_VERSION" != "$TARGET_AP_VERSION" ] && \
       [ "${ALLOW_REFERENCE_BUILD:-0}" != 1 ]; then
        echo "BLOQUEADO: fuente $SOURCE_AP_VERSION != firmware objetivo $TARGET_AP_VERSION." >&2
        echo "Esta fuente antigua sirve para estudiar, no como imagen flasheable." >&2
        echo "Para comprobar únicamente que compila: ALLOW_REFERENCE_BUILD=1 $0" >&2
        exit 1
    fi
fi

if [ "$(uname -s)" != Linux ]; then
    echo "El kernel Samsung sólo se construye de forma soportada en Linux." >&2
    exit 1
fi
test -f "$KERNEL/Makefile" || { echo "Falta $KERNEL; ejecuta fetch-sources.sh --full" >&2; exit 1; }
test -x "$KERNEL/scripts/kconfig/merge_config.sh" || {
    echo "El checkout es parcial; ejecuta scripts/fetch-sources.sh --full." >&2
    exit 1
}

if [ -n "${CLANG_ROOT:-}" ]; then
    export PATH="$CLANG_ROOT/bin:$PATH"
elif [ -x "$ROOT/sources/toolchain/clang-linux-x86/clang-r450784d/bin/clang" ]; then
    export PATH="$ROOT/sources/toolchain/clang-linux-x86/clang-r450784d/bin:$PATH"
fi
command -v clang >/dev/null || { echo "Falta clang; ejecuta fetch-toolchain.sh." >&2; exit 1; }

# Fija los metadatos que mkcompile_h incrusta en Image. Sin esto, dos builds
# idénticos cambian por la hora, el hostname y el contador .version.
export KBUILD_BUILD_USER=${KBUILD_BUILD_USER:-gts9fe-student}
export KBUILD_BUILD_HOST=${KBUILD_BUILD_HOST:-gts9fe-build}
export KBUILD_BUILD_VERSION=${KBUILD_BUILD_VERSION:-1}
if [ -z "${KBUILD_BUILD_TIMESTAMP:-}" ]; then
    KBUILD_BUILD_TIMESTAMP=$(git -C "$KERNEL" show -s --format=%cD HEAD)
    export KBUILD_BUILD_TIMESTAMP
fi

# Samsung lists these files in dtbo-y, but this tree's DTS Makefile assigns
# them through the obsolete `always` variable.  Consequently a plain `dtbs`
# can succeed without producing the device overlays.  Request every board DTS
# explicitly and verify it below so a successful build cannot be misleading.
mapfile -t board_dtbo_targets < <(
    cd "$KERNEL/arch/arm64/boot/dts"
    find "$BOARD_DTS_DIR" -maxdepth 1 -type f -name '*.dts' -print \
        | LC_ALL=C sort | sed 's/\.dts$/.dtbo/'
)
if [ "${#board_dtbo_targets[@]}" -eq 0 ]; then
    echo "No se encontraron overlays fuente en $BOARD_DTS_DIR" >&2
    exit 1
fi

# This Android 14 tree predates Clang 21.  That compiler added a warning for
# uninitialised const-qualified dummy variables in Linux's typecheck() macro.
# The macro only compares pointer types and never reads the dummy value, so the
# warning is not actionable.  Keep this narrowly version-gated: older Android
# Clang releases do not recognise the option.
clang_major=$(clang --version | sed -n '1s/.*version \([0-9][0-9]*\).*/\1/p')
extra_kcflags=${KCFLAGS:-}
if [ -n "$clang_major" ] && [ "$clang_major" -ge 21 ]; then
    extra_kcflags="${extra_kcflags:+$extra_kcflags }-Wno-default-const-init-var-unsafe -Wno-default-const-init-field-unsafe -Wno-strict-prototypes -Wno-deprecated-non-prototype"
    echo "Compatibilidad: Clang $clang_major; se permiten inicializadores const y prototipos heredados"
fi

mkdir -p "$OUT" "$DIST"
out_real=$(cd "$OUT" && pwd -P)
dist_real=$(cd "$DIST" && pwd -P)
project_parent=$(dirname "$ROOT")
for generated in "$out_real" "$dist_real"; do
    guard_output_directory "$generated" "Ruta de build"
    case "$generated" in
        /|/tmp|/var/tmp|"$ROOT"|"$project_parent"|"${HOME:-__no_home__}")
            echo "Ruta de build demasiado amplia y rechazada: $generated" >&2
            exit 1
            ;;
    esac
done
[ "$out_real" != "$dist_real" ] || {
    echo "KERNEL_OUT y DIST_DIR deben ser directorios distintos." >&2
    exit 1
}
case "$dist_real/" in
    "$out_real/"*)
        echo "DIST_DIR no puede estar dentro de KERNEL_OUT." >&2
        exit 1
        ;;
esac
case "$out_real/" in
    "$dist_real/"*)
        echo "KERNEL_OUT no puede estar dentro de DIST_DIR." >&2
        exit 1
        ;;
esac

# Un fallo posterior no debe dejar una distribución antigua con apariencia de
# éxito. Los objetos incrementales se conservan; sólo se invalidan entregables.
rm -rf -- "$DIST/modules-root" "$DIST/dtbs" "$DIST/dtbo-unsigned.entries"
rm -f -- "$DIST/Image" "$DIST/kernel.config" "$DIST/System.map" \
    "$DIST/BUILD-METADATA" "$DIST/SHA256SUMS" \
    "$DIST/dtbo-unsigned.img" "$DIST/dtbo-unsigned.img.sha256"

make_env=(
    ARCH=arm64 LLVM=1 LLVM_IAS=1
    PLATFORM_VERSION=13 ANDROID_MAJOR_VERSION=t
    TARGET_SOC="$TARGET_SOC" DTC_FLAGS=-@
    O="$OUT"
)
if [ -n "$extra_kcflags" ]; then
    make_env+=(KCFLAGS="$extra_kcflags")
fi

echo "1/4 Configuración base $DEFCONFIG"
make -C "$KERNEL" "${make_env[@]}" "$DEFCONFIG"

echo "2/4 Mezcla del fragmento Linux"
"$KERNEL/scripts/kconfig/merge_config.sh" -m -O "$OUT" "$OUT/.config" "$FRAGMENT"
make -C "$KERNEL" "${make_env[@]}" olddefconfig

echo "3/4 Kernel, DT y módulos"
make -C "$KERNEL" "${make_env[@]}" -j"$JOBS" \
    Image "$BASE_DTB_TARGET" modules "${board_dtbo_targets[@]}"
make -C "$KERNEL" "${make_env[@]}" \
    INSTALL_MOD_PATH="$DIST/modules-root" \
    INSTALL_MOD_STRIP="${INSTALL_MOD_STRIP:-1}" modules_install

echo "4/4 Recogida de artefactos"
cp "$OUT/arch/arm64/boot/Image" "$DIST/Image"
mkdir -p "$DIST/dtbs/$(dirname "$BASE_DTB_TARGET")"
cp "$OUT/arch/arm64/boot/dts/$BASE_DTB_TARGET" \
    "$DIST/dtbs/$BASE_DTB_TARGET"
for overlay in "${board_dtbo_targets[@]}"; do
    mkdir -p "$DIST/dtbs/$(dirname "$overlay")"
    cp "$OUT/arch/arm64/boot/dts/$overlay" "$DIST/dtbs/$overlay"
    test -s "$DIST/dtbs/$overlay" || {
        echo "Falta el overlay obligatorio: $DIST/dtbs/$overlay" >&2
        exit 1
    }
done
cp "$OUT/.config" "$DIST/kernel.config"
cp "$OUT/System.map" "$DIST/" 2>/dev/null || true

{
    echo "variant=$VARIANT"
    echo "source_ap_version=$SOURCE_AP_VERSION"
    echo "target_ap_version=${TARGET_AP_VERSION:-unknown}"
    echo "source_commit=$(git -C "$KERNEL" rev-parse HEAD)"
    echo "source_dirty=$(if git -C "$KERNEL" diff --quiet && git -C "$KERNEL" diff --cached --quiet; then echo no; else echo yes; fi)"
    echo "kernel_release=$(make -s -C "$KERNEL" "${make_env[@]}" kernelrelease)"
    echo "clang=$(clang --version | sed -n '1p')"
    echo "kbuild_build_user=$KBUILD_BUILD_USER"
    echo "kbuild_build_host=$KBUILD_BUILD_HOST"
    echo "kbuild_build_version=$KBUILD_BUILD_VERSION"
    echo "kbuild_build_timestamp=$KBUILD_BUILD_TIMESTAMP"
    echo "fragment_sha256=$(sha256sum "$FRAGMENT" | cut -d' ' -f1)"
    echo "defconfig_sha256=$(sha256sum "$KERNEL/arch/arm64/configs/$DEFCONFIG" | cut -d' ' -f1)"
    echo "patchset_sha256=$(cd "$PATCH_DIR" && find . -type f -name '*.patch' -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -d' ' -f1)"
} > "$DIST/BUILD-METADATA"

(
    cd "$DIST"
    find . -type f ! -name SHA256SUMS -print0 | LC_ALL=C sort -z | \
        xargs -0 sha256sum
) > "$DIST/SHA256SUMS"
echo "Build terminado en $DIST"
echo "No flashees todavía: continúa por docs/06-bring-up.md."
