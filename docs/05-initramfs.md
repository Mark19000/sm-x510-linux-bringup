# 5. Construir y entender el initramfs

## Qué resuelve

El initramfs es un pequeño sistema de archivos que el kernel desempaqueta en
RAM antes de acceder a Android o a una distribución. Linux ejecuta `/init` como
PID 1. Así podemos intentar `kernel → /init → shell` sin escribir UFS, sin
systemd y sin depender todavía de una raíz persistente.

Nuestro `/init` monta `/proc`, `/sys`, `/dev` y `/run`, imprime diagnóstico,
carga sólo los módulos declarados y termina en una shell. Una raíz indicada con
`gts9fe.root=` se monta siempre en sólo lectura.

## BusyBox ARM64 estático

Dentro de Linux/Lima:

```sh
./scripts/build-busybox.sh
file artifacts/busybox/busybox
cat artifacts/busybox/SOURCE_COMMIT
(cd artifacts/busybox && sha256sum -c SHA256SUMS)
```

La receta fija BusyBox 1.36.1 al commit
`1a64f6a20aaf6ea4dbba68bbfa8cc1ab7e5c57c4`, habilita sólo 27 applets y
verifica cada opción. Esto evita dos fallos ya encontrados: `tc` no compila con
cabeceras modernas porque su UAPI CBQ desapareció, y el `allnoconfig` de esta
versión ignoraba silenciosamente booleanos del miniconfig.

La salida probada es AArch64, estática y mide 1 253 440 bytes. Un BusyBox
dinámico fallaría por no tener cargador/bibliotecas; uno x86_64 daría
`Exec format error`.

## Perfiles de módulos U3 de referencia

El valor seguro por defecto es no copiar módulos:

```sh
DEVICE_VARIANT=wifi MODULES_MODE=none \
  INITRAMFS_OUT="$PWD/artifacts/initramfs/wifi" \
  ./scripts/build-initramfs.sh
```

Las rutas `artifacts/initramfs/wifi*` de este capítulo pertenecen al kernel U3.
Los perfiles U11, sus tamaños y sus guardas están separados en el
[capítulo 15](15-pipeline-u11-offline.md).

Perfiles disponibles:

| Perfil | Contenido | Uso |
|---|---|---|
| `none` | sólo BusyBox y `/init` | primer intento y máxima probabilidad de caber |
| `deps` | cierre de dependencias de la lista solicitada | llegar a un driver modular concreto |
| `all` | todos los módulos instalados | diagnóstico offline; normalmente demasiado grande |

Para preparar UFS downstream:

```sh
DEVICE_VARIANT=wifi MODULES_MODE=deps \
  MODULES_ROOT="$PWD/artifacts/kernel/wifi/reference-dist/modules-root/lib/modules" \
  MODULES_LIST="$PWD/configs/initramfs-modules.conf" \
  INITRAMFS_OUT="$PWD/artifacts/initramfs/wifi-ufs" \
  ./scripts/build-initramfs.sh
```

La lista pide `ufs-exynos-core`; `modprobe --show-depends` calcula el cierre
real, copia 28 módulos del mismo `kernelrelease`, regenera `modules.dep` y deja
la lista que `/init` cargará en `/etc/gts9fe-modules`. No copies `.ko` a mano:
puedes olvidar dependencias o mezclar módulos de otro kernel.

Para estudiar USB ACM existe una lista separada:

```sh
DEVICE_VARIANT=wifi MODULES_MODE=deps \
  MODULES_ROOT="$PWD/artifacts/kernel/wifi/reference-dist/modules-root/lib/modules" \
  MODULES_LIST="$PWD/configs/initramfs-modules-usb.conf" \
  INITRAMFS_OUT="$PWD/artifacts/initramfs/wifi-usb" \
  ./scripts/build-initramfs.sh
```

