# U11 Modules Audit ↔ EZE4 vendor_boot

## Result

- U11 modules: `282` (`5.15.180`)
- stock EZE4 modules in dlkm: `281`
- common modules: `280`, same relative order: `true`
- stock only: `sec_debug_test.ko`
- U11 only: `a96t396.ko, input_booster_lkm.ko`
- physical gate: `NO-GO`

## Checks

| status | check | detail |
|---|---|---|
| `PASS` | `stock_provenance` | vendor_boot EZE4 v4: generic + dlkm fragments, 281 modules; 6 verified files |
| `PASS` | `u11_module_metadata` | 282/282 modules with vermagic 5.15.180 and appended signature |
| `PASS` | `u11_hard_dependency_graph` | 282 modules.dep entries; all hard dependencies are present |
| `WARN` | `softdep_stale_names` | unresolvable references ['exynos_thermal', 'memory_group_manager', 'pcie_exynos_rc', 's2dos05_regulator']; matches EZE4 vendor_boot=True |
| `PASS` | `stock_u11_load_order` | 280 common in same order; stock only=['sec_debug_test.ko']; U11 only=['a96t396.ko', 'input_booster_lkm.ko'] |
| `PASS` | `ufs_closure` | 28 U11 modules; missing dependencies=0 |
| `PASS` | `usb_closure` | 45 U11 modules; missing dependencies=0 |
| `WARN` | `usb_role_scope` | profile gadget/ACM-oriented; xhci-exynos not included |
| `WARN` | `scsc_firmware` | Wi-Fi/BT is not included for M2/M3; /vendor/firmware/wifi and EFS calibration still need extraction |
| `WARN` | `physical_write_gate` | NO-GO: module audit does not authorize packaging or flashing |

## Interpretation

Equal relative order reduces early initialization risk, but does not prove
U11↔EZE4 binary ABI. Stock modules are never loaded with the U11 kernel, nor U11
modules with the stock kernel. UFS and USB only have static closure proven;
DT, clocks, PHY, regulators, and Type-C still require hardware observation.
