#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TARGET_FILE=${TARGET_FILE:-$ROOT/configs/target-sm-x510.env}
INPUT=${1:-}

test -f "$TARGET_FILE" || { echo "Falta $TARGET_FILE" >&2; exit 1; }
# shellcheck source=/dev/null
source "$TARGET_FILE"

cat <<EOF
Objetivo de este proyecto
  modelo:              $TARGET_MODEL
  variante:            $TARGET_VARIANT
  build Android:       $TARGET_PLATFORM_BUILD
  firmware AP Samsung: $TARGET_AP_VERSION
  Android / One UI:    $TARGET_ANDROID_MAJOR / $TARGET_ONE_UI
  binario bootloader:  $TARGET_BOOTLOADER_BINARY (U$TARGET_BOOTLOADER_REVISION)
  parche de seguridad: $TARGET_SECURITY_PATCH
  CSC activo:          $TARGET_CSC
  paquete multi-CSC:   $TARGET_MULTI_CSC
  versión CSC:         $TARGET_CSC_VERSION
  cadena SAOMC:        $TARGET_SAOMC

Referencia de código disponible
  firmware:            $REFERENCE_WIFI_AP_VERSION
  kernel:              $REFERENCE_WIFI_KERNEL
  estado:              NO coincide; análisis solamente
EOF

if [ -n "$INPUT" ]; then
    name=$(basename "$INPUT")
    case "$name" in
        *"$TARGET_AP_VERSION"*)
            echo "Comprobación: el nombre contiene la versión AP objetivo."
            ;;
        *)
            echo "ERROR: '$name' no contiene $TARGET_AP_VERSION." >&2
            echo "No lo uses como plantilla stock para esta unidad." >&2
            exit 1
            ;;
    esac
    case "$name" in
        *.zip)
            if command -v sha256sum >/dev/null 2>&1; then
                actual_sha=$(sha256sum "$INPUT" | cut -d' ' -f1)
            else
                actual_sha=$(shasum -a 256 "$INPUT" | cut -d' ' -f1)
            fi
            if [ "$actual_sha" != "$TARGET_FIRMWARE_SHA256" ]; then
                echo "ERROR: SHA-256 del firmware no aprobado: $actual_sha" >&2
                echo "Esperado: $TARGET_FIRMWARE_SHA256" >&2
                exit 1
            fi
            echo "Comprobación: SHA-256 del ZIP objetivo verificado."
            ;;
    esac
fi
