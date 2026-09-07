# 13. OSRC Staging for SM-X510 / Android 16 / U11

This workflow prepares the `X510XXSBDZB4` OSRC source code for the `SM-X510`
unit (Android 16, bootloader U11) without mixing it with the U3 Wi-Fi source kept in
`sources/wifi-kernel`. It does not modify extracted firmware or publish images
to `artifacts/` except for a new record per execution.

## What is Known About the Release

The observed OSRC delivery consists of:

- a base wrapper containing `Kernel.tar.gz`, `Platform.tar.gz`, and `README`;
- an `X510XXSBDZB4` regional overlay, rooted at
  `SM-X510_EUR_16_XX_X510XXSBDZB4/Kernel` and its `README`;
- the README directs applying the `X510XXU8DYJ4` base first, then applying the
  overlay.

The base tree declares kernel 5.15.180, `s5e8835-gts9fewifixx_defconfig`,
`clang-r450784d`, `PLATFORM_VERSION=13`, and `TARGET_SOC=s5e8835`. These data are
recorded as evidence and do not replace validating the commit, config, DTS,
and scripts in the received package.

## Safe Staging

Input is copied unopened to the ext4 disk of the Lima VM. Extraction of
the ZIP, `Kernel.tar.gz`, `Platform.tar.gz`, and nested ZIPs occurs
strictly under `$HOME/osrc-u11-work/<run-id>` inside the guest. The Platform
tree is kept separate and inventoried for analysis; it is never used as input
for the kernel build.
Compressed archives that are part of already-extracted code (such as test
fixtures) are kept as regular files and are not unpacked recursively.

First prepare or start the VM, then run inspection only:

```sh
./scripts/setup-lima.sh
OSRC_RELEASE=/path/to/SM-X510.zip \
  ./scripts/build-osrc-u11-in-lima.sh
```

A pre-downloaded directory can also be provided. Do not use a `.part` file;
the wrapper rejects it by name before copying. Do not point to
`sources/wifi-kernel`, `artifacts/kernel/wifi`, or any other existing output.
Extraction validates traversal, special types, hardlinks, and symlinks: only
relative symlinks remaining within the tree are permitted.

The inventory records `Kernel.tar.gz`, the overlay, roots containing
`Makefile`/`build_kernel.sh`, defconfigs, configs, commit references, and
toolchain paths. Small evidence files are copied to `artifacts/u11/<run-id>/`;
sources, objects, tarballs, and outputs remain on ext4. A repeated run-id
is rejected to avoid overwriting a previous record.

## Fixed Build

Inspection does not execute scripts supplied by third parties. When it finds
the README with the exact `X510XXSBDZB4` and `X510XXU8DYJ4` markers, the wrapper
copies the base to `u11-composite/Kernel` inside the guest and applies only the
`.../X510XXSBDZB4/Kernel` tree there. Original permissions are restored after
applying the overlay. The two original trees remain separate, and the exact
composite is not used as a working tree either: build mode creates a private
copy in `build-source/Kernel`, because some Samsung Makefiles generate files
inside the source tree even when using `O=`. The build never uses the U8 base
alone. The `overlay-manifest.txt` contains the SHA-256 of each applied file.

Once layout and composite have been reviewed, run the repository's pinned
profile:

```sh
./scripts/build-osrc-u11-in-lima.sh \
  --release /path/to/SM-X510.zip \
  --build --jobs 6 --run-id x510-u11-trial-01
```

A shell command supplied via environment variables is not accepted. The
profile requires kernel 5.15.180, the X510 defconfig, the nine patches with
their SHA-256s, the base DTB, exactly the three known DTBOs, and 282 modules.
It fixes user, host, date, Kconfig seed, and debug paths. It also rejects an
`Image` or `.ko` that retains the physical path of the run.

`CONFIG_IKHEADERS` and automatic module signing are disabled in this bring-up
profile: they introduced mtimes and a new key, respectively. `__FILE__` paths
are normalized via `KCPPFLAGS`; kernel and module BTF is preserved. These
decisions do not attempt to reproduce Samsung's signed binary.

`O=out-u11` is a direct child of the private source copy. Thus Kbuild uses
`srctree=..` and Clang receives relative source names; an EMS microbuild
confirmed zero occurrences of the physical run path. With a sibling `O=`,
ThinLTO retained the absolute path even with prefix-map.

If the release provides more than one kernel root, lacks the exact README/overlay,
or reuses a run-id, `--build` mode halts. It does not infer an arbitrary overlay,
does not build the U8 base alone, and does not overwrite the U3 checkout.

## Evidence and Failures

Each execution retains:

- `release-layout.json`: layout, configs, toolchain, and commit references;
- `archive-manifest.json`: processed tarballs/ZIPs and those kept only inventoried;
- `overlay-manifest.txt` and `composite-layout.json`: U11 composition and hashes;
- `build-metadata.txt`: selected root, defconfigs, scripts, and Git state;
- `u11-build.log`, `guest-console.log`, and `STATUS`.

A failure neither cleans up nor reuses another run. Review the log and run status
on ext4 before retrying with a new `--run-id`. This workflow does not authorize
signing, installing, or flashing an image to the tablet.

Attempts `fixed1` through `fixed4` are preserved as negative tests. They found
a positional incompatibility in GNU tar, absolute paths in ThinLTO, a detector
false negative caused by SIGPIPE, and finally demonstrated that paths resided in
`.rodata`/`__FILE__` and not in BTF. Each directory contains a `FAILURE.md`;
none is a physical candidate.

## Verified Result

The exact composite was verified against an independent reconstruction: zero
differences in content, mode, or symlink. A private tree was then created,
the nine Wi-Fi patches applied, and compilation performed with Clang 21 ARM64.
The full build produced kernel 5.15.180, `Image`, base DTB, DTBOs r00/r01/r04,
and 282 modules, exiting with status 0. Hashes, logs, and per-patch negative
tests are in `artifacts/u11/x510xxsbdzb4-u11-clang21-20260823`; analysis is
explained in `docs/14-resultados-u11-u3-eze4.md`.
