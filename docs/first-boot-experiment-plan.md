# First Boot Experiment Plan

Fecha de consolidación: 2026-08-24  
Alcance: Samsung Galaxy Tab S9 FE SM-X510, variante U12/EZE4  
Modo del documento: preparación de auditoría. No autoriza flasheo ni modifica artefactos existentes.

## Estado Actual

Las afirmaciones se clasifican como **EVIDENCIA CONFIRMADA** cuando proceden de inspección estática verificada o de artefactos presentes en el repositorio, y como **HIPÓTESIS** cuando requieren validación física.

### Cadena de arranque y AVB

**EVIDENCIA CONFIRMADA**

- `boot.img`, `init_boot.img`, `vendor_boot.img` y `dtbo.img` tienen footers y vbmeta embebidos firmados con `SHA256_RSA4096`. La verificación estática con `avbtool` fue correcta.
- El vbmeta raíz tiene `flags=0` y rollback index global `0`.
- El vbmeta raíz contiene hash descriptors para `boot`, `init_boot`, `vendor_boot` y `dtbo`; además encadena los vbmeta de `dtbo`, `prism` y `optics`.
- `init_boot.img` no contiene kernel. Contiene el ramdisk GKI genérico comprimido con LZ4 legacy.
- `vendor_boot.img` contiene vendor ramdisk LZ4, bootconfig y un DTB comprimido con formato propietario Samsung.
- Bajo bootloader LOCKED, cambiar cualquiera de las particiones cubiertas por hash invalida el descriptor firmado. En ese estado el kernel propio no debe considerarse ejecutable.

**HIPÓTESIS**

- El bootloader Samsung aplica exactamente la política AOSP esperada en estado UNLOCKED y tolera un vbmeta regenerado con verificación deshabilitada.
- No existen comprobaciones Samsung adicionales relevantes más allá de AVB, Knox/RPMB o políticas específicas del dispositivo.
- El bootloader selecciona el overlay DTBO según revisión de hardware y compone parámetros finales de línea de mandatos no observables por completo en las imágenes stock.

### ABI entre kernel U11 y vendor U12/EZE4

**EVIDENCIA CONFIRMADA**

- El kernel U11 construido reporta vermagic `5.15.180 SMP preempt mod_unload modversions aarch64`.
- Los inventarios stock apuntan a un entorno `5.15.189-android13-3`; no hay compatibilidad de vermagic directa.
- Ambos lados declaran `CONFIG_MODVERSIONS=y`. El árbol U11 tiene `Module.symvers`, pero no hay tabla CRC comparable del kernel stock ni módulos stock binarios suficientes para demostrar compatibilidad ABI.
- La mezcla del vendor_ramdisk stock U12 con el kernel U11 es NO-GO hasta disponer de evidencia CRC/símbolos.
- En el build U11 actual, los drivers tempranos críticos `EXYNOS_CHIPID_V2`, reloj S5E8835, MCT v3, watchdog y pinctrl Samsung son modulares, no built-in. La base GIC sí es built-in.
- `CONFIG_MODULE_SIG_PROTECT=y`, pero `CONFIG_MODULE_SIG_FORCE` no está activo y `CONFIG_SECURITY_LOCKDOWN_LSM` no está activo en el build U11 auditado. Por tanto, el rechazo incondicional por firma no es la conclusión correcta; el bloqueante principal es vermagic/CRC/CFI.

**HIPÓTESIS**

- Recompilar el kernel U11 con chipid, relojes, timer, pinctrl, PMU y soporte básico de reinicio integrados puede permitir alcanzar `/init` sin depender del cierre ABI del vendor ramdisk stock.
- CFI y diferencias binarias pueden producir fallos tardíos aunque los símbolos coincidan.

### Device tree y arranque pre-printk

**EVIDENCIA CONFIRMADA**

