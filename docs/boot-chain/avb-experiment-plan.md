# AVB Experiment Plan — SM-X510 U12/EZE4

> **SUPERSEDED — NO EJECUTAR.** Conservado como diseño histórico. La propuesta `vbmeta-only` no es la primera escritura canónica: altera la raíz completa y no prueba una política Samsung segura. El plan vigente condiciona un candidato `boot-only` a unlock y recovery previamente validados. USB/corriente/backlight nunca constituyen por sí solos prueba de ejecución.

Fecha: 2026-08-24
Modo: diseño de experimento. Este documento **no autoriza flasheo**, no genera imágenes y no sustituye la confirmación de precondiciones físicas.
Alcance: distinguir de forma reproducible un rechazo de Android Verified Boot de una entrega de control al kernel seguida de crash temprano.

## 1. Resumen ejecutivo

El vbmeta raíz stock usa `SHA256_RSA4096`, `Rollback Index = 0`, `Flags = 0`, y ancla por hash directo `boot`, `init_boot`, `vendor_boot`, `recovery`, `bootloader` y particiones firmware críticas (`ldfw`, `tzsw`, entre otras). `dtbo` no es un hash directo del root: es una chain partition (RIL 1) cuyo vbmeta embebido contiene el hash de `dtbo`. También encadena `prism` (RIL 2) y `optics` (RIL 3), con la misma clave pública (`sha1 b6924fd4...4029`).

Bajo bootloader LOCKED, cualquier modificación de una partición cubierta invalida la cadena. El kernel propio no debería ejecutarse en ese estado. Bajo UNLOCKED, AOSP permite verificación tolerante u omitida, pero el comportamiento exacto del bootloader Samsung de este modelo —aceptación de vbmeta con `VERIFICATION_DISABLED` (`flags=2`), advertencias visibles, límites de rollback o comprobaciones Knox adicionales— es todavía **hipótesis**.

El protocolo propuesto es incremental:

0. Calibrar señales con firmware 100% stock (baseline).
1. Escribir solo un vbmeta de prueba bajo UNLOCKED, sin tocar boot ni ramdisks, para observar la política AVB del bootloader.
2. Solo si la Fase 1 demuestra handoff tolerante, escribir kernel + vbmeta coherentes como segunda sonda.

Cada fase tiene criterios de éxito, fallo y aborto. La recuperación se basa en Download Mode accesible y restauración desde copias stock verificadas por hash.

## 2. Evidencia encontrada

### HECHOS verificados localmente

| Ítem | Valor observado |
|---|---|
| Algoritmo vbmeta raíz | `SHA256_RSA4096` |
| Clave pública (SHA-1) | `b6924fd490355eca36e5a5cd9c4d2b4bd6434029` |
| Rollback Index global | `0` |
| Rollback Index Location raíz | `0` |
| Flags | `0` en descriptor raíz y en chains observados |
| Release string | `avbtool 1.3.0` |

Descriptores relevantes del vbmeta raíz (`avbtool info_image --image artifacts/stock/images/vbmeta.img`):

- Chain partitions: `dtbo → RIL 1`, `prism → RIL 2`, `optics → RIL 3`.
- Hash descriptors directos que incluyen: `boot` (39,363,360 bytes; digest `3f28d10f...31a420c`), `init_boot` (digest `4f514634...f32efc`), `vendor_boot` (18,334,480 bytes; digest `7c5898f8...050da7`), `recovery`, `bootloader`, `fld`, `harx`, `keystorage`, `ldfw`, `tzsw`. `dtbo` aparece sólo mediante CHAIN en el root.
- Hashtree descriptors dm-verity: `system`, `vendor`, `product`, `odm`, `system_dlkm`, `vendor_dlkm`.
- Props: `com.android.build.boot.os_version=13`; `com.android.build.system.os_version=16`; security patch `2026-05-05`.

Implicación estructural directa: cambiar el contenido de `boot`, `init_boot`, `vendor_boot` o `dtbo` rompe su hash firmado aunque el tamaño de partición sea igual. No existe camino seguro LOCKED para un kernel propio manteniendo este vbmeta stock.

### HIPÓTESIS no confirmadas en este dispositivo

