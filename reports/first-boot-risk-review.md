# Independent Risk Review — First Boot Preparation

Fecha: 2026-08-24  
Objetivo: SM-X510 Wi-Fi, firmware físico `X510XXUCEZE4` / U12 / EZE4  
Candidato actual: kernel OSRC U11 `X510XXSBDZB4`, Linux 5.15.180  
Modo: revisión independiente de riesgos. Sólo lectura del repositorio. No se modificaron scripts, código ni imágenes.

## Resumen ejecutivo

El proyecto tiene una base documental fuerte y una puerta física coherente en **NO-GO**, pero la fase reciente introdujo tres riesgos importantes:

1. **Contradicción operativa entre documentos**: `docs/hardware-observation-plan.md` todavía recomienda preparar `earlycon`, `ramoops` y caminos orientados al primer flasheo con un tono más avanzado que el veredicto vigente de `PROJECT_STATUS.md`, `docs/12-preflight-primera-prueba.md` y la auditoría ABI. Sin marcarlo explícitamente como documento antiguo, puede ser seguido por error.

2. **El plan actual contiene una sintaxis inválida de `earlycon`**: propone `earlycon=samsung,0x13800000`, pero el driver auditable registra el nombre `exynos4210` para el compatible `samsung,exynos4210-uart`. Además, UART0 está `disabled`, usa modo USI v2 y depende de configuración previa del bootloader y pines físicos no demostrados. Por tanto, ausencia de UART no puede interpretarse como prueba de que el kernel no arrancó.

3. **La firma de módulos fue mal caracterizada en revisiones anteriores**: en el árbol U11 auditado, `CONFIG_MODULE_SIG_PROTECT=y` hace que la aplicación de `sig_enforce` se compile como `false`. Los módulos sin firma válida no son bloqueados por esa opción; se cargan con advertencia/taint. El bloqueante real sigue siendo vermagic, CRC de `MODVERSIONS`, diferencias binarias y CFI, especialmente frente a módulos stock U12.

No existe todavía una ruta de recuperación garantizada. El mejor camino disponible es restaurar el firmware oficial completo desde la copia local verificada mediante Download Mode, pero ese procedimiento no ha sido ensayado en esta unidad. El desbloqueo probablemente borra datos y puede activar de forma irreversible el Warranty Bit de Knox; las consecuencias exactas en este modelo y versión no están confirmadas.

Mientras esas incertidumbres permanezcan abiertas, cualquier intento físico prematuro convertiría un problema reversible de ingeniería en un riesgo innecesario de pérdida de datos o de dispositivo.

## Hallazgos críticos

### C1 — Contradicción entre el plan antiguo y la puerta física vigente

**Problema.**

`docs/hardware-observation-plan.md` recomienda preparar:

- `earlycon=exynos4210,mmio32,0x13800000`;
- reservar una región nueva para `ramoops`;
- alternar imágenes experimentales;
- usar señales USB/consumo para decidir si el kernel llegó a ejecutarse.

En cambio, los documentos y auditorías más recientes establecen:

- `NO-GO` hasta validar desbloqueo, recuperación, observabilidad y política AVB;
- no añadir `ramoops` ni memoria nueva;
- priorizar `sec_debug`/DSS existente;
- tratar consumo USB y enumeración como hipótesis por calibrar.

Evidencia principal:

- `docs/hardware-observation-plan.md`
- `reports/2026-08-23-u11-eze4-binary-abi-audit.md`
- `docs/12-preflight-primera-prueba.md`
- `reports/2026-08-24-crash-logging-audit-u11.md`
- `docs/first-boot-experiment-plan.md`

**Riesgo.**

Un ingeniero que lea primero el plan antiguo podría preparar `ramoops`, activar consola UART o diseñar un intento de arranque sin pasar por las puertas actuales de seguridad.

**Clasificación.**

Hipótesis operativa peligrosa mientras no se marque el documento antiguo como obsoleto o supersedido.

**Acción mínima segura.**

Documentar explícitamente qué partes de `hardware-observation-plan.md` quedan históricas y cuáles siguen válidas. Esto es una corrección de documentación, no una autorización para flashear.

---

### C2 — Sintaxis inválida de `earlycon` y canal UART no demostrado

**Hecho verificado en fuente.**

En el driver Samsung auditable:

- `OF_EARLYCON_DECLARE(exynos4210, "samsung,exynos4210-uart", ...)` registra el nombre `exynos4210`.
- El nodo real UART0 usa compatible `samsung,exynos-uart`, no el compatible registrado por `OF_EARLYCON_DECLARE`.

Por tanto, la variante propuesta en `docs/first-boot-experiment-plan.md`:

```text
earlycon=samsung,0x13800000
```

no es la forma genérica correcta. La forma coherente con el driver sería:

```text
earlycon=exynos4210,mmio32,0x13800000
```

Esta era precisamente la cadena usada en `docs/hardware-observation-plan.md`, lo que confirma una regresión documental.

**Riesgos adicionales no resueltos.**

UART0 en el DT stock EZE4/U12:

- dirección `0x13800000`;
- `status = "disabled"`;
- pines `gpq0-0` y `gpq0-1`;
- propiedad `samsung,usi-serial-v2`;
- referencia a configuración USI en `sysreg_peri_usi`;
- relojes y gates dependientes del CMU.

El earlycon genérico puede escribir directamente en MMIO aunque el nodo esté `disabled`, pero no configura por sí solo pinmux, modo USI ni clock gates. Depende de que el bootloader deje el hardware usable. Además, no hay evidencia física de que esos pines sean accesibles sin abrir la tablet.

**Conclusión operativa.**

Aunque se corrija la sintaxis, un resultado con cero bytes UART seguirá siendo ambiguo. Puede significar:

1. el kernel nunca recibió control;
2. el kernel murió antes de inicializar earlycon;
3. earlycon escribió correctamente pero el canal físico no está disponible;
4. el bootloader dejó UART, USI o clocks en estado no usable.

Ningún intento debe usar “no hay UART” como señal única de fallo pre-kernel.

---

### C3 — Firma de módulos: riesgo anterior sobrestimado y riesgo ABI persistente

**Corrección importante.**

Una revisión previa afirmó que `CONFIG_MODULE_SIG_PROTECT=y` impide cargar módulos no firmados bajo lockdown. En el árbol U11 auditable eso no es correcto.

Evidencia directa en `kernel.config`:

```text
CONFIG_MODULE_SIG=y
# CONFIG_MODULE_SIG_FORCE is not set
CONFIG_MODULE_SIG_PROTECT=y
```

Evidencia directa en `kernel/module.c` del árbol:

```c
#if defined(CONFIG_MODULE_SIG) && !defined(CONFIG_MODULE_SIG_PROTECT)
static bool sig_enforce = IS_ENABLED(CONFIG_MODULE_SIG_FORCE);
...
#else
#define sig_enforce false
#endif
```

Con `CONFIG_MODULE_SIG_PROTECT=y`, la aplicación de `sig_enforce` se compila como `false`. El rechazo por falta de firma no ocurre por esa ruta; los módulos pueden cargarse con advertencia/taint.

**Qué significa.**

- La firma no es hoy el principal bloqueante para módulos construidos con el mismo kernel U11.
- Tampoco es válido asumir que los módulos stock U12 puedan cargarse: el desfase `5.15.180` frente a `5.15.189-android13-3`, los CRC de `MODVERSIONS`, los tipos bajo `CONFIG_CFI_CLANG=y` y las diferencias de build siguen siendo bloqueantes reales.
- La mezcla kernel U11 con vendor_ramdisk U12 sigue siendo `NO-GO`.

**Riesgo residual.**

El comportamiento runtime puede tener hooks Samsung adicionales. Esta conclusión corrige el análisis estático dominante, pero debe confirmarse con la primera observación real de `modprobe`.

---

### C4 — Anti-rollback, Knox y recuperación tratados con demasiada ligereza

**Estado AVB observable.**

El `vbmeta.img` stock EZE4 muestra:

```text
Rollback Index: 0
Rollback Index Location: 0
Flags: 0
```

y las ubicaciones encadenadas conocidas son:

```text
dtbo   -> Rollback Index Location 1
prism  -> Rollback Index Location 2
optics -> Rollback Index Location 3
```

Con índices observados en `0`, un vbmeta de prueba que mantenga los mismos índices no debería, por sí solo, subir el piso anti-rollback de AVB. Un intento fallido tampoco sube rollback automáticamente: el incremento ocurre cuando el dispositivo acepta metadatos con valores mayores, típicamente durante actualización oficial.

**Incógnitas Samsung no cubiertas por AVB genérico.**

No está demostrado si el bootloader aplica además:

- contador binario del bootloader;
- protección por fecha de security patch;
- almacenamiento RPMB adicional;
- validaciones Knox propias;
- comprobaciones sobre `bootloader`, `ldfw`, `tzsw`, `prism` u otras particiones firmadas.

El vbmeta stock también expone propiedades como:

```text
com.android.build.boot.os_version = '13'
com.android.build.system.os_version = '16'
com.android.build.*.security_patch = '2026-05-05'
```

Si se genera un vbmeta experimental, conservar índices y evitar rebajar o eliminar propiedades relevantes es una precaución obligatoria hasta entender la política real del modelo.

