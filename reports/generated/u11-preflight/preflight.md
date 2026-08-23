# Preflight offline U11 para M2/M3

Este informe comprueba coherencia offline. **Nunca autoriza escribir en la tablet.**

## Veredicto

- análisis offline U11: `READY`
- payload M3: `READY`
- M2 observado en hardware: `false`
- M3 observado en hardware: `false`
- escritura física: `NO-GO`

## Initramfs frente a init_boot EZE4

| perfil | módulos | LZ4 (B) | margen (B) | cabe |
|---|---:|---:|---:|---|
| `minimal` | 0 | 690128 | 1796674 | sí |
| `ufs` | 28 | 2116711 | 370091 | sí |
| `usb` | 45 | 3018036 | -531234 | no |

## Comprobaciones

| estado | comprobación | detalle |
|---|---|---|
| `PASS` | `identity_separation` | source U11/B11 y objetivo EZE4/U12 están registrados como identidades distintas |
| `PASS` | `osrc_hashes` | hashes OSRC base, overlay y Kernel.tar.gz coinciden |
| `PASS` | `build_hashes` | 15 artefactos de build verificados |
| `PASS` | `build_identity` | BUILD_INFO enlaza source, kernel y 282 módulos |
| `PASS` | `early_userspace_config` | config preparado para initramfs y consola temprana |
| `PASS` | `installed_modules` | release=5.15.180, módulos=282, regulares verificados contra tar=296, symlinks=0 |
| `PASS` | `module_order_consistency` | modules.order build/install: 282/282 |
| `PASS` | `vendor_module_lists` | 7 módulos early + 2 módulos de producto presentes |
| `PASS` | `module_vendor_boot_audit` | metadatos, dependencias, orden stock y cierres UFS/USB verificados |
| `PASS` | `initramfs_minimal` | 0 módulos, LZ4=690128 B, margen=1796674 B |
| `PASS` | `initramfs_ufs` | 28 módulos, LZ4=2116711 B, margen=370091 B |
| `WARN` | `initramfs_usb` | 45 módulos, LZ4=3018036 B, margen=-531234 B; perfil diagnóstico sobredimensionado, no empaquetable |
| `WARN` | `dt_observed_distance` | r04 material=0, unresolved=207; DTB base compilado material=4, unresolved=14. No demuestra equivalencia. |
| `WARN` | `kernel_binary_reproducibility` | falta comparación válida de dos runs limpios del perfil fijo |
| `WARN` | `exact_eze4_source` | la solicitud OSRC X510XXUCEZE4 está pendiente; U11 no es U12/EZE4 |
| `WARN` | `hardware_observation` | sin consola ni prueba física; M2/M3 no observados |
| `WARN` | `physical_write_gate` | NO-GO: este informe nunca autoriza flash, firma ni downgrade |

## Cómo leer el resultado

`READY` sólo significa que los insumos offline son coherentes entre sí. Los estados
DTS incompletos, la falta de source EZE4 exacto y la
ausencia de observación física mantienen la puerta de escritura en `NO-GO`.