El cierre de `phy-exynos-usbdrd-super` y `dwc3-exynos-usb` arrastra 45 módulos.
Es una evidencia de dependencias, no un candidato: su LZ4 supera el ramdisk
stock. La siguiente hipótesis es integrar sólo glue/PHY esenciales en `Image`,
medir el crecimiento y volver a comprobar el límite de `boot`.

## Salidas y reproducibilidad

Cada perfil genera:

- `gts9fe-initramfs.cpio`, fácil de inspeccionar;
- `gts9fe-initramfs.cpio.gz`, gzip sin timestamp;
- `gts9fe-initramfs.cpio.lz4`, si `lz4` está instalado, en el formato legacy
  usado por las imágenes stock;
- `SHA256SUMS`.

El script ordena entradas y normaliza uid, gid y mtime. Dos ejecuciones con las
mismas entradas ya dieron archivos idénticos byte por byte. Valores medidos:

| Perfil | CPIO | LZ4 legacy | Margen respecto al ramdisk stock (2 486 802 B) |
|---|---:|---:|---:|
| mínimo | 1 266 176 B | 690 117 B | 1 796 685 B |
| UFS/deps | 6 589 952 B | 2 124 194 B | 362 608 B |
| USB/deps | 10 065 920 B | 3 036 866 B | **excede 550 064 B** |

El margen compara payload comprimido, no autoriza el flasheo. La imagen final
tiene cabecera, alineación y AVB, y el perfil UFS queda demasiado ajustado para
añadir herramientas alegremente.

Comprueba e inspecciona:

```sh
(cd artifacts/initramfs/wifi && sha256sum -c SHA256SUMS)
cpio -it < artifacts/initramfs/wifi/gts9fe-initramfs.cpio
cpio -it < artifacts/initramfs/wifi-ufs/gts9fe-initramfs.cpio | \
  grep 'lib/modules/.*\.ko$'
```

## Parámetros entendidos por `/init`

- sin opciones: shell sobre la consola abierta por el kernel;
- `gts9fe.usb_debug=1`: intenta configurar un gadget USB ACM y abre una shell
  en `/dev/ttyGS0`; requiere glue Exynos, PHY, DWC3 y ConfigFS funcionando;
- `gts9fe.root=/dev/...`: monta la raíz en **sólo lectura** bajo `/newroot` y
  permanece en rescate;
- `gts9fe.switch_root=1`: permite el cambio sólo junto a una raíz montada y un
  `/newroot/sbin/init` ejecutable. Se rechaza si también se pidió la shell USB.

No uses `gts9fe.root` antes de M5 ni `gts9fe.switch_root=1` en la primera prueba
de almacenamiento. Los nombres `/dev/sdX` pueden cambiar;
primero registra los UUID y el mapa de particiones.

## Qué debe estar integrado (`=y`)

Todo lo necesario antes de poder cargar módulos debe estar dentro de `Image`:
soporte initrd, devtmpfs, una consola y la infraestructura básica de bloques.
La configuración construida confirma `CONFIG_BLK_DEV_INITRD=y`,
`CONFIG_DEVTMPFS=y`, `CONFIG_DEVTMPFS_MOUNT=y`, consola Samsung, DWC3 y gadget
USB ConfigFS/ACM. El controlador UFS Exynos queda modular en este árbol y por
eso existe el perfil `deps`.

## Diagnóstico del primer arranque

M3 queda demostrado sólo si una consola física muestra algo como:

```text
[gts9fe-init] iniciando early userspace
[gts9fe-init] kernel: Linux ... aarch64
[gts9fe-init] cmdline: ...
[gts9fe-init] shell de rescate...
```

Si aparece `No working init found`, comprueba que `/init` sea 0755, empiece por
`#!/bin/busybox sh` y que `/bin/busybox` sea AArch64 estático. Si falla
`modprobe`, registra el módulo exacto, `uname -r`, `modules.dep` y el mensaje de
símbolo/versión; no lo soluciones cargando un módulo de otra compilación.
