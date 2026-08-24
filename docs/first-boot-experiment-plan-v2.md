# First Boot Experiment Plan v2

**Fecha:** 2026-08-24
**Proyecto:** Samsung Galaxy Tab S9 FE Linux Bring-Up
**Dispositivo:** SM-X510 Wi-Fi, U12/EZE4, Android 16, SoC S5E8835 (Exynos 1380)
**Kernel candidato:** U11 Linux 5.15.180 (OSRC X510XXSBDZB4)

---

## 1. Qué sabemos

### 1.1 Evidencia confirmada

| # | Hallazgo | Fuente |
|---|----------|--------|
| F1 | Todas las imágenes boot/init_boot/vendor_boot/dtbo firmadas SHA256_RSA4096 con misma clave (`b6924fd4...4029`). Flags=0 en todo. Rollback index global = 0. | Agente AVB, `avbtool info_image` |
| F2 | `boot.img`: kernel 39.36 MB, ramdisk vacío, cmdline header **vacío**. | Agente Earlycon |
| F3 | `init_boot.img`: sin kernel, ramdisk LZ4 2.49 MB, cmdline header **vacío**. | Agente Earlycon |
| F4 | `vendor_boot.img`: vendor_ramdisk 18 MB (281 módulos DLKM 5.15.189), DTB comprimido Samsung, bootconfig real = **0 bytes** (los 28B eran padding de la tabla). | Agente Earlycon |
| F5 | DT `chosen.bootargs` = `console=ram printk.devkmsg=on arm64.nopauth ...`. Sin `earlycon=` ni `stdout-path`. | Agente Earlycon |
| F6 | Driver legacy `samsung_tty.c` registra earlycon para `exynos4210-uart`; driver actual `exynos_tty.c` (`samsung,exynos-uart`) **NO tiene `OF_EARLYCON_DECLARE`**. | Agente Earlycon, sources/ |
| F7 | Overlays DTBO U11 vs EZE4: los tres byte-idénticos verificado con `cmp`. | Agente Image Architecture |
| F8 | `sec_debug_next @ 0x91200000`, 2 MiB, no-map — presente en overlay, NO en DTB base. | Agente sec_debug, DT audit |
| F9 | Módulos sec_debug U11 disponibles: cierre mínimo reset_reason = 6 módulos (~675 KiB raw); núcleo completo = 10 módulos (~725 KiB raw). | Agente sec_debug Integration |
| F10 | `CONFIG_MODULE_SIG_PROTECT=y` pero `sig_enforce` compila a `false` → módulos sin firma válida cargan con taint, NO son rechazados por esa vía. | Risk Reviewer C3 |
| F11 | Vermagic U11 5.15.180 ≠ stock 5.15.189-android13-3 → módulos stock DLKM incompatibles con kernel U11 por CRC/vermagic. | ABI audit previo |
| F12 | PSCI 1.0 smc; GIC-400; arch_timer 26 MHz; oscclk 52 MHz — idénticos entre U11 y EZE4. | DT audit |
| F13 | Las 4 diferencias DT U11→EZE4 (EMS×2, mfc debug_mode, scsc cpu_table_rps) son post-printk. No afectan pre-printk. | DT audit |
| F14 | hw_rev físico de la unidad: **desconocido**. Los nombres U12/EZE4/REV00 no permiten inferir la revisión física real. | Agente Hardware Identity |
| F15 | Perfil initramfs MINIMAL ya existe: ~674 KiB LZ4, margen positivo ~1.8 MiB sobre ramdisk stock init_boot. | Initramfs design previo |

### 1.2 Correcciones del Risk Reviewer

| # | Corrección | Impacto |
|---|-----------|---------|
| R1 | `earlycon=samsung,...` es inválido; forma registrada es `exynos4210` | Plan v1 tenía comando incorrecto |
| R2 | UART0 está `disabled` en DT y usa USI v2 — accesibilidad física no demostrada | earlycon puede no producir salida aunque se active |
| R3 | Riesgo de firma sobrestimado — problema real es CRC/vermagic | Reduce una barrera percibida para carga de módulos propios |
| R4 | `hardware-observation-plan.md` contradice el NO-GO vigente al recomendar ramoops nuevo | Documento antiguo necesita revisión |

---

## 2. Qué desconocemos

| # | Incógnita | Impacto en experimento |
|---|-----------|----------------------|
| U1 | ¿El bootloader Samsung respeta flags=1 bajo UNLOCKED? | Determina si podemos usar vbmeta propio o necesitamos otra ruta |
| U2 | ¿El unlock borra datos? ¿Activa Knox irreversible? | Decisión del propietario antes de cualquier flash |
| U3 | ¿El bootloader añade parámetros al cmdline final en runtime? | Podría activar earlycon automáticamente o añadir restricciones |
| U4 | hw_rev físico real (¿r00, r01 o r04?) | Determina qué overlay aplica el bootloader |
| U5 | ¿UART0 es físicamente accesible? (USI v2, disabled en DT) | Si no lo es, earlycon no produce salida visible |
| U6 | Ratio LZ4 real del perfil SEC_DEBUG initramfs | ¿Cabe dentro de init_boot? |
| U7 | Comportamiento del bootloader ante kernel crasheado temprano (¿reboot loop? ¿hang?) | Afecta interpretación de señales USB |
| U8 | Paths sysfs exactos que exponen los módulos sec_debug en este kernel | Requiere observación runtime |

