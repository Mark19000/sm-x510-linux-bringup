# 15. Offline U11 Laboratory, Step by Step

This guide is the short path to repeat the work without mixing versions or
writing to the tablet. The educational objective is to reach coherent artifacts
to study M2 (first kernel message) and M3 (`/init` as PID 1).

## 1. The Three Identities

| name | what it is | kernel | use |
|---|---|---|---|
| U3 `X510XXU3BXDG` | prior Android 14 source | 5.15.123 | historical reference, untouched |
| U11 `X510XXSBDZB4` on `X510XXU8DYJ4` | corresponding Android 16 source | 5.15.180 | best available engineering base |
| U12 `X510XXUCEZE4` | stock tablet firmware | 5.15.189 | binary target; exact source pending |

U11 does not replace U3, nor is it presented as EZE4 source. Packages,
sources, builds, initramfs, and reports live in separate namespaces.

## 2. Inspect Before Building

From `<project-root>`:

```sh
./scripts/setup-lima.sh
./scripts/build-osrc-u11-in-lima.sh \
  --release sources/osrc-releases/x510xxsbdzb4-u11-android16/wrapper \
  --inspect --run-id x510-u11-inspect-01
```

Full extraction occurs on ext4 inside Lima. This matters because APFS is
typically case-insensitive and Samsung's tar contains names that collide.
The wrapper verifies archives, symlinks, traversal, base+overlay identity,
and never executes arbitrary scripts from the package.

## 3. Build the Fixed Profile

```sh
./scripts/build-osrc-u11-in-lima.sh \
  --release sources/osrc-releases/x510xxsbdzb4-u11-android16/wrapper \
  --build --jobs 6 --run-id x510-u11-build-01
```

The script requires identity 5.15.180, the X510 defconfig, nine patches pinned
by hash, `Image`, `s5e8835.dtb`, DTBOs r00/r01/r04, and 282 modules. Each attempt
uses a new directory. If anything does not match, it fails: do not reuse objects
from another run to make it pass.

Two options are disabled only in the reproducible bring-up profile:

- `IKHEADERS`, because it packed wall-clock mtimes;
- automatic module signing, because it generated a new key.

Neither is necessary for the kernel to reach `/init`. BTF for kernel and
modules remains active. `__FILE__` paths are normalized via the preprocessor's
`KCPPFLAGS` entry. This profile tests buildability and consistency; it does not
attempt to reproduce Samsung's private signatures or binary `Image`.

The `O=out-u11` directory is placed directly under the private source copy.
This causes Kbuild to use `srctree=..`: the compiler never receives the absolute
path, and ThinLTO bitcode cannot retain a differing run-id.

## 4. Understanding Prior Failures

| symptom | cause | rule preventing recurrence |
|---|---|---|
| tar fails at the end | in GNU tar `--no-recursion` was positional | options placed before `--files-from` |
| hashes change across runs | `__FILE__` stored path in `.rodata` | macro prefix-map via `KCPPFLAGS` |
| detector reports success despite finding paths | `grep -q` caused SIGPIPE under `pipefail` | write the full list first |
| initramfs differs between APFS/ext4 | different root modes and symlinks | ext4 staging and normalized modes |

Failures are useful data. Retain log, run-id, and hashes; fix the recipe and
repeat from scratch rather than quietly patching the result.

## 5. Build Early Userspace

```sh
make u11-initramfs
```

Three reproducible profiles are produced:

- `minimal`: BusyBox and `/init`, to demonstrate PID 1;
- `ufs`: closure of 28 modules for storage;
- `usb`: diagnostic with 45 modules; measured, but does not fit the stock limit.

The UFS profile does not mean the tablet can now be mounted. It means known
dependencies are within the payload for a future controlled test.

## 6. Audit Modules and Preflight

```sh
make u11-modules-audit
make u11-preflight
# Or all three phases together:
make u11-offline
```

The audit checks stock `vendor_boot` provenance, metadata, dependency graph,
load order, and UFS/USB closures. Preflight verifies hashes, identities,
282 modules, early userspace config, initramfs, and DT distance. `READY`
signifies offline consistency, not permission to flash.

Demonstrating reproducibility requires two clean builds:

```sh
python3 tools/u11_repro_compare.py \
  artifacts/u11/<run-a>/dist artifacts/u11/<run-b>/dist \
  --json reports/generated/u11-repro/reproducibility.json \
  --markdown reports/generated/u11-repro/reproducibility.md
```

## 7. How to Read M2 and M3

M2 primarily depends on compatibility among bootloader, image format,
DT/DTBO, console, PSCI/GIC/timers, and reserved memory. U11 substantially
reduces kernel and DT uncertainty, but does not prove the AVB/rollback
contract on the U12 unit.

M3 adds initrd, `/init`, devtmpfs, console, and, if storage is needed,
the UFS closure. The initramfs is already auditable; observing M2 on hardware
remains necessary before attributing a failure to `/init`.

Final rule: as long as preflight reports `physical_write: NO-GO`, no signed
image is created, no downgrade is performed, and no flash command is executed.
