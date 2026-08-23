# 13. Staging OSRC para SM-X510 / Android 16 / U11

Este flujo prepara el código OSRC `X510XXSBDZB4` de la unidad `SM-X510`
(Android 16, bootloader U11) sin mezclarlo con la fuente Wi-Fi U3 que se conserva en
`sources/wifi-kernel`. No modifica el firmware extraído ni publica imágenes
en `artifacts/` salvo un registro nuevo por ejecución.

## Qué se conoce del release

La entrega OSRC observada está compuesta por:

- un wrapper base con `Kernel.tar.gz`, `Platform.tar.gz` y `README`;
- un overlay regional `X510XXSBDZB4`, con raíz
  `SM-X510_EUR_16_XX_X510XXSBDZB4/Kernel` y su `README`;
- el README indica usar primero la base `X510XXU8DYJ4` y después aplicar el
  overlay.

El árbol base declara kernel 5.15.180, `s5e8835-gts9fewifixx_defconfig`,
`clang-r450784d`, `PLATFORM_VERSION=13` y `TARGET_SOC=s5e8835`. Estos datos se
registran como evidencia y no sustituyen la validación del commit, config,
DTS y scripts del paquete que se reciba.

## Staging seguro

La entrada se copia sin abrir al disco ext4 de la VM Lima. La extracción del
ZIP, de `Kernel.tar.gz`, `Platform.tar.gz` y de los ZIP anidados ocurre
únicamente bajo `$HOME/osrc-u11-work/<run-id>` dentro del guest. El árbol
Platform se conserva separado y se inventaría para análisis; nunca se usa como
entrada de la compilación del kernel.
Los archivos comprimidos que formen parte del código ya extraído (por ejemplo,
fixtures de tests) se conservan como archivos normales y no se abren de forma
recursiva.

Primero prepara o arranca la VM y después ejecuta sólo la inspección:

```sh
./scripts/setup-lima.sh
OSRC_RELEASE=/ruta/SM-X510.zip \
  ./scripts/build-osrc-u11-in-lima.sh
```

También se puede entregar un directorio ya descargado. No uses un archivo
`.part`; el wrapper lo rechaza por nombre antes de copiarlo. No apuntes a
`sources/wifi-kernel`, a `artifacts/kernel/wifi` ni a otra salida existente.
La extracción valida traversal, tipos especiales, hardlinks y symlinks: sólo
se permiten symlinks relativos que permanezcan dentro del árbol.

El inventario registra `Kernel.tar.gz`, el overlay, raíces que contienen
`Makefile`/`build_kernel.sh`, defconfigs, configs, referencias de commit y
rutas de toolchain. Los ficheros pequeños de evidencia se copian a
`artifacts/u11/<run-id>/`; los fuentes, objetos, tarballs y salidas permanecen
en ext4. Un run-id repetido se rechaza para no sobrescribir un registro previo.

## Compilación fija

La inspección no ejecuta scripts entregados por terceros. Cuando encuentra el
README con los marcadores exactos `X510XXSBDZB4` y `X510XXU8DYJ4`, el wrapper
copia la base a `u11-composite/Kernel` dentro del guest y aplica allí sólo el
árbol `.../X510XXSBDZB4/Kernel`. Los modos originales se restauran después de
aplicar el overlay. Los dos árboles originales quedan separados y el composite
exacto tampoco se usa como árbol de trabajo: el modo build crea una copia
privada en `build-source/Kernel`, porque algunos Makefiles Samsung generan
ficheros dentro del source incluso usando `O=`. El build nunca usa la base U8
sola. El `overlay-manifest.txt` contiene el SHA-256 de cada fichero aplicado.

Cuando el layout y el composite hayan sido revisados, ejecuta el perfil fijado
del repositorio:

```sh
./scripts/build-osrc-u11-in-lima.sh \
  --release /ruta/SM-X510.zip \
  --build --jobs 6 --run-id x510-u11-prueba-01
```

No se acepta un comando de shell aportado mediante variables de entorno. El
perfil exige kernel 5.15.180, el defconfig de X510, los nueve parches con sus
SHA-256, el DTB base, exactamente los tres DTBO conocidos y 282 módulos. Fija
usuario, host, fecha, semilla Kconfig y rutas de depuración. También rechaza
una `Image` o un `.ko` que conserve la ruta física del run.

`CONFIG_IKHEADERS` y la firma automática de módulos se desactivan en este
perfil de bring-up: introducían respectivamente mtimes y una clave nueva. Los
paths de `__FILE__` se normalizan mediante `KCPPFLAGS`; BTF del kernel y de los
módulos se mantiene. Estas decisiones no pretenden reproducir el binario
firmado de Samsung.

El `O=out-u11` es hijo directo de la copia privada del source. Así Kbuild usa
`srctree=..` y Clang recibe nombres de fuente relativos; un microbuild de EMS
confirmó cero apariciones del run físico. Con un `O=` hermano, ThinLTO conservaba
la ruta absoluta aunque hubiera prefix-map.

Si el release trae más de una raíz de kernel, falta el README/overlay exacto o
se reutiliza un run-id, el modo `--build` se detiene. No infiere un overlay
arbitrario, no compila la base U8 sola y no sobreescribe el checkout U3.

## Evidencia y fallos

Cada ejecución conserva:

- `release-layout.json`: layout, configs, toolchain y referencias de commit;
- `archive-manifest.json`: tarballs/ZIP procesados y los que quedaron sólo
  inventariados;
- `overlay-manifest.txt` y `composite-layout.json`: composición U11 y hashes;
- `build-metadata.txt`: raíz elegida, defconfigs, scripts y estado Git;
- `u11-build.log`, `guest-console.log` y `STATUS`.

Un fallo no limpia ni reutiliza otra ejecución. Revisa el log y el estado del
run en ext4 antes de repetir con un nuevo `--run-id`. Este flujo no autoriza
firmar, instalar ni escribir una imagen en la tableta.

Los intentos `fixed1` a `fixed4` se conservan como pruebas negativas. Encontraron
una incompatibilidad posicional de GNU tar, rutas absolutas en ThinLTO,
un falso negativo del detector causado por SIGPIPE y, finalmente, demostraron
que las rutas estaban en `.rodata`/`__FILE__` y no en BTF. Cada directorio
contiene un `FAILURE.md`; ninguno es candidato físico.

## Resultado comprobado

El composite exacto se verificó contra una reconstrucción independiente: cero
diferencias de contenido, modo o symlink. Después se creó un árbol privado,
se aplicaron los nueve parches Wi-Fi y se compiló con Clang 21 ARM64. El build
completo produjo kernel 5.15.180, `Image`, DTB base, los DTBO r00/r01/r04 y 282
módulos, con salida 0. Los hashes, logs y pruebas negativas por parche están en
`artifacts/u11/x510xxsbdzb4-u11-clang21-20260823`; el análisis se explica en
`docs/14-resultados-u11-u3-eze4.md`.