---

## 3. Experimento mínimo

### Definición

El experimento mínimo NO es "flashear un kernel custom". Es una **secuencia de sondas controladas** donde cada fase aísla exactamente una variable.

### Fase 0 — Baseline stock (solo lectura)

**Objetivo:** documentar el comportamiento normal para tener referencia.

**Acciones (sin modificar nada):**
1. Conectar tablet encendida vía USB-C con medidor inline.
2. Documentar consumo en idle, durante carga, durante uso normal.
3. Entrar en Download Mode (Vol- + conectar cable): documentar VID/PID, consumo, tiempo de estabilización.
4. Desde ADB (si disponible), recolectar:
   - `getprop ro.hw_revision` / `ro.board.platform`
   - `/proc/device-tree/model`
   - `/proc/cmdline`
   - `/sys/firmware/fdt` (si accesible read-only)
5. Documentar tiempo total desde power-on hasta Android boot completo.

**Criterio:** datos cuantitativos guardados en ficha de experimento.

### Fase 1 — Sonda vbmeta-only (bajo UNLOCKED)

**Objetivo:** aislar la política del bootloader Samsung ante vbmeta modificado.

**Precondición:** dispositivo desbloqueado (decisión del propietario documentada).

**Acciones:**
1. Regenerar vbmeta.img con flags=1 (disable verification) usando avbtool local.
2. Flashear SOLO vbmeta.img. NO tocar boot/init_boot/vendor_boot/dtbo.
3. Observar arranque.

**Resultados posibles e interpretación:**

| Resultado | Interpretación | Siguiente paso |
|-----------|---------------|---------------|
| Boot normal Android | Bootloader respeta flags=1 bajo UNLOCKED → podemos proceder con kernel propio | Avanzar a Fase 2 |
| Warning naranja + boot lento pero funciona | Comportamiento estándar AOSP unlocked | Avanzar a Fase 2 |
| Warning rojo / reboot loop / modo download | Samsung rechaza vbmeta modificado incluso unlocked → bloqueante mayor | STOP, investigar alternativa |
| Brick / no responde a Download Mode | Escenario peor | Procedimiento recuperación oficial |

### Fase 2 — Kernel marker (boot + vbmeta)

**Objetivo:** confirmar que el bootloader entrega control al kernel U11.

**Acciones:**
1. Preparar boot.img con kernel U11 compilado + cmdline mínimo (`console=ram` igual al stock).
2. Mantener init_boot stock y vendor_boot stock.
3. Flashear boot.img + vbmeta.img (ya modificado).
4. Observar.

**Resultado esperado:** el kernel U11 recibe control. Puede crashear temprano por incompatibilidad con vendor_boot stock, pero eso YA ES INFORMACIÓN: confirma que el bootloader pasó control.

**Señal de éxito mínima:** cualquier transición USB (enumeración desaparece tras bootloader handoff), cambio en patrón de consumo, o reboot diferente al warning screen.

### Fase 3 — Initramfs MINIMAL (boot + init_boot + vbmeta)

**Objetivo:** demostrar que el kernel alcanza userspace (/init).

**Acciones:**
1. Usar perfil MINIMAL existente (~674 KiB LZ4) como ramdisk en init_boot.img.
2. Flashear boot + init_boot + vbmeta.
3. Observar.

**Señal de éxito:** si hay consola visible, mensaje `[gts9fe-init] userspace reached`. Si no, cambio de patrón eléctrico (kernel ejecutando scheduler vs bootloader plano).

### Fase 4 — SEC_DEBUG BRING-UP (boot + init_boot + vbmeta)

**Objetivo:** activar infraestructura Samsung de crash/debug para obtener evidencia post-mortem.

**Acciones:**
1. Extender initramfs MINIMAL con los primeros 4 módulos sec_debug:
   - `exynos-pmu-if.ko`
   - `dss.ko`
   - `sec_debug_dprt.ko`
   - `sec_debug_base_early.ko`
2. Script /init que carga módulos en orden y lista `/sys/kernel/sec_debug/*`.
3. Flashear y observar.
4. Si falla: provocar crash deliberado (`echo c > /proc/sysrq-trigger`) y verificar si `sec_debug_next @ 0x91200000` contiene datos tras reboot.

---

## 4. Imágenes participantes

| Fase | boot.img | init_boot.img | vendor_boot.img | dtbo.img | vbmeta.img |
|------|----------|--------------|----------------|----------|-----------|
| 0 | Stock | Stock | Stock | Stock | Stock |
| 1 | Stock | Stock | Stock | Stock | **Modificado** (flags=1) |
| 2 | **U11 kernel** | Stock | Stock | Stock | Modificado |
| 3 | **U11 kernel** | **MINIMAL ramdisk** | Stock | Stock | Modificado |
| 4 | **U11 kernel** | **SEC_DEBUG ramdisk** | Stock | Stock | Modificado |

