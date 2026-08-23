# 10. Cuaderno de la unidad SM-X510 / EZE4

Este capítulo traduce los identificadores de la tablet a decisiones concretas.
La regla principal es sencilla: **modelo, AP, CSC y revisión de bootloader son
datos distintos**. No basta con que un archivo diga “Tab S9 FE”.

## Lo que ya sabemos

La pantalla de Android mostró:

```text
BP4A.251205.006.x510xxuceze4
```

Se separa en:

- `BP4A.251205.006`: compilación base de la plataforma Android;
- `X510XXUCEZE4`: versión AP/PDA de Samsung, normalizada a mayúsculas;
- `X510`: familia SM-X510, la variante Wi-Fi;
- `C`: binario de bootloader U12;
- sistema publicado: Android 16 / One UI 8.5.

La ficha reproducible está en `configs/target-sm-x510.env`. Compruébala con:

```sh
make target
```

## CSC confirmado

La tablet muestra:

```text
SAOMC_SM-x510_oxm_eux_16_0001EUX/EUX/
```

Se conserva con mayúsculas/minúsculas y sin insertar espacios. Su lectura para
este proyecto es:

- `EUX`: CSC activo para la Unión Europea;
- `OXM`: familia multi-CSC que contiene EUX;
- `16`: versión mayor de Android;
- `EUX/EUX/`: los slots regionales visibles coinciden en EUX.

La pareja completa que debemos conservar es:

```text
AP/PDA: X510XXUCEZE4
CSC:    X510OXMCEZE4
```

El CSC identifica la región/canal de distribución y no se podía reconstruir a
partir del AP por sí solo. Como método de comprobación futura, en la tablet se
encuentra en:

```text
Ajustes → Acerca de la tableta → Información de software
→ Versión de software del proveedor de servicio
```

Con ADB también se puede intentar, sin root:

```sh
adb shell getprop ro.boot.sales_code
adb shell getprop ro.csc.sales_code
adb shell getprop ro.bootloader
```

Los comandos ADB pueden devolver alguna propiedad vacía; la cadena SAOMC de la
interfaz de Android es suficiente en este caso.

## Estado de los dos insumos

El port necesita dos cosas diferentes:

1. El paquete `SM-X510 / EUX / X510XXUCEZE4`, CSC `X510OXMCEZE4`. **Ya está
   obtenido y extraído**.
2. El código fuente GPL publicado por Samsung para SM-X510/Android 16. Se busca
   en Samsung Open Source Release Center por `SM-X510` y por
   `X510XXUCEZE4`. Si no aparece, usa “Inquiry → Request for source codes” e
   incluye modelo, versión AP, Android 16 y región/CSC.

El firmware aporta las imágenes binarias reales; OSRC aporta código que podemos
compilar y auditar. Uno no sustituye al otro. A fecha de este cuaderno tenemos
el primero y seguimos buscando/solicitando el segundo.

La búsqueda pública se repitió el 23 de agosto de 2026 sin localizar una
entrada exacta EZE4. El propietario envió manualmente la consulta oficial para
SM-X510/X510XXUCEZE4/Android 16 y Samsung confirmó que la remitió al departamento
correspondiente. Si no responde en 24 horas, se reenviará desde la misma cuenta.
El proyecto no integra nada hasta recibir y conservar la respuesta o archivo
íntegro con fecha, nombre y SHA-256.

Texto sugerido para “Request for source codes”:

```text
Subject: Complete corresponding source request for SM-X510 / X510XXUCEZE4

Hello,

I own a Samsung Galaxy Tab S9 FE Wi-Fi, model SM-X510, with software version
X510XXUCEZE4 (Android 16), CSC X510OXMCEZE4 / EUX and build
BP4A.251205.006.

Please provide the complete corresponding source code for the GPL-licensed
Linux kernel and kernel modules shipped in this exact software release,
including the configuration, Device Tree sources, build scripts and any other
scripts used to control compilation and installation.

This request is for the corresponding open-source material; I am not asking
for Samsung signing keys or proprietary firmware.

Thank you.
```

Cuando llegue una respuesta, conserva el mensaje original, nombre del archivo,
fecha, URL y SHA-256. No sustituyas todavía `sources/wifi-kernel`: extrae la
nueva entrega en otra ruta y compara primero commit, versión, defconfig, DTS y
scripts de build.

