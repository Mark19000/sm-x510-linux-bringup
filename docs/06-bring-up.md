# 6. Procedimiento de bring-up

## Ficha por intento

Crea una entrada por cada boot:

```text
Fecha/hora UTC:
Modelo, CSC, revisión:
Firmware stock y SHA-256:
Commit kernel:
Commit proyecto:
Config SHA-256:
Image/DTB/DTBO/initramfs SHA-256:
Cambio único de este intento:
Resultado/hito alcanzado:
Log completo:
Siguiente hipótesis:
```

Sin esta disciplina, dos imágenes llamadas `boot.img` se vuelven
indistinguibles y los fallos parecen aleatorios.

## Fase A: sin escribir en la tablet

1. Ejecuta `./scripts/collect-device.sh` con Android arrancado.
2. Extrae el paquete AP exacto.
3. Compara DT fuente, DT stock y DT en ejecución.
4. Registra tamaños y hashes de particiones/imágenes.
5. Construye kernel e initramfs y valida su arquitectura.

## Fase B: consola antes que periféricos

La consola es el multiplicador del proyecto. Prioriza, en este orden:

1. framebuffer/console ya inicializada por bootloader, si se conserva;
2. UART sólo tras localizar pinmux y nivel eléctrico (normalmente 1,8 V, nunca
   asumir 3,3/5 V);
3. USB ACM mediante gadget;
4. `pstore`/ramoops o mecanismo Samsung de último kmsg para fallos sin consola.

No actives `earlycon` con una dirección inventada. El UART0 downstream aparece
en `0x13800000`, pero está deshabilitado en el árbol base y depende de clock y
pinmux. Primero confirma el DT efectivo.

## Fase C: primera ejecución

Clasifica dónde se detiene:

| Síntoma | Zona probable |
|---|---|
| bootloader rechaza de inmediato | cabecera, firma/AVB, rollback, tamaño |
| reinicio antes de texto | DT incompatible, excepción temprana, watchdog |
| kernel imprime y se cuelga al iniciar SMP | clocks/PMU/PSCI/IRQ |
| `No working init found` | formato/arquitectura/permisos del initramfs |
| `/init` aparece sin `/dev` | devtmpfs/Kconfig/mount |
| shell funciona pero no hay UFS | módulo, PHY, calibración, clocks o IOMMU |

## Fase D: almacenamiento

Cuando aparezca UFS:

```sh
dmesg | grep -i -E 'ufs|scsi|sd '
cat /proc/partitions
blkid
mkdir -p /mnt/test
mount -o ro /dev/dispositivo /mnt/test
```

No ejecutes `fsck`, `mkfs`, `mount -o rw` ni escribas sobre particiones Android
durante bring-up.

## Fase E: periféricos

Integra uno por vez: USB, pantalla, táctil, Wi-Fi, audio, sensores y finalmente
energía/carga. Para cada uno conserva:

- nodo DT y revisión;
- clocks/resets/reguladores/GPIO usados;
- salida de probe y errores diferidos;
- cambios de config;
- prueba positiva y prueba de suspensión/reanudación.

Un driver que “hace probe” pero deja un regulador siempre activo aún no está
terminado.