- `sec_debug_next` está definido en los overlays, no en el DTB base: dirección física `0x91200000`, tamaño `0x200000`, propiedad `no-map`.
- Existen regiones Samsung/DSS ya cableadas, incluidas `log_kernel` en `0xFD010000`, `wdtmsg` en `0x8ADB11000`, historial ITMON y regiones adicionales de depuración.
- PSCI es versión 1.0 con conducción SMC. Las ocho CPU usan PSCI como método de arranque/apagado.
- El controlador global documentado es GIC-400/GICv2 en `0x12B00000`. No hay ITS.
- El arch_timer ARMv8 declara `clock-frequency = <26000000>` y la línea stock fuerza `clocksource=arch_sys_counter`.
- El oscilador principal declarado es de 52 MHz y el CMU central usa compatible `samsung,s5e8835-clock`.
- El diff conocido entre U11 y EZE4 se limita a cuatro propiedades asociadas a EMS, MFC y SCSC/Wi-Fi. Ninguna pertenece al conjunto memoria/PSCI/GIC/timer/clocks.
- El cmdline stock observable usa `console=ram` y no incluye `earlycon=`. `CONFIG_SERIAL_EARLYCON=y` y `CONFIG_SERIAL_SAMSUNG=y` están compiladas en U11.

**HIPÓTESIS**

- Los cuatro diffs U11→EZE4 son irrelevantes antes del primer printk. Esta conclusión es sólida pero el análisis semántico del diff no elimina toda incertidumbre residual.
- Sin parámetro efectivo `earlycon=` u otro mecanismo Samsung temprano, un kernel vivo puede permanecer silencioso incluso si supera la inicialización básica.
- El bootloader normalmente deja UART/clock gates en un estado usable, pero no hay prueba física en este dispositivo.

### Observabilidad Samsung y sec_debug

**EVIDENCIA CONFIRMADA**

- `sec_debug`, DSS y `reset_reason` están representados por nodos DT y por módulos construidos en el árbol U11.
- El perfil USB/initramfs actual no carga el conjunto completo necesario para activar sec_debug/DSS.
- La recuperación post-mortem requiere un contexto secundario: shell USB ACM, Android stock funcional, modo recovery/download accesible o lectura posterior de almacenamiento/región física.

**HIPÓTESIS**

- Un perfil reducido de 12 módulos puede activar sec_debug y DSS sin reservar memoria nueva ni modificar DT.
- Tras una falla posterior, `sec_debug_next`, `log_kernel`, `wdtmsg` o `/proc/last_kmsg` conservarán evidencia suficiente para diagnosticar el primer boot.

Fuente detallada: [`docs/debugging/sec-debug-analysis.md`](../debugging/sec-debug-analysis.md).

### Initramfs

**EVIDENCIA CONFIRMADA**

- Existe un perfil MINIMAL funcional de aproximadamente 674 KiB LZ4, frente a aproximadamente 2.49 MiB de ramdisk stock en `init_boot`.
- El perfil DEBUG/USB actual contiene 45 módulos y ocupa aproximadamente 2.9 MiB LZ4, por lo que no cabe dentro del tamaño stock.
- El cierre propuesto para sec_debug tiene 12 módulos únicos y menos de 800 KiB raw. Su tamaño final LZ4 todavía no ha sido medido.

**HIPÓTESIS**

- El perfil sec_debug escalonado cabe en `init_boot` junto al busybox base.
- Puede reducirse el cierre USB actual eliminando dependencias no obligatorias, pero esa poda requiere experimentación incremental.

## Incertidumbres

| ID | Incertidumbre | Impacto operativo |
|---|---|---|
| U1 | Estado real de bootloader: OEM unlock activado, UNLOCKED confirmado y política Samsung tras unlock. | Determina si cualquier kernel propio puede recibir control. Es condición previa absoluta. |
| U2 | Parámetro exacto de consola temprana y estado físico de UART/USB al handoff. | Sin señal temprana, distinguir fallo AVB de fallo pre-driver depende solo de consumo, resets y post-mortem. |
| U3 | Comportamiento real del bootloader ante imágenes modificadas con `vbmeta --flags 1`. | Define si el experimento mínimo llega a la primera instrucción del kernel. |
| U4 | Cierre exacto de dependencias runtime de sec_debug/DSS sobre DTB+overlay EZE4. | Una lista corta puede fallar por dependencia indirecta ausente; una lista amplia aumenta riesgo de panic temprano. |
| U5 | Necesidad real de pinctrl-samsung-core y otros drivers plataforma para probes de sec_debug/DSS. | Puede provocar probes fallidos silenciosos aunque los `.ko` carguen. |
| U6 | Tamaño LZ4 real del perfil sec_debug escalonado. | Condiciona empaquetado final de `init_boot` o vendor ramdisk propio. |
| U7 | Cmdline final compuesto por el bootloader y aplicación garantizada del overlay correcto. | Puede alterar observabilidad y reserva de `sec_debug_next`. |
| U8 | Señales USB y de consumo específicas de este hardware. | La matriz diagnóstica es marco experimental, no predicción validada. |
| U9 | Compatibilidad CFI/binaria más allá de CRC y vermagic. | Riesgo de fallo tardío difícil de interpretar sin logs. |