| ID | Hipótesis | Consecuencia si es falsa |
|---|---|---|
| H-AVB-1 | El estado UNLOCKED hace que el bootloader Samsung tolere un vbmeta alternativo con `VERIFICATION_DISABLED` (`flags=2`). | La Fase 1 puede terminar en rechazo persistente, advertencia roja o reboot loop. |
| H-AVB-2 | No hay rollback protection efectiva adicional por RIL/RPMB que rechace índices inferiores o iguales tras cambios locales. | Un vbmeta de test podría quedar bloqueado por política Samsung incluso restaurando imágenes stock. |
| H-AVB-3 | Download Mode permanece siempre accesible mediante combinación física, incluso tras fallo AVB o kernel panic. | El procedimiento de recuperación puede necesitar otra vía (carga de batería, timing distinto, herramienta Samsung). |
| H-SIG-1 | Las pantallas de advertencia siguen la semántica estándar YELLOW/ORANGE/RED. | La clasificación visual puede ser ambigua y requerir apoyo de USB/consumo/tiempos. |
| H-KRN-1 | Tras handoff, el kernel U11 puede fallar antes de inicializar USB/console, produciendo apariencia externa similar a un rechazo AVB. | Se necesita baseline temporal y post-mortem sec_debug/DSS para separar ambos casos. |

## 3. Qué significa

1. **AVB es un punto de corte anterior al kernel.** Si falla, ninguna instrucción del kernel U11 llega a ejecutarse: no hay dmesg, no hay gadget kernel, no hay sec_debug nuevo generado por esta sesión de boot.
2. **El primer objetivo físico debe ser medir la política del bootloader**, no probar ya el kernel completo. Un vbmeta-only probe aísla la pregunta "¿el bootloader acepta una cadena de confianza alternativa?" sin introducir simultáneamente incompatibilidades ABI ni DT.
3. **Las señales sin UART son probabilísticas hasta calibrarlas.** Enumeración USB, consumo, backlight y tiempos son útiles solo cuando se comparan contra un baseline stock registrado en el mismo cable, host y condiciones.
4. **El riesgo mayor no es el kernel sino quedar fuera de una política Samsung no documentada** (rollback/Knox/unlock). Por eso la primera escritura experimental es mínima y reversible, y cada fase exige reconfirmar acceso a Download Mode antes de continuar.

## 4. Matriz de señales AVB vs kernel

Nivel de confianza indicado tras cada fila: **C** = confirmado estructuralmente o en literatura AOSP; **H** = hipótesis a calibrar en este hardware.

| Señal | Apunta a fallo AVB | Apunta a kernel alcanzado | Confianza |
|---|---|---|---|
| Warning screen naranja/roja persistente en arranque normal | Sí | No | C (semántica AOSP) / H (Samsung exacto) |
| Dispositivo USB del bootloader visible (Samsung VID `04E8`) en Download Mode | Compatible con rechazo; también presente en baseline | Compatible con cualquier estado | C |
| Nuevo dispositivo USB con VID Linux `1d6b` (gadget kernel) | Nunca debería aparecer | Indicio fuerte de driver USB operativo | C (semántica USB) / H (config gadget real) |
| Consumo plano tipo bootloader durante todo el intento | Probable | No probable | H — requiere baseline |
| Cambio brusco de consumo tras fase bootloader (spike/valle) | No esperado | Posible (kernel ejecutándose o reset) | H — requiere baseline |
| Backlight se enciende brevemente y desaparece / reset loop corto | Menos probable | Posible crash temprano + reinicio | H |
| Tiempo hasta reset idéntico al baseline stock de fallo forzado (si existiera) | Más compatible | Menos compatible | H |
| `/proc/last_kmsg` o regiones DSS actualizadas tras el intento (leídas desde contexto posterior) | No (kernel nunca corrió) | Sí, si drivers debug llegaron a activarse | C (lógica) / H (activación real) |

Regla operativa: **ninguna señal aislada es diagnóstica la primera vez**. Se registra el vector completo (pantalla, USB, corriente vs tiempo, tiempo hasta reset, resultado post-mortem).

## 5. Precondiciones obligatorias antes de cualquier fase de escritura

1. Copias intactas de `boot.img`, `init_boot.img`, `vendor_boot.img`, `dtbo.img`, `vbmeta.img` stock con SHA-256 registrados y verificados.
2. Estado del bootloader documentado: OEM unlocking habilitado, dispositivo UNLOCKED confirmado por advertencia visible. **Si no hay evidencia de UNLOCKED, no ejecutar Fase 1.**
3. Baseline stock completado (Fase 0) con capturas timestamped.
4. Procedimiento probado de entrada a Download Mode con firmware stock, incluyendo tiempo máximo de espera y comportamiento de desconexión USB.
5. Host de observación preparado: log continuo de eventos USB (`lsusb`, `dmesg -w`, udev monitor), grabación de vídeo de pantalla, medidor de corriente USB con logging temporal.
6. Herramientas y archivos de restauración listos, pero **sin flashear nada** hasta que la fase correspondiente esté autorizada explícitamente.

