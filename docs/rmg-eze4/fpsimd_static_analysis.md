# Análisis Estático: Macros `SLIDE_ROUTE_FPSIMD` y `PRODUCTION_STACK_PI_RIGHT_ONLY`

- **Objetivo**: Investigación estática del propósito, dependencias arquitectónicas, código controlado y justificación técnica de las macros de configuración encontradas en el target ZG3 (`src/targets/gts9fewifi-X510XXSEEZG3/target.h`).
- **Repositorio Auditado**: `Root-My-Galaxy-Payloads-ZG3` (branch `gts9fewifi-X510XXSEEZG3-v4`)
- **Fecha de Auditoría**: 2026-09-06
- **Ámbito**: Exclusivamente análisis de diseño de software y compatibilidad arquitectónica.

---

## 1. Macro: `SLIDE_ROUTE_FPSIMD`

### 1.1 Declaración y Definición
- En `src/common.h`:
  ```c
  #define SLIDE_ROUTE_PSELECT 0
  #define SLIDE_ROUTE_MCAST   1
  #define SLIDE_ROUTE_FPSIMD  2
  ...
  #define SLIDE_USE_FPSIMD (SLIDE_ROUTE == SLIDE_ROUTE_FPSIMD)
  ```
- En `src/targets/gts9fewifi-X510XXSEEZG3/target.h`:
  ```c
  #define SLIDE_ROUTE SLIDE_ROUTE_FPSIMD
  ```

### 1.2 Código que Controla
1. **Puntos de Bifurcación**:
   - `src/slide_app.c`: Durante la inicialización del subproceso hijo (`slide_log_child_context`) y el punto de sincronización de la pila de espera (`slide_pi_worker_thread`), selecciona la función de copia:
     ```c
     #if SLIDE_USE_MCAST
       slide_mcast_stack_copy();
     #elif SLIDE_USE_FPSIMD
       slide_fpsimd_stack_copy();
     #else
       slide_pselect_stack_copy();
     #endif
     ```
   - `src/fpsimd.c`: Compila condicionalmente el manejador de señales, la inspección de registros vectoriales de ARM64 y el hilo consumidor con `sched_setattr`.
   - `src/util.c`: Habilita rutinas auxiliares de afinidad y deshabilitación de `rseq` específicas de la ruta.

### 1.3 Estructuras y Características del Kernel Involucradas
- **Mecanismo de Entrega de Señales ARM64 (`sigaction` / `rt_sigreturn`)**:
  - Al recibir una señal (en este caso `SIGUSR2` enviada mediante `tgkill()`), el kernel de Linux construye en el espacio de usuario (o en la pila alternativa de señales) un marco de contexto `struct ucontext_t`.
  - La cabecera de extensión ARM64 (`uc_mcontext.__reserved`) contiene bloques de contexto encabezados por `struct _aarch64_ctx`.
  - Entre estos bloques se incluye `struct fpsimd_context` con el número mágico `FPSIMD_MAGIC` (`0x46508001`).
  - Dicha estructura contiene el volcado de los 32 registros vectoriales de 128 bits de la FPU/NEON (`vregs[32]`, totalizando 512 bytes de datos continuos).
- **Ventana de Escritura y Alias de Estructuras**:
  - A través del manejador de señales, el código ubica el registro `fpsimd_context` y escribe un `fake_waiter` dentro del espacio `vregs`.
  - Al reanudar la ejecución o interactuar con el planificador, los datos colocados en `vregs` se reflejan en la pila según la alineación `FPSIMD_WAITER_OFF`.

### 1.4 Evolución Histórica en el Repositorio
- **Commit `529d88a` (2026-08-19, por `zainarbani`)**: *"Add fpsimd route & refactor"*.
  - Introduce `src/fpsimd.c` y define `SLIDE_ROUTE_FPSIMD 2`.
  - Retira la dependencia exclusiva de sockets multicast (`setsockopt` / `IP_MSFILTER`) y de `pselect6`.
- **Commit `0062f3d` (2026-08-28, por `zainarbani`)**: *"Switch to fpsimd route"*.
  - Migra los targets `a54x-A546BXXSLFZG3` y `a54x-A546EXXSKFZF4` (SoC Exynos 1380 / `s5e8835`) hacia `SLIDE_ROUTE_FPSIMD`.
- **Commit `b7a854e` (2026-09-01, por `Hameed Musharaf K`)**: *"V4: FPSIMD route fully working on gts9fewifi-X510XXSEEZG3"*.
  - Adapta y valida la ruta FPSIMD para la Galaxy Tab S9 FE Wi-Fi (`SM-X510`), reportando éxito de ejecución en el intento 1/8.