## Riesgos

### Críticos

1. **C1 — Experimento incompleto de boot chain:** no basta sustituir `boot.img` y vbmeta. Con kernel U11, también hay que evitar entregar el vendor_ramdisk stock incompatible. El alcance mínimo realista afecta al menos `boot.img`, `vendor_boot.img` y/o `init_boot.img`, además de vbmeta.
2. **C2 — Ausencia de consola temprana probada:** el cmdline stock no activa `earlycon`. Este es el mayor bloqueante de observabilidad en tiempo real y debe tratarse como parte del diseño, no como detalle posterior.
3. **C3 — Estado de bootloader desconocido:** sin confirmar UNLOCKED y su efecto real en este modelo, ningún intento físico cumple criterio de seguridad informativa.

### Importantes

1. **I1 — Firma sobrestimada, ABI subestimada:** el problema principal es CRC/vermagic/CFI, no un rechazo automático por firma en el build U11 auditado.
2. **I2 — Carga monolítica de sec_debug peligrosa:** cargar los 12 módulos de golpe puede perder evidencia si un driver con `panic()` en probe falla. La carga debe escalonarse.
3. **I3 — Dependencias plataforma ocultas:** el closure estático corto puede omitir módulos necesarios para probes reales.
4. **I4 — Señales no validadas:** la matriz USB/consumo es hipótesis estructurada y debe calibrarse primero contra el firmware stock.
5. **I5 — Contradicción pinctrl:** el informe ABI identifica pinctrl como bloqueante modular y el borrador sec_debug no lo incluía. Debe resolverse con auditoría de closures antes del paquete final.
6. **I6 — Regiones reservadas y firmware:** usar direcciones fijas sin conocer el mapa vivo puede confundir fallo de driver con colisión o acceso inválido.

### Menores

1. Corregir referencias tipográficas heredadas, como `ignore_loglevel`, al transcribir mandatos operativos.
2. Evitar incluir `sec_class` sin justificar necesidad concreta en el closure final.
3. No presentar el diff U11→EZE4 como absoluto cuando proviene de comparación parcialmente automatizada.

## Experimento Mínimo

Este es el diseño objetivo. La sesión actual no genera imágenes ni scripts definitivos. Antes del intento físico deben completarse los bloqueantes listados al final.

### Objetivo único del primer boot

Determinar si el kernel U11 recibe control desde el bootloader y alcanza userspace mínimo, maximizando la posibilidad de obtener evidencia post-mortem mediante infraestructura Samsung existente.

No es objetivo del primer intento tener USB, display, almacenamiento completo ni Linux normal.

### Precondiciones obligatorias

1. Confirmar visualmente que OEM unlocking está habilitado y que el dispositivo está en estado UNLOCKED.
2. Registrar advertencia visible al arrancar y acceso estable a Download Mode con firmware stock.
3. Medir baseline stock sin modificar nada:
   - corriente USB durante arranque;
   - tiempos aproximados de fases visibles;
   - enumeraciones USB observables;
   - comportamiento de backlight/pantalla;
   - tiempo total hasta Android o reset.
4. Guardar copias intactas de todas las imágenes stock y hashes correspondientes.

### Alcance de imágenes

El experimento necesita un conjunto coherente, no una sustitución única:

