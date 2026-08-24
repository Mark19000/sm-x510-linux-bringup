# Plan de observación de hardware y preparación del primer arranque

Fecha: 2026-08-24
Artefacto auditado: `artifacts/u11/x510xxsbdzb4-u11-clang21-20260823/kernel.config`
Fase: preparatoria, **no flasheo**

## 1. Auditoría del kernel `.config`

### Opciones críticas

| Config | Valor U11 | Clasificación | Impacto en M2 (primer printk) / M3 (`/init`) |
|---|---|---|---|
| `CONFIG_PSTORE` | `y` | ya activo | Necesario para persistir logs tras panic/reboot; sin efecto sobre llegar a `/init`. |
| `CONFIG_PSTORE_RAM` | `y` | ya activo | Permite ramoops si hay región reservada + cmdline correcto; clave para capturar fallos tardíos aunque no haya consola. |
| `CONFIG_USB_GADGET` | `y` | ya activo | Requisito para consola USB; no afecta a M2/M3 directamente. |
| `CONFIG_USB_CONFIGFS` | `y` | ya activo | Interfaz necesaria para crear gadget serial desde initramfs. |
| `CONFIG_USB_CONFIGFS_SERIAL` | `y` | ya activo | Función serial genérica disponible; ACM también está activo. |
| `CONFIG_SERIAL_SAMSUNG` | `y` (+ console) | ya activo | Driver UART Samsung; imprescindible para consola física si existe. |
| `CONFIG_SERIAL_EARLYCON` | `y` | ya activo | Mensajes antes que la consola normal; máxima prioridad M2. |
| `CONFIG_EARLY_PRINTK` | ausente (normal en arm64 moderno; se usa earlycon) | no necesario | No bloquea nada; `earlycon=` es el mecanismo correcto. |
| DRM core | `CONFIG_DRM=y`, DeCON/DSI/DPU/Samsung = `y/m` | ya activo | No relevante para M2/M3; útil después de tener shell/logs. |
| DRM panel específico | `DRM_PANEL_MCD_COMMON=m`; resto genérico off | parcialmente activo | Riesgo post-M3: si el panel real no matchea, pantalla negra pero sistema vivo. No prioridad inicial. |
| `CONFIG_USB_DWC3_EXYNOS` | `=y` y también `=m` (contradicción Kconfig aparente) | revisar | El módulo debe estar presente en initramfs usb-console; si sólo estuviera built-in, mejor. Verificar con `modules.builtin`. |
| Ramoops región reservada | no visible en config | necesario activar (DT/cmdline) | Sin dirección/tamaño reservados, pstore RAM no guarda nada. Acción offline antes de flashear. |

### Resumen

- **Ya activo:** pstore completo, ramoops base, gadget/configfs/serial/ACM, serial Samsung + earlycon, DRM core Samsung.
- **Necesario activar/preparar:** reserva de memoria ramoops en DT + parámetros cmdline; verificación explícita de módulo/built-in DWC3-Exynos.
- **No necesario:** `CONFIG_EARLY_PRINTK` clásico (obsoleto en arm64).

## 2. Tres perfiles de initramfs

Todos comparten BusyBox 1.36.1 ARM64 estático, `/init` actual y empaquetado reproducible gzip/lz4. Se documentan como diseño; no se construyen todavía.

### A) minimal

Objetivo: máxima probabilidad de ejecutar `/init`.

Contenido:
- BusyBox estático + `/init` + `/etc/passwd`, `/etc/group`.
- Cero módulos (`MODULES_MODE=none`).
- Sin USB gadget, sin carga de drivers.
- Cmdline recomendado:
  - `earlycon=exynos4210,mmio32,0x13800000`
  - `console=ttySAC0,115200n8`
  - `printk.devkmsg=on`
  - `panic_print=0x1f`
  - `panic_timeout=30`

Interpretación: si este perfil no llega a `/init`, el problema está antes (AVB/bootloader) o en el canal de observabilidad, no en drivers.

### B) debug

Objetivo: maximizar evidencia ante cualquier fallo.

Añade respecto a A:
- printk máximo vía cmdline: `loglevel=8 ignore_loglevel`.
- `pstore`/`ramoops` con región reservada definida en DT o `ramoops.mem_address=... ramoops.mem_size=... ramoops.record_size=... ramoops.console_size=...`.
- `crashkernel` NO se activa (innecesario para primer contacto y añade riesgo).
- `softlockup_panic=1 hardlockup_panic=1 nmi_watchdog=1` opcional si queremos convertir hangs en registros pstore.
- `panic_timeout=0` (sin reinicio automático durante experimentos con operador presente).

Uso previsto: segunda pasada, cuando ya sabemos que el kernel arranca y queremos capturar dónde muere.

### C) usb-console

Objetivo: shell por USB serial si el kernel alcanza el punto donde DWC3 + configfs funcionan.

Añade respecto a A:
- Módulos U11 cerrados por modprobe: `dwc3-exynos-usb` + `phy-exynos-usbdrd-super` (lista existente `configs/initramfs-modules-usb.conf`).
- Activación de gadget ACM (ya implementada en `/init` bajo `gts9fe.usb_debug=1`).
- Cmdline: `gts9fe.usb_debug=1` + los mismos de minimal.

Criterio de éxito: el host ve un nuevo puerto `/dev/ttyUSB*` o `/dev/ttyACM*`. Si aparece pero no hay shell, el problema es post-DWC3 pero pre-userspace-visible.

## 3. Evidencias buscadas e interpretación

