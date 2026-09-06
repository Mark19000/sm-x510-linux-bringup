# Minimal Modification Set — SM-X510 U12/EZE4

> **SUPERSEDED — NO USAR COMO PLAN OPERATIVO.** Conservado como auditoría histórica U11. Contiene conclusiones invalidadas sobre el mínimo, `dtbo` y flags AVB. La autoridad actual es `docs/boot-chain/minimum-first-boot-image-set.md`; el veredicto vigente es `CANNOT_YET_BE_DETERMINED`.

Fecha: 2026-08-24
Alcance: primer experimento con kernel propio, sin flashear ni generar imágenes ejecutables.
Estado: auditoría estática de imágenes stock y artefactos U11 ya presentes en el repositorio.

## Resumen Ejecutivo

- **ERRATA:** el root protege `boot`, `init_boot` y `vendor_boot` mediante HASH directo; `dtbo` mediante CHAIN a su vbmeta hijo, cuyo HASH cubre `dtbo`. Cada imagen inspeccionada contiene además vbmeta embebido.
- **HECHO:** `boot.img` aporta el kernel; `init_boot.img` aporta sólo ramdisk GKI; `vendor_boot.img` aporta vendor ramdisk, DTB base comprimido Samsung y bootconfig; `dtbo.img` aporta tres overlays.
- **HECHO:** El kernel U11 construido es `5.15.180` y los inventarios stock EZE4 corresponden a `5.15.189-android13-3`. Con `MODVERSIONS=y` y vermagic distinto, los 281 módulos del vendor ramdisk stock deben tratarse como incompatibles hasta demostrar lo contrario.
- **HECHO:** Los tres overlays U11 disponibles son byte-idénticos a los overlays extraídos de `dtbo.img` EZE4. Por tanto, `dtbo.img` stock es candidato válido para permanecer sin cambios en el experimento mínimo, sujeto a la política del bootloader desbloqueado.
- **ERRATA:** esa conclusión operativa queda retirada. Tras unlock, `boot-only` es el candidato mecánicamente mínimo para un marcador EZE4, pero la aceptación Samsung del hash roto es **UNKNOWN**; no hay conjunto probado.

## Evidencia Encontrada

### Inspección directa

| Imagen | Formato | Contenido relevante | AVB embebido |
|---|---|---|---|
| `artifacts/stock/images/boot.img` | Android boot v4 | kernel 39,356,928 B; ramdisk ausente | footer + vbmeta SHA256_RSA4096 |
| `artifacts/stock/images/init_boot.img` | Android boot v4 | sin kernel; ramdisk GKI LZ4-legacy de 2,486,802 B | footer + vbmeta SHA256_RSA4096 |
| `artifacts/stock/images/vendor_boot.img` | vendor boot v4 | vendor ramdisk LZ4-legacy de 18,077,432 B; DTB Samsung comprimido de 239,652 B; bootconfig `buildtime_bootconfig=enable` | footer + vbmeta SHA256_RSA4096 |
| `artifacts/stock/images/dtbo.img` | DTBO v0 | 3 overlays; custom `[0,0]`, `[1,3]`, `[4,32]` | footer + vbmeta SHA256_RSA4096 |
| `artifacts/stock/images/vbmeta.img` | vbmeta | clave pública SHA-1 `b6924fd490355eca36e5a5cd9c4d2b4bd6434029`; rollback index global 0; flags 0 | raíz de confianza |

### Descriptores del vbmeta raíz

- Hash descriptor `boot`: tamaño original `39,363,360`; digest `3f28d10f...31a420c`.
- Hash descriptor `init_boot`: tamaño original `2,495,248`; digest `4f514634...f32efc`.
- Hash descriptor `vendor_boot`: tamaño original `18,334,480`; digest `7c5898f8...050da7`.
- Hash descriptor `dtbo`: tamaño original `542,896`; digest `47c853eb...e2dde`.
- Chain partitions: `dtbo` RIL 1, `prism` RIL 2, `optics` RIL 3.

Los cuatro hash descriptors tienen `flags=0`. No hay indicación estática de tolerancia a modificaciones en estado bloqueado.

### ABI del vendor ramdisk stock

**HECHOS:**

