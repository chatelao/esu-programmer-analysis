# Plan: Disassembling `binaries/5.2.17/loksound5l-hv-all/5-2`

Status legend: ✅ verified by inspecting `5-2/*.fw` / `DecoderInfo.dat` / `LokProgrammer.exe`; ⚠️ hypothesis, still to verify.

## 1. Key insight (adapted from `DECOMPILE_lokpilot3h0fx_PLAN.md`)
All 17 firmware files in `binaries/5.2.17/loksound5l-hv-all/5-2/` (`5-6-145.fw` through `5-13-180.fw`) use the **exact same Stage 1 & Stage 2 pipeline** as `lokpilot3h0fx/0-0-6442.fw` (correcting earlier claims in `DECODER_FORMAT.md` and `DECRYPT.md` that the `.fw` container could not be decrypted):

```
.fw ("ESU " container) -> AES-256-CBC -> GZip -> XML (<dec:page> hex) -> per-page unwrap/decrypt -> MCU flash image(s)
```

Unlike `0-0-6442.fw` (single 105 × 144-byte PIC18 code stream), `loksound5l-hv-all/5-2` XML files contain **two distinct `<dec:page>` formats**:
- **272-byte pages** (278–295 pages, growing across firmware revisions; ~71–75.5 KB payload at 256 B/page): high entropy (`7.9976` bits/byte), completely re-randomized between builds (`271/272` bytes differ even between same-XML-size builds `5-12-177.fw` and `5-12-178.fw`), targeting the main **SAMC51** ARM Cortex-M MCU.
- **145-byte pages** (always **41 pages**, 100% byte-for-byte identical across all 17 revisions from `5-6-145.fw` to `5-13-180.fw` and across `5-0`/`5-1`/`5-2`): every page starts with `0x20` followed by 144 bytes (`13 + 128 + 3` frame layout), containing lightly scrambled arithmetic/XOR-masked tables rather than AES ciphertext — likely targeting an **auxiliary MCU** (coprocessor) or static bootloader/table region.

## 2. Stage 1 – Outer container ✅
Verified across all **17/17** `.fw` files in `binaries/5.2.17/loksound5l-hv-all/5-2/`. Example for the latest build, `5-13-180.fw` (168,020 bytes = `0x29054`):

| Offset | Size | Meaning |
|---|---|---|
| `0x00` | 4 | Magic `"ESU "` |
| `0x04` | 4 | Version `00 00 02 00` |
| `0x08` | 4 | Chunk 0 header (type `0x0001`, length 0) |
| `0x0C` | 2 | Chunk 1 type `0x0022` (encrypted GZip stream) |
| `0x0E` | 4 | Chunk 1 size `0x29024` |
| `0x12` | 16 | Stream ID (`01 00 …`) |
| `0x22` | 16 | AES IV (unique per `.fw` file; `42ff0227c26e4bfb26e19aa8052604bd` for `5-13-180.fw`) |
| `0x32` | `0x29000` | AES-256-CBC ciphertext |
| `0x29032` | `0x22` | Chunk type `0x0020`: directory entry `"5-13-180.xml"` → stream ID 1 |

AES-256 key (static, same as `0-0-6442.fw` and `DecoderInfo.dat`):
`3d15ed4f0ea1cc7caecd31500333b09728ff2dda41f472fc7115a454119f5625`.

Steps: read ciphertext `[0x32, 0x0E + chunk1_size)`, AES-256-CBC decrypt, strip PKCS7, check `1f 8b 08`, GunZip → `5-13-180.xml` (2,123,039 bytes).

## 3. Stage 2 – XML ✅
- **Schema nesting:** Unlike `0-0-6442.xml`, `<dec:firmware>` is nested inside `<dec:hardware id="ls5l-hv" version="5.2">` (`type="all"`).
- **Cross-reference in `DecoderInfo.dat`:** `"LokSound 5 L"`, `<sound type="V50"><flash>128</flash></sound>` (128 Mbit external sound flash), `hardware version="5.2" path="loksound5l-hv-all/5-2" productID="020000DD"`.
- **Inventory of all 17 revisions in `5-2/`:**