### 1.5 Diagnóstico de Naturaleza: ¿Hardware, Kernel o Build?
- **Nivel de Dependencia**: **Arquitectura de CPU / Subsistema de Señales de Kernel**.
- **Justificación**:
  - No depende de un offset arbitrario de firmware; se basa en la ABI pública de señales de ARM64 (`asm/sigcontext.h`).
  - Se adoptó en dispositivos Exynos 1380 debido a que las políticas estrictas de SELinux en Android restringen ciertas llamadas a sockets de red (`mcast`), mientras que la entrega de señales y el manejo de registros FP/SIMD son operaciones completamente estándar para cualquier hilo en espacio de usuario.
  - **Relevancia para EZE4**: Dado que EZE4 comparte la misma arquitectura ARM64 v8.2-A y el mismo kernel 5.15 con la misma convención de llamadas de señales, la ruta `SLIDE_ROUTE_FPSIMD` es conceptualmente idéntica entre ZG3 y EZE4.

---

## 2. Macro: `PRODUCTION_STACK_PI_RIGHT_ONLY`

### 2.1 Declaración y Definición
- En `src/targets/gts9fewifi-X510XXSEEZG3/target.h`:
  ```c
  #define PRODUCTION_STACK_PI_RIGHT_ONLY 0
  ```
- En otros targets (`a54x-A546BXXSLFZG3`, `e1s-S921BXXSFDZE1`, `e2s-S926BXXUEDZDR`):
  ```c
  #define PRODUCTION_STACK_PI_RIGHT_ONLY 1
  ```

### 2.2 Código que Controla
Esta macro modula el armado del árbol rojo-negro (rbtree) del waiter simulado en las rutinas de copia (`fpsimd.c`, `mcast.c`, `pselect.c`):

```c
/* En src/fpsimd.c, src/mcast.c, src/pselect.c */
#if defined(PRODUCTION_STACK_PI_RIGHT_ONLY) && PRODUCTION_STACK_PI_RIGHT_ONLY
  if (slide_oracle_parent == fake_fops &&
      slide_oracle_target == data_addr(ASHMEM_MISC_FOPS)) {
    tree_right = slide_oracle_target;
    tree_left = 0;
    pi_parent = fake_w0 + FAKE_WAITER_PI_TREE_ENTRY_OFF;
    pi_right = 0;
    pi_left = 0;
  }
#endif
```

Cuando `PRODUCTION_STACK_PI_RIGHT_ONLY` está definido en `0` (como en el target `gts9fewifi-X510XXSEEZG3`):
- Se mantiene la asignación por defecto:
  - `tree_left = slide_oracle_target;`
  - `tree_right = 0;`
  - `pi_parent = slide_oracle_parent;`
  - `pi_left = 0;` *(corrección incorporada en el commit b7a854e: "pi_left=NULL fix in fpsimd.c")*
  - `pi_right = 0;`

### 2.3 Estructuras y Características del Kernel Involucradas
- **Estructura del Árbol de Prioridad (`struct rb_node` en `struct rt_mutex_waiter`)**:
  - En el subsistema de cerrojos con herencia de prioridad, los waiters se ordenan en un árbol rojo-negro según su prioridad y su dirección de memoria.
  - Al insertar un nodo simulado en la estructura del cerrojo, el algoritmo compara la clave/dirección del nodo padre (`rb_parent`) con el nodo a insertar (`slide_oracle_target`).
  - Dependiendo de si la dirección virtual relativa del símbolo objetivo (como `ASHMEM_MISC_FOPS`) es mayor o menor que el nodo padre en el espacio virtual del kernel, el hijo debe situarse estrictamente en la rama izquierda (`rb_left`) o en la rama derecha (`rb_right`).

### 2.4 Justificación de `0` en Galaxy Tab S9 FE (ZG3)
- En terminales móviles como el Galaxy S24 (`e1s`) o Galaxy S24+ (`e2s`), la ubicación de las variables de fops y tablas dinámicas en el espacio virtual exigía vincular la rama derecha (`PRODUCTION_STACK_PI_RIGHT_ONLY 1`).
- En la Galaxy Tab S9 FE (`SM-X510`), el autor del target descubrió empíricamente que para este binario concreto de kernel (`ZG3`), la inserción sólo es válida orientada hacia la rama izquierda (`tree_left = slide_oracle_target`), obligando a fijar `PRODUCTION_STACK_PI_RIGHT_ONLY 0`.

### 2.5 Diagnóstico de Naturaleza: ¿Hardware, Kernel o Build?
- **Nivel de Dependencia**: **Layout Virtual del Kernel / Firmware Build**.
- **Justificación**:
  - Depende directamente de la dirección virtual relativa de los símbolos en la imagen del kernel (`System.map`) y de las decisiones del enlazador (LLD) sobre el ordenamiento de secciones `.data` y `.rodata`.
  - **Relevancia para EZE4**: En la Sección 4 de la auditoría preliminar, se demostró que las direcciones virtuales y desplazamientos de símbolos en EZE4 difieren sustancialmente de ZG3 (por ejemplo, `init_task` se desplazó de `0x239fd80` a `0x233f0c0`, y `kmalloc_caches` de `0x1b04c70` a `0x1ab9250`).
  - Por lo tanto, si en EZE4 la relación de orden entre las direcciones virtuales de los nodos padre e hijo difiere, esta macro no puede heredarse a ciegas y requerirá una validación estática rigurosa de las direcciones relativas del `System.map` de EZE4.
