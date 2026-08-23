# 12. Preflight de la primera prueba física

## Veredicto actual: NO-GO

Los artefactos de referencia sirven para el laboratorio offline, pero **no se
deben flashear**. La puerta no se abre porque “caben” o porque compilan; se abre
sólo cuando todas las evidencias de identidad, recuperación, observabilidad y
autenticidad están completas.

| Puerta | Evidencia actual | Estado |
|---|---|---|
| modelo/firmware | SM-X510, EUX/OXM, X510XXUCEZE4, U12 | completa |
| copia oficial | ZIP y particiones extraídas con hashes | completa |
| formato | boot/init_boot/vendor_boot v4 medidos | completa |
| build offline | Image, DTB/DTBO, 282 módulos, initramfs | completa |
| integridad del empaquetado | round trip byte a byte | completa |
| AVB stock | firma RSA4096 y digest verifican | completa |
| AVB candidato | digest no coincide, como era previsible | **bloquea** |
| fuente kernel EZE4 | sólo existe referencia U3 conocida | **bloquea** |
| revisión efectiva | tabla r00/r01/r04 conocida, elección física no | **bloquea** |
| consola observable | UART/USB/pstore sin validar en la unidad | **bloquea** |
| desbloqueo/Knox | estado y consecuencias no aceptados/registrados | **bloquea** |
| restauración ensayada | firmware disponible, procedimiento no probado | **bloquea** |

Un único `bloquea` mantiene el veredicto NO-GO.

## Recogida segura y de sólo lectura

Con Android arrancado y depuración USB autorizada:

```sh
./scripts/collect-device.sh
```

Después revisa, no sólo recolectes:

```sh
sed -n '1,120p' reports/device-*/identity.txt
sed -n '1,220p' reports/device-*/proc-cmdline.txt
sed -n '1,220p' reports/device-*/partitions-by-name.txt
file reports/device-*/running.dtb
```

Debes confirmar otra vez `SM-X510`, `X510XXUCEZE4`, bootloader U12 y EUX. Si
`running.dtb` está vacío por permisos de Android, se anota como dato ausente; no
se adivina el overlay.

No uses en esta fase `adb root`, `dd`, escrituras a `/dev/block`, cambios de
slot, Odin/Heimdall ni comandos de reboot a modos de actualización.

## Evidencia offline que debe pasar en cada build

```sh
make test

DIST=artifacts/kernel/wifi/reference-dist
(cd "$DIST" && sha256sum -c SHA256SUMS)
(cd artifacts/busybox && sha256sum -c SHA256SUMS)
(cd artifacts/initramfs/wifi && sha256sum -c SHA256SUMS)
./scripts/verify-avb-candidates.sh
```

El último comando **debe** decir dos cosas a la vez: stock válido y candidato
rechazado por digest. Que un candidato AVB-inválido sea rechazado es una prueba
del verificador, no una autorización para desactivar AVB.

Registra además:

```sh
cat "$DIST/BUILD-METADATA"
cat artifacts/stock/boot-layout.json
cat artifacts/candidates/reference/SHA256SUMS
```

## Condiciones necesarias antes de diseñar un intento

1. Obtener y comparar el código OSRC correspondiente a EZE4, o justificar cada
   divergencia que afecte DT/Kconfig/ABI. La referencia U3 no cumple esta puerta.
2. Identificar la revisión/overlay de la unidad mediante evidencia del
   bootloader o DT efectivo.
3. Documentar el estado real de OEM Unlock, el borrado de datos y la posible
   alteración irreversible de Knox. La decisión corresponde al propietario.
4. Disponer de una ruta de restauración oficial compatible con U12, alimentación
   estable, cable fiable y otro equipo desde el que recuperarla.
5. Tener una salida observable anterior a UFS: consola válida, USB ACM probado
   en esa ruta o almacenamiento persistente de logs entendido.
6. Resolver AVB con el flujo admitido por un bootloader legítimamente
   desbloqueado. No usar claves Samsung inexistentes, imágenes “vbmeta disable”
   de terceros ni downgrade.
7. Definir qué única variable cambia y cuál es el criterio temporal de aborto.

## Diseño del primer intento cuando todas las puertas estén verdes

El primer objetivo será únicamente M2/M3: mensaje temprano y ejecución de
`/init`. Debe usar el initramfs `MODULES_MODE=none`, sin raíz persistente y sin
drivers de carga experimentales. UFS, pantalla y Wi-Fi no forman parte de la
prueba inicial.

Antes de cualquier escritura futura crea una ficha inmutable:

```text
ID del intento:
Fecha UTC:
Modelo/AP/CSC/bootloader/hwrev:
Hash firmware oficial:
Commit fuente exacta y patchset_sha256:
SHA Image, DTB, DTBO, CPIO e imagen contenedora:
Resultado de AVB y política del bootloader:
Canal de consola y prueba previa:
Procedimiento de restauración y equipo disponible:
Único cambio:
Timeout y condición de aborto:
```

Tras el intento se adjunta el log bruto aunque esté vacío. Un reinicio sin log
no demuestra que “el kernel no funciona”; sólo localiza el fallo antes del
primer canal observable.

## Señales de parada inmediata

- el modelo, AP, CSC, binario o tamaño no coincide;
- aparece cualquier intención de bajar U12 a U3;
- el archivo no tiene el hash anotado en la ficha;
- el verificador AVB falla por una razón distinta a la esperada;
- no existe copia oficial/restauración o se depende de una descarga posterior;
- la tablet está caliente, con batería inestable o sin alimentación fiable;
- se propone probar simultáneamente kernel, DTBO, vbmeta y rootfs nuevos.

Ante cualquiera de estas condiciones se vuelve al análisis offline. Parar en
preflight es un resultado correcto: evita convertir una incógnita técnica en
una pérdida de datos o un dispositivo no recuperable.
