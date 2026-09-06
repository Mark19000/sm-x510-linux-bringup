# Fe de Erratas y Resolución Técnica: Espacio de Candidatos P0 (32 vs 125) en ZG3

- **Dispositivo**: Samsung Galaxy Tab S9 FE Wi-Fi (`SM-X510` / `gts9fewifi`)
- **SoC**: Samsung Exynos 1380 (`s5e8835`)
- **Branch Auditado**: `hmd-msrf-k/Root-My-Galaxy-Payloads` @ `gts9fewifi-X510XXSEEZG3-v4`
- **Fecha**: 2026-09-06
- **Resultado Formal de la Auditoría**: **`TWO_DISTINCT_CANDIDATE_SPACES`**

---

## 1. Naturaleza de la Contradicción Aparente

En fases previas de la auditoría se detectó una inconsistencia entre dos fuentes documentales:
1. En `docs/rmg-eze4/zg3_target_inventory_v2.csv` (fila 181) y en `target.h:72-80`, se listaba la macro `SLIDE_P0_OFFSET_CANDIDATES` conteniendo **32 valores** espaciados por `0x10000` (64 KB) y se describía `p0_fingerprints` como un *"array [32 entries]"*.
2. En `docs/rmg-eze4/PHASE3A.md` y `p0_oracle_algorithm.md`, se demostró que el target `gts9fewifi` requiere de forma mandatoria un paso KASLR de 16 KB (`0x4000`) resultando en **125 candidatos** para la ventana de sondeo de 2 MB (`0x1f0000`).

Esta auditoría analiza exclusivamente el código fuente real del branch de producción para resolver de forma concluyente esta divergencia.

---

## 2. Citas Exactas del Código Fuente

### 2.1 Macro `SLIDE_KASLR_STEP`
Ubicación: `src/targets/gts9fewifi-X510XXSEEZG3/target.h:82`
```c
#define SLIDE_KASLR_STEP 0x4000ULL
```

### 2.2 Macro `SLIDE_P0_OFFSET_CANDIDATES`
Ubicación: `src/targets/gts9fewifi-X510XXSEEZG3/target.h:72-80`
```c
#define SLIDE_P0_OFFSET_CANDIDATES \
  0x000000ULL, 0x010000ULL, 0x020000ULL, 0x030000ULL, \
  0x040000ULL, 0x050000ULL, 0x060000ULL, 0x070000ULL, \
  0x080000ULL, 0x090000ULL, 0x0a0000ULL, 0x0b0000ULL, \
  0x0c0000ULL, 0x0d0000ULL, 0x0e0000ULL, 0x0f0000ULL, \
  0x100000ULL, 0x110000ULL, 0x120000ULL, 0x130000ULL, \
  0x140000ULL, 0x150000ULL, 0x160000ULL, 0x170000ULL, \
  0x180000ULL, 0x190000ULL, 0x1a0000ULL, 0x1b0000ULL, \
  0x1c0000ULL, 0x1d0000ULL, 0x1e0000ULL, 0x1f0000ULL
```
*(Contiene exactamente 32 valores con paso de 0x10000).*

### 2.3 Número Real de Entradas en `p0_fingerprints[]`
Ubicación: `src/targets/gts9fewifi-X510XXSEEZG3/p0_fingerprint.h:17-518`
- Encabezado explicativo (`p0_fingerprint.h:2`):
  ```c
  // 0x4000 step fingerprint table.
  ```
- Primera entrada (`p0_fingerprint.h:18-21`):
  ```c
  { 0x000000ULL, { 0xf835013fd53cd04aULL, 0xf90002e8f9407a68ULL, ... } },
  ```
- Segunda entrada (`p0_fingerprint.h:22-25`):
  ```c
  { 0x004000ULL, { 0xa90357f6a9025ff8ULL, 0x943d785cb5fff9c8ULL, ... } },
  ```
- Última entrada (`p0_fingerprint.h:514-517`):
  ```c
  { 0x1f0000ULL, { 0x1487bffffa405a4dULL, 0xd503201fd503201fULL, ... } },
  ```
- **Conteo real**: Exactamente **125 entradas** tipo `struct p0_fingerprint`.

### 2.4 Macros que Determinan el Número de Fingerprints
- No existe ninguna macro de preprocesador explícita del tipo `#define P0_FINGERPRINT_ROWS 125`.
- La cabecera se incluye dinámicamente mediante:
  `src/targets/gts9fewifi-X510XXSEEZG3/target.h:64-65`:
  ```c
  #define P0_FINGERPRINT_HEADER \
    "targets/gts9fewifi-X510XXSEEZG3/p0_fingerprint.h"
  ```
