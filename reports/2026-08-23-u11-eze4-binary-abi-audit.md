# Auditoría binaria U11 source/build frente a EZE4/U12 stock — M2/M3

Fecha: 2026-08-23. Alcance: comparación binaria y de ABI observable entre un build U11 reproducido desde OSRC `X510XXSBDZB4` y el firmware stock `X510XXUCEZE4`/U12. No se flasheó ni editó ninguna imagen o módulo.

## Veredicto

- **NO-GO para escritura física**: no hay prueba de equivalencia ABI U11↔EZE4/U12.
- El build U11 es coherente internamente, pero su kernel es `5.15.180` mientras el stock EZE4 expone `5.15.189-android13-3-33478785`.
- El DTB base compilado y el DTB stock son semánticamente distintos e incompletos como evidencia; los tres overlays DTBO son idénticos byte a byte.
- La ausencia de source exacto EZE4/U12 impide atribuir con certeza las diferencias observadas a cambios reales del release, al toolchain distinto o a la ausencia de parches locales Samsung.

## Identidades e insumos auditados

| lado | identidad / origen | dato clave |
|---|---|---|
| Build U11 | OSRC `X510XXSBDZB4`, base `X510XXU8DYJ4`, Android 16 | `kernel_release=5.15.180`; 282 módulos; Clang 21.1.8; sin imágenes boot creadas ni AVB |
| Stock EZE4 | AP `X510XXUCEZE4`, Android 16/U12 | boot/init_boot/vendor_boot v4 extraídos sólo lectura |
| Artefactos | `artifacts/u11/x510xxsbdzb4-u11-clang21-20260823/`, `artifacts/stock/images/` | hashes listados abajo |

SHA-256 relevantes:

| objeto | SHA-256 |
|---|---|
| stock `boot.img` | `c96c0eb033d2208e84fbe0a0926df3ce2e8c6a94066702f2592e7bc165d11013` |
| stock payload kernel (`Image`) | `0ab39cc588c12511023a3e156a3a047a01480bb11562401245ab1d44e5224d4e` |
| stock `init_boot.img` | `9efb41692562f648b1227a7f7212bd87eec59d299689ac0b11c51348800e969c` |
| stock `vendor_boot.img` | `60e85ca061cc67cfa1f8d9fd86fc3840ccb46d87887c9b3ed20deca7c02459e8` |
| U11 `Image` | `423bae9d6a8979b1548a89759d2b3eddaf86e4c05170a50a76fb0b06de4444f3` |
| U11 `s5e8835.dtb` | `6b4fbf421516da5b99beecef258746773d33c840c9133b5fb036767852bd3f5e` |
| U11/stock overlay r00 | `4f2fd84ef62c70d4143919d8ddbe6d1152f6532d078878dc30fcb1cf68b790be` |
| U11/stock overlay r01 | `c764f7c69a9fef235af7c042b1ec7331f600b7eb60dd67d465ec721f8386f325` |
| U11/stock overlay r04 | `cdee895e13eae5ed35c3a951eb3b8a448a46f60c89f73546bcb7c3b4fae8d403` |

## Boot, init_boot y vendor_boot — hechos

| campo | stock EZE4 |
|---|---|
| `boot` | boot v4, 4096 B/page, kernel 39,356,928 B, ramdisk vacío, footer AVB v1 |
| `init_boot` | boot v4, ramdisk LZ4 legacy de 2,486,802 B, sin kernel |
| `vendor_boot` | vendor_boot v4, vendor ramdisk LZ4 legacy 18,077,432 B en dos fragmentos (generic + dlkm), DTB 239,652 B, tabla de 2 entradas, bootconfig 28 B |
| cmdline en encabezados | vacío en `boot`, `init_boot` y `vendor_boot` |
| bootconfig | única cadena observable: `buildtime_bootconfig=enable` |
| fragmentos dlkm | generic: 26 ficheros regulares y 0 módulos; dlkm CPIO 51,802,112 B descomprimido y 281 módulos |

No existe imagen empaquetada U11 comparable: el artefacto U11 disponible contiene kernel, DTB/DTBO y árbol instalable de módulos, pero registra explícitamente `boot_image_created=no` y `avb_signature_created=no`. Por tanto, no hay comparación válida de layout completo, firma AVB, tabla de ramdisk ni bootconfig generado por U11.

## Kernel, vermagic y dependencias — hechos

- Versión U11: `5.15.180`; vermagic único en 282 módulos: `5.15.180 SMP preempt mod_unload modversions aarch64`.
- Versión observable en el kernel stock: `5.15.189-android13-3-33478785`.
- Configuración embebida presente en ambos kernels. Las opciones observables relevantes coinciden: `MODVERSIONS=y`, `MODULE_SIG=y`, `MODULE_SIG_PROTECT=y`, `MODULE_SIG_ALL=y`, SHA-1, `TRIM_UNUSED_KSYMS=y`, `CFI_CLANG=y`, `ARM64_MODULE_PLTS=y` y `RELOCATABLE=y`.
- El `.config` completo tiene 18 hunks de diferencia, pero la extracción automática no permite atribuir todas las diferencias sin validar el entorno de generación.
- U11 exporta 10,365 símbolos en `Module.symvers`; el stock no incluye un `Module.symvers` comparable. Los módulos stock tampoco están presentes como ficheros en este inventario: sólo sus metadatos `modules.load`, `modules.dep` y `modules.softdep`.
- Comparación de orden: 280 módulos comunes en igual orden relativo; sólo stock `sec_debug_test.ko`; sólo U11 `a96t396.ko` y `input_booster_lkm.ko`.
- El grafo duro U11 está cerrado: 282 entradas y cero dependencias duras ausentes. Las referencias softdep obsoletas (`exynos_thermal`, `memory_group_manager`, `pcie_exynos_rc`, `s2dos05_regulator`) también existen en los metadatos stock.

