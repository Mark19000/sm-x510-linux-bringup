# 15. Laboratorio U11 offline, paso a paso

Esta guía es la ruta corta para repetir el trabajo sin mezclar versiones ni
escribir en la tablet. El objetivo didáctico es llegar a artefactos coherentes
para estudiar M2 (primer mensaje del kernel) y M3 (`/init` como PID 1).

## 1. Las tres identidades

| nombre | qué es | kernel | uso |
|---|---|---|---|
| U3 `X510XXU3BXDG` | source Android 14 anterior | 5.15.123 | referencia histórica, intacta |
| U11 `X510XXSBDZB4` sobre `X510XXU8DYJ4` | corresponding source Android 16 | 5.15.180 | mejor base de ingeniería disponible |
| U12 `X510XXUCEZE4` | firmware stock de la tablet | 5.15.189 | objetivo binario; source exacto pendiente |

U11 no sustituye a U3 y tampoco se presenta como source de EZE4. Los paquetes,
fuentes, builds, initramfs e informes viven en namespaces separados.

## 2. Inspeccionar antes de compilar

Desde `<project-root>`:

```sh
./scripts/setup-lima.sh
./scripts/build-osrc-u11-in-lima.sh \
  --release sources/osrc-releases/x510xxsbdzb4-u11-android16/wrapper \
  --inspect --run-id x510-u11-inspect-01
```

La extracción completa ocurre en ext4 dentro de Lima. Esto importa porque
APFS suele ser insensible a mayúsculas y el tar de Samsung contiene nombres
que colisionan. El wrapper verifica archives, symlinks, traversal, identidad
base+overlay y nunca ejecuta scripts arbitrarios del paquete.

## 3. Compilar el perfil fijo

```sh
./scripts/build-osrc-u11-in-lima.sh \
  --release sources/osrc-releases/x510xxsbdzb4-u11-android16/wrapper \
  --build --jobs 6 --run-id x510-u11-build-01
```

El script exige la identidad 5.15.180, el defconfig X510, nueve parches fijados
por hash, `Image`, `s5e8835.dtb`, DTBO r00/r01/r04 y 282 módulos. Cada intento
usa un directorio nuevo. Si algo no coincide, falla: no reutilices objetos de
otro run para hacerlo pasar.

Dos opciones se desactivan sólo en el perfil reproducible de bring-up:

- `IKHEADERS`, porque empaquetaba mtimes de pared;
- firma automática de módulos, porque generaba una clave nueva.

Ninguna es necesaria para que el kernel alcance `/init`. BTF del kernel y de
los módulos sigue activo. Las rutas de `__FILE__` se normalizan por la entrada
`KCPPFLAGS` del preprocesador. Este perfil prueba compilabilidad y coherencia; no intenta reproducir
las firmas privadas ni la `Image` binaria de Samsung.

El directorio `O=out-u11` se coloca directamente bajo la copia privada del
source. Esto hace que Kbuild use `srctree=..`: el compilador nunca recibe el
nombre absoluto y el bitcode ThinLTO no puede conservar un run-id distinto.

## 4. Entender los fallos ya encontrados

| síntoma | causa | regla que evita repetirlo |
|---|---|---|
| tar falla al final | en GNU tar `--no-recursion` era posicional | opciones antes de `--files-from` |
| hashes cambian entre runs | `__FILE__` guardaba el path en `.rodata` | macro prefix-map por `KCPPFLAGS` |
| detector dice éxito pese a encontrar paths | `grep -q` causó SIGPIPE con `pipefail` | primero se escribe la lista completa |
| initramfs cambia en APFS/ext4 | modos de raíz y symlinks diferentes | staging ext4 y modos normalizados |

Los fallos son datos útiles. Conserva log, run-id y hashes; corrige la receta y
repite desde cero en vez de parchear silenciosamente el resultado.

## 5. Construir early userspace

```sh
make u11-initramfs
```

Se producen tres perfiles reproducibles:

- `minimal`: BusyBox e `/init`, para demostrar PID 1;
- `ufs`: cierre de 28 módulos para almacenamiento;
- `usb`: diagnóstico con 45 módulos; se mide, pero no cabe en el límite stock.

El perfil UFS no significa que ya pueda montarse la tablet. Significa que las
dependencias conocidas están dentro del payload para una futura prueba
controlada.

## 6. Auditar módulos y preflight

```sh
make u11-modules-audit
make u11-preflight
# O las tres fases juntas:
make u11-offline
```

La auditoría comprueba procedencia del `vendor_boot` stock, metadata, grafo de
dependencias, orden de carga y cierres UFS/USB. El preflight verifica hashes,
identidades, 282 módulos, config de early userspace, initramfs y distancia DT.
`READY` significa coherencia offline, no permiso para flashear.

Para demostrar reproducibilidad se necesitan dos builds limpios:

```sh
python3 tools/u11_repro_compare.py \
  artifacts/u11/<run-a>/dist artifacts/u11/<run-b>/dist \
  --json reports/generated/u11-repro/reproducibility.json \
  --markdown reports/generated/u11-repro/reproducibility.md
```

## 7. Cómo leer M2 y M3

M2 depende sobre todo de que bootloader, formato de imagen, DT/DTBO, consola,
PSCI/GIC/timers y memoria reservada sean compatibles. U11 reduce mucho la
incertidumbre de kernel y DT, pero no demuestra el contrato AVB/rollback de la
unidad U12.

M3 añade initrd, `/init`, devtmpfs, consola y, si se necesita almacenamiento,
el cierre UFS. El initramfs ya es auditable; sigue faltando observar M2 en
hardware antes de atribuir un fallo a `/init`.

Regla final: mientras el preflight diga `physical_write: NO-GO`, no se crea una
imagen firmada, no se hace downgrade y no se ejecuta ningún comando de flash.