- En tiempo de compilación y ejecución, el tamaño de la tabla se determina mediante el operador C `sizeof`:
  `src/oracle.c:248-250`:
  ```c
  for (size_t index = 0;
       index < sizeof(p0_fingerprints) / sizeof(p0_fingerprints[0]);
       index++)
  ```

---

## 3. Rastreo del Flujo de Ejecución: `target.h` $\rightarrow$ `oracle.c`

Al inspeccionar el código fuente del exploit en `src/slide_app.c` y `src/oracle.c`, se descubre cómo conviven estos dos espacios:

### 3.1 Bifurcación Condicional en `slide_app.c`
En `src/slide_app.c:15-20`:
```c
#if defined(SLIDE_P0_OFFSET_CANDIDATES) && \
    (!defined(PHYS_P0_ORACLE) || !PHYS_P0_ORACLE)
static const uintptr_t slide_p0_offsets[] = {
  SLIDE_P0_OFFSET_CANDIDATES
};
#endif
```
**Efecto crítico**: El array `slide_p0_offsets[]` (los 32 candidatos de `SLIDE_P0_OFFSET_CANDIDATES`) **SÓLO SE COMPILA** si `PHYS_P0_ORACLE` es 0 o no está definido.

Dado que en `target.h:8`:
```c
#define PHYS_P0_ORACLE 1
```
El array `slide_p0_offsets[]` queda **completamente excluido de la compilación** en la suite activa.

### 3.2 Selección del Mecanismo de Filtración KASLR
En `src/slide_app.c:887-938`:
```c
int slide_leak_kernel_base(void) {
#if defined(PHYS_P0_ORACLE) && PHYS_P0_ORACLE
  const char *forced_offset_arg = getenv("SLIDE_P0_OFFSET");
  if (forced_offset_arg && *forced_offset_arg) {
    ...
  }
  return slide_leak_physical_base();
#else
  // Rama heredada (legacy non-P0 pselect/sysctl leak)
  ...
  for (int attempt = 1; attempt <= max_attempts; attempt++) {
    slide_p0_offset = slide_p0_offsets[
        (size_t)(attempt - 1) %
        (sizeof(slide_p0_offsets) / sizeof(slide_p0_offsets[0]))];
    ...
  }
#endif
}
```

### 3.3 Bucle en `src/oracle.c` (Ruta Activa de Producción)
1. `slide_leak_physical_base()` llama a `scan_p0_pipe_oracle()` en `src/oracle.c`.
2. En `src/oracle.c:248-259`:
   ```c
   for (size_t index = 0;
        index < sizeof(p0_fingerprints) / sizeof(p0_fingerprints[0]);
        index++) {
     int score = p0_fingerprint_score(page, &p0_fingerprints[index]);
     if (score > best_score) {
       second_score = best_score;
       best_score = score;
       best_slide = p0_fingerprints[index].slide;
     } else if (score > second_score) {
       second_score = score;
     }
   }
   ```
- **Array que itera el runtime**: `p0_fingerprints[]` (definido en `p0_fingerprint.h`).
- **Número de entradas recorridas**: $\frac{\text{sizeof}(p0\_fingerprints)}{\text{sizeof}(p0\_fingerprints[0])} = \mathbf{125 \text{ entradas}}$.
- **Qué representa cada candidato**: Un desplazamiento KASLR concreto $\text{slide} \in [0, \text{0x1f0000}]$ evaluado a intervalos de 16 KB (`0x4000`), asociado a 8 muestras QWORD de 64 bits de la imagen física.

---

## 4. Conteo Programático Riguroso

Se ejecutó un parser determinista de expresiones regulares sobre el archivo `src/targets/gts9fewifi-X510XXSEEZG3/p0_fingerprint.h`:

```python
import re
with open("src/targets/gts9fewifi-X510XXSEEZG3/p0_fingerprint.h") as f:
    text = f.read()

pattern = re.compile(r'\{\s*(0x[0-9a-fA-F]+)ULL\s*,\s*\{\s*([^}]+)\s*\}\s*\}')
matches = pattern.findall(text)
slides = [int(m[0], 16) for m in matches]
diffs = [slides[i+1] - slides[i] for i in range(len(slides)-1)]

print(f"Total entries: {len(matches)}")
print(f"First slide:   {hex(slides[0])}")
print(f"Last slide:    {hex(slides[-1])}")
print(f"Step size:     {[hex(d) for d in set(diffs)]}")
```