**ABI observable:** la coincidencia de flags y del orden relativo no demuestra igualdad de CRC modversions, firmas de tipos, estructuras privadas, símbolos exportados ni comportamiento. Con versiones `5.15.180` y `5.15.189-android13-3-33478785`, cargar cruzadamente módulos stock/U11 no puede considerarse seguro sin tablas CRC de ambos kernels, y esas tablas no están disponibles aquí.

## DTB, DTBO y reserved-memory — hechos

- El DTB base stock en `vendor_boot` y el DTB r03/recovery tienen hash idéntico: `4d6675ee...fea2820a`; tamaño 239,588 B.
- El DTB U11 compilado mide 239,584 B y tiene otro hash. La diferencia binaria incluye longitud y contenido; no hay igualdad byte a byte.
- La herramienta semántica reporta **DIFFERENT (INCOMPLETE)**: 1,493 nodos por lado, 4 diferencias materiales y 14 referencias no resueltas (7 en cada lado).
- Diferencias materiales:
  1. `/ems/pe-list/list@0`: representación/valor de `cpus` difiere.
  2. `/ems/pe-list/list@1`: orden de rangos `cpus` difiere.
  3. `/mfc`: `debug_mode` es `1` en U11 y `0` en stock.
  4. `/scsc_wifibt@11B40000`: `cpu_table_rps` es `"00","  "` en U11 frente a `"00","00","40","40"` en stock.
- Referencias no resueltas en ambos lados incluyen `camera_rmem`, cinco SysMMUs (`brp_s0`, `csis_s0`, `cstat_s0`, `rgbp_s0`, `yuvp_s0`) y `wlbt_hw_ver`.
- El subárbol completo `reserved-memory` tiene exactamente el mismo número de líneas no vacías (10,878) en ambos DTS, pero **no** es textualmente idéntico; el diff localizado corresponde a las diferencias materiales ya listadas, no a nodos reservados adicionales.
- Los tres overlays r00/r01/r04 son idénticos byte a byte entre U11 y stock.

**Interpretación limitada:** los overlays son equivalentes binarios, pero eso no extiende equivalencia al DTB base ni a `reserved-memory`. El estado incompleto del diff impide afirmar que las regiones reservadas son funcionalmente iguales aunque su inventario textual coincida salvo las cuatro propiedades citadas.

## Source/build frente a EZE4/U12 — hechos e inferencias

Hechos:

- El OSRC disponible es `X510XXSBDZB4`; no hay árbol fuente identificado como `X510XXUCEZE4`.
- El build U11 usa Clang 21.1.8 en lugar del toolchain Samsung registrado `clang-r450784d`, y aplica parches `0001–0006,0008–0010`; no hay commit Git en el archivo OSRC.
- El propio registro del build declara que es una compilación de compatibilidad, no una reproducción byte-for-byte, y que el enlace LTO no está demostrado reproducible.
- La comparación previa U3→U11 muestra 228 DTS cambiados, 3,721 drivers cambiados, 79 drivers nuevos y 17 DTS/dtsi nuevos. Esto no es una comparación U12→U11.

Inferencias:

- Es razonable tratar el kernel U11 como un candidato de desarrollo separado del stock EZE4/U12, no como reconstrucción equivalente.
- Las cuatro diferencias DTB pueden provenir de fuente, configuración de build o postprocesado Samsung, pero la causa exacta no puede asignarse sin source U12.
- El riesgo principal no es sólo el número de versión: también lo son cualquier cambio interno entre `.180` y `.189`, CRC modversions, orden/inicialización y diferencias de vendor ramdisk no comparables.

## Desconocidos bloqueantes

1. Source exacto `X510XXUCEZE4`/U12 y sus parches/configuración definitiva.
2. Tabla completa de CRC modversions del kernel stock y de cada módulo stock.
3. Lista/símbolos exportados por el vmlinux stock y módulos stock individuales.
4. Imagen boot/init_boot/vendor_boot generada por U11 y su política real de AVB/bootconfig/tablas de ramdisk.
5. Contenido y calibración de `/vendor/firmware/wifi` más EFS para Wi-Fi/BT SCSC.
6. Observación física M2/M3: consola, arranque temprano, UFS, USB, DT aplicado, clocks/reguladores y errores CFI/modprobe.
7. Resolución semántica de referencias externas del DTB y validación del diff completo de `.config`.

## Conclusión operativa

Los overlays y varios metadatos son prometedores, pero la auditoría binaria no establece compatibilidad ABI entre el build U11 y el stock EZE4/U12. Mantener la puerta física en **NO-GO** hasta obtener source EZE4/U12, tablas CRC/símbolos comparables, imágenes U11 empaquetadas y observación controlada en hardware.