| File | `.fw` Size | XML Size | Version | Date | Total Pages | 272 B | 145 B | `<dec:variable>` |
|---|---|---|---|---|---|---|---|---|
| `5-6-145.fw` | 162,323 | 2,098,754 | `5.6.145` | `04.04.2022@15:55:09` | 319 | 278 | 41 | 2,227 |
| `5-6-147.fw` | 163,059 | 2,099,904 | `5.6.147` | `06.09.2022@15:00:33` | 321 | 280 | 41 | 2,227 |
| `5-6-149.fw` | 163,011 | 2,100,050 | `5.6.149` | `11.01.2023@16:38:05` | 321 | 280 | 41 | 2,227 |
| `5-7-151.fw` | 164,291 | 2,104,022 | `5.7.151` | `01.02.2023@13:35:05` | 325 | 284 | 41 | 2,233 |
| `5-8-156.fw` | 164,691 | 2,111,191 | `5.8.156` | `09.05.2023@11:42:34` | 325 | 284 | 41 | 2,252 |
| `5-9-159.fw` | 165,635 | 2,113,366 | `5.9.159` | `11.10.2023@17:21:46` | 328 | 287 | 41 | 2,254 |
| `5-9-160.fw` | 165,587 | 2,113,366 | `5.9.160` | `23.11.2023@14:04:39` | 328 | 287 | 41 | 2,254 |
| `5-9-162.fw` | 165,075 | 2,101,856 | `5.9.162` | `09.02.2024@11:49:41` | 327 | 286 | 41 | 2,254 |
| `5-10-166.fw` | 165,652 | 2,103,248 | `5.10.166` | `29.04.2024@16:37:07` | 329 | 288 | 41 | 2,255 |
| `5-10-168.fw` | 165,636 | 2,103,248 | `5.10.168` | `13.06.2024@10:25:28` | 329 | 288 | 41 | 2,255 |
| `5-11-169.fw` | 166,436 | 2,105,427 | `5.11.169` | `27.06.2024@16:57:54` | 332 | 291 | 41 | 2,257 |
| `5-12-172.fw` | 166,532 | 2,109,317 | `5.12.172` | `19.07.2024@16:50:03` | 332 | 291 | 41 | 2,259 |
| `5-12-175.fw` | 167,252 | 2,115,347 | `5.12.175` | `23.10.2024@10:18:31` | 334 | 293 | 41 | 2,259 |
| `5-12-176.fw` | 167,348 | 2,115,347 | `5.12.176` | `08.11.2024@11:53:06` | 334 | 293 | 41 | 2,259 |
| `5-12-177.fw` | 167,572 | 2,117,589 | `5.12.177` | `27.11.2024@10:47:07` | 335 | 294 | 41 | 2,259 |
| `5-12-178.fw` | 167,620 | 2,117,589 | `5.12.178` | `20.05.2025@12:26:47` | 335 | 294 | 41 | 2,259 |
| `5-13-180.fw` | 168,020 | 2,123,039 | `5.13.180` | `21.11.2025@11:46:32` | 336 | 295 | 41 | 2,279 |

- **`<dec:configuration>`:** `default="0" backup="255@2364" size="12*224"` (2,688-byte banked CV/NVM map: 12 banks × 224 bytes, indexed via CV31/CV32 `index="..."`). In `5-13-180.xml`, 2,279 `<dec:variable>` entries map CVs and bit slices (`prot.nmra.*`, `prot.mmot.*`, `mot.*`, `map.*.in.key.*`, `rnd.gen.*`, sound slot triggers/volumes) to `location="0..2687"`, serving as the symbol table for semantic recovery.

## 4. Stage 3 – Dual Page Frames & Decryption/Descrambling ⚠️
Unlike `lokpilot3h0fx`, `5-13-180.xml` has two page types with completely different properties:

### 4.1 Type A: 272-byte pages (`idx 0..294` in `5-13-180.xml`)
- **Observed properties ✅:**
  - `295 × 256 = 75,520` bytes (~73.75 KB) if framed as `16 B overhead + 256 B payload` (matching SAM NVM 256-byte row/page programming).
  - Overall entropy is `7.9976` bits/byte; every byte position `0..271` has `157..203` unique values across 295 pages. All `5,015` 16-byte blocks and `20,060` 4-byte words are unique (ruling out ECB mode and static XOR pads).
  - Differential test (`5-12-177.fw` vs `5-12-178.fw`, identical XML size `2,117,589` bytes): **all 294** 272-byte pages differ in ~271/272 bytes. Cross-hardware test (`5-0` vs `5-2`, `5-1` vs `5-2` for `5-13-180.fw`): `0/295` 272-byte pages match.
  - `.NET` metadata audit of `LokProgrammer.exe` ✅: the static Stage 1 AES-256 key (`3d15ed4f...`) appears at file offsets `0x8b7f6d` and `0x8b832b`, and there are **only two** `CreateDecryptor` callers in the entire executable (`0x0600359c` at RVA `0x1ff114`, `0x060036c0` at RVA `0x20849c` — Babel string DB and Stage 1 `.fw`/`DecoderInfo.dat`). Thus `LokProgrammer.exe` **never** decrypts `<dec:page>` payloads; the 272-byte pages are decrypted exclusively by the **SAMC51 bootloader** (e.g., 16-byte IV/nonce + 256-byte AES-CBC/CTR, or 12-byte header + 256-byte ciphertext + 4-byte tag/CRC).