No descargues ni uses paquetes “root”, `vbmeta` desactivados o kernels
preparados por terceros para esta fase. Queremos conservar un original limpio y
calcular su hash.

## Firmware exacto validado y extraído

El archivo conservado es:

```text
SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_fac.zip
MD5:    255c0e65e2ec62b0ba723612c1ece5a4
SHA256: 45a450875ce753e74d8183aa085837ada91cabe2832d9725a1567aa29b01d375
AP:     AP_X510XXUCEZE4_X510XXUCEZE4_MQB109790656_REV00_user_low_ship_MULTI_CERT_meta_OS16.tar.md5
```

Las imágenes relevantes ya están bajo `artifacts/stock/images/`; los hashes y
la procedencia quedan en `artifacts/stock/SHA256SUMS`,
`FIRMWARE_SHA256SUM` y `firmware-metadata.txt`.

Para reproducir la extracción desde el archivo descargado:

```sh
make stock FIRMWARE=/ruta/SAMFW.COM_SM-X510_EUX_X510XXUCEZE4_....zip
```

Esto ahorra más de 11 GB al transmitir el AP directamente hacia `tar` y extraer
únicamente las particiones de arranque. El `super.img` grande no se copia.

La primera comprobación sólo valida el identificador del nombre; el hash y la
procedencia validan el contenido. `extract-stock.sh` trabaja sobre el fichero
local y no escribe nada en la tablet.

## Arquitectura de las imágenes EZE4 observada

`tools/bootimg_info.py` registró los valores exactos en
`artifacts/stock/boot-layout.json`:

| Imagen | Cabecera | Contenido relevante |
|---|---:|---|
| `boot.img` | Android v4 | kernel 39 356 928 B, ramdisk 0 B |
| `init_boot.img` | Android v4 | ramdisk LZ4 legacy 2 486 802 B |
| `vendor_boot.img` | Android v4 | ramdisk 18 077 432 B, DTB 239 652 B, dos fragmentos |
| `dtbo.img` | tabla DTBO | tres overlays, después padding/pie AVB hasta 8 MiB |

El campo `os_version` de la cabecera de arranque indica 13.0.0 aunque Android
userspace sea 16; es un campo del kernel/GKI heredado y no contradice la versión
de la tablet.

El `Image` de referencia mide 995 328 bytes menos que el kernel stock. Tanto el
initramfs mínimo como el perfil UFS comprimido caben por tamaño de payload, pero
esto sólo elimina un error mecánico: no resuelve compatibilidad, AVB ni rollback.

## Por qué la fuente U3 sigue siendo útil

`X510XXU3BXDG` permite aprender la jerarquía DTS/DTSI, los nombres de placa y
los drivers S5E8835. También sirve para automatizar informes y practicar la
compilación. Pero entre U3/Android 14 y U12/Android 16 pueden haber cambiado
Kconfig, ABI de módulos, DTBO, cabeceras de boot y políticas AVB.

Por eso hay dos operaciones distintas:

```sh
make report VARIANT=wifi

# Sólo ensayo de compilación; salida no destinada a la tablet:
./scripts/build-reference-in-lima.sh
```

En un host Linux nativo puedes usar
`ALLOW_REFERENCE_BUILD=1 make build VARIANT=wifi`; en macOS usa el wrapper de
Lima mostrado arriba.

El build normal seguirá bloqueado hasta registrar una fuente compatible. Nunca
intentes bajar el bootloader de U12 a U3.

## Puerta de entrada al bring-up

Antes de M2 deben existir y quedar anotados:

- CSC `EUX` / multi-CSC `OXM` confirmado;
- hash del paquete de firmware exacto e imágenes extraídas (completado);
- DTB/DTBO extraídos (completado) y revisión de hardware identificada
  (pendiente en la unidad física);
- fuente kernel compatible o diferencias justificadas una por una;
- copia restaurable del firmware oficial;
- método de observación (UART o USB) y estado real del desbloqueo OEM.

Hasta entonces el trabajo seguro es análisis, build de referencia, initramfs y
reempaquetado offline marcado `UNSIGNED`; no flasheo.
