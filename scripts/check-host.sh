#!/usr/bin/env bash
set -u

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
errors=0

printf 'Proyecto: %s\n' "$ROOT"
printf 'Host: %s %s\n' "$(uname -s)" "$(uname -m)"

for tool in bash git python3 make cpio gzip file; do
    if command -v "$tool" >/dev/null 2>&1; then
        printf '  [ok] %-12s %s\n' "$tool" "$(command -v "$tool")"
    else
        printf '  [falta] %s\n' "$tool"
        errors=$((errors + 1))
    fi
done

for optional in dtc fdtoverlay lz4 adb clang aarch64-linux-gnu-gcc \
    modprobe depmod limactl magiskboot avbtool; do
    if command -v "$optional" >/dev/null 2>&1; then
        printf '  [ok] %-12s %s\n' "$optional" "$(command -v "$optional")"
    else
        printf '  [opcional] %-12s no encontrado\n' "$optional"
    fi
done

if [ "$(uname -s)" != Linux ]; then
    cat <<'EOF'

Aviso: el análisis y el empaquetado pueden ejecutarse aquí, pero el kernel de
Samsung debe compilarse en Linux. En este Apple Silicon se ha validado la VM
Lima ARM64 de `scripts/setup-lima.sh`, usando Clang de Ubuntu. El checkout debe
vivir en su disco ext4: APFS case-insensitive no representa fielmente todos los
nombres del árbol Samsung. Esto reproduce nuestro build, aunque no el Clang
Android x86_64 original del fabricante.
EOF
fi

if [ "$errors" -ne 0 ]; then
    printf '\nFaltan %d herramientas básicas. Consulta docs/04-build.md.\n' "$errors"
    exit 1
fi

printf '\nComprobación básica superada.\n'
