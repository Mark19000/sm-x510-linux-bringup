# Pre-Flight Validation Report

**Fecha:** 2026-08-24
**Proyecto:** Samsung Galaxy Tab S9 FE Linux Bring-Up
**Dispositivo:** SM-X510 Wi-Fi, U12/EZE4, Android 16
**Kernel:** U11 Linux 5.15.180 (OSRC X510XXSBDZB4)
**Rol:** Principal Engineer — validación pre-contacto físico

---

## 1. Estado actual del proyecto

### 1.1 Lo que está confirmado y documentado

| Área | Estado | Evidencia |
|------|--------|-----------|
| Compilación kernel U11 | ✅ Completa | 9 builds fixed1–fixed9 PASS, Clang 21 ARM64 |
| DTB/DTBO compilados | ✅ Completa | 3 overlays byte-idénticos a EZE4 (verificado con `cmp`) |
| Initramfs reproducible | ✅ Completa | Perfiles minimal/ufs/usb en artifacts/ |
| Auditoría U11→U12 | ✅ Completa | reports/2026-08-23-u11-eze4-* |
| Cadena Android boot entendida | ✅ Completa | docs/boot-chain/*, docs/debugging/earlycon-analysis.md |
| sec_debug disponible | ✅ Completa | docs/debugging/sec-debug-firstboot-profile.md (530 líneas) |
| Plan first boot | ✅ Creado | docs/first-boot-experiment-plan-v2.md |
| Riesgos identificados | ✅ Completa | reports/first-boot-risk-review.md (366 líneas) |

### 1.2 Lo que NO está resuelto

| Área | Estado | Bloqueante |
|------|--------|-----------|
| Unlock/Knox decisión propietario | ❌ Pendiente | Requiere decisión humana irreversibile |
| hw_rev físico real | ❌ Desconocido | No se puede determinar sin boot |
| Baseline consumo USB stock | ❌ No medido | Requiere tablet encendida |
| Cmdline final runtime | ❌ No capturado | Requiere ADB en stock |
| LZ4 real perfil SEC_DEBUG | ❌ No empaquetado | Solo estimación (~0.9–1.2 MiB) |
| Procedimiento restauración ensayado | ❌ No probado | Existe firmware oficial local pero ruta no verificada |
| Comportamiento bootloader ante vbmeta flags=1 | ❌ Hipótesis | Solo observable en Fase 1 |

---

## 2. Veredicto: NO-GO condicionado

El proyecto **NO está listo para el primer contacto físico hoy**.

Sin embargo, la brecha es estrecha y está bien definida. Con 3 acciones concretas (descritas en §5), el estado puede pasar a GO en una sesión de trabajo offline sin hardware.

### Justificación

**Lo que impide GO:**

1. **No existe baseline stock medido.** Sin datos de referencia (consumo, tiempo boot, enumeración USB), no podemos distinguir "kernel crashea" de "bootloader rechaza" ni "kernel funciona pero invisible". El experimento sería ciego.
2. **No hay procedimiento de recuperación ensayado.** Tenemos el firmware oficial descargado, pero nadie ha verificado que el flujo Odin/Download Mode funcione para esta unidad específica. Si algo sale mal, no sabemos si podemos volver.
3. **La decisión de unlock no está tomada ni documentada.** Knox puede ser irreversible. El borrado de datos probable. Esta decisión pertenece al propietario y debe estar registrada antes de tocar nada.
4. **hw_rev desconocido.** Si el bootloader aplica un overlay incorrecto para nuestra revisión física, los nodos DT podrían no corresponder al hardware real. Esto afecta a todo lo posterior.

**Lo que ya está resuelto:**

- Sabemos exactamente qué imágenes modificar y cuáles dejar stock.
- Tenemos un protocolo AVB en fases abortables.
- Tenemos infraestructura sec_debug diseñada para capturar fallos.
- Los riesgos están identificados y clasificados.

---

## 3. Información faltante crítica

Si otro ingeniero recibe este repo mañana, estas son las lagunas que le impedirían reproducir el experimento:

| # | Información ausente | Dónde debería estar | Impacto |
|---|---------------------|---------------------|---------|
| I1 | Hash SHA256 de las imágenes modificadas que se van a flashear | Ficha de intento en cada fase | No se puede verificar integridad post-flash |
| I2 | Instrucción exacta de cómo generar vbmeta con flags=1 (comando avbtool completo) | docs/boot-chain/avb-experiment-plan.md | Ingeniero nuevo no sabría qué comando usar |
| I3 | Tamaño LZ4 real del initramfs SEC_DEBUG | docs/debugging/sec-debug-firstboot-profile.md | ¿Cabe o no cabe? Solo hay estimación |
| I4 | Captura de pantalla del warning unlock Samsung | N/A hasta tener dispositivo | ¿Qué dice exactamente el prompt? |
| I5 | Confirmación de si Download Mode sigue accesible tras flash fallido | reports/first-boot-risk-review.md | Ruta de escape |
| I6 | Versión exacta de Odin/Heimdall compatible con este bootloader | docs/06-bring-up.md o similar | Herramienta correcta para restauración |
| I7 | Lista de módulos built-in en kernel U11 que cubren los primeros 15 de modules.load stock | docs/debugging/sec-debug-firstboot-profile.md | Determina si vendor_boot stock es viable |

---

## 4. Plan de primer experimento recomendado

### Experimento 0 — Baseline stock

**Duración estimada:** 30 minutos
**Riesgo:** CERO (solo lectura)

Registrar:
- [ ] Modelo/CSC/AP/bootloader confirmados vía ADB
- [ ] `/proc/cmdline` completo capturado
- [ ] `/proc/device-tree/model` capturado
- [ ] Consumo USB en idle (mA) — medidor inline
- [ ] Consumo USB durante boot completo — patrón temporal
- [ ] Tiempo desde power-on hasta lock screen
- [ ] VID/PID en modo normal vs Download Mode
- [ ] Comportamiento Download Mode: enumeración, respuesta, timeout
- [ ] hw_rev si visible via getprop o device-tree
- [ ] Screenshots de cualquier warning/unlock prompt

### Experimento 1 — Kernel marker

**Objetivo:** demostrar que el kernel U11 recibe control del bootloader.

**Superficie mínima:**
- Modifica: `boot.img` (kernel U11 + cmdline stock) + `vbmeta.img` (flags=1)
- Stock: `init_boot.img`, `vendor_boot.img`, `dtbo.img`

**Precondición:** Experimento 0 completado. Dispositivo desbloqueado. Decisión propietario documentada.

**Evidencia buscada:**
- Cambio en patrón USB: enumeración bootloader desaparece → handoff ocurrió
- Cambio en consumo eléctrico: transición de patrón plano a variable
- Cualquier output en consola (si earlycon funciona)
- Cualquier cambio visual (pantalla negra vs warning persistente)

**Interpretación:**
- Boot normal/warning amarillo → kernel ejecutó, posiblemente llegó a userspace con ramdisk stock → ÉXITO
- Warning rojo/reboot loop → bootloader aún bloquea → investigar AVB
- Hang estable sin cambios → kernel crashea temprano → activar sec_debug (Exp 3)
- Silencio total idéntico a antes → AVB aún rechaza boot modificado → verificar flags/vbmeta

### Experimento 2 — Initramfs minimal

**Objetivo:** demostrar que el kernel alcanza userspace (/init).

**Superficie:**
- Modifica: `boot.img` + `init_boot.img` (ramdisk MINIMAL ~674 KiB) + `vbmeta.img`
- Stock: `vendor_boot.img`, `dtbo.img`

**Contenido initramfs:**
- BusyBox estático AArch64
- Script /init: mount proc/sys/devtmpfs, echo marcador, shell interactivo
- Cero módulos

**Criterio de éxito:**
- Mensaje `[gts9fe-init] userspace reached` en consola visible, O
- Cambio sostenido en patrón de consumo (>100 mA fluctuante = scheduler activo), O
- Enumeración USB gadget (si se incluye configfs ACM en versión futura)

**Criterio de fallo interpretable:**
- Reboot loop → panic en kernel o init → pasar a Exp 3
- Hang estable → posible fallo GIC/timer/memoria → revisar DT/config
- Sin ningún cambio respecto a Exp 1 → initramfs no entregado → verificar header v4 init_boot

### Experimento 3 — SEC_DEBUG bring-up

**Objetivo:** obtener evidencia de crash post-mortem usando infraestructura Samsung existente.

**Superficie:**
- Modifica: mismo conjunto que Exp 2, pero init_boot contiene ramdisk SEC_DEBUG

**Initramfs extendido:**
- Base MINIMAL +
- Módulos fase A (bajo riesgo): `exynos-pmu-if.ko`, `dss.ko`
- Módulos fase B: `sec_debug_dprt.ko`, `sec_debug_base_early.ko`
- Orden de carga según modules.dep
- Script /init que lista `/sys/kernel/sec_debug/*`

**Protocolo:**
1. Arrancar normalmente → verificar módulos cargan sin error
2. Verificar sysfs nodes presentes
3. Provocar crash deliberado: `echo c > /proc/sysrq-trigger`
4. Tras reboot automático, leer región sec_debug_next (0x91200000):
   - Via ADB en Android stock (recovery boot)
   - Via lectura directa si hay acceso físico
   - Via segundo arranque con initramfs que lee y exporta por consola

**Señal de éxito:** datos no-cero en región 0x91200000 tras reboot post-crash = evidencia capturada.

---

## 5. Checklist antes de tocar hardware

### Offline (sin tablet)

- [ ] Empaquetar initramfs SEC_DEBUG y medir tamaño LZ4 real
- [ ] Documentar comando avbtool exacto para regenerar vbmeta flags=1
- [ ] Generar boot.img candidato con kernel U11 y calcular hash
- [ ] Generar init_boot candidato MINIMAL y calcular hash
- [ ] Verificar que kernel Image tiene entry point correcto para ARM64
- [ ] Confirmar lista de drivers built-in en U11 que cubren los críticos stock
- [ ] Preparar ficha de intento inmutable con todos los hashes
- [ ] Ensayar procedimiento de restauración en VM/emulador si es posible
- [ ] Documentar herramienta exacta (Odin vX.X o Heimdall vX.X) y su fuente

### Propietario

- [ ] Leer y entender consecuencias de unlock (Knox, borrado datos, garantía)
- [ ] Firmar/confirmar decisión de desbloqueo
- [ ] Confirmar que tiene backup de datos si los hubiera
- [ ] Establecer condición de aborto y timeout

### Hardware (día del experimento)

- [ ] Tablet con batería >80%
- [ ] Cable USB-C de calidad verificado
- [ ] Medidor USB inline conectado
- [ ] Segundo equipo con firmware oficial listo
- [ ] Registro de tiempo/consumo/enumeración desde minuto 0
- [ ] Condición de aborto clara: "si X no ocurre en Y minutos, STOP"

---

## 6. Tabla de riesgos

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| AVB rechaza boot modificado incluso unlocked | Media | Alto — no avanza | Fase 1 sonda vbmeta-only antes de tocar boot |
| Rollback index sube permanentemente | Baja | Crítico — brick permanente | RI observado = 0; no flashear imágenes con RI superior |
| Bootloop infinito tras kernel propio | Media | Medio — recuperable via Download Mode | Mantener Vol- accesible; firmware oficial preparado |
| Kernel U11 incompatible con vendor_boot stock DLKM | Alta | Bajo para M2/M3 — módulos fallan pero boot continúa | Drivers built-in en kernel; módulos DLKM solo necesarios post-init |
| DTBO incorrecto aplicado (hw_rev mismatch) | Baja-Media | Alto — probes fallan silenciosamente | Capturar DT efectivo en Exp 0; comparar con esperado |
| Módulos sec_debug crashean al cargar | Media | Medio — pierde canal debug | Escalonar carga: primero pmu-if+dss solo, verificar, luego expandir |
| Sin logs visibles (earlycon inactivo, sin UART) | Alta | Alto — experimento a ciegas | Usar consumo USB como proxy + sec_debug como post-mortem |
| Dispositivo no vuelve tras flash fallido | Baja | Crítico — brick total | Firmware oficial local + Download Mode + Odin/Heimdall verificados |
| Unlock borra datos sin advertencia previa | Baja | Bajo — solo si había datos importantes | Backup previo; confirmar en prompt |
| Knox efuse se quema irreversiblemente | Alta (al unlock) | Medio — pérdida garantía/Samsung Pay | Documentado; decisión propietario informada |

---

## 7. Criterio de GO/NO-GO final

### GO cuando TODAS las siguientes condiciones se cumplan:

1. ✅ Experimento 0 (baseline) ejecutado y datos guardados
2. ✅ Todos los hashes de imágenes candidatas calculados y registrados en ficha
3. ✅ Tamaño LZ4 real del initramfs SEC_DEBUG medido (no estimado)
4. ✅ Procedimiento de restauración documentado paso a paso con herramienta verificada
5. ✅ Propietario confirma por escrito comprensión de unlock/Knox/borrado
6. ✅ Condición de aborto definida con timeout numérico
7. ✅ Segundo equipo disponible con cable y firmware oficial cargado
8. ✅ hw_rev determinado (o aceptamos riesgo de overlay incorrecto con justificación)

### NO-GO si cualquiera de estas situaciones existe:

1. ❌ Firmware oficial no disponible localmente o corrupto
2. ❌ Tablet con batería inestable o daño físico visible
3. ❌ Propietario duda sobre unlock
4. ❌ Alguna imagen candidata no tiene hash verificado
5. ❌ No existe ruta de escape documentada
6. ❌ Se propone cambiar más de una variable simultáneamente

---

## 8. Auditoría de documentación

### ¿Otro ingeniero puede reproducir esto mañana?

**Parcialmente.** La documentación técnica es excelente en profundidad (auditorías DT, ABI, AVB, sec_debug). Pero le faltarían:

1. Los comandos exactos para generar imágenes candidatas (existen scripts pero no están referenciados desde el plan v2).
2. La versión de avbtool y el comando preciso para flags=1.
3. Una guía paso a paso del día del experimento que no requiera leer 10 documentos previos.
4. La conexión entre los informes de agentes y las decisiones del plan v2 (por qué elegimos SEC_DEBUG sobre USB console, por ejemplo).

### Recomendaciones de documentación adicional

| Prioridad | Documento sugerido |
|-----------|-------------------|
| Alta | `docs/runbook-first-boot.md`: guía operativa de un solo archivo para el día del experimento |
| Alta | Actualizar `docs/hardware-observation-plan.md` (contradice NO-GO vigente — Risk Reviewer C1) |
| Media | `docs/tooling/avb-vbmeta-regeneration.md`: comando avbtool exacto |
| Media | `docs/initramfs/sec-debug-size-audit.md`: resultado de medición real LZ4 |
| Baja | Consolidar informes de agentes en un índice navegable |

---

## Resumen ejecutivo

El proyecto tiene una base técnica sólida y bien documentada. Los agentes han producido auditorías de alta calidad. Sin embargo, **NO-GO** porque:

1. No hay baseline stock (no podemos interpretar resultados sin él)
2. No hay ruta de recuperación ensayada (riesgo inaceptable)
3. La decisión unlock no está tomada (es prerrequisito legal/ético)
4. Falta medir el initramfs SEC_DEBUG real (estimación ≠ dato)

Con 1 sesión offline (empaquetar, medir, generar hashes) + 1 sesión con tablet encendida (baseline + decisión unlock), el proyecto puede pasar a **GO condicionado** para Fase 1 (vbmeta-only).

El siguiente paso concreto es: **empaquetar el initramfs SEC_DEBUG localmente y medir su tamaño LZ4 real.**