**Salida obtenida**:
```
Total entries: 125
First slide:   0x0
Last slide:    0x1f0000
Step size:     ['0x4000']
```

Adicionalmente, se inspeccionaron todos los targets del repositorio, revelando una segregación arquitectónica total:
- **Dispositivos Qualcomm / Exynos 2400 / MediaTek** (paso KASLR de 64 KB):
  - `e1s`, `e2s`, `e3q`, `dm3q`, `pa3q`, `q7q`, `a15`, `a36xq`, `essi`: **32 entradas** (`step=0x10000`).
- **Dispositivos Samsung Exynos 1380 (`s5e8835`)** (paso KASLR de 16 KB):
  - `a54x-A546EXXSKFZF4`: **125 entradas** (`step=0x4000`).
  - `a54x-A546BXXSLFZG3`: **125 entradas** (`step=0x4000`).
  - `gts9fewifi-X510XXSEEZG3`: **125 entradas** (`step=0x4000`).

---

## 5. Explicación de la Discrepancia y Origen del Error en el Inventario

Existen **dos espacios de candidatos conceptual y funcionalmente distintos** en la base de código de Root-My-Galaxy:

1. **Espacio 1: Oráculo Físico P0 en Memoria (`PHYS_P0_ORACLE == 1`) — [ACTIVO EN PRODUCCIÓN]**:
   - Reside en: `src/targets/gts9fewifi-X510XXSEEZG3/p0_fingerprint.h`.
   - Utilizado por: `src/oracle.c:scan_p0_pipe_oracle()`.
   - Geometría: **125 candidatos** espaciados por **`0x4000`** (16 KB).
   - Generado por: `tools/generate_p0_fingerprint.pl` que lee `#define SLIDE_KASLR_STEP 0x4000ULL` de `target.h`.
   - Este es el espacio real con el que el exploit obtuvo root en el intento 1/8 en commit `b7a854e`.

2. **Espacio 2: Muestreo Brute-Force Legacy para pselect (`!PHYS_P0_ORACLE`) — [INACTIVO / RESIDUAL]**:
   - Reside en: Macro `SLIDE_P0_OFFSET_CANDIDATES` en `target.h:72-80`.
   - Geometría: **32 candidatos** espaciados por **`0x10000`** (64 KB).
   - Utilizado exclusivamente en la rama de compilación `#else` de `src/slide_app.c:15-20` y `887-938`.
   - Queda como código muerto cuando `PHYS_P0_ORACLE == 1`.

### Causa Raíz del Error en `zg3_target_inventory_v2.csv`
En la fila 181 del inventario inicial:
```csv
p0_fingerprints,struct p0_fingerprint array [32 entries],p0_fingerprint.h,17,FIRMWARE_FINGERPRINT,DISASSEMBLY,Lookup table of 32 physical page candidate samples from Image
```
El autor del inventario transcribió apresuradamente `"32 entries"` asumiendo erróneamente que la tabla `p0_fingerprints[]` correspondía al valor de `SLIDE_MAX_ATTEMPTS 32` o a los 32 elementos de la macro `SLIDE_P0_OFFSET_CANDIDATES`, **sin contar las líneas reales del archivo `p0_fingerprint.h`** (el cual tiene 521 líneas y 125 estructuras).

---

## 6. Conclusión Formal

El resultado formal de esta verificación técnica es unívoco:

$$\mathbf{TWO\_DISTINCT\_CANDIDATE\_SPACES}$$

1. En el runtime activo de producción de `gts9fewifi-X510XXSEEZG3`, el oráculo físico P0 itera y evalúa exclusivamente los **125 candidatos a paso 0x4000** definidos en `p0_fingerprint.h`.
2. La macro `SLIDE_P0_OFFSET_CANDIDATES` con 32 candidatos a paso `0x10000` corresponde a la ruta alternativa `!PHYS_P0_ORACLE`, inactiva bajo `PHYS_P0_ORACLE 1`.
3. Por tanto, la afirmación de `PHASE3A.md` es **ESTRICTAMENTE CORRECTA**: para Exynos 1380 / Tab S9 FE, el oráculo físico P0 requiere una tabla de **125 entradas con paso 0x4000**.