**vendor_boot permanece stock en todas las fases iniciales.**

Riesgo conocido: sus 281 módulos DLKM son incompatibles con kernel U11 (F11). Pero si el kernel U11 tiene drivers suficientes built-in para alcanzar /init, los módulos DLKM simplemente no cargan (fallan con error en dmesg) y el sistema sigue funcional en modo limitado. Esto es aceptable para first-boot.

**dtbo.img permanece stock** porque los overlays U11 y EZE4 son idénticos (F7).

---

## 5. Evidencia buscada

| Tipo | Método | Fase |
|------|--------|------|
| Política AVB Samsung bajo UNLOCKED | Resultado visual/USB tras flashear solo vbmeta | F1 |
| Control transferido al kernel | Transición USB (bootloader desaparece) + cambio consumo | F2+ |
| Kernel alcanzó userspace | Mensaje /init en consola O cambio patrón eléctrico sostenido | F3+ |
| sec_debug operativo | Nodos sysfs presentes post-carga módulos | F4 |
| Crash capturado | Datos en región 0x91200000 tras reboot deliberado | F4 |
| hw_rev físico | getprop /proc/device-tree en Android stock | F0 |
| Cmdline final real | cat /proc/cmdline en Android stock | F0 |

---

## 6. Interpretación de resultados

### Árbol de decisión

```
Fase 1 (vbmeta-only):
├── Boot normal/warning amarillo → bootloader tolera flags=1 → CONTINUAR
├── Warning rojo/reboot → Samsung bloquea → ESCALAR (investigar alternativas)
└── Brick → RECUPERAR via firmware oficial → RE-EVALUAR proyecto

Fase 2 (kernel marker):
├── Cambio observable USB/consumo → kernel recibió control → CONTINUAR
├── Warning rojo/reboot inmediato → AVB aún bloquea boot.img → verificar flags/vbmeta
└── Silencio total sin cambio → kernel crashea pre-printk → investigar PSCI/GIC/timer

Fase 3 (minimal initramfs):
├── Shell/mensaje visible → M3 alcanzado → pasar a UFS/rootfs
├── Consumo fluctuante sin consola → kernel vivo, falta canal → priorizar USB ACM
├── Reboot loop → panic temprano → activar sec_debug (Fase 4) para capturar causa
└── Hang estable → posible fallo GIC/timer → revisar config kernel U11

Fase 4 (sec_debug):
├── Módulos cargan, sysfs presente → infraestructura operativa → provocar crash test
├── Invalid module format → CRC mismatch entre módulos U11 y kernel U11 (inesperado) → verificar hashes
├── Required key not available → sig_enforce=true en runtime (contradice F10) → investigar
├── Probe falla silenciosamente → DTBO no aplicado correctamente → verificar overlay seleccionado
└── Reset durante carga → riesgo región memoria/TZ → reducir conjunto módulos
```

---

## 7. Siguiente paso después de cada escenario

| Escenario | Acción siguiente |
|-----------|-----------------|
| Fases 1-4 todas exitosas | Pasar a rootfs persistente read-only (UFS), luego USB ACM console, luego display |
| Fase 1 exitosa, Fase 2 falla | Verificar que boot.img fue regenerado correctamente (header v4, tamaño, hash); auditar kernel Image entry point |
| Fase 2 exitosa, Fase 3 hang | Kernel corre pero no llega a userspace → investigar initramfs formato, devtmpfs, console setup |
| Fase 3 exitosa sin consola visible | Construir perfil DEBUG USB con gadget serial ACM para obtener canal interactivo |
| Fase 4 revela crash capturable | Analizar dump sec_debug_next para identificar causa raíz del fallo original |
| Cualquier fase produce brick | Restaurar firmware oficial completo (AP_X510XXUCEZE4 tar.md5) via Odin/Download Mode |

---

## Bloqueantes pendientes antes de hardware

| # | Bloqueante | Estado |
|---|-----------|--------|
| B1 | Decisión propietario sobre unlock/Knox/borrado datos | Pendiente usuario |
| B2 | Medición real LZ4 del initramfs SEC_DEBUG (empaquetar localmente) | Pendiente offline |
| B3 | Captura baseline stock (consumo, cmdline, hw_rev) | Requiere tablet encendida |
| B4 | Ensayar procedimiento restauración oficial en entorno seguro | Pendiente |
| B5 | Investigar si bootloader añade parámetros cmdline en runtime | Fase 0 |

---

## Referencias

- `docs/debugging/earlycon-analysis.md` — análisis earlycon
- `docs/debugging/sec-debug-firstboot-profile.md` — diseño perfil SEC_DEBUG
- `docs/boot-chain/minimal-modification-set.md` — arquitectura imágenes
- `docs/boot-chain/avb-experiment-plan.md` — protocolo AVB en fases
- `docs/hardware/device-identity.md` — identidad hardware
- `reports/first-boot-risk-review.md` — revisión independiente de riesgos
- `docs/debugging/sec-debug-analysis.md` — auditoría sec_debug previa
- `docs/first-boot-experiment-plan.md` — plan v1 (obsoleto, reemplazado por este)
