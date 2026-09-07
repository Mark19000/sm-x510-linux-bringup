# EZE4 AVB trust graph — SM-X510

**Status: MECHANICALLY CONFIRMED FOR AVAILABLE IMAGES; COMPLETE DEVICE GRAPH PARTIAL.** Missing `prism`, `optics`, PIT, `super`/logical payloads, and Samsung metadata outside AVB.

Date: 2026-09-05. Source: official AOSP 1.3.0 `avbtool info_image` (local SHA-256 `e5a664a38db623da00f080219bc0ee60a640a9dc4a872803616fae4938ac749b`) over stock images in `artifacts/stock/images/`. Read-only inspection.

## Root Identity

`vbmeta.img`: SHA256_RSA4096; public-key SHA-1 `b6924fd490355eca36e5a5cd9c4d2b4bd6434029`; rollback index `0`, location `0`; flags `0`; release `avbtool 1.3.0`.

```text
vbmeta root (RIL 0, index 0)
├── HASH: boot, bootloader, fld, harx, init_boot, keystorage, ldfw, recovery,
│         tzsw, vendor_boot
├── HASHTREE: odm, product, system, system_dlkm, vendor, vendor_dlkm
├── CHAIN: dtbo  (RIL 1, OEM key) → embedded vbmeta → HASH dtbo
├── CHAIN: prism (RIL 2, OEM key) → child descriptors UNKNOWN (image absent)
└── CHAIN: optics (RIL 3, OEM key) → child descriptors UNKNOWN (image absent)
```

There is no direct hash of `dtbo` in root. The chain validates the embedded vbmeta of `dtbo`, which in turn contains its hash.

## Descriptors Table

All root descriptors use the root signature/key. The three chains declare the same key digest `b6924fd490355eca36e5a5cd9c4d2b4bd6434029`.

| Partition | Descriptor | Parent | Algorithm | Digest/root digest | Rollback index/location |
|---|---|---|---|---|---|
| boot | HASH | root | sha256 | `3f28d10f...31a420c` | root 0/0 |
| bootloader | HASH | root | sha256 | `7e62135d...67cd358` | root 0/0 |
| fld | HASH | root | sha256 | `1e964fb1...8e63ea9` | root 0/0 |
| harx | HASH | root | sha256 | `cc0b9883...279fa980` | root 0/0 |
| init_boot | HASH | root | sha256 | `4f514634...9f32efc` | root 0/0 |
| keystorage | HASH | root | sha256 | `f3db807c...839be499` | root 0/0 |
| ldfw | HASH | root | sha256 | `245d887e...1d61ef77` | root 0/0 |
| recovery | HASH | root | sha256 | `4fe5fd06...1a04ead7` | root 0/0 |
| tzsw | HASH | root | sha256 | `828b0aea...a6f3cad` | root 0/0 |
| vendor_boot | HASH | root | sha256 | `7c5898f8...7d050da7` | root 0/0 |
| odm | HASHTREE | root | sha256 | `f09c82ab...e5a664d` | root 0/0 |
| product | HASHTREE | root | sha256 | `41c99b30...3176953` | root 0/0 |
| system | HASHTREE | root | sha256 | `800d21ee...430ecc9` | root 0/0 |
| system_dlkm | HASHTREE | root | sha256 | `517a3198...525ce1` | root 0/0 |
| vendor | HASHTREE | root | sha256 | `fae03cae...e5cd3f2a` | root 0/0 |
| vendor_dlkm | HASHTREE | root | sha256 | `c10333ac...b50ca5d` | root 0/0 |
| dtbo | CHAIN | root | child HASH sha256 | child `47c853eb...77e2dde` | effective chain location 1; index 0 observed in child |
| prism | CHAIN | root | unknown inside child | child image absent | location 2; index unknown |
| optics | CHAIN | root | unknown inside child | child image absent | location 3; index unknown |

### Exact root HASH parameters

All use sha256, flags 0, and inherit rollback `0@location 0` from root.

| Partition | Image bytes | Salt | Digest |
|---|---:|---|---|
| boot | 39,363,360 | `a9b70a9b8c813071c8855ffe4fbee890cbd98a087c560ef8ab59dad40b43c1ba` | `3f28d10f5a347fff6ab0649058f71e83027c2575af5feb33c8935f30131a420c` |
| bootloader | 6,099,760 | `519778a6d66a59e1e21a3f9e196338e47f6ff2ba7add93e0f8c82c15b14db564` | `7e62135dd8b767ccd2720ed68b557d7407c4a2c323482bb40a1cc0aa367cd358` |
| fld | 17,200 | `f386f41f158423552d28ec26392d6c0f969aa70632605391d7e28d1f0c9999a2` | `1e964fb1058fa6cd8ad95c3ebcccf3a83d2bcf5463aa04c91ad268f3c8e63ea9` |
| harx | 2,097,936 | `b64c025448a0a4fa8bd9f793949b588c1dbe180ec347b73865daa239790ebb3c` | `cc0b988325d3030ff3ef72d15aafbb05ffb4777ae3b7ef1323bbf7a2279fa980` |
| init_boot | 2,495,248 | `b60b096362e60a2c065071a96afa8cf5f8b725e83b65d3406b2c0e26694158e0` | `4f514634dc0c2efbd654f25536b4d32c621ea6db50defb7ee4193f49d9f32efc` |
| keystorage | 17,168 | `0b7472ce219afb9d62e51dc2371265cf1baadd25b15324749fc97d5369c756e6` | `f3db807c7c35b57c7dacf8d9ac5c64bbdcb24d1035c201f56a947881839be499` |
| ldfw | 1,278,736 | `31ccaa946f499b8049eb6eca4a552adf66482d1e38f9588999428be4604f4050` | `245d887e4982f50f811eb4b4d43dae300aa43091e297d1818bcfb71b1d61ef77` |
| recovery | 72,770,336 | `d22982cfaf46250401b617eb16336492d1ad3d34b510e30c8056675d866d3273` | `4fe5fd0623377c46872c3b5fe2206e62b247f9e3b4e2de258777fdfb1a04ead7` |
| tzsw | 1,573,648 | `466d9968697555bae0ec421e44316a4e96aec17db46e3af154a4fc696907e3d1` | `828b0aeac9bebcf171877ce1442f7799a0311ed620a12aa3558d41872a6f3cad` |
| vendor_boot | 18,334,480 | `ecccd3614d9f2bdbeb8979e85b812f76db2360aedd63c674cda224097e2b1b3d` | `7c5898f8f643d5fb3109cd75a207b7a363876f7c0acf388c42ef1fe87d050da7` |

