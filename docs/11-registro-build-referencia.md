# 11. Registro del build downstream de referencia

## Resultado reproducido

El 22 de agosto de 2026 se completó el kernel Wi-Fi publicado para
`X510XXU3BXDG`, commit `9a752a83347461b3785711760ba925fcabea3071`:

- kernel `5.15.123-g9a752a833474-dirty`;
- `Image` ARM64 de 38 361 600 bytes;
- DTB base `s5e8835.dtb`;
- overlays SM-X510 `r00`, `r01` y `r04`;
- 282 módulos, con `modpost`, firma, `strip` y `depmod`;
- enlace LTO/BTF y procedimiento FIPS Samsung completados;
- código de salida final 0.

El 23 de agosto se repitió además `scripts/build-all-reference.sh` completo:
checkout ext4, aplicación idempotente de parches, kernel, módulos, BusyBox,
dos initramfs, DTBO, reempaquetado y AVB terminaron con código 0. Después se
verificaron de nuevo todos los manifiestos. Tras el endurecimiento posterior,
la suite ampliada contiene 88 pruebas host-only, incluidas las guardas OSRC U11,
comparación de árboles, seguridad/adversariales, semántica DTS y herramientas.

Tras fijar usuario, host, contador y timestamp Kbuild al commit fuente, dos
enlaces consecutivos produjeron el mismo `Image`, SHA-256
`16ec4fdba131639f41d3ccd8c724be561c7e7e11cccf6c99539d193ad910cd9c`.
Esto demuestra reproducibilidad incremental en la VM conservando su clave de
firma de módulos; una reconstrucción desde un disco vacío todavía debe comparar
también la clave autogenerada antes de afirmar reproducibilidad universal.

El sufijo `dirty` es esperado: representa la serie de parches aplicada sobre el
commit publicado. No significa que el archivo esté corrupto. La salida y el log
están en `artifacts/kernel/wifi/reference-dist` y
`artifacts/logs/reference-kernel-build.log`.

Este éxito valida el proceso de compilación, **no la compatibilidad con EZE4**.
La tablet usa Android 16/U12 y la fuente es Android 14/U3.

## Entorno probado

| Elemento | Valor |
|---|---|
| Host | macOS ARM64, Apple Silicon |
| VM | Lima/VZ, Ubuntu 26.04 ARM64 |
| Recursos | 6 CPU, 8 GiB RAM, disco 35 GiB |
| Compilador | Clang/LLD 21.1.8 |
| `make` / DTC | 4.4.1 / 1.7.2 |
| Árbol y objetos | ext4 dentro de la VM |
| Salida | carpeta del proyecto montada mediante virtiofs |

El checkout del kernel no se puede construir de forma fiable sobre el APFS
normal de macOS: Linux contiene nombres que sólo difieren en mayúsculas y el
checkout aparece modificado por colisiones. Por eso los objetos y la fuente de
compilación viven bajo `$HOME/gts9fe-work` dentro de la VM.

## Fallos encontrados y solución

| Fase/síntoma | Causa | Solución reproducible |
|---|---|---|
| APFS muestra cambios que no hicimos | filesystem case-insensitive | clonar y compilar dentro del disco ext4 de Lima |
| `sysbusy` y `filemap` fallan con prototipos | C antiguo aceptado por el toolchain Samsung | tipos explícitos y compatibilidad Clang 21 (`0002`) |
| KVM usa `clidr` sin inicializar | análisis de flujo más estricto | inicialización segura (`0002`) |
| `exynos-devfreq.h` omite tipo de retorno | declaración C heredada | retorno `int` explícito (`0003`) |
| Wi-Fi, RCD y cpupm tienen declaraciones inválidas | tipos implícitos y uso antes de validar error | `bool`/`int` y orden correcto (`0004`) |
| QoS Mali omite tipo | C implícito | retorno `bool` (`0005`) |
| UFS no encuentra headers `s5e8835` | faltaba `TARGET_SOC=s5e8835` | exportarlo como hace `build_kernel.sh` |
| devfreq consulta `buf` no inicializado | fallback vendor incompleto | eliminar sólo el fallback roto (`0006`) |
| cargador SM5714 usa valor sin inicializar | flujo de error incompleto | inicializar propiedad (`0008`) |
| test Samsung viola `-mgeneral-regs-only` | módulo deliberado de crash/FPSIMD | no construir ese test durante bring-up (`0008`) |
| Novatek devuelve errno desde IRQ | mezcla de dominios de retorno | devolver `IRQ_HANDLED` (`0009`) |
| Type-C compara enums incompatibles | data-role frente a port-type | usar `TYPEC_PORT_SRC/SNK` (`0010`) |
| `dtbs` termina sin overlays de la tablet | Makefile usa `always` antiguo | solicitar y verificar cada DTBO explícitamente |
| el dist contiene cientos de DTB ajenos | `dtbs` construye/copia todas las placas ARM64 | pedir y distribuir sólo `s5e8835.dtb` y los tres overlays X510 |
| módulos instalados ocupan 499 MiB | símbolos de debug | `INSTALL_MOD_STRIP=1`; quedan unos 51 MiB |
| BusyBox falla en `tc.c` con headers nuevos | CBQ fue retirado del UAPI moderno | miniconfig de rescate sin `tc` |
| BusyBox sale dinámico | su `allnoconfig` ignora el miniconfig booleano | aplicar opciones después y verificar una por una |
| script clásico espera kernel+ramdisk juntos | header v4 separa `boot` e `init_boot` | dos scripts de reempaquetado distintos |
| ruta relativa a `magiskboot` se rompe al hacer `cd` | el binario se resolvía demasiado tarde | convertirla a absoluta antes del directorio temporal |
| ARM64 ELF no ejecuta en macOS ARM64 | formato de ejecutable distinto pese a la misma ISA | ejecutar el binario oficial dentro de Lima |
| un fallo deja un artefacto anterior visible | salidas no invalidadas al empezar | retirar sólo la salida conocida antes de reconstruir |
| una salida coincide con el stock, un overlay o el manifiesto | un `rm`/reempaquetado podía destruir su propia entrada | resolver rutas y rechazar alias antes de tocar ninguna salida |
| un DTBO malformado pasa el análisis superficial | faltaban límites para cabecera, tabla, payload y FDT | validar rangos, solapes, tamaños y magic antes de escribir archivos |
| un header boot/AVB incoherente parece válido | no se acotaban `header_size` ni `original_image_size` | comprobar mínimos de formato y que todos los offsets queden dentro de la imagen |
| AVB informa del fallo esperado para una imagen demasiado grande | sólo se comprobaba el texto de `avbtool` | rechazar primero cualquier candidato vacío o mayor que la partición stock |