Criterio de aborto global: pérdida de acceso a Download Mode, comportamiento térmico/electrico anómalo, advertencia de integridad inesperada en modo recovery, o cualquier estado donde la restauración stock no sea verificable.

## 6. Protocolo por fases

### Fase 0 — Baseline stock (solo lectura)

Objetivo: calibrar el vector de señales sin modificar nada.

Pasos recomendados:

1. Arrancar 3 veces con firmware stock completo, cronometrando desde inserción de cable/pulsación hasta Android.
2. Registrar por corrida: timeline de enumeración USB (VID/PID y timestamps), curva de corriente exportada, eventos de pantalla/backlight, tiempo total.
3. Entrar en Download Mode 2 veces y registrar enumeración USB y consumo estacionario.
4. Opcional avanzado (requiere contexto secundario funcional): leer `reset_reason` / DSS tras reinicios normales para conocer el formato "sano".

Éxito: tres timelines consistentes y reproducibles; patrón Download Mode conocido.
Fallo del baseline: variabilidad impide definir umbrales → repetir con mejor instrumentación antes de continuar.
Aborto: cualquier anomalía de carga/temperatura o imposibilidad de volver a Android stock.

### Fase 1 — Sonda AVB: solo vbmeta modificado

Estado requerido: UNLOCKED confirmado + Fase 0 completa.

Contenido lógico de la sonda (definición, **no fabricar en esta tarea**):

- Hipótesis de laboratorio: `vbmeta.img` con `VERIFICATION_DISABLED` (`flags=2`), o firma de test válida según política confirmada, conservando la estructura de chain partitions. `flags=1` es exclusivamente `HASHTREE_DISABLED`; `flags=3` combina ambos bits. Ninguna variante está autorizada ni demostrada en Samsung.
- Todas las demás particiones permanecen stock: `boot`, `init_boot`, `vendor_boot`, `dtbo`, system, vendor, etc.

Interpretación de resultados:

| Observación dominante | Lectura más plausible | Acción siguiente |
|---|---|---|
| Boot normal hasta Android (posible warning) | Bootloader tolera vbmeta alterado bajo UNLOCKED | Continuar a Fase 2 |
| Warning roja/naranja persistente y no continúa | Rechazo de política AVB/Samsung | No flashear kernel; auditar unlock/rollback/política; probar firma de test conocida |
| Reboot loop inmediato antes de Android | Rechazo activo o política no tolerante | Recuperar a Download Mode; documentar timing; no interpretar como fallo kernel |
| Ningún cambio visible respecto a stock y Android arranca | Flags ignorados o política permisiva silenciosa | Documentar; repetir con marcador observable antes de asumir éxito |

Éxito: el bootloader acepta o tolera claramente la sonda y el sistema vuelve a estado recuperable.
Fallo: rechazo consistente → detener escalado, investigar política Samsung/rollback.
Aborto: pérdida de Download Mode o comportamiento no recuperable con el procedimiento ensayado.

Recuperación: restaurar `vbmeta.img` stock y verificar hash; confirmar arranque Android normal antes de cerrar la fase.

### Fase 2 — Kernel marker: boot + vbmeta

Solo se autoriza si Fase 1 fue exitosa y documentada.

Contenido lógico:

- `boot.img` con kernel U11 de auditoría, preferiblemente con drivers tempranos críticos integrados (chipid/clocks/MCT/pinctrl/PMU) según el plan general.
- `vbmeta.img` coherente con ese contenido (regenerado/firmado según la política validada en Fase 1).
- `init_boot` y `vendor_boot` **stock en esta fase deliberadamente**: el objetivo aquí es solo observar si ocurre handoff y qué señal produce un kernel distinto, no conseguir userspace. Los fallos ABI del vendor_ramdisk stock se asumen y se documentan como variable contaminante conocida.

Nota crítica: esta fase **no** pretende boot útil. Pretende responder: ¿la transición post-bootloader cambia respecto al baseline? Cualquier señal nueva (consumo, backlight, enumeración efímera) indica que el kernel recibió control aunque luego muera.

Interpretación:

| Resultado | Significado probable |
|---|---|
| Mismo patrón exacto que rechazo AVB de Fase 1 | Handoff no ocurrió o kernel murió instantáneamente; priorizar AVB |
| Nueva fase eléctrica/backlight breve + reset | Kernel ejecutó y falló temprano; priorizar earlycon/sec_debug |
| Gadget USB efímero o estable aparece | Kernel llegó a init USB; éxito parcial alto |
| Sin ninguna diferencia mensurable | Ambiguo; repetir con instrumentación mejorada y post-mortem DSS |

