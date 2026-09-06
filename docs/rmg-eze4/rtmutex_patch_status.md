# Estado de Parche de Kernel: CVE-2026-43499 (`rtmutex.c`)

- **Objetivo**: Determinación estática de la presencia o ausencia de la corrección upstream para CVE-2026-43499 en el árbol de código fuente Samsung EZE4 (`5.15.189-android13-3-33478785`).
- **Archivo Auditado**: `audit/eze4-source-intake/extracted/kernel/kernel/locking/rtmutex.c`
- **Función Clave**: `remove_waiter(struct rt_mutex_base *lock, struct rt_mutex_waiter *waiter)`
- **Fecha de Auditoría**: 2026-09-06
- **Clasificación Estricta**: **`PATCH ABSENT`**

---

## 1. Veredicto y Clasificación

```
================================================================================
VEREDICTO: PATCH ABSENT
Clasificación de Seguridad: Árbol Local No Parcheado
Impacto: La implementación local de remove_waiter() mantiene la suposición
         heredada de que el waiter pertenece exclusivamente a "current",
         omitiendo la sincronización y limpieza del "waiter->task" real.
================================================================================
```

---

## 2. Contexto Técnico del Problema (CVE-2026-43499)

El subsistema de exclusión mutua en tiempo real (`rtmutex`) proporciona soporte para herencia de prioridad (Priority Inheritance, PI). En escenarios normales de contención de cerrojos directos, un hilo (`current`) que se bloquea al intentar adquirir un `rt_mutex` registra su propio `rt_mutex_waiter` en la estructura del cerrojo y se pone a dormir.

Sin embargo, en el contexto de **futex proxy locking** (principalmente utilizado en operaciones `futex_requeue` con cerrojos PI mediante `rt_mutex_start_proxy_lock()`), un hilo invocador actúa como proxy configurando la adquisición de un cerrojo en nombre de **otro hilo**. En esta ruta de ejecución:
$$\text{waiter}\to\text{task} \neq \text{current}$$

Cuando el cerrojo no puede adquirirse o el proceso de espera falla prematuramente, la función `remove_waiter()` es invocada para retirar el registro del hilo en espera.

### Defecto Estructural en Árboles No Parcheados:
En las versiones previas a la corrección, la función `remove_waiter()` asumía incondicionalmente que el hilo en espera era el hilo que ejecutaba la llamada (`current`):
1. Adquiría `current->pi_lock` en lugar de `waiter->task->pi_lock`.
2. Asignaba `current->pi_blocked_on = NULL`, dejando intacto el puntero `waiter->task->pi_blocked_on` en el hilo objetivo.
3. El hilo real retenía una referencia colgante (dangling pointer) hacia una estructura `rt_mutex_waiter` asignada típicamente en la pila de un hilo cuyo marco de llamada podía ser liberado.

---

## 3. Evidencia en el Árbol Local EZE4

En el código fuente exacto de Samsung EZE4 (`kernel/locking/rtmutex.c`, líneas 1459–1510), la función `remove_waiter` se encuentra implementada de la siguiente manera:

```c
/* Líneas 1459-1472 en kernel/locking/rtmutex.c (EZE4) */

static void __sched remove_waiter(struct rt_mutex_base *lock,
				  struct rt_mutex_waiter *waiter)
{
	bool is_top_waiter = (waiter == rt_mutex_top_waiter(lock));
	struct task_struct *owner = rt_mutex_owner(lock);
	struct rt_mutex_base *next_lock;

	lockdep_assert_held(&lock->wait_lock);

	raw_spin_lock(&current->pi_lock);
	rt_mutex_dequeue(lock, waiter);
	current->pi_blocked_on = NULL;
	raw_spin_unlock(&current->pi_lock);

	/*
	 * Only update priority if the waiter was the highest priority
	 * waiter of the lock and there is an owner to update.
	 */
	if (!owner || !is_top_waiter)
		return;
...
```

### Observaciones Directas del Código Local:
1. **Línea 1468**: Se ejecuta `raw_spin_lock(&current->pi_lock);` vinculando el cerrojo del hilo invocador, sin evaluar `waiter->task`.
2. **Línea 1470**: Se limpia únicamente `current->pi_blocked_on = NULL;`.
3. **Ausencia de comprobación de puntero**: No existe ninguna guardia `if (!waiter->task)` ni referencia a `waiter->task->pi_lock`.

---

## 4. Comparación con la Corrección Upstream

La corrección oficial upstream (asociada a la resolución de CVE-2026-43499 y relacionada con el commit `3bfdc63936dd` y derivados) introduce una gestión explícita de `waiter->task` y documenta explícitamente la discrepancia entre el invocador proxy y el hilo en espera:

### Diff Mínimo Conceptual (Upstream vs EZE4 Local):

```diff
--- kernel/locking/rtmutex.c (Local EZE4 5.15.189)
+++ kernel/locking/rtmutex.c (Upstream Patched)
@@ -1453,6 +1453,8 @@
  * Remove a waiter from a lock and give up
  *
  * Must be called with lock->wait_lock held and interrupts disabled. It must
  * have just failed to try_to_take_rt_mutex().
+ *
+ * When invoked from rt_mutex_start_proxy_lock() waiter::task != current !
  */
 static void __sched remove_waiter(struct rt_mutex_base *lock,
				  struct rt_mutex_waiter *waiter)
+	__must_hold(&lock->wait_lock)
 {
	bool is_top_waiter = (waiter == rt_mutex_top_waiter(lock));
	struct task_struct *owner = rt_mutex_owner(lock);
+	struct task_struct *waiter_task = waiter->task;
	struct rt_mutex_base *next_lock;

	lockdep_assert_held(&lock->wait_lock);

-	raw_spin_lock(&current->pi_lock);
-	rt_mutex_dequeue(lock, waiter);
-	current->pi_blocked_on = NULL;
-	raw_spin_unlock(&current->pi_lock);
+	if (!waiter_task) /* never enqueued */
+		return;
+
+	scoped_guard(raw_spinlock, &waiter_task->pi_lock) {
+		rt_mutex_dequeue(lock, waiter);
+		waiter_task->pi_blocked_on = NULL;
+	}

	/*
	 * Only update priority if the waiter was the highest priority
```

---

## 5. Razonamiento Técnico Conclusivo

1. **Paridad con ZG3**: El firmware `X510XXSEEZG3` (compilado en julio de 2026 sobre la base 5.15.189) demostró en el repositorio de referencia ser susceptible al mecanismo de explotación basado en la corrupción de punteros de `remove_waiter()`.
2. **Cronología de Versiones**: El firmware local `X510XXUCEZE4` corresponde a la compilación de mayo de 2026 (dos meses anterior a ZG3). Dado que la corrección no fue incorporada en el árbol de soporte a largo plazo (LTS) de Samsung hasta compilaciones posteriores al ciclo de parches de agosto de 2026, el código fuente local preserva la lógica vulnerable intacta.
3. **Conclusión**: El árbol fuente del kernel `X510XXUCEZE4` clasifica sin ambigüedad como **`PATCH ABSENT`**.
