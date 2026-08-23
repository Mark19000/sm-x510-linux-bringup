# Auditoría de módulos U11 ↔ vendor_boot EZE4

## Resultado

- módulos U11: `282` (`5.15.180`)
- módulos stock EZE4 en dlkm: `281`
- módulos comunes: `280`, mismo orden relativo: `true`
- sólo stock: `sec_debug_test.ko`
- sólo U11: `a96t396.ko, input_booster_lkm.ko`
- puerta física: `NO-GO`

## Comprobaciones

| estado | comprobación | detalle |
|---|---|---|
| `PASS` | `stock_provenance` | vendor_boot EZE4 v4: fragmentos generic + dlkm, 281 módulos; 6 ficheros verificados |
| `PASS` | `u11_module_metadata` | 282/282 módulos con vermagic 5.15.180 y firma añadida |
| `PASS` | `u11_hard_dependency_graph` | 282 entradas modules.dep; todas las dependencias duras están presentes |
| `WARN` | `softdep_stale_names` | referencias no resolubles ['exynos_thermal', 'memory_group_manager', 'pcie_exynos_rc', 's2dos05_regulator']; coinciden con vendor_boot EZE4=True |
| `PASS` | `stock_u11_load_order` | 280 comunes en igual orden; sólo stock=['sec_debug_test.ko']; sólo U11=['a96t396.ko', 'input_booster_lkm.ko'] |
| `PASS` | `ufs_closure` | 28 módulos U11; dependencias ausentes=0 |
| `PASS` | `usb_closure` | 45 módulos U11; dependencias ausentes=0 |
| `WARN` | `usb_role_scope` | perfil orientado a gadget/ACM; xhci-exynos no incluido |
| `WARN` | `scsc_firmware` | Wi-Fi/BT no se incluye para M2/M3; falta extraer /vendor/firmware/wifi y calibración EFS |
| `WARN` | `physical_write_gate` | NO-GO: auditoría de módulos no autoriza empaquetar ni flashear |

## Interpretación

La igualdad de orden relativo reduce el riesgo de inicialización temprana, pero no
demuestra ABI binaria U11↔EZE4. Nunca se cargan módulos stock con el kernel U11
ni módulos U11 con el kernel stock. UFS y USB sólo tienen cierre estático probado;
DT, clocks, PHY, reguladores y Type-C aún requieren observación en hardware.