| Imagen | Contenido objetivo | Motivo |
|---|---|---|
| `boot.img` | Kernel U11 reproducible. Preferible con chipid, clocks S5E8835, MCT v3, PMU, pinctrl core y soporte básico de reboot integrados. | Reduce dependencia crítica del vendor ramdisk stock e intenta llegar a `/init`. |
| `vendor_boot.img` | Vendor ramdisk propio mínimo o vacío controlado; DTB EZE4 stock preservado; bootconfig controlado. | Elimina el vendor_ramdisk U12 incompatible sin descartar el DT base/overlay entregado por bootloader. |
| `init_boot.img` | Perfil MINIMAL + paquete sec_debug escalonado, medido y autocontenido. | Proporciona marcadores de userspace y activa observabilidad post-mortem. |
| `vbmeta.img` | Generación de auditoría con verificación deshabilitada o firma de test, según política confirmada tras unlock. | Permite que las imágenes modificadas sean aceptadas bajo UNLOCKED. |

`dtbo.img` debe mantenerse stock salvo hallazgo posterior que demuestre incompatibilidad. Cambiar DT innecesariamente contaminaría el resultado.

### Initramfs sec_debug escalonado

Usar como referencia el perfil MINIMAL existente, creando un perfil experimental nuevo sin editar scripts vigentes.

Fase de arranque propuesta dentro de `/init`:

1. Montar `proc`, `sysfs` y `devtmpfs`.
2. Emitir marcadores de fase en todas las salidas disponibles.
3. Cargar grupo A de bajo riesgo:
   - `exynos-pmu-if`;
   - `dss`;
   - `sec_debug_dprt`;
   - `sec_debug_base_early`.
4. Pausa corta, registrar éxito/fallo y comprobar sysfs/procs creados.
5. Solo si el grupo A no reinicia, cargar grupo B:
   - `exynos-chipid_v2`;
   - `pinctrl-samsung-core` si el closure final lo confirma;
   - `sec_debug_mode`;
   - `sec_debug_extra_info`.
6. Solo si el grupo B sobrevive, cargar grupo C:
   - `sec_debug_reset_reason`;
   - `exynos-reboot`;
   - `hardlockup-watchdog`;
   - `sec_reboot`;
   - `sec_debug`.
7. Volcar estado detectado a consola/buffer y entrar en shell de rescate o espera controlada.

Cada paso debe registrar nombre de módulo, código de retorno y rutas sysfs observadas antes de continuar.

### Línea de mandatos experimental

Ejecutar dos variantes de auditoría local antes de decidir el paquete físico:

**Variante A — máxima compatibilidad:**

```text
console=ram clocksource=arch_sys_counter ignore_loglevel
```

**Variante B — prueba temprana de consola:**

```text
console=ram clocksource=arch_sys_counter ignore_loglevel earlycon=samsung,0x13800000
```

La dirección `0x13800000` corresponde al nodo UART documentado en el DT auditado, pero el formato exacto aceptado por el driver U11 debe confirmarse en fuente/build antes de flashear. Si no se valida, la primera prueba física debe usar la variante A y depender de sec_debug/consumo.

Añadir parámetros propios con prefijo estable, por ejemplo `gts9fe.first_boot=1`, para identificar el experimento desde runtime/post-mortem.

### Protocolo de observación

Durante el primer boot:

1. Grabar vídeo continuo de pantalla/backlight.
2. Capturar tráfico/enumeración USB con host Linux y log timestamped.
3. Medir corriente USB con resolución suficiente para distinguir fases gruesas.
4. Definir timeout máximo sin señal y volver a Download Mode usando combinación física documentada.
5. Tras cada reset, intentar recuperación por contexto secundario disponible: Android stock, recovery, download tools o lectura posterior de región persistente.
6. Documentar siempre timestamps relativos desde inserción de cable o pulsación de power.

## Señales Esperadas

Todas las señales son **HIPÓTESIS EXPERIMENTALES** hasta calibrarse en este dispositivo concreto.

