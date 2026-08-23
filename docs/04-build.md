# 4. Compilar el kernel U3 de referencia

## Qué estamos compilando

Hay que separar dos afirmaciones:

1. **El árbol U3 compila**: valida scripts, parches, configuración, DT y módulos.
2. **El resultado sirve en EZE4**: todavía no está demostrado, porque Samsung no
   ha publicado el árbol exacto U12/Android 16 y AVB invalida cualquier byte
   modificado.

El build de referencia ya completado usa el commit
`9a752a83347461b3785711760ba925fcabea3071` de `X510XXU3BXDG`. Produce un
`Image` de 38 361 600 bytes, 282 módulos y los overlays Wi-Fi r00, r01 y r04.
El registro de errores reales está en
[11-registro-build-referencia.md](11-registro-build-referencia.md).
Para el pipeline U11 Android 16, usa la receta aislada del
[capítulo 15](15-pipeline-u11-offline.md), no `make build`.

## Entorno reproducible en este Mac

El host es macOS ARM64 y APFS normalmente no distingue mayúsculas. El árbol
Samsung sí contiene nombres que colisionan, de modo que compilar directamente
en la carpeta compartida genera cambios fantasma y fallos difíciles de explicar.
La receta probada usa una VM Lima ARM64 con su disco ext4:

```sh
brew install lima
./scripts/setup-lima.sh
./scripts/fetch-image-tools.sh
./scripts/build-reference-in-lima.sh
```

La plantilla fija Ubuntu 26.04 ARM64, 6 CPU, 8 GiB de RAM y 35 GiB de disco. El
checkout y el directorio de objetos viven dentro de la VM; sólo los artefactos
terminados se copian al proyecto montado. La medición del 23 de agosto dejó
36 GiB libres en el host y 20 GiB en la VM. Hay margen para builds
incrementales, pero comprueba `df -h` antes de una reconstrucción limpia: el
espacio crítico es el disco virtual, no sólo lo liberado en macOS.

Para entrar a inspeccionar:

```sh
limactl shell gts9fe-build
cd ~/gts9fe-work/wifi-kernel
git status --short
```

En un PC Linux nativo instala como mínimo:

```sh
sudo apt update
sudo apt install -y git make bc bison flex build-essential libssl-dev \
  libelf-dev dwarves device-tree-compiler lz4 cpio rsync python3 file \
  clang lld llvm \
  gcc-aarch64-linux-gnu libc6-dev-arm64-cross diffstat kmod
```

## Qué hace la automatización

`build-reference-in-lima.sh`:

1. comprueba el commit exacto del checkout ext4;
2. aplica idempotentemente `patches/downstream/wifi/*.patch`;
3. activa explícitamente `ALLOW_REFERENCE_BUILD=1`;
4. mezcla `configs/gts9fe-linux.fragment` sobre el defconfig Samsung;
5. ejecuta `olddefconfig`;
6. construye `Image`, el DTB base objetivo, los tres DTBO de placa y módulos;
7. instala módulos reducidos con `INSTALL_MOD_STRIP=1`;
8. guarda configuración, metadatos y SHA-256 bajo
   `artifacts/kernel/wifi/reference-dist/`.

La excepción `ALLOW_REFERENCE_BUILD=1` es intencionadamente visible. Sin ella,
el script compara `X510XXU3BXDG` con el objetivo `X510XXUCEZE4` y se detiene.

## Ejecución manual dentro de Linux

Para aprender cada capa o cambiar una variable:

```sh
DEVICE_VARIANT=wifi ./scripts/apply-patches.sh

ALLOW_REFERENCE_BUILD=1 DEVICE_VARIANT=wifi \
  KERNEL_DIR="$HOME/gts9fe-work/wifi-kernel" \
  KERNEL_OUT="$HOME/gts9fe-work/obj" \
  DIST_DIR="$PWD/artifacts/kernel/wifi/reference-dist" \
  JOBS=6 ./scripts/build-downstream.sh 2>&1 | tee artifacts/logs/reference-kernel-build.log
```

Variables útiles:

```sh
JOBS=4                         # reduce presión de RAM
CLANG_ROOT=/ruta/al/toolchain  # usa un Clang concreto
INSTALL_MOD_STRIP=0            # conserva debug; ocupa casi diez veces más
```

