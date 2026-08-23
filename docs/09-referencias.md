# 9. Referencias y procedencia

## Fuentes primarias

- [Samsung Open Source Release Center](https://opensource.samsung.com/): fuente
  oficial que debe buscarse por modelo y versión exacta.
- [Historial oficial de software SM-X510](https://doc.samsungmobile.com/SM-X510/029471240301/spa-us.html),
  usado para contrastar la compilación de la unidad.
- [Firmware SM-X510 EUX X510XXUCEZE4](https://samfw.com/firmware/SM-X510/EUX/X510XXUCEZE4),
  índice secundario útil para identificar AP/CSC y binario; el paquete debe
  contrastarse con el CSC real y su hash antes de analizarlo.
- [Fuente stock SM-X510 X510XXU3BXDG](https://github.com/underdog54/android_kernel_samsung_gts9fewifi/tree/stock),
  espejo comunitario usado para el análisis Wi-Fi.
- [Fuente SM-X516 X516BXXU7CYE1](https://github.com/Fede2782/android_kernel_samsung_gts9fe),
  espejo comunitario usado para contrastar la variante 5G.
- [Linux mainline](https://git.kernel.org/pub/scm/linux/kernel/git/torvalds/linux.git/),
  snapshot fijado por hash en `fetch-sources.sh`.
- [Documentación AOSP para compilar kernels](https://source.android.com/docs/setup/build/building-kernels).
- [Android Verified Boot / `avbtool` oficial](https://android.googlesource.com/platform/external/avb/),
  fijado localmente desde la rama `android16-release`.
- [Magisk v30.7 oficial](https://github.com/topjohnwu/Magisk/releases/tag/v30.7),
  procedencia del `magiskboot-arm64` usado únicamente para reempaquetado offline.

Los archivos descargados y el `avbtool.py` extraído tienen sus SHA-256 fijados en
`configs/toolchain-reference.sha256`; se comprueban desde la raíz del proyecto
antes de sustituir o actualizar una herramienta.
- [Manifest Android common 13 / 5.15](https://android.googlesource.com/kernel/manifest/+/refs/heads/common-android13-5.15/default.xml).
- [Documentación del kernel sobre initramfs](https://docs.kernel.org/filesystems/ramfs-rootfs-initramfs.html).
- [Documentación de overlays Device Tree](https://docs.kernel.org/devicetree/overlay-notes.html).
- [Especificación Device Tree](https://www.devicetree.org/specifications/).

## Cómo citar un hallazgo

Registra repositorio, commit y ruta. Ejemplo:

```text
Fuente: android_kernel_samsung_gts9fewifi
Commit: 9a752a83347461b3785711760ba925fcabea3071
Ruta: arch/arm64/boot/dts/exynos/s5e8835.dts
Nodo: /ufs@0x13500000
Observación: compatible samsung,exynos-ufs; dirección 0x13500000
```

No cites sólo una línea de un DTS decompilado como especificación eléctrica. Un
hallazgo sólido combina fuente, DT efectivo, log del driver y prueba en hardware.
