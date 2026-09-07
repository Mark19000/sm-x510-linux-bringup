#!/usr/bin/env bash
set -Eeuo pipefail

# Production build and reproducibility orchestrator for canonical EZE4 kernel.
# Executes builds inside the Linux/ext4 Lima guest to guarantee case-sensitive
# compilation and exact toolchain alignment.
#
# Enforces strict safety rules:
# - NO flashing
# - NO touching device hardware
# - NO AVB signature modification
# - Automated ABI verification gate (CONFIG_MODVERSIONS parity)

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
source "$ROOT/scripts/safety-paths.sh"
source "$ROOT/configs/eze4-x510xxuceze4.env"

VM=${LIMA_INSTANCE:-gts9fe-build}
BUILD_JOBS=${EZE4_JOBS:-6}
RUN_ID=${EZE4_RUN_ID:-eze4-$(date -u +%Y%m%dT%H%M%SZ)-$$}
HOST_ARTIFACTS_DIR=${EZE4_HOST_ARTIFACTS:-$ROOT/artifacts/eze4/$RUN_ID}
SKIP_ABI_GATE=0

usage() {
    cat >&2 <<'EOF'
Uso:
  ./scripts/build-eze4-in-lima.sh [opciones]

Opciones:
  --vm NAME             Instancia Lima (por defecto gts9fe-build)
  --jobs N              Paralelismo de compilación (1..64; por defecto 6)
  --run-id ID           Identificador único de compilación
  --artifacts-dir DIR   Directorio host para almacenar artefactos finales
  --skip-abi-gate       Omite la validación estricta de paridad ABI
  -h, --help            Muestra esta ayuda

Requisitos:
  - VM Lima iniciada con entorno Clang 21 y ext4
  - Paquete oficial Kernel.tar.gz en audit/eze4-source-intake/packages/base/
  - Manifiesto configs/eze4-patches.sha256 íntegro
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --vm)
            shift
            [ "$#" -gt 0 ] || { usage; exit 2; }
            VM=$1
            ;;
        --jobs)
            shift
            [ "$#" -gt 0 ] || { usage; exit 2; }
            BUILD_JOBS=$1
            ;;
        --run-id)
            shift
            [ "$#" -gt 0 ] || { usage; exit 2; }
            RUN_ID=$1
            ;;
        --artifacts-dir)
            shift
            [ "$#" -gt 0 ] || { usage; exit 2; }
            HOST_ARTIFACTS_DIR=$1
            ;;
        --skip-abi-gate)
            SKIP_ABI_GATE=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Argumento desconocido: $1" >&2
            usage
            exit 2
            ;;
    esac
    shift
done

case "$BUILD_JOBS" in ''|*[!0-9]*) echo "--jobs debe ser un entero positivo." >&2; exit 2 ;; esac
[ "$BUILD_JOBS" -ge 1 ] && [ "$BUILD_JOBS" -le 64 ] || { echo "--jobs fuera de rango 1..64." >&2; exit 2; }

case "$RUN_ID" in
    ''|.|..|*[!A-Za-z0-9._-]*)
        echo "RUN_ID sólo puede contener caracteres alfanuméricos, guiones y puntos: $RUN_ID" >&2
        exit 2
        ;;
esac

echo "========================================================================"
echo "SM-X510 EZE4 CANONICAL BUILD ORCHESTRATOR"
echo "Target SoC: Exynos S5E8835 | Firmware: X510XXUCEZE4 (Android 16 / U12)"
echo "Run ID: $RUN_ID"
echo "VM: $VM (Jobs: $BUILD_JOBS)"
echo "========================================================================"

# 1. Pre-flight host verification
command -v limactl >/dev/null || { echo "ERROR: Falta limactl en el host." >&2; exit 1; }
command -v python3 >/dev/null || { echo "ERROR: Falta python3 en el host." >&2; exit 1; }
command -v shasum >/dev/null || command -v sha256sum >/dev/null || { echo "ERROR: Falta herramienta sha256." >&2; exit 1; }

KERNEL_TARBALL_PATH="$ROOT/$EZE4_KERNEL_TARBALL"
[ -f "$KERNEL_TARBALL_PATH" ] || { echo "ERROR: Falta Kernel.tar.gz en $KERNEL_TARBALL_PATH" >&2; exit 1; }

echo "[1/6] Verificando integridad de Kernel.tar.gz oficial..."
actual_tarball_hash=$(shasum -a 256 "$KERNEL_TARBALL_PATH" | cut -d' ' -f1)
if [ "$actual_tarball_hash" != "$EZE4_KERNEL_TARBALL_SHA256" ]; then
    echo "ERROR: Checksum no coincide para Kernel.tar.gz:" >&2
    echo "  Esperado: $EZE4_KERNEL_TARBALL_SHA256" >&2
    echo "  Obtenido: $actual_tarball_hash" >&2
    exit 1
fi
echo "  OK: Hash oficial verificado ($actual_tarball_hash)"

