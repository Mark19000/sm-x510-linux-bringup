# Phase J2.1-R1 Clock Model & Invariants

## 1. Authoritative Clock Domain
The sole authoritative duration clock for candidate compatibility evaluation is the supervisor's device `CLOCK_MONOTONIC`.

- **Start Epoch ($t_0$)**: Captured as the parent's post-fork sample of `CLOCK_MONOTONIC` immediately upon spawning the child attempt.
- **Pre-Slide Stage**: Governed by the separate $1200\text{ s}$ pre-slide watchdog measured from $t_0$.
- **Candidate Overall Slide**: Governed by the $2200\text{ s}$ candidate overall watchdog measured from the **same** original post-fork epoch $t_0$.
- **`slide_ready` Handshake**: Merely switches the active timeout threshold from $1200\text{ s}$ to $2200\text{ s}$ against $t_0$. It **never** resets or re-arms the clock epoch.

## 2. Mathematical Duration & Headroom Equations
$$\Delta t_{\text{ns}} = t_{\text{terminal\_device\_monotonic\_ns}} - t_{\text{post\_fork\_device\_monotonic\_ns}}$$
$$\text{duration\_seconds} = \frac{\Delta t_{\text{ns}}}{10^9}$$
$$\text{canonical\_headroom\_seconds} = 2200.000000000 - \text{duration\_seconds}$$

## 3. Affirmative Compatibility Headroom ($2195.0\text{ s}$ Boundary)
- **$T \le 2195.000000000\text{ s}$ from post-fork**: Qualifying clean completion satisfies affirmative compatibility headroom ($\ge 5.000\text{ s}$) $\implies$ `COMPATIBLE_VOTE`.
- **$2195.000000001\text{ s} \le T < 2200.000000000\text{ s}$ from post-fork**: Qualifying clean completion lacks affirmative headroom $\implies$ `VALID` + `NO_VOTE`.
- **$T \ge 2200.000000000\text{ s}$ from post-fork**: Exceeds watchdog budget; supervisor emits `WATCHDOG_EXPIRY` $\implies$ `SUPERVISOR_OVERALL_TIMEOUT`.

## 4. Supervisor Integer Clock Correlation (The $1.1\text{ s}$ Sanity Check)
Supervisor timeout loops maintain an integer-second accumulator updated on $100\text{ ms}$ polling ticks. The analyzer cross-checks this value against the reconstructed nanosecond duration:
$$|\text{duration\_seconds} - \text{supervisor\_integer\_elapsed\_sec}| \le 1.100\text{ s}$$
This rule detects supervisor process stalls or scheduler starvation within the **same clock domain**. It does **not** perform cross-domain clock subtraction. Any delta exceeding $1.1\text{ s}$ triggers `MEASUREMENT_FAILURE` and campaign STOP.

## 5. Secondary Clock Domains
- `CLOCK_BOOTTIME`: Retained for boot-instance context and pre-session quiet window analysis. Never subtracted from monotonic attempt timestamps.
- Host UTC / Wall Clock: File chronology and packet receipt ordering only.
- Host Monotonic Clock: Collector heartbeat and transport gap detection only. Host time never influences candidate compatibility duration.