- Inventario EZE4: 281 módulos en `modules.load` y `modules.dep`.
- Kernel U11: 282 módulos con vermagic `5.15.180 SMP preempt mod_unload modversions aarch64`.
- Referencia stock documentada: `5.15.189-android13-3-33478785`.
- Ambos lados usan `CONFIG_MODVERSIONS=y`. El árbol U11 tiene `Module.symvers`, pero no existe tabla CRC comparable del kernel stock en este repositorio.
- Los primeros módulos stock incluyen `exynos-chipid_v2.ko`, `exynos-reboot.ko`, `sec_debug_base_early.ko`, `clk_exynos.ko`, `exynos_mct_v3.ko`, `s3c2410_wdt.ko` y `pinctrl-samsung-core.ko`.
- En el build U11 auditado, chipid, clocks S5E8835, MCT v3, watchdog y pinctrl core son modulares; GIC base es built-in (`CONFIG_EXYNOS_GIC=y`).
- `CONFIG_MODULE_SIG_FORCE` y `CONFIG_SECURITY_LOCKDOWN_LSM` no están activos en el kernel U11 auditado. El rechazo automático por firma no debe sobreestimarse; el bloqueante principal es vermagic/CRC/ABI binaria/CFI.

**HIPÓTESIS:**

- Si un init o loader intenta cargar los módulos stock con el kernel U11, el fallo normal esperado comienza por formato/vermagic y continúa con CRC/símbolos desconocidos cuando aplique. El comportamiento exacto depende del loader y de la política de errores.
- Si el vendor ramdisk se entrega pero no se procesa, el kernel puede alcanzar `/init`; sin drivers tempranos críticos integrados, puede quedarse sin clocks/timers/pinctrl funcionales o colgar antes de userspace.

### DTBO

Comparación byte a byte:

| Overlay stock | Artefacto U11 | Resultado |
|---|---|---|
| `overlay-00-id-00000000-rev-00000000.dtbo` | `gts9fewifi_eur_open_w00_r00.dtbo` | BYTE-IDENTICAL |
| `overlay-01-id-00000000-rev-00000000.dtbo` | `gts9fewifi_eur_open_w00_r01.dtbo` | BYTE-IDENTICAL |
| `overlay-02-id-00000000-rev-00000000.dtbo` | `gts9fewifi_eur_open_w00_r04.dtbo` | BYTE-IDENTICAL |

Esto respalda mantener `dtbo.img` stock en el primer experimento. No elimina la incertidumbre sobre cómo selecciona overlay el bootloader Samsung ni sobre comprobaciones adicionales propias del fabricante.

## Qué Significa

### Tabla de decisión por imagen

| Imagen | Función | Necesario modificar | Puede permanecer stock | Riesgo |
|---|---|---|---|---|
| `boot.img` | Entregar el kernel propio al bootloader | Sí, para ejecutar kernel U11 | No, si el objetivo es ejecutar ese kernel bajo UNLOCKED | Invalida descriptor AVB; posible warning orange/red; bajo LOCKED probablemente impide handoff |
| `init_boot.img` | Aportar ramdisk GKI/genérico inicial | Depende: sí si `/init` propio o initramfs experimental sustituye al stock; no si se usa el ramdisk GKI stock intacto | Sólo si su contenido sigue siendo compatible con el kernel U11 y no carga código ABI cruzada | Ramdisk stock Android puede esperar entorno/vendor Android16 y ocultar o impedir `/init` experimental |
| `vendor_boot.img` | Aportar vendor ramdisk, DTB base y bootconfig | No como requisito estructural si el kernel tiene todos los drivers pre-`/init` built-in y se evita procesar sus DLKM stock; sí si se quiere reemplazar DTB/bootconfig o eliminar módulos incompatibles | Hipótesis riesgosa: DT/bootconfig correctos, pero 281 módulos `5.15.189` son NO-GO para kernel `5.15.180` | Carga ABI cruzada puede fallar por vermagic/CRC; fallos en clocks/MCT/pinctrl pueden impedir userspace; mantener stock reduce cambios pero no riesgo funcional |
| `dtbo.img` | Aplicar overlay según revisión de hardware | No en este momento | Sí como candidato fuerte: overlays U11 son byte-idénticos a EZE4 | Selección bootloader y políticas Samsung no verificadas; cualquier cambio rompe AVB innecesariamente |
| `vbmeta.img` | Anclar hashes, claves, rollback indexes y chain partitions | Sí en un flujo UNLOCKED coherente: regenerar/firmar con clave controlada o usar política de verificación deshabilitada validada por el bootloader | No si cambia `boot` o `init_boot`; el vbmeta stock seguiría anclando hashes antiguos | Firma incorrecta o flags mal interpretados pueden producir RED-state/no-boot; regeneración no autoriza flasheo |