Éxito: obtención de un vector de señales diferenciable, aunque el kernel no sobreviva.
Fallo: ambigüedad total → no escalar imágenes; mejorar observabilidad primero.
Aborto: idéntico criterio global.

### Fases posteriores (fuera de alcance inmediato)

La sustitución coordinada de `init_boot`/`vendor_boot` con perfiles MINIMAL/sec_debug pertenece al experimento completo de first boot descrito en `docs/first-boot-experiment-plan.md`. Este documento solo valida la frontera AVB→kernel.

## 7. Riesgos específicos

| Severidad | Riesgo | Mitigación |
|---|---|---|
| Crítico | Política Samsung desconocida convierte la Fase 1 en un estado difícil de revertir (rollback/Knox). | Sonda mínima, UNLOCKED previo, copias stock verificadas, Download Mode ensayado, aborto inmediato ante anomalía. |
| Crítico | Confundir "AVB rechazó" con "kernel crashea en <50 ms". | Fase 0 obligatoria, comparación de timelines y post-mortem DSS/reset_reason cuando sea accesible. |
| Alto | Señales USB/consumo mal calibradas inducen conclusión falsa. | Mismo cable/host/instrumento, 3 repeticiones, exportar logs timestamped. |
| Alto | Escribir vbmeta-only cambia también expectativas de hashtree/dm-verity en runtime Android. | Interpretar cualquier comportamiento Android anómalo como parte del experimento; restaurar vbmeta stock al cerrar fase. |
| Medio | Warning screens de Samsung difieren de la semántica AOSP documentada. | Tratar color/texto como dato, no como diagnóstico definitivo; apoyarse en USB/tiempo/post-mortem. |
| Medio | Batería baja impide entrar a recovery/download durante recuperación. | Cargar por encima de umbral cómodo antes de empezar; documentar comportamiento con batería baja en Fase 0. |

## 8. Registro mínimo por corrida

Cada intento debe dejar un registro con:

1. Fecha/hora, fase, hash de cada imagen implicada.
2. Estado bootloader declarado y evidencia de ese estado.
3. Timeline: t=0 referencia, eventos USB (attach/detach, VID/PID), picos de corriente, eventos de pantalla.
4. Duración total hasta estado final (Android / warning persistente / reset / timeout).
5. Método y resultado de recuperación (incluyendo hashes tras restaurar).
6. Conclusión separada en: **observaciones**, **interpretación provisional**, **hipótesis descartadas/no descartadas**, **siguiente paso**.

## 9. Respuestas directas a las preguntas del encargo

- **¿Cómo sabemos que AVB falló?** Combinación de: advertencia de verified boot persistente o reboot pre-kernel consistente, ausencia total de cualquier fase nueva post-bootloader frente a baseline, y (si se accede después) falta de evidencia nueva en mecanismos que solo el kernel puede escribir. En estado UNLOCKED, la Fase 1 con vbmeta-only es la sonda diseñada para provocar y clasificar exactamente esto.
- **¿Cómo sabemos que el kernel llegó?** Solo con evidencia de efectos que ocurren después del handoff: nueva fase de consumo/backlight, enumeración de un gadget kernel, o datos nuevos en sec_debug/DSS/last_kmsg recuperados desde otro contexto. La presencia continua del dispositivo del bootloader no cuenta como evidencia de kernel.
- **¿Cómo recuperar si AVB rechaza?** Vía primaria hipotética-pero-ensayable: mantener acceso a Download Mode, restaurar `vbmeta.img` stock desde copia verificada y revalidar boot Android. Si Download Mode no responde con el procedimiento estándar, detener todo escalado y tratar el caso como bloqueante de seguridad, no como dato del kernel.

## 10. Documentación propuesta

- Actualizar `docs/first-boot-experiment-plan.md` tras ejecutar Fase 0/1 para sustituir hipótesis H-AVB-1..3 por observaciones fechadas.
- Crear un archivo de corridas (por ejemplo `reports/first-boot-runlog.md`) usando la plantilla de §8; un registro por intento, sin mezclar conclusiones.
- Referencias cruzadas: `docs/debugging/sec-debug-analysis.md` (recuperación post-mortem), informe ABI U11/U12 (por qué Fase 2 no busca userspace), y `docs/boot-chain/minimal-modification-set.md` cuando exista (para las fases posteriores).