Cada cambio al kernel vive en `patches/downstream/wifi`; `apply-patches.sh` fue
ejecutado dos veces y reconoció todos los parches como ya aplicados. También
pasó `git diff --check`.

## Advertencias que no se deben olvidar

El build aún muestra avisos no fatales:

- strings multilínea en Kconfig SCSC;
- redefinición bool/tristate de `MALI_ARBITRATION`;
- falta de newline en un Kconfig de sensorhub;
- frames de pila algo mayores de 2 KiB en nanohub/debug Samsung;
- copias fallidas de `perflog.h`, resueltas por el fallback `kperfmon_DUMMY`;
- scripts FIPS con escapes Python que serán inválidos en versiones futuras.
- BusyBox 1.36.1 avisa con GCC moderno sobre retornos de `write()` ignorados,
  un descarte de `const` y código de edición no usado; el enlace ARM64 estático
  termina correctamente y su configuración mínima se verifica símbolo a
  símbolo.

No bloquean este build, pero son deuda técnica. Si una actualización convierte
uno en error, se corrige aisladamente y se registra; no se oculta todo `-Werror`.

## BusyBox, initramfs y tamaño

BusyBox 1.36.1 queda fijado al commit
`1a64f6a20aaf6ea4dbba68bbfa8cc1ab7e5c57c4`. El binario mínimo es ARM64,
estático y contiene 27 applets; `rm` y `rmdir` permiten retirar con seguridad
un gadget ConfigFS parcial.

| Perfil | Módulos | CPIO | LZ4 | Uso |
|---|---:|---:|---:|---|
| `none` | 0 | 1 266 176 B | 690 117 B | primera shell |
| `deps` UFS | 28 | 6 589 952 B | 2 124 194 B | investigar almacenamiento |
| `deps` USB | 45 | 10 065 920 B | 3 036 866 B | sólo diagnóstico; no cabe |

Ambos perfiles se construyeron dos veces y el LZ4 resultó idéntico byte a byte.
El ramdisk stock de `init_boot` ocupa 2 486 802 bytes: incluso el perfil UFS
cabe por 362 608 bytes. El perfil USB excede ese ramdisk por 550 064 bytes;
ninguna de estas comparaciones constituye autorización de flasheo.
Los SHA-256 LZ4 medidos son:

- `none`: `587fd79a7e36ce9774bf58927be8b5a917026f90a6bcbb78720e37f667986964`;
- `deps` UFS: `81159c01dfd4f925c044a2007d2768f4c6d6f2d5a04e108ece61ec24af299666`;
- `deps` USB: `aa5d40f18ad2607be94d251d2d2fb333162ff1189b82d0080b82612bb11f7978`.

Los manifiestos canónicos están junto a los artefactos.

## Empaquetado y AVB

El firmware exacto usa header v4:

- `boot`: kernel de 39 356 928 B, sin ramdisk;
- `init_boot`: ramdisk LZ4 legacy de 2 486 802 B, sin kernel;
- `vendor_boot`: ramdisk vendor de 18 077 432 B, DTB de 239 652 B y dos
  fragmentos en su tabla.

Con `magiskboot` oficial v30.7 se reempaquetaron copias y después se volvieron a
extraer. El kernel y el CPIO recuperados coinciden byte a byte con sus inputs.
`avbtool` de AOSP `android16-release` verifica correctamente la imagen stock;
en las candidatas verifica la estructura VBMeta pero rechaza el hash de la
partición. Era el resultado esperado: conservan una firma Samsung sobre el
contenido anterior. Las candidatas están marcadas `UNSIGNED` y no se flashean.

Los scripts hacen una segunda extracción y comparan kernel o ramdisk byte a
byte. `verify-avb-candidates.sh` exige simultáneamente que stock verifique, que
la estructura/firma RSA4096 del candidato siga siendo legible y que el digest
del contenido modificado sea rechazado. Una causa AVB distinta no se acepta
como el fallo esperado.
