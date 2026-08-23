#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT=${1:-$ROOT/reports/device-$STAMP}

command -v adb >/dev/null || { echo "Falta adb (Android platform-tools)." >&2; exit 1; }
adb get-state >/dev/null
mkdir -p "$OUT"

model=$(adb shell getprop ro.product.model | tr -d '\r')
display_build=$(adb shell getprop ro.build.display.id | tr -d '\r')
bootloader=$(adb shell getprop ro.bootloader | tr -d '\r')
security_patch=$(adb shell getprop ro.build.version.security_patch | tr -d '\r')
boot_csc=$(adb shell getprop ro.boot.sales_code | tr -d '\r')
sales_csc=$(adb shell getprop ro.csc.sales_code | tr -d '\r')
printf '%s\n' \
    "model=$model" \
    "display_build=$display_build" \
    "bootloader=$bootloader" \
    "security_patch=$security_patch" \
    "boot_csc=$boot_csc" \
    "sales_csc=$sales_csc" > "$OUT/identity.txt"

adb shell getprop > "$OUT/getprop.txt"
adb shell uname -a > "$OUT/uname.txt"
adb shell cat /proc/cmdline > "$OUT/proc-cmdline.txt" || true
adb shell cat /proc/partitions > "$OUT/proc-partitions.txt" || true
adb shell cat /proc/iomem > "$OUT/proc-iomem.txt" || true
adb shell cat /proc/config.gz > "$OUT/config.gz" || true
adb shell ls -l /dev/block/by-name > "$OUT/partitions-by-name.txt" || true
adb shell ls -l /sys/firmware/devicetree/base > "$OUT/devicetree-root.txt" || true
adb exec-out cat /sys/firmware/fdt > "$OUT/running.dtb" || true
adb shell dmesg > "$OUT/dmesg.txt" || true

TARGET_FILE="$ROOT/configs/target-sm-x510.env"
if [ -f "$TARGET_FILE" ]; then
    # shellcheck source=/dev/null
    source "$TARGET_FILE"
    if [ "$model" != "$TARGET_MODEL" ]; then
        echo "AVISO: el dispositivo conectado dice '$model', se esperaba '$TARGET_MODEL'." >&2
    fi
    case "${bootloader}${display_build}" in
        *"$TARGET_AP_VERSION"*) ;;
        *)
            echo "AVISO: el dispositivo conectado no anuncia $TARGET_AP_VERSION." >&2
            echo "Revisa $OUT/identity.txt antes de usar sus datos." >&2
            ;;
    esac
fi

if [ -s "$OUT/running.dtb" ] && command -v dtc >/dev/null 2>&1; then
    dtc -I dtb -O dts -o "$OUT/running.dts" "$OUT/running.dtb" || true
fi

echo "Inventario de sólo lectura guardado en $OUT"
echo "Revisa getprop.txt: modelo, bootloader y build deben coincidir con el firmware fuente."
