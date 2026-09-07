# fixed8/fixed9 Recovery and Demonstration of U11 Reproducibility

Date: 2026-08-23 · Scope: offline laboratory only, no physical write.

## Final Result

`fixed8` and `fixed9` completed with `status=0`. Comparison with `tools/u11_repro_compare.py` produces **PASS**: all 19 files in the dist, including Image, DTB, DTBOs, and the 282-module tar, are **byte-for-byte identical** between two independent clean trees.

This result confirms that patch 0011 (reproducible build IDs) resolves the single divergence preventing PASS in `fixed6/fixed7`.

## Failures Encountered During Recovery

Each failure is documented with: what occurred, why it occurred, how it was detected, how it was resolved, and what knowledge it contributes.

### 1. Insufficient Disk Space (root cause of original failures)

- **What occurred:** `fixed8` and `fixed9` failed with `Errno 28 No space left on device`.
- **Why:** The Lima VM had 33 GB at 98% capacity (852 MB free). Each build generates ~6 GB across extracted sources, intermediate objects, and dist.
- **How it was detected:** `df -h /` showed 852 MB free; STATUS in both runs showed `status=1`.
- **Solution:** ~17 GB were freed by removing exclusively regenerable directories inside `~/osrc-u11-work`: failed runs (prior `fixed8/fixed9`), bulky subdirectories of `fixed7` (whose complete dist was already copied to host), and staging-only from `inspect4`. Host `artifacts/`, `sources/`, and `configs/` were not touched.
- **Knowledge:** A kernel LTO/BTF build requires a minimum of ~8 GB free in the guest. Before each run, checking `df -h` is as critical as verifying recipe hashes.

### 2. Incorrect Source Tree Structure (tar without Kernel/ subdirectory)

- **What occurred:** The first manual attempt assumed the tar extracted to a `Kernel/` subdirectory, but it did so directly in `build-source/`.
- **Why:** The Samsung tar has no explicit root directory.
- **How it was detected:** `test -f Makefile` failed; `git apply --check` reported nonexistent files.
- **Solution:** Extract directly in `build-source/` and apply the overlay there, not in a nonexistent subdirectory.
- **Knowledge:** Always verify actual post-extraction structure before assuming paths.

### 3. Guard: `OUT already exists`

- **What occurred:** Retrying the build without cleaning `out-u11` caused immediate rejection.
- **Why:** The script requires a fresh run to avoid mixing stale artifacts.
- **How it was detected:** Message `OUT ya existe; cada build U11 requiere un run nuevo`.
- **Solution:** Remove `out-u11`, revert applied patches (`git apply -R`), and relaunch.
- **Knowledge:** Anti-reuse guards are intentional; never force their bypass.

### 4. Guard: `modules-stage already exists`

- **What occurred:** After a partial attempt, the re-run failed because `build-output/modules-stage` already existed.
- **Why:** Same anti-mixing policy as OUT/DIST.
- **How it was detected:** Message `modules-stage ya existe`.
- **Solution:** Remove the directory before retrying.
- **Knowledge:** Each attempt must start from scratch across all outputs, not just one.

### 5. Physical Paths in Modules (reproducibility guard)

- **What occurred:** The first build successful compilation-wise was rejected for containing absolute paths in `.rodata` of modules.
- **Why:** Used `--out build-output` (sibling of source) instead of `out-u11` (direct child of source), causing ThinLTO to record the guest absolute path.
- **How it was detected:** `grep -a -F "$RUN_ROOT" ems.ko` found 7 matches.
- **Solution:** Change `--out` to `$RUN/build-source/out-u11` so Kbuild uses `srctree=..` and `-fdebug-prefix-map` flags normalize correctly.
- **Knowledge:** The position of `O=` relative to the source tree determines whether Kbuild passes relative or absolute paths to Clang. It is a structural ThinLTO constraint, not a bug.

## Documented Correct Procedure

For future manual builds outside the wrapper:

1. Extract Kernel.tar.gz directly into `RUN/build-source/` (no subdirectory).
2. Apply overlay X510XXSBDZB4 onto that same level.
3. Check `git apply --check patches/*.patch`.
4. Invoke `build-u11-kernel-guest.sh` with `--run-root RUN --kernel RUN/build-source --out RUN/build-source/out-u11 --dist RUN/dist`.
5. Never precreate `out-u11` or `build-output/modules-stage`; the script creates them itself.
6. If a partial attempt fails: revert patches (`git apply -R`), delete `out-u11`, `dist`, and `modules-stage`, then relaunch.

## Generated Evidence

| Artifact | Location |
|---|---|
| Dist fixed8 | `artifacts/u11/x510xxsbdzb4-u11-fixed8-20260823/dist/` |
| Dist fixed9 | `artifacts/u11/x510xxsbdzb4-u11-fixed9-20260823/dist/` |
| STATUS fixed8 | `artifacts/u11/x510xxsbdzb4-u11-fixed8-20260823/STATUS` |
| STATUS fixed9 | `artifacts/u11/x510xxsbdzb4-u11-fixed9-20260823/STATUS` |
| Build log fixed8 | `artifacts/u11/x510xxsbdzb4-u11-fixed8-20260823/u11-build.log` |
| Build log fixed9 | `artifacts/u11/x510xxsbdzb4-u11-fixed9-20260823/u11-build.log` |
| Reproducibility report | `reports/generated/u11-repro/reproducibility.md` |
| Reproducibility JSON | `reports/generated/u11-repro/reproducibility.json` |

Operational verdict: **Physical NO-GO**. Hardware write remains blocked.