| Señal observada | Interpretación probable | Confianza | Acción de diagnóstico |
|---|---|---|---|
| Warning naranja/roja persiste y nunca desaparece. | Fallo/rechazo en boot chain; kernel posiblemente no recibe control. | Alta conceptual, media en Samsung. | Verificar estado UNLOCKED, vbmeta y descriptores. |
| Download Mode sigue accesible siempre. | Bootloader sano y independiente del kernel. | Alta. | Repetir con logging y cambiar una variable por vez. |
| Interfaz bootloader aparece y desaparece; después no aparece nada. | Handoff ocurrió; fallo muy temprano o kernel vivo silencioso. | Media. | Comparar consumo y probar variante A/B de cmdline. |
| Aparece gadget ACM estable. | Kernel, UDC/PHY y userspace alcanzaron configuración USB. | Media-alta si el perfil USB está presente; baja en perfil sec_debug mínimo. | Abrir shell y extraer logs/módulos cargados. |
| Aparece dispositivo USB breve y desaparece. | Kernel avanzó hacia gadget y crasheó/reset. | Media-baja. | Priorizar recuperación sec_debug/DSS y correlacionar consumo. |
| Consumo plano tipo bootloader. | Probablemente no hubo handoff efectivo. | Hipótesis. | Baseline stock obligatorio para comparar patrón. |
| Spike seguido de caída/reset. | Ejecución temprana seguida de panic/watchdog/fallo de memoria. | Hipótesis. | Recuperar reset_reason, wdtmsg y last_kmsg. |
| Reset cíclico con periodo estable. | Panic automático, watchdog o fallo determinista temprano. | Media. | Variar cmdline/initramfs y medir cambio de periodo. |
| Backlight se enciende y apaga abruptamente. | Fase display alcanzada o reset; ambiguo sin logs. | Baja. | No usar como señal única. |
| Ningún síntoma cambia entre variantes. | Posible rechazo previo al kernel o consola/driver inactivo. | Media. | Revisar boot chain antes de seguir depurando kernel. |

## Interpretación de Resultados

```text
¿El dispositivo entra en Download Mode?
├─ NO
│  └─ Detener. Fallo de bootloader/power/storage o protocolo incorrecto.
│     Acción: recuperar con combinación oficial y documentar nivel de brick.
│
└─ SÍ
   ¿Arranque stock baseline reproduce patrón conocido?
   ├─ NO
   │  └─ Resolver entorno de medición o estado del dispositivo antes de probar kernel.
   │
   └─ SÍ
      ¿Warning UNLOCKED aparece con conjunto experimental?
      ├─ NO
      │  └─ Fallo boot chain/vbmeta/política Samsung.
      │     Acción: auditar vbmeta, slots y política unlock; no culpar aún al kernel.
      │
      └─ SÍ
         ¿Hay transición distinta tras warning?
         ├─ NO
         │  └─ Kernel no recibió control o murió en primeras instrucciones.
         │     Acción: verificar entry/load addresses, DTB entregado y estado EL1/EL2.
         │
         └─ SÍ
            ¿Consumo/enumeración muestra nueva fase?
            ├─ NO
            │  └─ Fallo pre-printk o kernel silencioso.
            │     Acción: recuperar sec_debug/DSS; repetir solo cambiando earlycon/cmdline.
            │
            ├─ FASE BREVE + RESET
            │  └─ Kernel corrió y falló antes de userspace/gadget estable.
            │     Acción: clasificar con wdtmsg/reset_reason/last_kmsg y revisar timers/GIC/DT.
            │
            ├─ GADGET ACM ESTABLE
            │  └─ Éxito parcial alto: userspace/controlador USB alcanzados.
            │     Acción: extraer dmesg, cmdline, iomem, módulos y estado sec_debug.
            │
            └─ RESET DESPUÉS DE MARCADORES INITRAMFS
               └─ Userspace alcanzado; fallo en fase/module probe.
                  Acción: aislar último grupo cargado y validar closure/pinctrl/DT.
```

Regla general: un resultado negativo solo se considera concluyente si baseline stock, estado unlock, imágenes usadas y método de recuperación quedaron registrados.

## Siguiente Decisión Después del Primer Intento

### Resultado 1 — Rechazo evidente de boot chain

