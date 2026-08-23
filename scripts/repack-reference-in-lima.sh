#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
VM=${LIMA_INSTANCE:-gts9fe-build}

command -v limactl >/dev/null || { echo "Falta limactl." >&2; exit 1; }
for input in \
    "$ROOT/artifacts/stock/images/boot.img" \
    "$ROOT/artifacts/stock/images/init_boot.img" \
    "$ROOT/artifacts/kernel/wifi/reference-dist/Image" \
    "$ROOT/artifacts/initramfs/wifi/gts9fe-initramfs.cpio" \
    "$ROOT/sources/toolchain/magisk-v30.7/magiskboot-arm64"; do
    test -f "$input" || { echo "Falta $input" >&2; exit 1; }
done

limactl shell "$VM" env HOST_PROJECT="$ROOT" bash -lc '
set -euo pipefail
cd "$HOST_PROJECT"
sha256sum -c configs/toolchain-reference.sha256
tool="$HOST_PROJECT/sources/toolchain/magisk-v30.7/magiskboot-arm64"
mkdir -p "$HOST_PROJECT/artifacts/candidates/reference"
rm -f -- "$HOST_PROJECT/artifacts/candidates/reference/SHA256SUMS"
MAGISKBOOT="$tool" ./scripts/repack-boot.sh \
    artifacts/stock/images/boot.img \
    artifacts/kernel/wifi/reference-dist/Image \
    artifacts/candidates/reference/boot-UNSIGNED.img
MAGISKBOOT="$tool" ./scripts/repack-init-boot.sh \
    artifacts/stock/images/init_boot.img \
    artifacts/initramfs/wifi/gts9fe-initramfs.cpio \
    artifacts/candidates/reference/init_boot-UNSIGNED.img
(cd artifacts/candidates/reference && \
    sha256sum boot-UNSIGNED.img init_boot-UNSIGNED.img > SHA256SUMS)
./scripts/verify-avb-candidates.sh
'
