#!/usr/bin/env bash
set -euo pipefail

ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
TOOL_ROOT="$ROOT/sources/toolchain"
MAGISK_DIR="$TOOL_ROOT/magisk-v30.7"
MAGISK_APK="$MAGISK_DIR/Magisk-v30.7.apk"
MAGISKBOOT="$MAGISK_DIR/magiskboot-arm64"
AVB_ARCHIVE="$TOOL_ROOT/avb-android16.tar.gz"
AVB_DIR="$TOOL_ROOT/avb-android16"
AVBTOOL="$AVB_DIR/avbtool.py"

MAGISK_URL=https://github.com/topjohnwu/Magisk/releases/download/v30.7/Magisk-v30.7.apk
AVB_URL=https://android.googlesource.com/platform/external/avb/+archive/refs/heads/android16-release.tar.gz
MAGISK_SHA=e0d32d2123532860f97123d927b1bb86c4e08e6fd8a48bfc6b5bee0afae9ebd5
MAGISKBOOT_SHA=d7440e2cd89899426e809554bf793baef9804ccbe5a52ce34a8b6242725d3c77
AVB_ARCHIVE_SHA=d4683e75f9a12a0a7089871fcc0432d242ccc6d44e7c5fe18f4a0f527151ab66
AVBTOOL_SHA=e5a664a38db623da00f080219bc0ee60a640a9dc4a872803616fae4938ac749b

for command_name in curl unzip tar; do
    command -v "$command_name" >/dev/null || {
        echo "Falta $command_name" >&2
        exit 1
    }
done

hash_file() {
    if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$1" | cut -d' ' -f1
    else
        shasum -a 256 "$1" | cut -d' ' -f1
    fi
}

check_hash() {
    file=$1
    expected=$2
    label=$3
    actual=$(hash_file "$file")
    [ "$actual" = "$expected" ] || {
        echo "$label tiene SHA-256 inesperado: $actual" >&2
        echo "No se sobrescribe. Aparta el archivo y vuelve a ejecutar." >&2
        exit 1
    }
}

mkdir -p "$MAGISK_DIR" "$TOOL_ROOT"
if [ ! -f "$MAGISK_APK" ]; then
    temp_apk=$(mktemp "$MAGISK_DIR/.Magisk-v30.7.XXXXXX.apk")
    trap 'rm -f -- "${temp_apk:-}" "${temp_boot:-}" "${temp_avb:-}"' EXIT
    curl -fL --retry 3 --output "$temp_apk" "$MAGISK_URL"
    check_hash "$temp_apk" "$MAGISK_SHA" "APK Magisk"
    mv "$temp_apk" "$MAGISK_APK"
    temp_apk=
else
    check_hash "$MAGISK_APK" "$MAGISK_SHA" "APK Magisk"
fi

if [ ! -f "$MAGISKBOOT" ]; then
    temp_boot=$(mktemp "$MAGISK_DIR/.magiskboot.XXXXXX")
    unzip -p "$MAGISK_APK" lib/arm64-v8a/libmagiskboot.so > "$temp_boot"
    check_hash "$temp_boot" "$MAGISKBOOT_SHA" "magiskboot ARM64"
    chmod 0755 "$temp_boot"
    mv "$temp_boot" "$MAGISKBOOT"
    temp_boot=
else
    check_hash "$MAGISKBOOT" "$MAGISKBOOT_SHA" "magiskboot ARM64"
fi

if [ ! -f "$AVB_ARCHIVE" ]; then
    temp_avb=$(mktemp "$TOOL_ROOT/.avb-android16.XXXXXX.tar.gz")
    curl -fL --retry 3 --output "$temp_avb" "$AVB_URL"
    check_hash "$temp_avb" "$AVB_ARCHIVE_SHA" "archivo AOSP AVB"
    mv "$temp_avb" "$AVB_ARCHIVE"
    temp_avb=
else
    check_hash "$AVB_ARCHIVE" "$AVB_ARCHIVE_SHA" "archivo AOSP AVB"
fi

if [ ! -f "$AVBTOOL" ]; then
    if [ -e "$AVB_DIR" ]; then
        echo "$AVB_DIR existe pero no contiene avbtool.py; no se sobrescribe." >&2
        exit 1
    fi
    avb_stage=$(mktemp -d "$TOOL_ROOT/.avb-stage.XXXXXX")
    trap 'rm -f -- "${temp_apk:-}" "${temp_boot:-}" "${temp_avb:-}"; rm -rf -- "${avb_stage:-}"' EXIT
    tar -xzf "$AVB_ARCHIVE" -C "$avb_stage"
    check_hash "$avb_stage/avbtool.py" "$AVBTOOL_SHA" "avbtool.py"
    mv "$avb_stage" "$AVB_DIR"
    avb_stage=
else
    check_hash "$AVBTOOL" "$AVBTOOL_SHA" "avbtool.py"
fi

echo "Herramientas de imagen verificadas."
echo "magiskboot es ELF/ARM64: ejecútalo mediante repack-reference-in-lima.sh."