### Preguntas específicas

#### ¿Cuál es el mínimo conjunto absoluto?

Desde el punto de vista de contenido ejecutable:

1. `boot.img` con kernel U11;
2. `vbmeta.img` coherente con las imágenes cambiadas y aceptable por el bootloader en estado UNLOCKED;
3. un camino de initramfs controlado.

Ese tercer punto puede materializarse de dos formas:

- **Ruta A:** modificar `init_boot.img` (y posiblemente `vendor_boot.img`) para entregar initramfs/módulos U11 coherentes. Conjunto práctico: 3–4 imágenes.
- **Ruta B:** usar ramdisk stock intacto sólo si el kernel U11 lleva todo lo necesario hasta `/init` como built-in y ningún proceso carga los 281 módulos stock. Conjunto nominal: 2 imágenes (`boot`, `vbmeta`), pero esta ruta es una hipótesis condicionada a build/configuración y al comportamiento del ramdisk Android stock.

Por tanto, no existe todavía un “mínimo físico” universal: depende del perfil initramfs y del build U11 elegido.

#### Si sólo cambias `boot.img` e `init_boot.img`, ¿puede `vendor_boot` quedar stock?

Sólo bajo tres condiciones simultáneas:

1. Estado UNLOCKED y vbmeta regenerado/coherente aceptado por el bootloader.
2. El DTB base stock sigue siendo correcto para el hardware y kernel U11.
3. Ningún componente carga los módulos `5.15.189` contenidos en el vendor ramdisk, o el loader tolera y aísla esos fallos sin afectar el camino hasta `/init`.

La primera condición pertenece al experimento AVB. Las otras dos son factibles sólo con evidencia adicional. Mantener `vendor_boot` stock conserva DTB/bootconfig, pero entrega un inventario incompatible; no es recomendable como primera prueba salvo que el kernel tenga los drivers tempranos críticos built-in y se controle explícitamente el loader de módulos.

#### ¿Qué pasa si los 281 módulos stock llegan al kernel U11?

**Escenario inferido, no observado:**

- El vermagic `5.15.189-android13-3` no coincide con `5.15.180`; la carga normal falla antes de resolver símbolos.
- Con `MODVERSIONS=y`, incluso ignorando vermagic, faltan tablas CRC stock para demostrar igualdad ABI.
- `CONFIG_CFI_CLANG=y` añade riesgo de discrepancia binaria de callbacks más allá de nombres/CRC.
- Fallos en módulos tempranos pueden dejar el sistema sin clocks, MCT, pinctrl o identidad SoC. Dependiendo del driver y probe, el resultado puede ser error, hang o panic.
- Si el loader ignora fallos individuales, el boot puede alcanzar `/init`, pero con subsistemas esenciales ausentes; eso no es un éxito y complica el diagnóstico.

#### ¿Puede `dtbo.img` quedar stock si los overlays U11 son byte-idénticos?

Sí, como decisión técnica de contenido. Los tres artefactos comparados son idénticos byte a byte. Quedan dos incertidumbres separadas:

- política del bootloader al seleccionar overlay y validar `dtbo` en estado UNLOCKED/vbmeta alternativo;
- selección correcta de revisión de hardware, aún no observada físicamente.

No modificar `dtbo` reduce variables y preserva el comportamiento de selección stock.

#### ¿Siempre hay que regenerar `vbmeta.img`? ¿Basta un flag?

Si cambia cualquier imagen anclada por el vbmeta raíz, su descriptor deja de coincidir. La clave OEM no está disponible. En un dispositivo UNLOCKED, una hipótesis es usar `VERIFICATION_DISABLED` (`flags=2`), siempre que el bootloader Samsung respete esa política. `flags=1` es `HASHTREE_DISABLED`, no desactiva hashes/firmas; `flags=3` combina ambos bits.

