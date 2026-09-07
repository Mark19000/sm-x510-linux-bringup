# 4. Compiling the Reference U3 Kernel

## What We Are Compiling

Two distinct assertions must be maintained:

1. **The U3 tree compiles**: validates build scripts, patches, configuration fragments, Device Tree compilation, and kernel modules.
2. **The resulting binary is usable on EZE4**: not yet demonstrated, because Samsung has not released the exact U12 / Android 16 source tree and AVB invalidates any modified byte.

The completed reference build uses commit `9a752a83347461b3785711760ba925fcabea3071` from `X510XXU3BXDG`. It produces an `Image` of 38,361,600 bytes, 282 kernel modules, and the r00, r01, and r04 Wi-Fi overlays. The record of real compiler and build issues is in [11-reference-build-log.md](11-reference-build-log.md). For the Android 16 U11 pipeline, use the isolated recipe in [chapter 15](15-pipeline-u11-offline.md), not `make build`.

## Reproducible Environment on Apple Silicon

The host is ARM64 macOS, and APFS is case-insensitive by default. The Samsung vendor kernel source contains case-colliding filenames; compiling directly on a shared macOS folder causes ghost modifications and erratic build errors. The tested recipe runs an ARM64 Lima VM with native ext4 storage:

```sh
brew install lima
./scripts/setup-lima.sh
./scripts/fetch-image-tools.sh
./scripts/build-reference-in-lima.sh
```

The template configures Ubuntu 26.04 ARM64, 6 vCPUs, 8 GiB RAM, and 35 GiB disk. The source checkout and object build directory reside inside the VM; only finished build artifacts are copied out to the project directory. The disk measurement on August 23 recorded 36 GiB free on host and 20 GiB free in the VM. There is sufficient margin for incremental builds, but check `df -h` before clean rebuilds: the critical constraint is guest virtual disk capacity, not merely available macOS disk space.

To inspect the VM environment:

```sh
limactl shell gts9fe-build
cd ~/gts9fe-work/wifi-kernel
git status --short
```

On a native Linux workstation, install at minimum:

```sh
sudo apt update
sudo apt install -y git make bc bison flex build-essential libssl-dev \
  libelf-dev dwarves device-tree-compiler lz4 cpio rsync python3 file \
  clang lld llvm \
  gcc-aarch64-linux-gnu libc6-dev-arm64-cross diffstat kmod
```

## What the Automation Does

`build-reference-in-lima.sh`:

1. Verifies the exact commit of the ext4 git checkout;
2. Idempotently applies `patches/downstream/wifi/*.patch`;
3. Explicitly sets `ALLOW_REFERENCE_BUILD=1`;
4. Merges `configs/gts9fe-linux.fragment` on top of Samsung defconfig;
5. Executes `olddefconfig`;
6. Compiles `Image`, the target base DTB, the three board DTBOs, and modules;
7. Strips and installs modules with `INSTALL_MOD_STRIP=1`;
8. Writes configuration, build metadata, and SHA-256 digests under `artifacts/kernel/wifi/reference-dist/`.

The `ALLOW_REFERENCE_BUILD=1` exception is intentionally visible. Without it, the script compares `X510XXU3BXDG` with target `X510XXUCEZE4` and aborts.

## Manual Execution Inside Linux

To inspect each layer or adjust build parameters:

```sh
DEVICE_VARIANT=wifi ./scripts/apply-patches.sh

ALLOW_REFERENCE_BUILD=1 DEVICE_VARIANT=wifi \
  KERNEL_DIR="$HOME/gts9fe-work/wifi-kernel" \
  KERNEL_OUT="$HOME/gts9fe-work/obj" \
  DIST_DIR="$PWD/artifacts/kernel/wifi/reference-dist" \
  JOBS=6 ./scripts/build-downstream.sh 2>&1 | tee artifacts/logs/reference-kernel-build.log
```

Useful environment variables:

```sh
JOBS=4                         # Reduce memory pressure
CLANG_ROOT=/path/to/toolchain  # Point to a specific Clang toolchain
INSTALL_MOD_STRIP=0            # Preserve debug symbols; increases size nearly tenfold
```

