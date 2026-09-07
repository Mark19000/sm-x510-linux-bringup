# Bootloader Unlock and Knox — Decision Gate

Date: 2026-09-05. The tablet remains stock locked/green and `warranty_bit=0`.

## Distinct Events

| Event | EZE4 Evidence | Established Consequence |
|---|---|---|
| Enter warning/Download | **CONFIRMED** | Did not alter observed state. |
| Long-press for Device Unlock Mode | Visible instruction **CONFIRMED**; execution not yet photographed | Expected to open a dialog; confirmation not assumed. |
| Confirm unlock | **NOT PERFORMED** | AOSP supports transition + wipe; final Samsung detail pending. |
| Factory reset | **STRONGLY_SUPPORTED** | Must be accepted and backed up beforehand. |
| Boot stock unlocked | **UNKNOWN** here | Must be measured before custom boot. |
| Custom flash/execution | **NOT PERFORMED** | Distinct event from unlock. |
| Warranty Bit `0→1` | transition **NOT OBSERVED** | Persistence after unapproved software supported; exact EZE4 timing **UNKNOWN**. |

Effects on Widevine, OTA, each Knox service, or duration of warnings are not presented as universally measured.

## Decision State

The entry path is already advertised by the unit itself; practical capability is **STRONGLY_SUPPORTED**. Capturing the final dialog and its safe exit remains pending. Host recovery also remains unvalidated, but this is an absolute gate for the first flash, not necessarily for the owner to conceptually evaluate unlocking.

Prior to executing unlock: backup/credentials verified; explicit acceptance of wipe and Knox risk; final dialog documented; locked baseline archived. Prior to any custom flash, additionally: full firmware and host/PIT recovery prepared.

Operational status until photographing final dialog: **NOT_READY_FOR_OWNER_UNLOCK_DECISION**. First custom flash: **NOT READY**.
