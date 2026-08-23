# 1. Arquitectura de arranque

## Las piezas

Un PC descubre mucho hardware por buses enumerables. Un SoC embebido no: Linux
necesita un Device Tree que describa direcciones, interrupciones, relojes, GPIO y
relaciones entre dispositivos.

En esta tablet intervienen, simplificando:

```text
Boot ROM -> cargadores Samsung -> verificación AVB
                                  |
                                  +-> boot: kernel/ramdisk según cabecera
                                  +-> vendor_boot: ramdisk vendor y/o DTB
                                  +-> dtbo: overlays de modelo y revisión
                                  |
                                  `-> kernel + DT efectivo + initramfs
                                                     |
                                                     `-> /init (PID 1)
```

La configuración publicada declara Android boot image header v4, construye
`Image`, `s5e8835.dtb` y `dtbo.img`, y admite ramdisk LZ4. No se deben copiar esos
parámetros a ciegas: `extract-stock.sh` permite inspeccionar el firmware exacto.

## DTB frente a DTBO

- **DTS/DTSI**: fuente de texto que leen las personas.
- **DTB**: representación binaria que recibe el kernel.
- **DTBO**: uno o más overlays binarios que modifican el árbol base.
- **DT efectivo**: resultado final que realmente vio el kernel tras aplicar la
  selección de bootloader.

El repositorio Samsung contiene un `s5e8835.dts` grande. La X510 Wi-Fi aporta
tres overlays (r00, r01 y r04) y la referencia X516 5G aporta cuatro (añade
r02). Son fuentes decompiladas: usan phandles numéricos,
nombres no normalizados y propiedades privadas. Sirven como documentación del
hardware, pero no como DT listo para enviar a mainline.

## Kernel downstream y mainline

**Downstream** es el kernel 5.15 modificado por Android/Samsung. Tiene los
drivers privados necesarios y es el camino realista al primer shell. **Mainline**
es el árbol upstream de Linux. Tiene mejor mantenibilidad, pero en el snapshot
analizado no contiene soporte S5E8835/Exynos 1380.

La estrategia es deliberadamente incremental:

1. arrancar downstream con un initramfs Linux;
2. identificar cada dependencia y firmware;
3. escribir bindings y drivers upstream por subsistema;
4. crear un DTS mainline limpio sólo cuando clocks, pinctrl e interrupciones
   básicos tengan soporte;
5. mantener Android recuperable mientras se sustituye hardware bloque a bloque.

## Qué ocurre al ejecutar `/init`

El kernel descomprime un archivo `cpio` en `rootfs`. Si encuentra `/init`, lo
ejecuta como proceso 1. Ese programa monta `/proc`, `/sys` y `/dev`, descubre
dispositivos y, opcionalmente, monta una raíz persistente y llama a
`switch_root`. En nuestro hito M3 no hace falta una distro: BusyBox estático y el
script `initramfs/rootfs/init` bastan para demostrar que kernel, memoria, DT y
early userspace llegaron suficientemente lejos.
