#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
MODE=--analysis
VARIANT=${DEVICE_VARIANT:-wifi}
SOURCES="$ROOT/sources"
MAINLINE_DIR="$SOURCES/mainline-kernel"

MAINLINE_URL=${MAINLINE_URL:-https://github.com/torvalds/linux.git}
MAINLINE_COMMIT=${MAINLINE_COMMIT:-26260251022fbc2f248a3d747a9b2b961b18d2d8}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --analysis|--full) MODE=$1 ;;
        --variant) shift; VARIANT=${1:-} ;;
        *) echo "Uso: $0 [--analysis|--full] [--variant wifi|5g]" >&2; exit 2 ;;
    esac
    shift
done

case "$VARIANT" in
    wifi)
        DEVICE_DIR="$SOURCES/wifi-kernel"
        DEVICE_URL=${DEVICE_URL:-https://github.com/underdog54/android_kernel_samsung_gts9fewifi.git}
        DEVICE_BRANCH=${DEVICE_BRANCH:-stock}
        DEVICE_COMMIT=${DEVICE_COMMIT:-9a752a83347461b3785711760ba925fcabea3071}
        BOARD_DTS=/arch/arm64/boot/dts/samsung/gts9fewifi/
        DEVICE_DEFCONFIG=/arch/arm64/configs/s5e8835-gts9fewifixx_defconfig
        MODULE_LIST=/vendor_module_list_s5e8835_gts9fewifi.cfg
        ;;
    5g)
        DEVICE_DIR="$SOURCES/device-kernel"
        DEVICE_URL=${DEVICE_URL:-https://github.com/Fede2782/android_kernel_samsung_gts9fe.git}
        DEVICE_BRANCH=${DEVICE_BRANCH:-sep-16.0/stock}
        DEVICE_COMMIT=${DEVICE_COMMIT:-56f84616c0263aa85ccbbfb77f69af2fe4aa4bb6}
        BOARD_DTS=/arch/arm64/boot/dts/samsung/gts9fe/
        DEVICE_DEFCONFIG=/arch/arm64/configs/s5e8835-gts9fexx_defconfig
        MODULE_LIST=/vendor_module_list_s5e8835_gts9fe.cfg
        ;;
    *) echo "Variante inválida: $VARIANT (usa wifi o 5g)" >&2; exit 2 ;;
esac

mkdir -p "$SOURCES"

if [ ! -d "$DEVICE_DIR/.git" ]; then
    git clone --depth 1 --filter=blob:none --sparse --branch "$DEVICE_BRANCH" \
        "$DEVICE_URL" "$DEVICE_DIR"
    if [ "$(git -C "$DEVICE_DIR" rev-parse HEAD)" != "$DEVICE_COMMIT" ]; then
        git -C "$DEVICE_DIR" fetch --depth 1 origin "$DEVICE_COMMIT"
        git -C "$DEVICE_DIR" checkout --detach "$DEVICE_COMMIT"
    fi
fi

if [ "$MODE" = --full ]; then
    echo "Hidratando el árbol completo del kernel Samsung (puede tardar)..."
    git -C "$DEVICE_DIR" sparse-checkout disable
else
    git -C "$DEVICE_DIR" sparse-checkout set --no-cone \
        /arch/arm64/boot/dts/exynos/ \
        "$BOARD_DTS" \
        "$DEVICE_DEFCONFIG" \
        /build_kernel.sh /Makefile \
        /vendor_boot_module_order_s5e8835.cfg \
        /vendor_module_list_s5e8835.cfg \
        "$MODULE_LIST" \
        /drivers/clk/samsung/clk-s5e8835.c \
        /drivers/gpu/drm/samsung/panel/tft_common/hx83102j_gts9fe_boe.c \
        /drivers/gpu/drm/samsung/panel/tft_common/nt36523n_gts9fe_csot.c \
        /drivers/mfd/samsung/pmic/s2mpu15_core_8835.c \
        /drivers/mfd/samsung/pmic/s2mpu16_core_8835.c \
        /drivers/scsi/ufs/s5e8835/ \
        /include/dt-bindings/clock/s5e8835.h
fi

actual_device=$(git -C "$DEVICE_DIR" rev-parse HEAD)
if [ "$actual_device" != "$DEVICE_COMMIT" ]; then
    echo "ERROR: device-kernel está en $actual_device; se exige $DEVICE_COMMIT" >&2
    exit 1
fi

if [ ! -d "$MAINLINE_DIR/.git" ]; then
    git clone --depth 1 --filter=blob:none --sparse "$MAINLINE_URL" "$MAINLINE_DIR"
    if [ "$(git -C "$MAINLINE_DIR" rev-parse HEAD)" != "$MAINLINE_COMMIT" ]; then
        git -C "$MAINLINE_DIR" fetch --depth 1 origin "$MAINLINE_COMMIT"
        git -C "$MAINLINE_DIR" checkout --detach "$MAINLINE_COMMIT"
    fi
fi

git -C "$MAINLINE_DIR" sparse-checkout set \
    arch/arm64/boot/dts/exynos arch/arm64/configs \
    drivers/clk/samsung drivers/pinctrl/samsung drivers/tty/serial \
    drivers/iommu drivers/ufs/host drivers/phy/samsung \
    drivers/gpu/drm/exynos drivers/gpu/drm/panel drivers/usb/dwc3 drivers/usb/typec \
    drivers/of drivers/irqchip drivers/clocksource drivers/dma drivers/soc/samsung \
    drivers/spi drivers/i2c drivers/hid drivers/input/keyboard drivers/input/tablet \
    drivers/input/touchscreen sound/soc/samsung sound/soc/codecs \
    drivers/mfd drivers/regulator drivers/mmc/host drivers/power/supply \
    Documentation/devicetree/bindings

actual_mainline=$(git -C "$MAINLINE_DIR" rev-parse HEAD)
if [ "$actual_mainline" != "$MAINLINE_COMMIT" ]; then
    echo "ERROR: mainline está en $actual_mainline; se exige $MAINLINE_COMMIT" >&2
    exit 1
fi

printf 'Fuentes preparadas:\n  variante: %s\n  Samsung: %s\n  mainline: %s\n' \
    "$VARIANT" "$actual_device" "$actual_mainline"
