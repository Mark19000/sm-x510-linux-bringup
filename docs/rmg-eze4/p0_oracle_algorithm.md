# Auditoría Técnica del Algoritmo Oráculo P0 (KASLR Physical Slide Oracle)

- **Dispositivo**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510` / `gts9fewifi`)
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Firmware Base Objetivo**: `X510XXUCEZE4` (Kernel Linux 5.15.189)
- **Firmware de Referencia**: `X510XXSEEZG3` (Kernel Linux 5.15.189)
- **Archivos de Código Auditados**:
  - `src/oracle.c`
  - `src/targets/gts9fewifi-X510XXSEEZG3/p0_fingerprint.h`
  - `src/targets/gts9fewifi-X510XXSEEZG3/target.h`
  - `tools/generate_p0_fingerprint.pl`
  - `src/slide_app.c`, `src/fops.c`, `src/pselect.c`, `src/fpsimd.c`
- **Fecha**: 2026-09-06

---

## 1. Fundamento y Propósito de P0

### ¿Qué es P0?
En la arquitectura de memoria física de Samsung Exynos 1380, **P0** hace referencia a la base física de carga de la memoria DRAM del kernel (`P0_KERNEL_PHYS_LOAD = 0x80000000ULL`).

En el contexto de la suite *Root-My-Galaxy*, el **Oráculo P0** (*Physical Page 0 Oracle*) es un mecanismo de filtración de KASLR (*Kernel Address Space Layout Randomization*) que opera en el dominio de memoria física. A diferencia de las técnicas tradicionales de leak basadas en sockets de red (multicast), temporización de páginas de usuario o interfaces `/proc` y `sysfs` (fuertemente restringidas por SELinux en Android 13/14), el oráculo P0 utiliza la geometría de los buffers de tuberías de Linux (`struct user_pipe_buffer` de 40 bytes / `0x28`) y primitivas de sondeo físico para leer una página de memoria del kernel sin privilegios de root previos.

### ¿Qué intenta identificar?
Su objetivo exclusivo es determinar con certeza matemática absoluta el desplazamiento de aleatorización **`slide`** de KASLR en la sesión actual de arranque:
$$	ext{VA}(	ext{symbol}) = 	ext{KIMAGE\_TEXT\_BASE} + 	ext{offset} + 	ext{slide}$$

En la arquitectura ARM64 de Samsung:
- `KIMAGE_TEXT_BASE = 0xffffffc008000000ULL`
- `slide \in [0x000000, 0x1f0000]`
Al obtener el `slide`, el exploit desaleatoriza en tiempo de ejecución todas las funciones de control (`commit_creds`, `prepare_kernel_cred`, gadgets de retorno).

---

## 2. Parámetros y Mecanismo del Oráculo Físico

### Macro `PHYS_P0_ORACLE`
Definida en `target.h` (`#define PHYS_P0_ORACLE 1`), instruye al compilador y al runtime a compilar y utilizar las funciones de `src/oracle.c` (`prepare_p0_pipe_oracle`, `verify_p0_pipe_oracle_gate`, `scan_p0_pipe_oracle`, `restore_p0_oracle_pages`). Si estuviera en 0, el exploit dependería de oráculos de red como multicast (`SLIDE_USE_MCAST`) o tracefs (`SLIDE_USE_TRACEFS`), ambos inoperantes o inestables en el entorno SELinux de Samsung One UI 6.

### Uso de `P0_ORACLE_PROBE_OFFSET`
Definido para Tab S9 FE como:
$$	ext{P0\_ORACLE\_PROBE\_OFFSET} = 	ext{0x1f0000ULL} \quad (2	ext{ MB})$$

El exploit configura una página física fija de sondeo ubicada a exactamente $2	ext{ MB}$ de la base física de DRAM:
$$P_{probe} = P_{base} + 	ext{P0\_ORACLE\_PROBE\_OFFSET} = 	ext{0x80000000} + 	ext{0x1f0000} = 	ext{0x801f0000}$$

Cuando el bootloader carga el kernel con un KASLR slide aleatorio $	ext{slide}$, el inicio del kernel se posiciona en:
$$P_{load} = P_{base} + 	ext{slide}$$

Por lo tanto, la posición relativa dentro del archivo binario `Image` que queda expuesta bajo la dirección física de sondeo $P_{probe}$ es:
$$P_{load} + 	ext{Image\_offset} = P_{probe}$$
$$(P_{base} + 	ext{slide}) + 	ext{Image\_offset} = P_{base} + 	ext{P0\_ORACLE\_PROBE\_OFFSET}$$
$$\mathbf{	ext{Image\_offset} = 	ext{P0\_ORACLE\_PROBE\_OFFSET} - 	ext{slide}}$$

Esta fórmula es la piedra angular del oráculo: **a medida que el slide del kernel crece, la ventana observada en la página física retrocede en el archivo Image**.

---

## 3. Discrepancia 32 vs 125 Candidatos y `SLIDE_KASLR_STEP`

### ¿Cómo interviene `SLIDE_KASLR_STEP`?
El paso de KASLR (`SLIDE_KASLR_STEP`) define la granularidad de alineación mínima permitida por el kernel al aleatorizar su dirección de carga.
- En la mayoría de teléfonos insignia (Galaxy S24/S23, SoC Qualcomm o Exynos 2400), el paso es de **64 KB** (`0x10000`).
- En la familia Samsung Galaxy Tab S9 FE y teléfonos de gama media con Exynos 1380 (`s5e8835`), el kernel utiliza un paso de **16 KB** (`0x4000`):
  $$	ext{SLIDE\_KASLR\_STEP} = 	ext{0x4000ULL} \quad (16	ext{ KB})$$

