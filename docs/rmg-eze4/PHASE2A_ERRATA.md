# Errata Técnico de Fase 2A: Desplazamientos de `task_struct` en `remove_waiter()`

- **Documento Corregido**: `docs/rmg-eze4/stock_rtmutex_binary_verification.md` (Sección 5, punto 4)
- **Fecha de Errata**: 2026-09-06
- **Alcance**: Corrección de la atribución del operando `#2208` en el desensamblado del binario stock EZE4 (`Image.stock`) y resolución formal de los miembros situados en `0x8a0` y `0x8a8`.

---

## 1. Identificación del Error en Fase 2A

En el informe de Fase 2A, la Sección 5 afirmaba:
> *"4. `TASK_STRUCT_PI_TOP_TASK_OFF`: `0x8a8` (decimal 2208 + 8). Evidencia: `ldr x8, [x21, #2208]` en `0xffffffc009150734` y `0xffffffc009150748`."*

### Error Matemático y Semántico:
- **Conversión Base**: $2208_{10} = \mathbf{0x8a0}_{16}$ (exacto), **no** `0x8a8`.
- **Interpretación Errónea**: La instrucción `ldr x8, [x21, #2208]` no estaba accediendo al puntero `pi_top_task`, sino a otro miembro específico de la estructura.
- **Acción Correctiva**: No propagar dicha atribución y determinar mediante Ground Truth (BTF / DWARF) la asignación precisa de los offsets `0x8a0` y `0x8a8`.

---

## 2. Resolución Mediante BTF y DWARF (`vmlinux` EZE4)

La inspección de la estructura `struct task_struct` (Type ID 462) en el BTF y DWARF del kernel EZE4 revela la siguiente disposición física contigua:

```
/* Offset Decimal */  /* Offset Hex */  /* Tipo y Miembro */
2176                  0x880              spinlock_t alloc_lock; (size: 4)
2180                  0x884              raw_spinlock_t pi_lock; (size: 4)
2184                  0x888              struct wake_q_node wake_q; (size: 8)
2192                  0x890              int wake_q_count; (size: 4)
                      [Hueco de alineación de 4 bytes]
2200                  0x898              struct rb_root_cached pi_waiters; (size: 16)
2216                  0x8a8              struct task_struct *pi_top_task; (size: 8)
2224                  0x8b0              struct rt_mutex_waiter *pi_blocked_on; (size: 8)
```

### Desglose Interno de `struct rb_root_cached` (Type ID 496):
El campo `pi_waiters` no es un puntero simple, sino una estructura de 16 bytes que optimiza el árbol rojo-negro reteniendo un puntero directo al nodo de mayor prioridad (`rb_leftmost`):

```c
struct rb_root_cached {
    struct rb_root rb_root;     /* Offset +0 (en task_struct: 2200 / 0x898), size: 8 */
    struct rb_node *rb_leftmost;/* Offset +8 (en task_struct: 2208 / 0x8a0), size: 8 */
};
```

---

## 3. Asignación Definitiva de Offsets

| Offset Decimal | Offset Hexadecimal | Miembro en `struct task_struct` | Tipo de Dato | Tamaño |
| :---: | :---: | :--- | :--- | :---: |
| **2200** | **`0x898`** | `pi_waiters.rb_root` | `struct rb_root` (`struct rb_node *`) | 8 bytes |
| **2208** | **`0x8a0`** | `pi_waiters.rb_leftmost` | `struct rb_node *` | 8 bytes |
| **2216** | **`0x8a8`** | `pi_top_task` | `struct task_struct *` | 8 bytes |
| **2224** | **`0x8b0`** | `pi_blocked_on` | `struct rt_mutex_waiter *` | 8 bytes |

---

## 4. Reinterpretación del Desensamblado de `Image.stock`

En la función `remove_waiter()` del binario de fábrica:
- `x21` almacena el puntero `owner` (`struct task_struct *`).
- En la línea `ffffffc009150734`:
  ```asm
  ffffffc009150734:  f94452a8  ldr  x8, [x21, #2208]
  ```
  La instrucción desreferencia `owner->pi_waiters.rb_leftmost` (offset `0x8a0` / 2208), extrayendo el nodo del árbol rojo-negro que representa al waiter de mayor prioridad en la cola del propietario.
- En la línea `ffffffc009150748`:
  ```asm
  ffffffc009150748:  f90452a0  str  x0, [x21, #2208]
  ```
  La instrucción actualiza `owner->pi_waiters.rb_leftmost = x0` tras la reorganización del árbol.

### Estado de `TASK_STRUCT_PI_TOP_TASK_OFF`:
- La macro en el target ZG3 define:
  ```c
  #define FAKE_TASK_PI_TOP_TASK_OFF 0x8a8
  ```
- **Conclusión**: El valor `0x8a8` para `pi_top_task` es **completamente correcto** en EZE4 (offset 2216). El error de Fase 2A fue únicamente citar `#2208` (`0x8a0`) como prueba de `0x8a8`, cuando `#2208` corresponde a `pi_waiters.rb_leftmost`.
