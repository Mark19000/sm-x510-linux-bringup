# Closure of the three probably-reusable parameters

## `P0_FINGERPRINT_MIN_BEST = 5`

Defined in ZG3 `target.h:66` and used only by `oracle.c:284-290` after scoring every active fingerprint. It rejects a winner with fewer than five matching sampled words. The code contract, eight sampled offsets, and scoring implementation are firmware-independent, but the achievable score under corruption/noise depends on the firmware-specific page contents and runtime read condition. EZE4's static table simulation proves 121 clean rows pass and the four known rows reject; it cannot prove the runtime word-error distribution. **Final status: `REQUIRES_RUNTIME_VALIDATION`.**

Definition/use closure found no other definition or consumer. It has no direct SoC dependency; SoC behavior matters indirectly through the runtime read/error condition. ZG3 and EZE4 share the implementation and word count, while their fingerprint arrays differ.

## `P0_FINGERPRINT_MIN_MARGIN = 3`

Defined in ZG3 `target.h:67` and used only by `oracle.c:284-290` to require separation from the runner-up. Its prerequisites include the firmware-specific fingerprint population, and its operational adequacy depends on which sampled words are reliably read at runtime. EZE4 static discrimination exposes the four structural problem rows but supplies no runtime noise model. **Final status: `REQUIRES_RUNTIME_VALIDATION`.**

Definition/use closure found no other definition or consumer. It has no direct SoC dependency; firmware contents determine clean margins and runtime state determines observed margins. ZG3 and EZE4 share the scorer and offsets but not the fingerprint population.

## `ROOT_UMH_PATH = "/data/local/tmp/cve-2026-43499-root"`

Defined in ZG3 `target.h:125`; `root.c:212` copies the string into the usermode-helper data prepared by the later root stage. Repository-wide target definitions use the same deployment convention. The value has no symbol, structure, SoC, or firmware-address dependency. It does depend on external deployment state: the named file must exist and be suitable when that conditional late path is reached. No retained EZE4 property or package manifest directly confirms it. **Final status: `RUNTIME_VALIDATION_REQUIRED`.**

Definition/use closure found no alternate gts9fewifi definition and no second runtime consumer. ZG3 and EZE4 have identical Android pathname semantics in the retained source prerequisites, but EZE4 deployment state is not captured.

The retained EZE4 stock artifacts are boot, init_boot, vendor_boot, DT/DTBO, and reconstructed kernel artifacts; they do not contain the userdata `/data` filesystem. Repository search finds the helper only as a payload build/deployment artifact, not as a stock-firmware file. Therefore the audit cannot assert that the exact pathname exists on an untouched EZE4 filesystem. Its compatibility is deployment-state dependent rather than firmware-build or SoC dependent.

All three parameters leave the canonical probably-reusable accounting and are classified as requiring runtime validation. For `ROOT_UMH_PATH`, this reflects unconfirmed deployment state, while the string itself remains firmware-independent and statically compatible. None is promoted to confirmed identical.