## Boot-family embedded metadata

`boot`, `init_boot`, `vendor_boot`, `dtbo` and `recovery` each have an AVB footer and embedded self-HASH vbmeta signed with the same key digest; their embedded headers show index 0/flags 0. Root nevertheless protects boot/init_boot/vendor_boot/recovery through its own direct HASH descriptors. Do not treat a self-footer as a separate root edge that is absent from the descriptors.

| Image | Container bytes | Original bytes | Self-HASH salt | Self-HASH digest |
|---|---:|---:|---|---|
| boot | 67,108,864 | 39,363,360 | `a9b70a9b8c813071c8855ffe4fbee890cbd98a087c560ef8ab59dad40b43c1ba` | `3f28d10f5a347fff6ab0649058f71e83027c2575af5feb33c8935f30131a420c` |
| init_boot | 16,777,216 | 2,495,248 | `b60b096362e60a2c065071a96afa8cf5f8b725e83b65d3406b2c0e26694158e0` | `4f514634dc0c2efbd654f25536b4d32c621ea6db50defb7ee4193f49d9f32efc` |
| vendor_boot | 33,554,432 | 18,334,480 | `ecccd3614d9f2bdbeb8979e85b812f76db2360aedd63c674cda224097e2b1b3d` | `7c5898f8f643d5fb3109cd75a207b7a363876f7c0acf388c42ef1fe87d050da7` |
| dtbo | 8,388,608 | 542,896 | `558dc9051ca9f4d6616b9bf07175ad3f3a1a2534cc1026902eb4909441f3e456` | `47c853ebdd4c511ff3a45d080fbf6313f204319348407f0ead1fb17da77e2dde` |
| recovery | 100,663,296 | 72,770,336 | `d22982cfaf46250401b617eb16336492d1ad3d34b510e30c8056675d866d3273` | `4fe5fd0623377c46872c3b5fe2206e62b247f9e3b4e2de258777fdfb1a04ead7` |

All: SHA256_RSA4096, key SHA-1 `b6924fd490355eca36e5a5cd9c4d2b4bd6434029`, rollback index 0, flags 0. The salts/digests of boot/init_boot/vendor_boot/recovery match the root descriptors.

## Root HASHTREE parameters

| Partition | Image bytes | Salt | Root digest | Flags / rollback parent |
|---|---:|---|---|---|
| odm | 1,282,048 | `12046f75ee0b6add426a1bd3e7a3f34755d09dab0b42878464786d24fa8b77d7` | `f09c82ab2ec552243c71e86a3ff512dcb83695ffaf81e9f0a4db67930e5a664d` | 0 / root 0@0 |
| product | 2,047,344,640 | `523f0eab4324d441da78485b6d39b85663890a8898a51fa1912eaedaf1ffed52` | `41c99b3076777c415459dc17aa5f412b280cd1218f3a39f0a1d81df913176953` | 0 / root 0@0 |
| system | 8,343,461,888 | `3959ffa82aa3b29023d795bc10a4135251c8bbde8bf8aeb35966a5d8e3fde156` | `800d21ee501996e9154b4887596b10b8f226dd101b27bddb2fd5cd3d1430ecc9` | 0 / root 0@0 |
| system_dlkm | 262,144 | `d6835baa97f8a102f0316c1f03ccc18e4db92aeb85d10c55e195c02dd60d1f0c` | `517a3198b722f9e977b6dafdbe601e33c31caf30d5905ad8a5f675d11b525ce1` | 0 / root 0@0 |
| vendor | 1,072,418,816 | `e7f47c350e5a2c8d3177b6003f721db14f7de4aa7091e7394fbf9dbf761bb174` | `fae03cae3dfac01089fd01dec259e86be9957e87a1e25830d219b26601073f2a` | 0 / root 0@0 |
| vendor_dlkm | 262,144 | `226a5cafe5a63149bf36d028c4380bd71edd191ee5483f9838292ab04d58841b` | `c10333ac6a86caa2a9c0b7df7355431a8c463437c0ee0e2dba633ab66b50ca5d` | 0 / root 0@0 |

## Canonical flag semantics

- `1`: `HASHTREE_DISABLED` only.
- `2`: `VERIFICATION_DISABLED`.
- `3`: both bits.

These are AOSP semantics, not proof that Samsung accepts flags 2/3 when unlocked. No candidate vbmeta was generated.

## Limits

`prism` and `optics` are not present locally, so their child descriptors, algorithms and rollback values cannot be claimed. `super.img` is absent and the raw logical images are not retained. CP/PIT/RPMB/Samsung SWREV policy is outside what AVB descriptors reveal. Consequently this is exact for the inspected nodes, not a claim of a globally complete device trust graph.