El árbol declara los overlays mediante una variable `always` obsoleta. Un
`make dtbs` podía terminar correctamente sin construir ninguno. El script pide
los tres objetivos `.dtbo` de forma explícita y falla si falta uno; éste es un
ejemplo importante de por qué “exit 0” no basta como prueba.

## Verificaciones posteriores

```sh
DIST=artifacts/kernel/wifi/reference-dist
file "$DIST/Image"
grep -E 'CONFIG_(DEVTMPFS|BLK_DEV_INITRD|SERIAL_SAMSUNG_CONSOLE)=' \
  "$DIST/kernel.config"
cat "$DIST/BUILD-METADATA"
(cd "$DIST" && sha256sum -c SHA256SUMS)
find "$DIST/dtbs/samsung/gts9fewifi" -name '*.dtbo' -print
find "$DIST/modules-root" -name '*.ko' | wc -l
```

Los metadatos Kbuild de fecha, usuario, host y contador están fijados. Dos
enlaces incrementales dieron el mismo `Image` y SHA-256; eso demuestra la
reproducibilidad del kernel en esta VM con sus objetos y clave de módulos
conservados. Una reconstrucción desde cero aún debe fijar el toolchain y tratar
la clave autogenerada antes de afirmar reproducibilidad universal.
`BUILD-METADATA` explica con qué entradas se hizo cada salida.

## Construir el contenedor DTBO

```sh
DEVICE_VARIANT=wifi \
  DIST_DIR="$PWD/artifacts/kernel/wifi/reference-dist" \
  ./scripts/build-dtbo.sh
```

El contenedor preserva la tabla observada en stock: r00 para hwrev 0, r01 para
1–3 y r04 para 4–32. El script extrae de nuevo el resultado y compara cada blob.
Sigue siendo `dtbo-unsigned.img`: no incluye el pie AVB Samsung ni padding hasta
8 MiB y no debe flashearse.

## Reempaquetado correcto para Android boot v4

En EZE4 el kernel está en `boot.img`, pero su ramdisk mide cero. El ramdisk real
está en `init_boot.img`; por eso se sustituyen por separado. El `magiskboot`
extraído del APK oficial es ELF/ARM64 y se ejecuta dentro de Lima, no en macOS:

```sh
./scripts/repack-reference-in-lima.sh
```

El wrapper equivale, dentro de Linux, a:

```sh
MAGISKBOOT=sources/toolchain/magisk-v30.7/magiskboot-arm64 \
  ./scripts/repack-boot.sh \
  artifacts/stock/images/boot.img \
  artifacts/kernel/wifi/reference-dist/Image \
  artifacts/candidates/reference/boot-UNSIGNED.img

MAGISKBOOT=sources/toolchain/magisk-v30.7/magiskboot-arm64 \
  ./scripts/repack-init-boot.sh \
  artifacts/stock/images/init_boot.img \
  artifacts/initramfs/wifi/gts9fe-initramfs.cpio \
  artifacts/candidates/reference/init_boot-UNSIGNED.img
```

`magiskboot` conserva la estructura de la cabecera, y un desempaquetado de
control confirmó que `Image` y `cpio` vuelven idénticos. Aun así, `avbtool`
verifica el VBMeta Samsung pero rechaza el descriptor hash de cada candidato:
es exactamente lo esperado tras modificar su contenido sin la clave Samsung.
**No se arregla desactivando vbmeta al azar.**

## Fallos ya absorbidos por los parches

- Clang 21 endureció diagnósticos y prototipos antiguos.
- Varios callbacks vendor tenían tipos de retorno incompatibles.
- Había declaraciones ausentes en Wi-Fi, RCD y cpupm.
- El fallback `devfreq` llamaba una API inexistente.
- Un callback Novatek podía salir sin valor y Type-C usaba nombres retirados.
- Dos opciones de depuración provocaban deliberadamente crash/FPSIMD test.
- APFS case-insensitive no puede representar el checkout fielmente.
- `dtbs` omitía silenciosamente los overlays de placa.

Los warnings restantes y su clasificación están en el registro del build. No
los ocultes globalmente: distingue entre ruido heredado, riesgo de stack y una
dependencia externa realmente ausente.

Terminar el build sólo demuestra M1. M2 exige un mensaje capturado desde la
tablet; no se puede inferir desde el compilador.
