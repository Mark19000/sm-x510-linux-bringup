#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VM=${LIMA_INSTANCE:-gts9fe-build}

command -v limactl >/dev/null || { echo "Falta limactl." >&2; exit 1; }
test -d "$ROOT/artifacts/kernel/wifi/reference-dist/modules-root/lib/modules" || {
    echo "Faltan módulos; ejecuta primero scripts/build-reference-in-lima.sh." >&2
    exit 1
}

limactl shell "$VM" env HOST_PROJECT="$ROOT" bash -lc '
set -euo pipefail
cd "$HOST_PROJECT"
./scripts/build-busybox.sh
DEVICE_VARIANT=wifi MODULES_MODE=none \
    INITRAMFS_OUT="$HOST_PROJECT/artifacts/initramfs/wifi" \
    ./scripts/build-initramfs.sh
DEVICE_VARIANT=wifi MODULES_MODE=deps \
    MODULES_ROOT="$HOST_PROJECT/artifacts/kernel/wifi/reference-dist/modules-root/lib/modules" \
    INITRAMFS_OUT="$HOST_PROJECT/artifacts/initramfs/wifi-ufs" \
    ./scripts/build-initramfs.sh
DEVICE_VARIANT=wifi MODULES_MODE=deps \
    MODULES_ROOT="$HOST_PROJECT/artifacts/kernel/wifi/reference-dist/modules-root/lib/modules" \
    MODULES_LIST="$HOST_PROJECT/configs/initramfs-modules-usb.conf" \
    INITRAMFS_OUT="$HOST_PROJECT/artifacts/initramfs/wifi-usb" \
    ./scripts/build-initramfs.sh
usb_lz4="$HOST_PROJECT/artifacts/initramfs/wifi-usb/gts9fe-initramfs.cpio.lz4"
layout="$HOST_PROJECT/artifacts/stock/boot-layout.json"
if [ -f "$usb_lz4" ] && [ -f "$layout" ]; then
    stock_limit=$(python3 -c \
        "import json,sys; print(next(x[\"ramdisk_size\"] for x in json.load(open(sys.argv[1])) if x.get(\"path\", \"\").endswith(\"init_boot.img\")))" \
        "$layout")
    usb_size=$(stat -c %s "$usb_lz4")
    if [ "$usb_size" -gt "$stock_limit" ]; then
        echo "AVISO: perfil USB $usb_size B > ramdisk stock $stock_limit B; sólo diagnóstico, no reempaquetar."
    fi
fi
'