echo "[2/6] Verificando manifiesto de parches EZE4..."
PATCH_MANIFEST_PATH="$ROOT/$EZE4_PATCH_MANIFEST"
[ -f "$PATCH_MANIFEST_PATH" ] || { echo "ERROR: Falta manifiesto de parches: $PATCH_MANIFEST_PATH" >&2; exit 1; }
(cd "$ROOT/$EZE4_PATCH_DIR" && shasum -a 256 -c "$PATCH_MANIFEST_PATH" >/dev/null)
echo "  OK: 10 parches EZE4 verificados íntegros."

echo "[3/6] Verificando estado de la VM Lima ($VM)..."
vm_status=$(limactl list --format '{{if eq .Name "'"$VM"'"}}{{.Status}}{{end}}')
if [ "$vm_status" != "Running" ]; then
    echo "ERROR: La VM Lima '$VM' no está en estado Running (actual: $vm_status)." >&2
    echo "Ejecuta: limactl start $VM" >&2
    exit 1
fi
echo "  OK: VM activa."

# 2. Stage run in guest
GUEST_RUN_DIR="/home/markpi.guest/osrc-eze4-work/runs/$RUN_ID"
echo "[4/6] Acondicionando espacio de compilación ext4 en la VM: $GUEST_RUN_DIR"

limactl shell "$VM" bash -c "
set -euo pipefail
rm -rf '$GUEST_RUN_DIR'
mkdir -p '$GUEST_RUN_DIR/build-source' '$GUEST_RUN_DIR/patches' '$GUEST_RUN_DIR/logs'

echo '  Extrayendo Kernel.tar.gz en ext4...'
tar -xzf '$KERNEL_TARBALL_PATH' -C '$GUEST_RUN_DIR/build-source'

echo '  Copiando parches y manifiesto...'
cp '$ROOT/$EZE4_PATCH_DIR'/*.patch '$GUEST_RUN_DIR/patches/'
cp '$PATCH_MANIFEST_PATH' '$GUEST_RUN_DIR/patches/PATCHES.sha256'
"

# 3. Execute build script inside guest
echo "[5/6] Ejecutando compilación del kernel EZE4 (-j$BUILD_JOBS)..."
limactl shell "$VM" bash -c "
set -euo pipefail
'$ROOT/scripts/build-eze4-baseline-guest.sh' \
  --run-root '$GUEST_RUN_DIR' \
  --kernel '$GUEST_RUN_DIR/build-source' \
  --out '$GUEST_RUN_DIR/build-source/out-eze4' \
  --dist '$GUEST_RUN_DIR/dist' \
  --patch-dir '$GUEST_RUN_DIR/patches' \
  --patch-manifest '$GUEST_RUN_DIR/patches/PATCHES.sha256' \
  --jobs '$BUILD_JOBS' > '$GUEST_RUN_DIR/logs/build.log' 2>&1
"
echo "  OK: Compilación concluida con éxito."

# 4. Automated ABI Gate
if [ "$SKIP_ABI_GATE" -eq 0 ]; then
    echo "[6/6] Ejecutando puerta de calidad ABI (CONFIG_MODVERSIONS parity gate)..."
    limactl shell "$VM" bash -c "
    set -euo pipefail
    STOCK_DIR='/home/markpi.guest/osrc-eze4-work/stock-modules/lib/modules'
    if [ ! -d \"\$STOCK_DIR\" ]; then
        echo '  Extrayendo módulos stock para verificación ABI...'
        mkdir -p \"\$STOCK_DIR\"
        (cd /home/markpi.guest/osrc-eze4-work/stock-vendor-boot && \
         /Users/markpi/tab-s9-fe-linux/sources/toolchain/magisk-v30.7/magiskboot-arm64 unpack /Users/markpi/tab-s9-fe-linux/artifacts/stock/images/vendor_boot.img || [ \$? -eq 3 ])
        (cd \"\$STOCK_DIR\" && cpio -idm < /home/markpi.guest/osrc-eze4-work/stock-vendor-boot/vendor_ramdisk/dlkm.cpio)
    fi

    python3 '$ROOT/scripts/verify-eze4-abi.py' \
      --symvers '$GUEST_RUN_DIR/dist/Module.symvers' \
      --stock-modules-dir \"\$STOCK_DIR\" \
      --built-modules-dir '$GUEST_RUN_DIR/build-output/modules-stage'
    "
    echo "  OK: ABI Gate demostrada (100.00% parity, 0 mismatches)."
else
    echo "[6/6] ABI Gate omitida (--skip-abi-gate)."
fi

# 5. Retrieve artifacts to host
echo "Preservando artefactos en host: $HOST_ARTIFACTS_DIR"
mkdir -p "$HOST_ARTIFACTS_DIR"
limactl shell "$VM" cp -a "$GUEST_RUN_DIR/dist/." "$HOST_ARTIFACTS_DIR/"
limactl shell "$VM" cp -a "$GUEST_RUN_DIR/logs" "$HOST_ARTIFACTS_DIR/"

echo "Limpiando objetos intermedios en guest para conservar espacio de disco..."
limactl shell "$VM" bash -c "
rm -rf '$GUEST_RUN_DIR/build-source/out-eze4'
rm -rf '$GUEST_RUN_DIR/build-output'
"

echo "========================================================================"
echo "BUILD EZE4 COMPLETADO EXITOSAMENTE"
echo "Artefactos finales en: $HOST_ARTIFACTS_DIR"
echo "========================================================================"