| Resultado observable | Significado | Decisión siguiente |
|---|---|---|
| Cero bytes UART + host USB no ve nada nuevo | Fallo antes del kernel (AVB, bootloader, imagen inválida). Kernel posiblemente nunca ejecutó una instrucción. | Volver a AVB/firma/formato boot/init_boot. No tocar drivers ni rootfs. |
| Cero bytes UART + host USB sí enumera gadget serial | Kernel llegó lejos; sólo falta canal UART físico. | Continuar M3/M4 por USB. UART pasa a ser problema de hardware/pines, no de boot. |
| Bytes parciales UART y hang | Fallo temprano en timer/PSCI/GIC/memoria. | Comparar DTBO elegido, revisar earlycon y PSCI; considerar JTAG. |
| Log UART completo hasta panic "no init found" | Kernel OK; initramfs inválido o corrupto. | Revisar formato cpio, compresión, tamaño y metadata boot v4. |
| Shell USB funciona | M3 superado. | Pasar a UFS/rootfs read-only, luego pantalla (post-M3), no antes. |
| Pantalla negra pero USB/UART vivo | DRM/panel aún no matchea. | Es resultado esperable; no cuenta como fallo de boot. |
| Reinicio en loop sin log | Panic temprano con reboot automático o watchdog firmware. | Repetir con perfil debug y `panic_timeout=0`. |
| Nada en absoluto, incluso USB host no detecta | Probable rechazo bootloader o hardware distinto al esperado. | Auditar AVB/vbmeta y overlay r00/r01/r04 efectivo. |

## 4. Interpretación de consumo por USB

El puerto USB-C del host nos da tres señales independientes, todas baratas y sin abrir la tablet:

1. **Corriente consumida** (medible con un medidor USB inline):
   - < ~20 mA constante: probablemente no ha arrancado nada real; puede estar esperando negociación o en modo download/recovery silencioso.
   - Salto brusco a >100 mA sostenido: señal de actividad CPU real (kernel ejecutando algo), aunque no haya enumeración.
   - Consumo oscilante estable (~100–300 mA): patrón típico de kernel vivo con scheduler activo.
2. **Enumeración USB**:
   - Aparece dispositivo Samsung (VID 0x04e8) → bootloader habló por USB (modo download u Odin-like).
   - Aparece dispositivo Linux Gadget (VID 0x1d6b, producto "Tab S9 FE rescue") → kernel llegó a DWC3 + userspace init. Prueba directa de M3.
   - No aparece nada → o bootloader no entró en modo transferencia, o kernel no llegó a USB.
3. **Tipo de puerto/negociación**:
   - Si el host reporta "dispositivo desconocido" o error de descriptor → hubo intento de hablar USB, fallo parcial.
   - Si no hay ninguna transacción eléctrica → problema previo a USB, posiblemente pre-kernel.

Regla: el consumo USB es indicio estadístico, nunca prueba determinista. Sólo la enumeración con VID/PID correctos o un log son prueba fuerte.

## 5. Cadena USB-C: qué depende de quién

Sin desmontar la tablet, la cadena USB-C tiene tres capas:

| Capa | Responsable | Observable desde el host |
|---|---|---|
| Física / CC / orientación | PMIC + controlador tipo-C + bootloader Samsung | Negociación de corriente, presencia de VBUS, detección de cable/orientación |
| Bootloader / modo download | SBOOT/LK2 Samsung | Enumeración VID 0x04e8 en Odin/Heimdall, respuesta a protocolo propio |
| Kernel Linux (DWC3 + gadget) | Kernel U11 + initramfs + módulos | Enumeración VID 0x1d6b con gadget serial/ACM, aparición de `/dev/tty*` en host |

Conclusiones prácticas:

- Si el dispositivo entra en modo download y el host lo ve como Samsung, **el bootloader y la capa física USB-C funcionan**, independientemente de nuestro kernel. Esto se puede probar hoy sin riesgo, sin flashear.
- Si el kernel no llega a gadget, no sabemos si el fallo es USB-C físico, bootloader, o kernel; necesitamos otra evidencia (UART, pstore) para discriminar.
- La función serial depende completamente del kernel; su aparición es prueba de M3, no del bootloader.

## 6. Árbol de decisión tras el primer intento

```text
Primer intento (perfil minimal)
├── Host ve gadget Samsung en modo download?
│   ├── Sí → bootloader OK, capa física OK. Flashear candidato y observar.
│   └── No → resolver entrada a modo download primero. STOP.
│
├── Tras flasheo, host ve gadget Linux (0x1d6b)?
│   ├── Sí → kernel llegó a /init. Ir a pruebas UFS/read-only.
│   └── No → seguir.
│
├── Hay bytes UART?
│   ├── Sí, log completo hasta panic initramfs → arreglar formato/init_boot.
│   ├── Sí, hang parcial → revisar PSCI/timer/earlycon.
│   └── No bytes → continuar.
│
├── Consumo USB salta a patrón activo (>100 mA sostenido)?
│   ├── Sí → kernel probablemente vivo, problema sólo de observabilidad.
│   │        → repetir con usb-console.
│   └── No, consumo plano bajo → probablemente pre-kernel. Volver a AVB/firma.
│
└── Nada de lo anterior → repetir con perfil debug + pstore.
    Extraer pstore tras recovery/ADB si Android stock vuelve a arrancar.
```

## 7. Reglas fijas para esta fase

- Un único cambio entre intentos.
Ficha de intento obligatoria antes de tocar hardware (ver `docs/12-preflight-primera-prueba.md`).
- Timeout y condición de aborto escritos antes del intento.
- Ningún cambio simultáneo de kernel + DTBO + vbmeta + rootfs.
- El veredicto sigue siendo **NO-GO para flasheo**; esta fase sólo prepara instrumentos.