**Knox/eFuse/desbloqueo.**

La documentación propia del repositorio afirma correctamente que desbloquear normalmente borra datos y puede activar de forma irreversible el Warranty Bit de Knox. Lo que no está confirmado es:

- si este SM-X510 Wi-Fi permite desbloqueo en esta región/build;
- el procedimiento exacto en Android 16 / One UI 8.5;
- si existe temporizador obligatorio;
- qué funcionalidades Knox se pierden de forma permanente;
- cómo reacciona exactamente el bootloader tras unlock con vbmeta regenerado.

Sin consentimiento explícito del propietario y registro de consecuencias, ningún paso de desbloqueo es aceptable.

**Recovery path actual.**

Existe firmware oficial completo local y con hash verificado, pero eso no es una ruta garantizada. Falta ensayar, sólo lectura o en condiciones controladas:

1. entrada reproducible a Download Mode;
2. identificación del dispositivo por el equipo host;
3. herramienta y protocolo compatibles con U12/EZE4;
4. procedimiento completo de restauración oficial con BL/AP/CSC coherentes;
5. validación posterior del dispositivo restaurado.

Además, un kernel experimental puede no controlar carga/batería. Una sesión larga puede agotar la batería justo en un estado donde el dispositivo no pueda entrar a Download Mode. Este riesgo térmico/eléctrico no aparece suficientemente destacado en el plan vigente.

**Regla derivada.**

No hay recuperación “garantizada”; sólo hay una ruta de recuperación probable y todavía no ensayada. Mientras sea así, el primer intento físico sigue bloqueado.

## Hallazgos importantes

### I1 — Perfiles initramfs: tamaños y closures aún no cerrados

Los hechos medidos muestran tensiones entre objetivos:

- el perfil USB actual no cabe en el espacio del ramdisk stock de `init_boot`;
- el perfil SEC_DEBUG estimado entre ~0,9 y ~1,2 MiB LZ4 no ha sido medido;
- los closures cortos pueden omitir dependencias de plataforma;
- los grupos escalonados incluyen módulos como chipid, pinctrl o reboot cuyo probe puede fallar de forma visible o incluso causar reset.

Esto no autoriza construir imágenes todavía. Antes de cualquier GO deben completarse auditorías locales:

1. closure estático completo por grupo;
2. medición real de cpio/LZ4 en directorios temporales;
3. simulación del orden de `modprobe`;
4. decisión explícita sobre `pinctrl-samsung-core` y dependencias de PMU/DSS.

### I2 — sec_debug no es una red de seguridad universal

El sistema Samsung es valioso, pero su alcance real es limitado:

- DSS y los handlers empiezan a capturar después de que los módulos cargan y hacen probe;
- un fallo antes de userspace puede no dejar nada recuperable;
- recuperar DRAM requiere un segundo contexto vivo;
- `/dev/block/by-name/debug` existe como ruta en DT, pero su presencia, permisos y semántica de escritura no están probadas;
- `panic_to_wdt=0` está presente por defecto en el análisis actual.

Por tanto, sec_debug mejora la probabilidad de diagnóstico, pero no convierte un fallo temprano en evidencia garantizada.

### I3 — El diff DT U11→EZE4 es sólido, pero no absoluto

Los tres overlays Wi-Fi r00/r01/r04 son idénticos byte a byte entre U11 y stock EZE4. Eso es evidencia fuerte.

Sin embargo, el comparador semántico del DTB base reporta estado incompleto, con 14 referencias externas sin resolver y limitaciones de extracción automatizada. Decir “ninguna diferencia afecta pre-printk” es una hipótesis bien fundamentada, no una equivalencia formal completa.

La estrategia prudente sigue siendo mantener DTB y DTBO stock salvo necesidad demostrada, en lugar de generalizar equivalencia.

### I4 — Las señales USB/consumo son hipótesis, no predicciones calibradas

Los umbrales como “menos de ~20 mA” o “más de 100 mA sostenido” no provienen de mediciones de esta unidad. Tampoco se ha observado todavía:

- patrón real de Download Mode;
- transición bootloader→kernel;
- aparición o desaparición del gadget ACM;
- efecto de un crash temprano sobre enumeración USB;
- comportamiento de backlight/pantalla con kernel propio.

Sólo después de un baseline stock repetible podrán interpretarse las mismas señales durante un boot experimental.

### I5 — Operación de particiones, slots y vbmeta insuficientemente especificada

Antes de cualquier futuro intento, el plan debe definir:

