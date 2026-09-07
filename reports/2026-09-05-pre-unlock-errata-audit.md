# Pre-Unlock Errata Audit — Repository Sweep

Date: 2026-09-05. Technical history is preserved; dangerous documents are annotated/quarantined and current authorities are linked.

## Corrections by Claim

| File / Context | Legacy Claim | State | Canonical Phrasing / Action |
|---|---|---|---|
| `docs/boot-chain/minimal-modification-set.md`, summary/AVB | Direct root HASH over `dtbo` | **CONTRADICTED** | Root CHAIN `dtbo` RIL 1; child HASH `dtbo`. Document superseded and sentence annotated. |
| same, conclusion | minimal `boot+init_boot+vbmeta` | **CONTRADICTED** | Minimum **CANNOT_YET_BE_DETERMINED**; boot-only only conditioned candidate. |
| same, strategy | changing boot requires vbmeta | **OVERSTATED** | Breaks HASH, but unlocked Samsung tolerance is **UNKNOWN**. |
| same, flags | flags 1 as disable-verification | **STALE** | 1=hashtree; 2=verification; Samsung acceptance untested. |
| `docs/boot-chain/avb-experiment-plan.md`, descriptors | dtbo simultaneously CHAIN and root HASH | **CONTRADICTED** | Removed from direct HASHes; plan superseded. |
| same, phases | vbmeta-only is first safe probe | **OVERSTATED** | Alters root; boot-only is mechanically smaller, but not yet authorized. |
| same, signals | electrical signal / backlight implies kernel | **CONTRADICTED** | Only readable kernel-owned marker confirms execution. |
| `docs/first-boot-experiment-plan-v2.md` | operational U11 plan and phased flash | **STALE** | Banner `SUPERSEDED`; EZE4 authority separated. |
| same, recovery | Odin/Download restores any failure | **OVERSTATED** | Recovery remains unvalidated. |
| `docs/hardware/recovery-runbook.md`, entry | warning and expected FRP/OEM/SWREV values | **UNKNOWN** | Do not predict screen/values; transcribe only what is observed. Runbook quarantined. |
| same, firmware | complete local AP/BL/CSC package | **CONTRADICTED** | Historical hash/provenance only, and six partial images. |
| `reports/2026-09-05-hardware-preflight-v2.md` | Recovery READY / 100% GO | **CONTRADICTED** | Quarantined; `RECOVERY_NOT_VALIDATED`. |
| same, Knox | confirming unlock necessarily burns eFuse | **OVERSTATED** | Persistent Warranty Bit supported; exact EZE4 trigger **UNKNOWN**. |
| same, downgrade | U11 causes hard-brick | **CONTRADICTED** | SWREV normally rejects downgrade; erroneous BL/PIT writes are a distinct risk. |
| same, minimum/flags | definitive boot+vbmeta; flags 2 suffice | **OVERSTATED** | Minimum untested; flags do not prove Samsung acceptance. |
| `reports/...bootloader-unlock-investigation.md`, KG/EUX | absence of lockout and unlock likely | **CONTRADICTED** | KG, CSC, and permission are separate states; report quarantined. |
| same, `kg.bit=00` | confirmed absence of remote lockout | **UNKNOWN** | Observed value only; without proven exact decoding. |
| same, D2/screens | D2=screen lock; removing PIN guarantees path | **CONTRADICTED/UNKNOWN** | D2/PIN remain unexplained. `IMG_2113.HEIC` subsequently confirms this unit announces long-press to enter Device Unlock Mode; final screen remains unknown. |
| same, EUX | all Exynos EUX expose unlock | **OVERSTATED** | EUX is not a capability bit. |
| same, Knox | triggers marked CONFIRMED | **OVERSTATED** | Separate Download, selection, confirmation, wipe, unlock, flash, execution, and fuse. |
| `docs/decisions/oem-unlock-knox.md` | unlock, eFuse, and services conflated | **OVERSTATED** | Rewritten as table of specific events/evidence. |
| same, state | zero cable and guaranteed kernel | **CONTRADICTED/OVERSTATED** | Download observed; exact ABI does not guarantee boot. |
| `reports/first-boot-risk-review.md`, firmware | full ZIP still present | **STALE** | Historical provenance; file absent. |
| `README.md` | U11 best source, 90 tests, wait for EZE4 | **STALE** | Rewritten to canonical EZE4, 95/95 and current gates. |
| `README.md`, AVB | direct root `vbmeta→dtbo` | **OVERSTATED** | CHAIN root→dtbo child→HASH dtbo. |
| `PROJECT_STATUS.md`, pending | wait for OSRC EZE4 | **STALE** | Canonical update added; U11 section marked historical. |
| `reports/2026-09-05-adversarial-first-boot-review.md` | defects already resolved | **CONTRADICTED** | Errata added: identifying did not equal fixing all remnants. |

## Correct Claims Preserved

- AOSP: flags 1/2/3 = hashtree-disabled/verification-disabled/both.
- `KG Completed != OEM unlock allowed`.
- Download Mode and USB `04e8:685d` are confirmed; flashing/recovery are not.
- Warranty Bit baseline 0 is confirmed; transition timing unknown.
- Previous assertion that warning / Device Unlock Mode were not observed was superseded by `IMG_2113.HEIC`: warning and advertised entry are **CONFIRMED**. Final screen remains **UNKNOWN**; D2 remains unknown.
- AVB graph is mechanically exact only for available images.

## Active Documentary Authority

`eze4-avb-trust-graph.md`, `minimum-first-boot-image-set.md`, `unlock-evidence-matrix.md`, `recovery-readiness-v2.md`, `download-mode-capture-checklist.md`, `post-unlock-stock-baseline.md`, `first-custom-kernel-experiment.md`, and `2026-09-05-pre-unlock-closure.md`.

The presence of a banner does not make the historical body correct; it prevents it from being used operationally and preserves the reasoning that was invalidated.