### ¿Por qué existen 32 candidatos en unos y 125 en otros?
El espacio de búsqueda del oráculo abarca una ventana total de $2	ext{ MB}$ (`0x1f0000`).
1. **Dispositivos de 64 KB (`0x10000`)**:
   $$	ext{Candidatos} =
rac{	ext{0x1f0000}}{	ext{0x10000}} + 1 = 31 + 1 = \mathbf{32 	ext{ entradas}}$$
   (Slides: `0x000000`, `0x010000`, `0x020000`, ..., `0x1f0000`).
2. **Tab S9 FE / Exynos 1380 (`0x4000`)**:
   $$	ext{Candidatos} =
rac{	ext{0x1f0000}}{	ext{0x4000}} + 1 = 124 + 1 = \mathbf{125 	ext{ entradas}}$$
   (Slides: `0x000000`, `0x004000`, `0x008000`, ..., `0x1f0000`).

La mención histórica de "32 candidatos" se deriva del diseño original para terminales de 64 KB, pero la implementación real para `gts9fewifi` requiere de forma mandatoria **125 candidatos** para cubrir la malla de 16 KB.

---

## 4. Estructura de la Huella Dactilar (Fingerprint)

### Los 8 Offsets Intrapágina
Dentro de una página física estándar de 4 KB (4096 bytes / `0x1000`), se toman muestras en 8 desplazamientos uniformemente espaciados por 512 bytes (`0x200`):
$$\{ 	ext{0x000}, 	ext{0x200}, 	ext{0x400}, 	ext{0x600}, 	ext{0x800}, 	ext{0xa00}, 	ext{0xc00}, 	ext{0xe00} \}$$

Esta dispersión intrapágina garantiza que la huella muestree:
- El inicio del bloque (`0x000`)
- Puntos intermedios cada medio kilobyte
- El final del bloque (`0xe00` a `0xe07`)
Evitando que páginas con cabeceras idénticas o áreas de padding de ceros provoquen falsos emparejamientos.

### Representación de Cada Palabra (`word`)
Cada palabra almacenada en `words[8]` es un entero de 64 bits sin signo (`uint64_t`, 8 bytes) en formato little-endian ARM64:
```c
struct p0_fingerprint {
  uintptr_t slide;
  uint64_t words[8];
};
```
Cada palabra extrae directamente los 8 bytes binarios de la imagen estática:
$$	ext{words}[i] = 	ext{Image}[(	ext{P0\_ORACLE\_PROBE\_OFFSET} - 	ext{slide}) + 	ext{offset}_i]$$

Dado que el código `.text` y las tablas `.rodata` del kernel son inmutables durante la ejecución, estos 64 bytes totales forman una firma criptográficamente robusta de la página física proyectada.

---

## 5. Algoritmo de Puntuación, Confianza y Colisiones

### Cálculo del Score (`p0_fingerprint_score`)
En `src/oracle.c:197-208`, la comparación se evalúa palabra por palabra:
```c
static int p0_fingerprint_score(
    const unsigned char *page, const struct p0_fingerprint *fingerprint) {
  int score = 0;
  for (size_t index = 0; index < P0_FINGERPRINT_WORDS; index++) {
    uint64_t value = 0;
    memcpy(&value, page + p0_fingerprint_offsets[index], sizeof(value));
    if (value == fingerprint->words[index]) {
      score++;
    }
  }
  return score;
}
```
El puntaje final de una comparación es un entero discreto en el rango $[0, 8]$.

### Criterio `P0_FINGERPRINT_MIN_BEST = 5`
- Establece que el mejor candidato debe tener al menos **5 de 8 palabras idénticas** ($62.5\%$ de coincidencia mínima).
- Si la página leída del pipe estuviera vacía, contuviera basura de memoria de usuario o estuviera corrupta, el puntaje típico es $\le 1$. Al imponer $	ext{score} \ge 5$, se descarta automáticamente cualquier lectura fallida antes de cometer una dirección errónea.

### Criterio `P0_FINGERPRINT_MIN_MARGIN = 3`
- Establece la separación requerida entre el candidato ganador y su competidor más cercano:
  $$	ext{best\_score} - 	ext{second\_score} \ge 3$$
- Si el mejor candidato obtiene 6 puntos y el segundo obtiene 4 puntos ($	ext{margen} = 2 < 3$), la muestra se considera ambigua y se **rechaza**.
- Esto protege contra colisiones accidentales producidas por patrones repetitivos de código en el kernel (por ejemplo, secuencias consecutivas de NOPs o funciones stub).

### Gestión de Colisiones
En `src/oracle.c:278-292`:
1. Si no se modifica exactamente 1 página (`changed_pages != 1`), retorna `-1`.
2. Si hay empate ($	ext{best\_score} \le 	ext{second\_score}$), retorna `-1`.
3. Si no se supera el umbral o el margen, el oráculo emite:
   `p0 fingerprint rejected low-confidence best=%d second=%d min_best=%d margin=%d`
   y retorna `(uintptr_t)-1`.
4. El proceso llamador (`slide_app.c`) detecta el valor `-1` y reintenta el oráculo con un nuevo intento limpio, **evitando provocar un kernel panic**.

---

## 6. Conclusión de la Auditoría del Algoritmo P0

El algoritmo P0 es un discriminador probabilístico altamente optimizado, determinista y matemáticamente formalizado:
- Total de candidatos en EZE4: **125 entradas** (paso `0x4000` en ventana `0x1f0000`).
- Muestreo: **8 palabras de 64 bits** (64 bytes/página en offsets `0x200`).
- Validación: **Score $\ge 5$** con **Margen $\ge 3$**.
