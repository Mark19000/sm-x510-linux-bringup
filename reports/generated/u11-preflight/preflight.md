# U11 Offline Preflight for M2/M3

This report verifies offline consistency. **It never authorizes writing to the tablet.**

## Verdict

- U11 offline analysis: `READY`
- M3 payload: `READY`
- M2 observed on hardware: `false`
- M3 observed on hardware: `false`
- physical write: `NO-GO`

## Initramfs vs EZE4 init_boot

| profile | modules | LZ4 (B) | margin (B) | fits |
|---|---:|---:|---:|---|
| `minimal` | 0 | 690128 | 1796674 | yes |
| `ufs` | 28 | 2116711 | 370091 | yes |
| `usb` | 45 | 3018036 | -531234 | no |

## Checks

| status | check | detail |
|---|---|---|
| `PASS` | `identity_separation` | U11/B11 source and EZE4/U12 target are registered as distinct identities |
| `PASS` | `osrc_hashes` | OSRC base, overlay, and Kernel.tar.gz hashes match |
| `PASS` | `build_hashes` | 15 build artifacts verified |
| `PASS` | `build_identity` | BUILD_INFO links source, kernel, and 282 modules |
| `PASS` | `early_userspace_config` | config prepared for initramfs and early console |
| `PASS` | `installed_modules` | release=5.15.180, modules=282, regular files verified against tar=296, symlinks=0 |
| `PASS` | `module_order_consistency` | modules.order build/install: 282/282 |
| `PASS` | `vendor_module_lists` | 7 early modules + 2 product modules present |
| `PASS` | `module_vendor_boot_audit` | metadata, dependencies, stock order, and UFS/USB closures verified |
| `PASS` | `initramfs_minimal` | 0 modules, LZ4=690128 B, margin=1796674 B |
| `PASS` | `initramfs_ufs` | 28 modules, LZ4=2116711 B, margin=370091 B |
| `WARN` | `initramfs_usb` | 45 modules, LZ4=3018036 B, margin=-531234 B; oversized diagnostic profile, unpackable |
| `WARN` | `dt_observed_distance` | r04 material=0, unresolved=207; compiled base DTB material=4, unresolved=14. Does not prove equivalence. |
| `WARN` | `kernel_binary_reproducibility` | missing valid comparison of two clean runs of fixed profile |
| `WARN` | `exact_eze4_source` | OSRC X510XXUCEZE4 request is pending; U11 is not U12/EZE4 |
| `WARN` | `hardware_observation` | no console or physical testing; M2/M3 not observed |
| `WARN` | `physical_write_gate` | NO-GO: this report never authorizes flashing, signing, or downgrade |

## How to Read the Result

`READY` only means that offline inputs are consistent with each other. Incomplete
DTS states, lack of exact EZE4 source, and the
absence of physical observation keep the write gate at `NO-GO`.