Prioridad:

1. Auditar política real Samsung en UNLOCKED.
2. Probar vbmeta de test conocido válido bajo esta política.
3. Confirmar slot activo y qué imagen lee realmente el bootloader.

No continuar ajustando kernel hasta que una imagen marcadora pueda recibir control.

### Resultado 2 — Handoff pero silencio total

Prioridad:

1. Recuperar cualquier contenido de sec_debug/DSS/reset_reason.
2. Repetir con variante A/B de cmdline, cambiando solo ese campo.
3. Auditar formato exacto de `earlycon` y estado de UART clocks en el kernel U11.
4. Considerar instrumentación mínima adicional solo si post-mortem no aporta datos.

### Resultado 3 — Reset temprano antes de userspace

Prioridad:

1. Clasificar reset reason/watchdog.
2. Validar DTB/DTBO aplicado y regiones reservadas vivas.
3. Reducir variables: kernel sin initramfs opcional, luego MINIMAL, luego sec_debug.
4. Convertir drivers críticos modulares a built-in si los `.ko` impiden la fase temprana.

### Resultado 4 — Userspace alcanzado

Prioridad:

1. Extraer evidencia completa: `dmesg`, `cmdline`, `/proc/iomem`, sysfs, módulos cargados y errores.
2. Confirmar si sec_debug quedó realmente activo y dónde expone datos.
3. Pasar de MINIMAL a perfil sec_debug completo de forma incremental.
4. Solo después abordar USB ACM como canal permanente.

### Resultado 5 — Falla en carga de módulos

Prioridad:

1. Separar error de formato/vermagic, símbolo/CRC, firma, probe o dependencia.
2. Reconstruir closure con `modules.dep` completo y probar grupos aún más pequeños.
3. Corregir la contradicción pinctrl con evidencia de probe real.

## Bloqueantes Pendientes

Estos puntos impiden pasar hoy al primer intento físico:

1. **Confirmar y registrar estado UNLOCKED/OEM unlock**, incluyendo advertencia visible y acceso a Download Mode.
2. **Resolver mecanismo de consola temprana**: validar sintaxis exacta de `earlycon` en el driver U11 y decidir si existe alternativa Samsung útil.
3. **Definir composición completa de tres piezas**: kernel/config final, vendor_boot propio con DT stock y `init_boot` propio. No usar el vendor_ramdisk stock U12 con kernel U11.
4. **Auditoría de closures sec_debug/DSS**: incluir dependencias plataforma reales, resolver pinctrl y eliminar supuestos no verificados.
5. **Medición real de tamaño LZ4** del perfil MINIMAL + sec_debug escalonado, sin generar imagen flasheable todavía.
6. **Calibrar baseline stock** de consumo, USB y pantalla con método repetible y timestamps.
7. **Validar política vbmeta tras unlock** en este modelo antes de asumir que `--flags 1` es suficiente o permitido.
8. **Preparar procedimiento seguro de recuperación** desde cualquier resultado: timeout, entrada a Download Mode y restauración stock verificada por hash.
9. **Documentar plantilla de registro del experimento** con hipótesis, variables, observaciones y conclusión separadas.

## Referencias

- [`docs/debugging/sec-debug-analysis.md`](debugging/sec-debug-analysis.md) — auditoría sec_debug, DSS, DT y recuperación.
- [`reports/2026-08-24-crash-logging-audit-u11.md`](../reports/2026-08-24-crash-logging-audit-u11.md) — auditoría previa de logging y crash recovery.
- [`docs/hardware-observation-plan.md`](hardware-observation-plan.md) — plan anterior de observación hardware.

Informes verbales consolidados de esta sesión:

- Agente 2 — cadena AVB/boot y matriz de diagnóstico USB.
- Agente 3 — ABI U11/U12, módulos críticos y firma.
- Agente 4 — reserved-memory, PSCI, GIC, timers, clocks y diffs DT.
- Agente 5 — perfiles initramfs MINIMAL, DEBUG/USB y SEC_DEBUG.
- Agente 6/9 — revisión independiente y correcciones críticas C1/C2 e I1–I5.
