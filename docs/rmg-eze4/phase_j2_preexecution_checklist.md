# J2 human pre-execution checklist

This checklist contains no execution command and grants no authorization.

- [ ] Device model/device identity matches SM-X510 / gts9fewifi.
- [ ] Firmware fingerprint and incremental match approved EZE4 identity.
- [ ] Kernel identity matches the approved EZE4 baseline.
- [ ] Current boot identity is captured and unique.
- [ ] Payload, target, stock Image and collector hashes match the approved manifest.
- [ ] Effective candidate is 2200; no environment override or unrelated parameter change exists.
- [ ] Phase I plus J2 synthetic self-tests pass from a clean checkout.
- [ ] A new raw evidence directory and immutable session/trial naming are configured.
- [ ] Free disk space satisfies the approved worst-case capture budget plus 2x reserve.
- [ ] Device-monotonic clock capture/resolution and calibration tuples are available.
- [ ] ADB/collector transport is stable for the approved preflight interval.
- [ ] Foreground/freezer and thermal-condition detection are ready and tested synthetically.
- [ ] Operator understands all trial, session and experiment STOP rules.
- [ ] No unrelated validation, tuning, background stressor, or parameter change is active.
- [ ] Dirty/writer/unsafe-retry signals are visible and will terminate the session.
- [ ] Recovery path, device ownership, legal authorization and human abort path are understood.
- [ ] Exact condition thresholds and artifact manifest have received independent approval.
- [ ] This design has separate explicit authorization for any future real L3 run.