Ningún valor es automáticamente suficiente:

- **HECHO:** el vbmeta stock tiene flags 0 y firma OEM.
- **HIPÓTESIS:** el bootloader desbloqueado acepta un vbmeta alternativo con `flags=2` o `flags=3`.
- **HIPÓTESIS:** Samsung no añade comprobaciones adicionales que hagan fallar esa configuración.

El experimento AVB debe definir primero una ruta de recuperación validada. Bajo LOCKED no debe asumirse que ningún flag permita boot.

## Riesgos

| Riesgo | Clase | Mitigación propuesta |
|---|---|---|
| Mezclar kernel U11 con 281 módulos stock U12 | Alto | Tratar como NO-GO; usar initramfs U11 coherente o drivers tempranos built-in |
| Creer que cambiar sólo boot/vbmeta basta | Crítico si se usa ramdisk stock Android | Definir explícitamente quién provee `/init` y qué módulos se cargan |
| Modificar DTBO sin necesidad | Medio | Mantener stock porque los overlays son idénticos |
| Asumir `flags=2/3` universalmente válido | Alto | Mantenerlo como hipótesis Samsung hasta validar recovery y obtener autorización futura |
| Ocultar fallos de módulo por loader tolerante | Medio-Alto | Registrar cada resultado de carga; no interpretar llegada a shell como compatibilidad total |
| Confundir rechazo AVB con crash temprano de kernel | Alto | Usar matriz de señales: warning persistente, Download Mode, enumeración USB y consumo |

## Hipótesis

1. Un kernel U11 con chipid, clock S5E8835, MCT v3, pinctrl y PMU básico built-in puede alcanzar `/init` sin procesar módulos stock U12.
2. El ramdisk GKI stock puede convivir con ese kernel sólo si no impone dependencias incompatibles antes del `/init` experimental.
3. Hipótesis histórica corregida: el bootloader UNLOCKED acepta imágenes modificadas con `VERIFICATION_DISABLED` (`flags=2`) mientras `vendor_boot` y `dtbo` siguen stock. La aceptación Samsung permanece **UNKNOWN** y el conjunto ya no es el candidato mínimo canónico.
4. La selección DTBO stock funciona sin cambio de imagen porque el contenido overlay es equivalente byte a byte.
5. Samsung no exige una cadena Knox/RPMB adicional incompatible con este esquema.

Ninguna hipótesis anterior autoriza un intento físico por sí sola.

## Experimentos Recomendados

Todos son auditorías locales o preparación de plan; ninguno genera imagen flasheable.

1. **Cerrar ruta built-in:** auditar config/build necesarios para integrar drivers pre-userspace críticos como `=y` y verificar que `/init` no dependa del vendor ramdisk stock.
2. **Definir initramfs mínimo U11:** empaquetado local no flasheable para medir tamaño y dependencias; separar perfil MINIMAL de SEC_DEBUG.
3. **Simular composición de imágenes:** calcular offsets, tamaños y hashes de boot/init_boot/vbmeta candidatos sin escribir particiones.
4. **Probar política AVB localmente:** verificar cadenas candidatas con avbtool y documentar qué descriptor debería fallar en cada combinación.
5. **Calibrar baseline stock:** plan de observación USB/consumo/display con firmware actual antes de cualquier cambio físico.
6. **Decidir orden físico:** tras cerrar earlycon/sec_debug y unlock, empezar por el menor número de imágenes cambiadas que garantice initramfs coherente; no optimizar por “menos bytes” sino por menos incertidumbre.

## Documentación Propuesta

- Este documento como fuente canónica del conjunto mínimo de modificación.
- `docs/boot-chain/avb-experiment-plan.md` debe definir estados, señales y recuperación.
- `docs/debugging/earlycon-analysis.md` debe decidir cmdline/bootconfig antes de fijar `boot`/`vendor_boot`.
- `docs/debugging/sec-debug-firstboot-profile.md` debe fijar módulos y orden de carga del initramfs.
- Actualizar `docs/first-boot-experiment-plan-v2.md` con la conclusión: el mínimo real depende de la ruta initramfs/built-in, y el vendor ramdisk stock U12 no debe cargarse contra kernel U11.
