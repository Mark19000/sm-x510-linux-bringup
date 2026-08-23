#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
DEST=${CLANG_ROOT:-$ROOT/sources/toolchain/clang-linux-x86}
REF=${CLANG_REF:-android13-release}
VERSION=${CLANG_VERSION:-clang-r450784d}
URL=https://android.googlesource.com/platform/prebuilts/clang/host/linux-x86

if [ "$(uname -s)" != Linux ] || [ "$(uname -m)" != x86_64 ]; then
    echo "El prebuilt oficial $VERSION requiere Linux x86_64." >&2
    echo "Usa una VM/contenedor x86_64 o define CLANG_ROOT con un toolchain compatible." >&2
    exit 1
fi

if [ ! -d "$DEST/.git" ]; then
    git clone --depth 1 --filter=blob:none --sparse --branch "$REF" "$URL" "$DEST"
fi
git -C "$DEST" sparse-checkout set "$VERSION"

test -x "$DEST/$VERSION/bin/clang"
"$DEST/$VERSION/bin/clang" --version | head -n 1
echo "Toolchain listo en $DEST/$VERSION"