### 4.2 Type B: 145-byte pages (`idx 295..335` in `5-13-180.xml`)
- **Observed properties ✅:**
  - Always **41 pages**, 100% identical across all 17 revisions (`5-6-145` to `5-13-180`) and across hardware `5-0`, `5-1`, `5-2`.
  - Byte `0` is always `0x20` (`41/41` pages). Bytes `1..144` are 144 bytes (same frame length as `lokpilot3h0fx`'s `13 + 128 + 3`).
  - Does **not** use `0-0-6442`'s `0x55 - byte ^ i`, and is **not** AES-encrypted:
    - `145B[13]` (`idx 308`) exhibits `0xAC + (pos ^ 4)` at `pos 15..39` (`b7, c0..c3, bc..bf, c8..cb, c4..c7, d0..d3, cc..cf, d8`).
    - `145B[31]` (`idx 326`) exhibits `0xBC + ((pos - 13) ^ 0x0F)` at `pos 13..68` (`cb..bc, db..cc, eb..dc, fb..f4`) and `0x7B - ((pos - 77) ^ 0x02)` at `pos 77..108` (`79, 78, 7b, 7a, 75, 74, 77, 76...`).
  - Total payload at 128 B/page is `41 × 128 = 5,248` bytes — consistent with a static auxiliary/coprocessor firmware, bootloader stub, or immutable lookup tables.

### 4.3 Tasks
1. **Trace `LokProgrammer.exe` packet dispatch:** Inspect `GetNextPacket` / `ls5l-hv` handlers in `LokProgrammer.exe` to confirm whether `272B` and `145B` pages are sent verbatim over serial, and how the `0x20` prefix byte on `145B` pages is interpreted by the bootloader protocol.
2. **Solve the 145-byte pages (`0x20` + 144 B):** Use the exact arithmetic/XOR-masked runs in `145B[13]` and `145B[31]` to recover the position-dependent and byte-level descrambling transform, decode the 13-byte header + 3-byte trailer, and determine the target (secondary MCU code vs static tables).
3. **Recover the 272-byte page cipher/key:** Determine the `272 = 16 + 256` (or `13 + 256 + 3` / `12 + 256 + 4`) layout and obtain the decryption key/algorithm (either from `LokProgrammer.exe` if client-side, or via hardware bootloader extraction / SWD / fault injection / bus capture if decrypted exclusively inside the SAMC51 bootloader).

## 5. Stage 4 – Target Architecture: SAMC51 (ARM Cortex-M, assumed) ⚠️
Assume a **Microchip SAMC51** ARM Cortex-M microcontroller (note: in Microchip's SAM lineup, `SAMC21` is Cortex-M0+ 5V with 64 B Flash pages / 256 B rows, whereas `SAMD51`/`SAME51` is Cortex-M4F 3.3V with 512 B Flash pages / 8 KB blocks; "SAMC51" is treated here as an ARM Cortex-M0+/M4F SAM-family MCU with 256-byte NVM programming units).

- **Memory map & Flash geometry (SAM Cortex-M conventions):**
  - **Flash:** Base `0x00000000`. Bootloader likely occupies the first `16 KB` (`0x00000000..0x00003FFF`) or `32 KB` (`0x00000000..0x00007FFF`); application image (~75.5 KB for `5.13.180`) sits immediately above the bootloader with `SCB->VTOR` pointing to the relocated vector table.
  - **SRAM:** Base `0x20000000` (initial stack pointer `MSP` at word 0 of the vector table will be `0x2000xxxx`).
  - **Peripherals:** `0x40000000..0x48000000` — look for `NVMCTRL` (Flash & `RWWEE` / SmartEEPROM for the `12*224` = 2,688-byte CV store), `SERCOM` (SPI/QSPI to the 128 Mbit V5.0 sound flash + UART), `TCC`/`TC` (motor H-bridge PWM & function output dimming), `EIC`/`EVSYS` (DCC/MM/mfx/Selectrix edge capture), and `ADC` (motor BEMF & RailCom/current sense).
- **Instruction set:**
  - Little-endian ARM **Thumb / Thumb-2** (16-bit and 32-bit instructions; all function pointers and vector entries have bit 0 set: `addr | 1`).
  - Vector table validation: `[0] = 0x2000xxxx` (4-byte aligned SP), `[1..15]` = `0x00004xxx | 1` or `0x00008xxx | 1` (Reset, NMI, HardFault, SVCall, PendSV, SysTick), followed by SAM peripheral IRQs.
- **Disassembly tooling:**
  - `llvm-objdump -d --triple=thumbv6m-none-eabi` (Cortex-M0+) or `--triple=thumbv7em-none-eabi` (Cortex-M4F) — `/usr/bin/llvm-objdump` is already available in this environment.
  - `arm-none-eabi-objdump` / Ghidra (`ARM:LE:32:Cortex`) for full cross-referencing, literal pool (`LDR Rd, [PC, #imm]`) resolution, and decompilation.

## 6. Stage 5 – Reconstruction & semantic recovery ⚠️
1. Decrypt/descramble and sort the 295 × 256-byte payloads by their decoded Flash address into `out/ls5l_hv_5_13_180.bin` (75,520 bytes) and `.hex`/`.elf`; separately export the 41 × 128-byte region as `out/ls5l_hv_aux_145b.bin` (5,248 bytes).
2. Disassemble as Thumb/Thumb-2; confirm exact SAM variant (`SAMC21` Cortex-M0+ vs `SAMD51`/`SAME51` Cortex-M4F vs `SAMC51`) from `VTOR` base, `MSP` SRAM size, `CPUID` checks, and `NVMCTRL`/`SERCOM`/`TCC` peripheral base addresses (`0x4000xxxx` vs `0x4100xxxx` vs `0x4200xxxx`).
3. Map the 2,279 `<dec:variable>` entries (`size="12*224"`, `location="0..2687"`) to the NVM/RWWEE CV read/write routines and RAM shadow struct.
4. Label core LokSound 5 L HV subsystems:
   - Relocated vector table, `Reset_Handler` (`.data`/`.bss` init, clock/PLL setup), and `SysTick`.
   - Multi-protocol (`type="all"`) DCC/Motorola/mfx/Selectrix edge-capture ISR (`EIC`/`TC`) and packet parser.
   - RailCom cutout & bidirectional feedback driver.
   - Motor H-bridge PWM (`TCC`), BEMF `ADC` sampling, and PID speed controller.
   - 128 Mbit V5.0 external sound flash (`SERCOM` SPI/QSPI) streaming, audio decompression/mixing, and DAC/amplifier output.
   - Function outputs, lighting effects, and random sound generators (`rnd.gen.*`).
   - Bootloader re-entry trigger and firmware update handler.
5. Export the annotated disassembly (`out/ls5l_hv_5_13_180.asm`) and symbol table (`out/symbols.txt`).

## 7. Deliverables
- `tools/unpack_fw.py` (Stages 1–2) – AES-256-CBC + GZip → `5-13-180.xml` (and batch support for all 17 files in `5-2/`).
- `tools/descramble_145b.py` (Stage 3.2) – descrambler for the 41 × 145-byte `0x20`-prefixed pages.
- `tools/decrypt_272b.py` (Stage 3.1) – 272-byte page decryptor/assembler (once key/IV layout is recovered) → `out/ls5l_hv_5_13_180.bin`, `.hex`.
- `out/ls5l_hv_5_13_180.asm`, `out/symbols.txt`.

## 8. Risks / open questions
- **272-byte page encryption key:** Differential analysis (`5-12-177.fw` vs `5-12-178.fw`) confirms per-page/per-build encryption; if the key resides solely inside the read-protected SAMC51 bootloader (not in `LokProgrammer.exe`), software-only decryption of Stage 3.1 is blocked without hardware key extraction.
- **Exact SAM part ("SAMC51"):** Confirm whether the silicon is Cortex-M0+ (`SAMC21`-class, `thumbv6m`) or Cortex-M4F (`SAMD51`/`SAME51`-class, `thumbv7em`) once Stage 3.1 yields plaintext instructions/vectors.
- **Role of the 41 × 145-byte (`0x20`) pages:** Determine whether they represent an auxiliary MCU image or static decoder data/tables, and why they remain invariant across all 17 firmware revisions.

## 9. Algorithms

### 9.1 Stage 1: `.fw` / `DecoderInfo.dat` Container Decryption ✅
Verified against all 17 `.fw` files in `5-2/` and `DecoderInfo.dat` (implemented in `LokProgrammer.exe` method `0x060036c0` at `RVA 0x20849c`):

1. **Header validation:** Verify magic `data[0x00:0x04] == b"ESU "` and version `data[0x04:0x08] == b"\x00\x00\x02\x00"`.
2. **Chunk 1 parsing:** Read `<HI` at `0x0C` → `(chunk_type, chunk_size)` where `chunk_type == 0x0022` (encrypted GZip stream).
   - `stream_id = data[0x12:0x22]` (16 bytes).
   - `iv = data[0x22:0x32]` (16 bytes, unique per file).
   - `ciphertext = data[0x32 : 0x0E + chunk_size]` (multiple of 16 bytes).
   - Directory chunk follows at `0x0E + chunk_size`: `chunk_type == 0x0020`, `<HI` header + ASCII XML filename + 16-byte stream ID.
3. **AES-256-CBC decryption:**
   - Static 256-bit key (stored in `LokProgrammer.exe` at file offsets `0x8b7f6d` and `0x8b832b`):
     `K = 3d15ed4f0ea1cc7caecd31500333b09728ff2dda41f472fc7115a454119f5625`
   - Decrypt `ciphertext` with `AES-256-CBC(key=K, iv=iv)` and strip PKCS#7 padding.
4. **GZip decompression:** Verify magic `1f 8b 08` and GunZip to UTF-8 XML (with UTF-8 BOM `ef bb bf`).

### 9.2 Stage 2: XML Code & Configuration Extraction ✅
1. **XML traversal:** Parse `<dec:decoder>/<dec:hardware id="ls5l-hv" version="5.2">/<dec:firmware>` (namespace `http://www.esu.eu/2008/DECODER/specs`).
2. **Page classification:** Hex-decode each `<dec:code>/<dec:page>` element and partition by byte length:
   - `len == 272` → Type A (SAMC51 main firmware pages; `278..295` pages depending on version).
   - `len == 145` → Type B (invariant `0x20`-prefixed pages; always `41` pages).
3. **Configuration symbol mapping:** Parse `<dec:configuration size="12*224">` (`2,688` bytes across 12 banks of 224 bytes). Each `<dec:variable>` maps `(index, number)` (where `index` encodes CV31/CV32 bank selection) and bit `slice` (`msb:lsb`) to byte offset `location` (`0..2687`).

### 9.3 Stage 3A: 272-Byte Page Encryption Model (SAMC51) ⚠️
- **PC-side pass-through:** `LokProgrammer.exe` has only two `CreateDecryptor` call sites (`0x0600359c` for Babel `KmnL.res.bin` and `0x060036c0` for Stage 1 `.fw`/`DecoderInfo.dat`). `GetNextPacket` (`0x06001d7f`, `0x06001dcc`, `0x06001e5b`) dispatches `<dec:page>` bytes without decryption.
- **Cipher properties:**
  - `5,015/5,015` unique 16-byte blocks and `20,060/20,060` unique 4-byte words across `5-13-180.fw` (rules out ECB and static XOR).
  - Entropy `7.9976` bits/byte; `0/295` pages match across `5-0`/`5-1`/`5-2`; `294/294` pages change in ~271/272 bytes between `5-12-177.fw` and `5-12-178.fw`.
- **Inferred bootloader algorithm:** Each 272-byte frame consists of `16 B` per-page IV/nonce/header + `256 B` ciphertext (matching SAM 256-byte NVM row programming), or `12 B` header + `256 B` ciphertext + `4 B` integrity tag/CRC, decrypted inside the SAMC51 bootloader using a hardware-resident key (AES-128/256-CBC/CTR or AEAD).

### 9.4 Stage 3B: 145-Byte Page Obfuscation Model (`0x20` + 144 B) ⚠️
- **Framing:** `byte[0] == 0x20` (packet/target selector, constant across all 41 pages), followed by a 144-byte frame (`pos 1..144`), matching the `13 B header + 128 B payload + 3 B trailer` geometry of `0-0-6442.fw`.
- **Observed scrambling invariants (non-AES):**
  - Unlike `0-0-6442.fw`'s `Y[pos] = ((0x55 - page[pos]) & 0xFF) ^ ((pos - 13) & 0xFF)`, the 145-byte pages expose direct arithmetic/XOR-masked runs in raw bytes:
    - `145B[13]`, `pos 15..39`: `byte[pos] = (0xAC + (pos ^ 0x04)) & 0xFF`
    - `145B[31]`, `pos 13..68`: `byte[pos] = (0xBC + ((pos - 13) ^ 0x0F)) & 0xFF`
    - `145B[31]`, `pos 77..108`: `byte[pos] = (0x7B - ((pos - 77) ^ 0x02)) & 0xFF`
    - `145B[31]`, `pos 112..143`: 8 × 4-byte structured records.
  - Because all 41 pages are 100% identical across `5-6-145`..`5-13-180` and `5-0`/`5-1`/`5-2`, and no blank-flash (`0xFF`) page is present, the exact inverse bijection remains to be recovered from the bootloader or known-plaintext table matching.

### 9.5 Reference: `LokProgrammer.exe` Babel.NET Resource Decryption ✅
Used internally by `LokProgrammer.exe` (`0x0600359c` at `RVA 0x1ff114`) to unpack `KmnL.res.bin` (4 MB string/constant database, unrelated to `.fw` payload decryption):
- `AES-256-CBC` with key `7c5d7ab7e9ae50329323d2110dae054b37bc0e50085c1dd55e32a1fa94daa67b` and IV `5e3f5d94bd3120c03d0a6629f302dd39`, followed by Babel's LZW + Huffman decompression (`Class794`).