The vendor tree declares overlays using an obsolete `always` Kbuild variable. Running `make dtbs` could exit 0 without building any overlay. The script requests the three `.dtbo` targets explicitly and fails if any is missing; this is a prime example of why an exit code of 0 alone does not prove success.

## Post-Build Verifications

```sh
DIST=artifacts/kernel/wifi/reference-dist
file "$DIST/Image"
grep -E 'CONFIG_(DEVTMPFS|BLK_DEV_INITRD|SERIAL_SAMSUNG_CONSOLE)=' \
  "$DIST/kernel.config"
cat "$DIST/BUILD-METADATA"
(cd "$DIST" && sha256sum -c SHA256SUMS)
find "$DIST/dtbs/samsung/gts9fewifi" -name '*.dtbo' -print
find "$DIST/modules-root" -name '*.ko' | wc -l
```

Kbuild build metadata for timestamp, user, hostname, and version counter are pinned. Two consecutive incremental link steps produced identical `Image` binaries and SHA-256 hashes; this demonstrates kernel build reproducibility within this VM given preserved intermediate objects and module signing keys. A clean rebuild from scratch must pin toolchains and control module key generation before claiming universal bit-for-bit reproducibility. `BUILD-METADATA` records the exact inputs associated with each build artifact.

## Building the DTBO Container

```sh
DEVICE_VARIANT=wifi \
  DIST_DIR="$PWD/artifacts/kernel/wifi/reference-dist" \
  ./scripts/build-dtbo.sh
```

The container preserves the table observed in stock firmware: r00 for hwrev 0, r01 for 1–3, and r04 for 4–32. The script unpacks the resulting image and verifies each blob bitwise. The output remains `dtbo-unsigned.img`: it lacks the Samsung AVB footer and 8 MiB padding, and must not be flashed.

## Repackaging for Android Boot Image Header v4

In EZE4 the kernel resides in `boot.img`, but its ramdisk has a length of zero. The actual generic ramdisk resides in `init_boot.img`; therefore both are repacked separately. The `magiskboot` binary extracted from the official APK is an ARM64 ELF executable and runs inside Lima, not directly on macOS:

```sh
./scripts/repack-reference-in-lima.sh
```

Inside Linux, the wrapper corresponds to:

```sh
MAGISKBOOT=sources/toolchain/magisk-v30.7/magiskboot-arm64 \
  ./scripts/repack-boot.sh \
  artifacts/stock/images/boot.img \
  artifacts/kernel/wifi/reference-dist/Image \
  artifacts/candidates/reference/boot-UNSIGNED.img

MAGISKBOOT=sources/toolchain/magisk-v30.7/magiskboot-arm64 \
  ./scripts/repack-init-boot.sh \
  artifacts/stock/images/init_boot.img \
  artifacts/initramfs/wifi/gts9fe-initramfs.cpio \
  artifacts/candidates/reference/init_boot-UNSIGNED.img
```

`magiskboot` preserves header layout, and control unpack tests confirmed that `Image` and `cpio` payloads extract byte-identically. Even so, `avbtool` validates the Samsung VBMeta structure but rejects the hash descriptor for each repacked candidate: this is the expected behavior after modifying content without Samsung signing keys. **This cannot be fixed by arbitrarily disabling vbmeta verification.**

## Defects Resolved by Downstream Patches

- Clang 21 tightened diagnostic enforcement and rejected deprecated C function prototypes.
- Several vendor callbacks had incompatible function return types.
- Missing function declarations in Wi-Fi, RCD, and cpupm drivers.
- The `devfreq` fallback path called a non-existent kernel API.
- A Novatek touch callback exited without a return value, and Type-C code referenced removed identifiers.
- Two debug options intentionally triggered crash and FPSIMD selftests at boot.
- Case-insensitive APFS cannot represent the source tree faithfully.
- `make dtbs` silently omitted board Device Tree overlays.

Remaining warnings and their classifications are detailed in the reference build log. Do not suppress warnings globally: distinguish between inherited legacy noise, kernel stack hazards, and genuine missing external dependencies.

Completing the build establishes milestone M1 only. M2 requires verified log output captured from the physical device; it cannot be inferred from clean compiler termination.
