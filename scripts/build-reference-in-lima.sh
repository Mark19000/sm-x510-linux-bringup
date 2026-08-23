#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VM=${LIMA_INSTANCE:-gts9fe-build}
DEVICE_URL=${DEVICE_URL:-https://github.com/underdog54/android_kernel_samsung_gts9fewifi.git}
DEVICE_COMMIT=${DEVICE_COMMIT:-9a752a83347461b3785711760ba925fcabea3071}
JOBS=${JOBS:-6}
LOG=${BUILD_LOG:-$ROOT/artifacts/logs/reference-kernel-build.log}

command -v limactl >/dev/null || { echo "Falta limactl." >&2; exit 1; }
mkdir -p "$(dirname "$LOG")"
limactl shell "$VM" env \
    HOST_PROJECT="$ROOT" DEVICE_URL="$DEVICE_URL" \
    DEVICE_COMMIT="$DEVICE_COMMIT" BUILD_JOBS="$JOBS" bash -lc '
set -euo pipefail
guest_work="$HOME/gts9fe-work"
kernel="$guest_work/wifi-kernel"
object="$guest_work/obj"
mkdir -p "$guest_work"
if [ ! -d "$kernel/.git" ]; then
    git clone --depth 1 --branch stock "$DEVICE_URL" "$kernel"
fi
actual=$(git -C "$kernel" rev-parse HEAD)
if [ "$actual" != "$DEVICE_COMMIT" ]; then
    echo "Commit inesperado: $actual (esperado $DEVICE_COMMIT)" >&2
    exit 1
fi
cd "$HOST_PROJECT"
DEVICE_VARIANT=wifi KERNEL_DIR="$kernel" scripts/apply-patches.sh
ALLOW_REFERENCE_BUILD=1 DEVICE_VARIANT=wifi \
    KERNEL_DIR="$kernel" KERNEL_OUT="$object" \
    DIST_DIR="$HOST_PROJECT/artifacts/kernel/wifi/reference-dist" \
    JOBS="$BUILD_JOBS" KBUILD_BUILD_USER=student \
    KBUILD_BUILD_HOST=gts9fe-build scripts/build-downstream.sh
' 2>&1 | tee "$LOG"