- slot activo real;
- si se escribe un slot, ambos, o se evita manipulación de slots;
- preservación exacta del tamaño de partición y padding;
- tratamiento del bootconfig de `vendor_boot`;
- conservación de rollback index y propiedades relevantes en vbmeta experimental;
- prohibición explícita de tocar `bootloader`, `tzsw`, `ldfw`, `prism`, `optics` u otras particiones de confianza.

La ambigüedad aquí puede transformar un experimento recuperable en un estado confuso de arranque.

## Hallazgos menores

### M1 — Typo heredado en informe de crash logging

`reports/2026-08-24-crash-logging-audit-u11.md` menciona transitoriamente `ignore_logline`; el parámetro correcto es `ignore_loglevel`. El propio texto lo reconoce, pero debe corregirse antes de usarlo como referencia operativa.

### M2 — Inclusión de `sec_class` poco justificada

Algunas propuestas lo colocan primero por ser infraestructura Samsung, pero no se demostró que forme parte del closure duro mínimo. Debe incluirse sólo si la auditoría de dependencias lo exige.

### M3 — Recomendación vieja de ramoops sigue activa en documento antiguo

Ya está cubierto por C1, pero merece mención específica porque contradice directamente la decisión actual de no crear reservas nuevas.

### M4 — Estado DWC3 Exynos debe describirse con precisión

El `.config` U11 muestra `CONFIG_USB_DWC3_EXYNOS=y`. Algunas notas intermedias hablan del controlador como módulo. Para el diseño final debe distinguirse claramente entre glue built-in, capas genéricas y funciones gadget.

## Información crítica ausente

Antes de convertir el plan en intento físico faltan datos concretos:

1. estado real de OEM unlocking y política exacta de desbloqueo en esta unidad;
2. advertencia visual y texto exacto tras unlock;
3. comportamiento Samsung tras vbmeta regenerado o con verificación deshabilitada;
4. cmdline final entregado por el bootloader;
5. slot activo y mapa de particiones en ejecución;
6. revisión de hardware y DTBO realmente aplicado;
7. accesibilidad física de UART0/USI sin desmontar;
8. VID/PID y tiempos de enumeración en Download Mode;
9. patrón eléctrico stock calibrado;
10. comportamiento de carga/batería bajo kernel de rescate;
11. existencia y permisos de `/dev/block/by-name/debug`;
12. respuesta real de `modprobe` ante módulos U11 sin firma válida;
13. política Samsung adicional sobre rollback/security patch/RPMB.

## Recomendaciones operativas

### Puertas obligatorias antes de reconsiderar el NO-GO

1. Reconciliar documentación: marcar `docs/hardware-observation-plan.md` como histórico o supersedirlo explícitamente.
2. Corregir toda referencia futura de earlycon a la forma validable por fuente:

   ```text
   earlycon=exynos4210,mmio32,0x13800000
   ```

3. Registrar por escrito que cero UART no prueba fallo pre-kernel.
4. Medir tamaño LZ4 real del perfil MINIMAL + SEC_DEBUG escalonado en artefactos temporales, sin generar imagen flasheable.
5. Validar closures completos de cada grupo de módulos con `modules.dep` y orden simulado.
6. Calibrar baseline stock: vídeo, enumeración USB, consumo, tiempos y temperatura.
7. Documentar consentimiento del propietario respecto a borrado de datos y posible pérdida irreversible de Knox.
8. Identificar procedimiento de desbloqueo específico para el modelo/región/build antes de ejecutarlo.
9. Ensayar la ruta de recuperación: entrada a Download Mode, detección por host y restauración oficial completa con hashes verificados.
10. Definir condición de batería mínima, tiempo máximo de sesión y criterio térmico de parada.
11. Conservar siempre rollback index `0` y propiedades relevantes en cualquier vbmeta de laboratorio.
12. Prohibir explícitamente escrituras a particiones de confianza y downgrades.

### Regla de interpretación

Ningún resultado negativo debe considerarse concluyente mientras:

- no exista baseline stock comparable;
- el estado de desbloqueo y política AVB estén sin confirmar;
- el canal de observabilidad no haya sido validado;
- la ruta de recuperación no haya sido ensayada.

Un boot silencioso no es información suficiente. Es una variable ambigua hasta que se demuestre qué canales funcionan.

## Veredicto

La preparación offline debe continuar, pero el primer contacto físico sigue siendo **NO-GO**.

Los siguientes pasos de mayor valor son documentales y de laboratorio seguro:

1. reconciliar planes antiguos y nuevos;
2. corregir earlycon y su interpretación;
3. medir initramfs SEC_DEBUG;
4. calibrar baseline stock;
5. investigar y registrar unlock/Knox/recuperación para esta unidad exacta.

Sólo después de cerrar esas evidencias tiene sentido discutir un experimento físico mínimo.
