#!/bin/sh
# Build the temporary observer with an Android NDK clang.  No dependency
# download is performed.  Set ANDROID_NDK explicitly when the host has more
# than one NDK installation.
set -eu

ROOT=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
SOURCE="$ROOT/tools/rmg-eze4/c2_dual_clock_observer.c"
OUTPUT=${OUTPUT:-$ROOT/artifacts/c2/c2_dual_clock_observer}
ANDROID_API=${ANDROID_API:-29}
NDK_ROOT=${ANDROID_NDK:-}

if [ -z "$NDK_ROOT" ]; then
	printf '%s\n' 'ANDROID_NDK is not set; refusing to download or guess a toolchain.' >&2
	exit 2
fi

case "$(uname -s):$(uname -m)" in
	Darwin:arm64) HOST_TAG=darwin-arm64 ;;
	Darwin:x86_64) HOST_TAG=darwin-x86_64 ;;
	Linux:x86_64) HOST_TAG=linux-x86_64 ;;
	Linux:aarch64) HOST_TAG=linux-aarch64 ;;
	*)
		printf 'unsupported host for NDK lookup: %s\n' "$(uname -s):$(uname -m)" >&2
		exit 2
		;;
esac

CLANG="$NDK_ROOT/toolchains/llvm/prebuilt/$HOST_TAG/bin/clang"
SYSROOT="$NDK_ROOT/toolchains/llvm/prebuilt/$HOST_TAG/sysroot"
if [ ! -x "$CLANG" ] || [ ! -d "$SYSROOT" ]; then
	printf 'Android NDK clang/sysroot not found under %s\n' "$NDK_ROOT" >&2
	exit 2
fi
mkdir -p "$(dirname -- "$OUTPUT")"
"$CLANG" --target="aarch64-linux-android$ANDROID_API" --sysroot="$SYSROOT" \
	-std=c11 -O2 -fPIE -pie -Wall -Wextra -Wpedantic -Werror \
	"$SOURCE" -o "$OUTPUT"
"$CLANG" --version | sed -n '1p'
printf 'output=%s\n' "$OUTPUT"
file "$OUTPUT"
