# Estado del proyecto

Fecha de corte: 23 de agosto de 2026.

## Terminado en el workspace

- objetivo físico confirmado: SM-X510 Wi-Fi, `BP4A.251205.006` /
  `X510XXUCEZE4`, Android 16, One UI 8.5, binario U12, CSC `EUX` dentro de
  multi-CSC `OXM` (`X510OXMCEZE4`);
- fuentes downstream stock separadas para X510 (`X510XXU3BXDG`) y X516
  (`X516BXXU7CYE1`), más mainline, descargadas de forma parcial;
- inventario de DT base y overlays (X510 Wi-Fi: r00/r01/r04; referencia X516
  5G: r00/r01/r02/r04);
- matriz razonada de controladores;
- extractor de contenedores DTBO y escáner de FDT incrustados;
- recolector ADB de sólo lectura;
- parche/fragmento Kconfig para early userspace;
- VM Lima ARM64 reproducible (Ubuntu 26.04, ext4), scripts de toolchain, kernel
  y BusyBox;
- kernel downstream de referencia compilado completamente con Clang 21:
  `Image`, BTF, módulos firmados e instalados y los tres overlays Wi-Fi;
- nueve parches de compatibilidad/corrección documentados para el árbol vendor;
- BusyBox 1.36.1 ARM64 estático con configuración mínima verificada;
- initramfs reproducible en perfiles mínimo, UFS (28 módulos) y USB (45
  módulos); el USB demuestra su dependencia real pero no cabe en `init_boot`,
  mientras la raíz persistente se monta sólo en lectura;
- constructor DTBO que conserva los rangos de revisión stock y prueba de
  ida/vuelta por hashes;
- documentación de build, bring-up y roadmap mainline;
- ficha y cuaderno específicos de la unidad EZE4, con guardas de modelo/versión
  en la extracción, el inventario ADB y la compilación.
- firmware EUX/EZE4 descargado; ZIP validado por estructura, MD5 publicado
  `255c0e65e2ec62b0ba723612c1ece5a4` y SHA-256 local;
- extractor ZIP→AP→particiones en streaming para evitar duplicar 11+ GB;
- `boot`, `init_boot`, `vendor_boot`, `dtbo` y `vbmeta` EZE4 extraídos y
  analizados; cabeceras Android v4, tamaños, compresión y pies AVB registrados;
- candidatos `boot`/`init_boot` sin firma reconstruidos y comprobados por
  desempaquetado; AVB detecta correctamente que el hash Samsung ya no coincide;
- pipeline Lima integral (`reference-all`), metadatos Kbuild deterministas,
  hashes relativos y guardas contra artefactos obsoletos tras un fallo;
- pipeline integral repetido de extremo a extremo con salida 0; la suite ampliada
  alcanza 88 pruebas host-only, incluidas las guardas OSRC U11, comparación de
  árboles, seguridad/adversariales, semántica DTS y herramientas de imágenes.
- entrega OSRC Android 16/U11 confirmada internamente: base `X510XXU8DYJ4` más
  suplemento `X510XXSBDZB4`, kernel 5.15.180, extraída íntegramente en ext4 sin
  alterar U3 ni el stock EZE4;
- comparación sistemática U3→U11→EZE4 generada: el overlay U11 no presenta
  diferencias materiales observables respecto al r04 stock EZE4, aunque quedan
  referencias externas sin resolver, y el DT base difiere materialmente en
  `mfc/debug_mode` dentro de lo observable;
- U11 compilado completamente con Clang 21 ARM64 y los nueve parches actuales:
  Image, BTF/LTO, DTB, tres DTBO, 282 módulos construidos e instalados; pruebas
  negativas confirman los fallos que reaparecen al retirar cada parche de
  compatibilidad relevante;
- pipeline U11 fijo sin comandos arbitrarios, con nueve hashes de parche,
  metadatos deterministas y rechazo de rutas físicas en Image/módulos;
- auditoría binaria de los DTB compilados U11→EZE4: cuatro diferencias
  observables (EMS, MFC y SCSC) y 14 referencias sin resolver; ninguna autoriza
  afirmar equivalencia completa;
- auditoría de 282 módulos U11 frente a 281 stock: 280 comunes conservan orden,
  las dependencias duras y los cierres UFS/USB están completos;
- preflight U11 e initramfs separados del pipeline U3, siempre con puerta
  física `NO-GO`.

## Actualización canónica 2026-09-05 — EZE4 y Evidencia Física de Desbloqueo

El bloque U11 inferior se conserva como historia, pero ya no describe el estado activo. Samsung OSRC EZE4 (`5.15.189`) es la base canónica del pipeline:
- `kernelrelease` stock exacto: `5.15.189-android13-3-33478785`
- `vermagic` stock exacto: `5.15.189-android13-3-33478785 SMP preempt mod_unload modversions aarch64`
- Compatibilidad ABI: 100.00% (281/281 módulos propietarios stock verificados, 15,123/15,123 símbolos CRC exactos, 0 discrepancias).
- Suite de pruebas de regresión: 98/98 pruebas aprobadas en host (incorporadas guardas anti-self-confirmation de identidad física 5.15.189-android13-3-33478785 y alias repro_compare).
- Proyecto Root-My-Galaxy EZE4: Fase J2.1-R1 Non-Semantic Remediation COMPLETADA; stack de validación J2 congelado (68/68 pruebas passing); J3 en HOLD; L3 en NO-GO; exploit real no demostrado.

### Estado Físico y Evidencia de Diagnóstico (Actualizado por `IMG_2113.HEIC` y `IMG_2114.HEIC`)

