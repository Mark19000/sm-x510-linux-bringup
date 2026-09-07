# Kernel Patch Status: CVE-2026-43499 (`rtmutex.c`)

- **Objective**: Static determination of the presence or absence of the upstream fix for CVE-2026-43499 in the Samsung EZE4 source code tree (`5.15.189-android13-3-33478785`).
- **Audited File**: `audit/eze4-source-intake/extracted/kernel/kernel/locking/rtmutex.c`
- **Key Function**: `remove_waiter(struct rt_mutex_base *lock, struct rt_mutex_waiter *waiter)`
- **Audit Date**: 2026-09-06
- **Strict Classification**: **`PATCH ABSENT`**

---

## 1. Verdict and Classification

```
================================================================================
VERDICT: PATCH ABSENT
Security Classification: Local Tree Unpatched
Impact: The local implementation of remove_waiter() retains the legacy
         assumption that the waiter belongs exclusively to "current",
         omitting synchronization and cleanup of the actual "waiter->task".
================================================================================
```

---

## 2. Technical Context of the Issue (CVE-2026-43499)

The real-time mutual exclusion (`rtmutex`) subsystem provides Priority Inheritance (PI) support. In normal direct-lock contention scenarios, a thread (`current`) that blocks attempting to acquire an `rt_mutex` registers its own `rt_mutex_waiter` on the lock structure and goes to sleep.

However, in the context of **futex proxy locking** (primarily used in `futex_requeue` operations with PI locks via `rt_mutex_start_proxy_lock()`), a calling thread acts as a proxy setting up lock acquisition on behalf of **another thread**. On this execution path:
$$\text{waiter}\to\text{task} \neq \text{current}$$

When the lock cannot be acquired or the wait process fails prematurely, the `remove_waiter()` function is called to withdraw the waiting thread's registration.

### Structural Flaw in Unpatched Trees:
In versions prior to the fix, `remove_waiter()` unconditionally assumed that the waiting thread was the thread executing the call (`current`):
1. Acquired `current->pi_lock` instead of `waiter->task->pi_lock`.
2. Set `current->pi_blocked_on = NULL`, leaving the `waiter->task->pi_blocked_on` pointer intact on the target thread.
3. The actual thread retained a dangling pointer to an `rt_mutex_waiter` structure typically allocated on the stack of a thread whose call frame could be freed.

---

## 3. Evidence in Local EZE4 Tree

In the exact Samsung EZE4 source code (`kernel/locking/rtmutex.c`, lines 1459–1510), the `remove_waiter` function is implemented as follows:

```c
/* Lines 1459-1472 in kernel/locking/rtmutex.c (EZE4) */

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

### Direct Observations of Local Code:
1. **Line 1468**: Executes `raw_spin_lock(&current->pi_lock);` locking the calling thread's lock, without evaluating `waiter->task`.
2. **Line 1470**: Only clears `current->pi_blocked_on = NULL;`.
3. **Absence of pointer check**: There is no `if (!waiter->task)` guard or reference to `waiter->task->pi_lock`.

---

## 4. Comparison with Upstream Fix

The official upstream fix (associated with CVE-2026-43499 resolution and related to commit `3bfdc63936dd` and derivatives) introduces explicit handling of `waiter->task` and explicitly documents the discrepancy between the proxy caller and the waiting thread:

### Conceptual Minimal Diff (Upstream vs Local EZE4):

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
+    __must_hold(&lock->wait_lock)
 {
     bool is_top_waiter = (waiter == rt_mutex_top_waiter(lock));
     struct task_struct *owner = rt_mutex_owner(lock);
+    struct task_struct *waiter_task = waiter->task;
     struct rt_mutex_base *next_lock;

     lockdep_assert_held(&lock->wait_lock);

-    raw_spin_lock(&current->pi_lock);
-    rt_mutex_dequeue(lock, waiter);
-    current->pi_blocked_on = NULL;
-    raw_spin_unlock(&current->pi_lock);
+    if (!waiter_task) /* never enqueued */
+        return;
+
+    scoped_guard(raw_spinlock, &waiter_task->pi_lock) {
+        rt_mutex_dequeue(lock, waiter);
+        waiter_task->pi_blocked_on = NULL;
+    }

     /*
      * Only update priority if the waiter was the highest priority
```

---

## 5. Conclusive Technical Reasoning

1. **Parity with ZG3**: Firmware `X510XXSEEZG3` (compiled in July 2026 on the 5.15.189 base) was shown in the reference repository to be susceptible to the exploitation mechanism based on `remove_waiter()` pointer corruption.
2. **Version Chronology**: Local firmware `X510XXUCEZE4` corresponds to the May 2026 build (two months prior to ZG3). Since the fix was not incorporated into Samsung's long-term support (LTS) tree until builds subsequent to the August 2026 patch cycle, the local source code preserves the vulnerable logic intact.
3. **Conclusion**: The `X510XXUCEZE4` kernel source tree unambiguously classifies as **`PATCH ABSENT`**.
