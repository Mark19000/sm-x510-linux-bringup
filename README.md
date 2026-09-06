# Samsung Galaxy Tab S9 FE Linux Bring-Up

Evidence-driven downstream Linux bring-up for Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510`, Exynos S5E8835), preserving the historical U11 work while using official EZE4 as the canonical active base.

## Current baseline

- Firmware: `X510XXUCEZE4`, Android 16, bootloader U12.
- Samsung OSRC EZE4: Linux `5.15.189`.
- Exact kernelrelease: `5.15.189-android13-3-33478785`.
- Exact stock vermagic.
- ABI: 281/281 stock modules compatible; 15,123/15,123 MODVERSIONS CRCs exact.
- DTBO r00/r01/r04 byte-identical to stock.
- Pipeline: 98/98 tests; functional deterministic reproducibility.

## Boot-chain status

The inspected EZE4 root vbmeta directly HASH-protects `boot`, `init_boot`, `vendor_boot`, `recovery` and firmware partitions; HASHTREE-protects the retained logical partitions; and CHAIN-protects `dtbo`, `prism` and `optics`. The `dtbo` child vbmeta hashes the DTBO image. `prism`, `optics`, PIT and the complete firmware package are not currently retained, so the complete device graph remains partial.

Correct AOSP flag semantics:

- `flags=1`: `HASHTREE_DISABLED`.
- `flags=2`: `VERIFICATION_DISABLED`.
- `flags=3`: both.

None proves acceptance by the Samsung retail bootloader.

## Physical gate

The unit is stock locked, AVB green and has Warranty Bit 0. Download Mode and USB `04e8:685d` enumeration are confirmed. `IMG_2113.HEIC` confirms that the bootloader warning's Chinese text advertises long-press Volume Up for Device Unlock Mode, although the English text omits it. Entry is therefore confirmed-as-advertised and owner capability is strongly supported; the final confirmation dialog has not been captured. Host flashing, PIT query and complete stock restore are not validated.

Current verdicts:

```text
NOT_READY_FOR_OWNER_UNLOCK_DECISION
NOT_READY_FOR_FIRST_CUSTOM_FLASH
```

No repository command authorizes hardware writes. Historical U11 plans/reports are retained for technical provenance and marked superseded where their operational conclusions are stale.

## Canonical documents

- `reports/2026-09-05-pre-unlock-closure.md`
- `reports/2026-09-05-pre-unlock-errata-audit.md`
- `docs/boot-chain/eze4-avb-trust-graph.md`
- `docs/boot-chain/minimum-first-boot-image-set.md`
- `docs/boot-chain/unlock-evidence-matrix.md`
- `docs/hardware/recovery-readiness-v2.md`
- `docs/hardware/download-mode-capture-checklist.md`
- `docs/hardware/post-unlock-stock-baseline.md`
- `docs/boot-chain/first-custom-kernel-experiment.md`

## Project structure

`configs/`, `docs/`, `patches/`, `reports/`, `scripts/`, `tests/`, `initramfs/` and `lima/` contain the reproducible pipeline, evidence and historical evolution U11 → EZE4. Samsung source and firmware binaries are not redistributed.

## License

MIT — see [LICENSE](LICENSE).