Se obtuvieron capturas fotográficas directas de la pantalla de advertencia previa (`IMG_2113.HEIC`) y de la pantalla estándar de Odin Mode (`IMG_2114.HEIC`, transcripción pública con identificadores únicos redactados en [`docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md`](file:///Users/markpi/tab-s9-fe-linux/docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md)):
- **Pantalla de advertencia previa (Warning Screen)**: **CONFIRMED** (fotografiada físicamente en `IMG_2113.HEIC`).
- **Ruta a Device Unlock Mode**: **CONFIRMED** (anunciada explícitamente en el microcódigo del cargador en la localización en chino: `长按音量增加键：设备解锁模式`, omitida en inglés).
- **Pantalla normal de Odin Mode**: **CONFIRMED** (alcanzada mediante pulsación corta de Vol Up desde la pantalla de advertencia, fotografiada en `IMG_2114.HEIC`).
- **CURRENT BINARY**: `Samsung Official` (**CONFIRMED** en UI de bootloader).
- **KG STATE**: `Completed (00)` (**CONFIRMED** en UI de bootloader).
- **Secure Download**: `Enabled` (**CONFIRMED** en UI de bootloader).
- **Sales code / CID / AID**: `EUX//` (**CONFIRMED** en UI de bootloader).
- **WARRANTY VOID**: `0 (0x0000)` (**CONFIRMED** en UI de bootloader).
- **RP SWREV (Bootloader)**: `B:12` (**CONFIRMED** en UI de bootloader; confirma físicamente nivel de rollback 12).
- **HW REV**: `4` (**CONFIRMED** en UI de bootloader; coincide con DTBO `r04`).
- **DDR SIZE**: `8G` (**CONFIRMED** en UI de bootloader).
- **BUILD VERSION**: `X510XXUCEZE4` (**CONFIRMED** en UI de bootloader).
- **Campos no mostrados en Odin Mode**: `OEM LOCK`, `FRP LOCK`, `SYSTEM STATUS` (**`NOT DISPLAYED`**; no inferir estados desde la ausencia).
- **Secuencia segura de reinicio/cancelación**: `Volume Down Key + Side key for more than 7 secs` (**CONFIRMED** en UI).
- **Capacidad práctica de desbloqueo del propietario**: **STRONGLY_SUPPORTED** (anunciada en UI de SBOOT/LOKE en hardware Exynos EUX libre).
- **Pantalla de Device Unlock Mode (2B)**: **NOT YET CAPTURED / NOT YET OBSERVED**.
- **Desbloqueo exitoso completado**: **NOT YET TESTED / LOCKED** (el dispositivo físico continúa estrictamente `ro.boot.flash.locked=1`, `ro.boot.vbmeta.device_state=locked`, `ro.boot.verifiedbootstate=green`, `ro.boot.warranty_bit=0`).
- **Estado de decisión del propietario**: **`READY_FOR_OWNER_UNLOCK_DECISION`** (se cuenta con evidencia física directa suficiente para evaluar borrado de fábrica y consecuencias en eFuse Knox).
- **Estado para primer flasheo custom**: **`NOT_READY_FOR_FIRST_CUSTOM_FLASH`** (la recuperación está sólo parcialmente validada y AVB multi-partición no está probado).
- **Recuperación**: **PARTIALLY VALIDATED** (acceso a Download Mode, diagnóstico visual y enumeración USB `04e8:685d` confirmados; herramientas host en macOS, handshake LOKE, lectura PIT y restauración completa pendientes).
- **Significado de `[Reboot Device - D2]`**: estrictamente **UNKNOWN** (la hipótesis comunitaria de bloqueo de pantalla queda como conjetura no demostrada).
- **Banderas AVB 2.0**: se distingue formalmente `flags=1` (`HASHTREE_DISABLED`) de `flags=2` (`VERIFICATION_DISABLED`).
- **Documentos de Referencia Canónica**: [`docs/boot-chain/unlock-evidence-matrix.md`](file:///Users/markpi/tab-s9-fe-linux/docs/boot-chain/unlock-evidence-matrix.md), [`docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md`](file:///Users/markpi/tab-s9-fe-linux/docs/hardware/evidence/2026-09-05-odin-mode-stock-baseline.md), [`docs/hardware/evidence/2026-09-05-download-warning-device-unlock-mode.md`](file:///Users/markpi/tab-s9-fe-linux/docs/hardware/evidence/2026-09-05-download-warning-device-unlock-mode.md).

## Pendiente de datos físicos (histórico U11; superseded)

- recibir la respuesta a la solicitud oficial Samsung OSRC del código exacto
  `SM-X510` / `X510XXUCEZE4`; U11 es la mejor referencia actual, no EZE4;
- obtener DT en ejecución y mapa de particiones;
- localizar una consola observable;
- identificar la revisión física/overlay realmente elegida por el bootloader;
- repetir/adaptar los parches sobre el código EZE4 cuando Samsung lo publique;
- decidir y validar el procedimiento de desbloqueo, firma/AVB y rollback sin
  arriesgar datos ni anti-rollback;
- ejecutar M2-M5 en hardware y capturar logs.

## Bloqueo de seguridad vigente

`scripts/build-downstream.sh` compara la fuente conocida
(`X510XXU3BXDG`) con el objetivo (`X510XXUCEZE4`) y se detiene. Se puede usar
`ALLOW_REFERENCE_BUILD=1` únicamente para practicar/diagnosticar la compilación;
no convierte el resultado en compatible ni autoriza su flasheo.

## No afirmado

No se afirma que mainline arranque, que el kernel de referencia sea compatible
con EZE4, que los candidatos sin firma sean flasheables ni que pantalla, UFS,
Wi-Fi o carga funcionen. Esas afirmaciones sólo se añadirán junto a un log de
hardware y hashes reproducibles.
