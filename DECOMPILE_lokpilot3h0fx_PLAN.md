# Plan: Disassembling `binaries/5.2.17/lokpilot3h0fx/0-0-6442.fw`

Status legend: ✅ verified by reverse-engineering `LokProgrammer.exe` / the data; ⚠️ hypothesis, still to verify.

## 1. Key insight (corrects earlier attempts)
`0-0-6442.fw` is **not** raw MCU code and not an opaque blob. `LokProgrammer.exe` decrypts it **on the PC**. Earlier attempts in `ATTEMPTS.md` failed because they began AES at offset `0x22` (treating the IV as ciphertext) and looked for XML magic instead of GZip. The pipeline has four layers:

```
.fw ("ESU " container) -> AES-256-CBC -> GZip -> XML (<dec:page> hex) -> per-page scrambling -> MCU flash image
```

## 2. Stage 1 – Outer container ✅ (22,372 bytes = 0x5764)
Parsed in the .NET obfuscated types (`TypeDef 691/695`, `Read` at RVA token `0x06001be7`).

| Offset | Size | Meaning |
|---|---|---|
| 0x00 | 4 | Magic `"ESU "` |
| 0x04 | 4 | Version `00 00 02 00` |
| 0x08 | 4 | Chunk 0 header (type `0x0001`, length 0) |
| 0x0C | 2 | Chunk 1 type `0x0022` (encrypted GZip stream) |
| 0x0E | 4 | Chunk 1 size `0x5734` |
| 0x12 | 16 | Stream ID (`01 00 …`) |
| 0x22 | 16 | AES IV `885463d3ada7578549c445c60cb4edae` |
| 0x32 | 0x5710 | AES-256-CBC ciphertext |
| 0x5742 | 0x22 | Chunk type `0x0020`: directory entry `"0-0-6442.xml"` → stream ID 1 |

AES-256 key (static, `FieldRVA` `0x8b9d6d`, also used by `DecoderInfo.dat`):
`3d15ed4f0ea1cc7caecd31500333b09728ff2dda41f472fc7115a454119f5625`.

Steps: read ciphertext `[0x32, 0x32+0x5710)`, AES-CBC decrypt, strip PKCS7, check `1f 8b 08`, GunZip → `0-0-6442.xml` (129,896 bytes).
The same procedure works for `DecoderInfo.dat` (decompresses to 104,485 bytes).

## 3. Stage 2 – XML ✅
- `<dec:hardware id="lp3h0fx" version="3.0">`, `<dec:firmware version="0.0.6442" type="dcc" date="18.10.2007@16:54:00">`.
- Cross-reference in `DecoderInfo.xml`: "LokPilot Fx V3.0", productID `0200002c`, magiccode `62E339AD`, cv7=136/mask 248.
- `<dec:code>`: **105 `<dec:page>`**, 288 hex chars = 144 bytes each (13,440 payload bytes = `0x3480`).
- `<dec:configuration>`: **100 `<dec:variable number location>`** entries mapping CVs `1..235` to `location="0..234"` (`location = CV - 1`) + bit slices (e.g. `map.33.out.phy.1.1`). This fits a 256-byte internal EEPROM and serves as the symbol table for semantic recovery.

## 4. Stage 3 – Page frame & descrambling
The PC sends each 144-byte page to the decoder's bootloader unchanged (via `GetNextPacket` types `0x060021ce`/`0x06001e5b`), so the scrambling is decoded on the PIC18F bootloader.

Frame layout ✅: `0..12` header (13 B), `13..140` payload (128 B), `141..143` trailer (3 B; `pos 141` low nibble is always `5` or `d`, likely checksum/CRC).

Position-dependent layer ✅: for the entire 144-byte frame (`pos = 0..143`, defining `i = (pos - 13) & 0xFF`),
```
Y[pos] = ((0x55 - page[pos]) & 0xFF) ^ i
```
Evidence this exact index-offset (`0x55 - byte`, matching a single PIC18 `SUBLW 0x55`, followed by `XORWF FSR0L` with a RAM buffer aligned so payload byte 0 sits at low address `0x00`) applies across the whole 144-byte frame:
- Blank flash regions in pages 4, 19, 33, 40, 71, 84, 93, 98, and 104 all yield constant `Y = 0x1C`.
- Header byte `pos 2` (raw values split across `0x36..0x39`, `0x42..0x45`, `0xb6..0xb9`, `0xc2..0xc5`) collapses to contiguous `0x04..0x0b` / `0x84..0x8b` (16 unique values) under `Y[2] ^ 0xE3`.
- Header `pos 4` (`0x6a`/`0x72` → `0xff`/`0xf7`), `pos 6` (`0x78`/`0x80` → `0xc7`/`0xcf`), `pos 7` (8 values), and `pos 10` (32 values, always even) show low-cardinality address/page-metadata fields, confirming pages in XML may be shuffled or non-sequentially addressed.

Inner byte substitution (`Y -> plain`) ✅/⚠️:
An empirical inversion from blank flash (`Y = 0x1C -> 0xFF`), a 21-entry descending/ascending table in page 4 (`i = 82..122`), and repeating structures in pages 0, 1, and 98 gives:
```python
z = Y ^ 0x0E
z ^= (z & 0x40) << 1
v = ((z >> 4) | (z << 4)) & 0xFF   # PIC18 SWAPF
dec2 = (0x20 - v) & 0xFF            # PIC18 SUBLW 0x20
```
- Under `dec2`: blank flash is `0xFFFF`; page 4 yields a 20-entry `RETLW` table (`0x0C0B..0x0C1E`); page 0 yields sequential offsets (`0x38..0x60`) paired with decrementing indices (`0x1F..0x16`); and 2-word instruction pairs appear with high regularity (`0xC1`/`0xC2`/`0x00` → `0x4F..0x53` ~95% of the time; `0x3E` → `0xFC`/`0xFE`; `0xD2` → `0x53`).
- ⚠️ **Unresolved residual quirk:** `dec2` still shows non-standard high-byte values (`0xC1`/`0xC2`/`0x00` → `0x4F..0x53` instead of standard PIC18 `0xEC/0xED/0xEF` → `0xF0`, a `0x41` vs `0x81` bit-6/7 flip in page 0, and `0x0D1F` after `0x0C1E` in page 4), meaning `Y -> plain` still has a slight non-linearity (likely another carry/offset or exact `SWAPF`/`SUBLW` ordering in the bootloader) or an extra PIC18-side encoding on `0x4F..0x53`.

Tasks:
1. **Solve exact `Y -> plain` bijection:** Use the known invariants (`0x1C -> 0xFF`, page 0's `+3`/`+6`/`+4` word-offset progression, page 4's `0x0B..0x1F` table, page 98's arithmetic blocks, and PIC18 2-word rules `CALL`/`GOTO` `0xEC..EF -> 0xF0` and `MOVFF` `0xC0..CF -> 0xF0..FF`) to eliminate the `bit 6/7` flip and `0x4F..0x53` discrepancy.
2. **Decode the 13-byte header (`pos 0..12`) & page order:** Correlate `(pos 2, pos 4, pos 6, pos 7, pos 10)` across all 105 pages (16 combinations of `(pos 2 & 0x7F, pos 4)` × 8 values of `pos 7`, etc.) to recover the 16-bit PIC18 Flash base address (`0x0000..0x3FFF` or shifted past a boot block) for every page and sort pages into linear Flash order.
3. **Solve the 3-byte trailer (`pos 141..143`):** Notice `pos 141` (raw) always ends in nibble `5` or `d`; test 16/24-bit CRC or sum/XOR over `pos 0..140` as an automatic correctness oracle.
4. **Optional hardware verification:** Capture or dump via the LokProgrammer bootloader protocol (see `PROTOCOL` notes / `LokProgrammer.exe` `..` → `..GetNextPacket`) if needed to confirm the bootloader's exact memory layout and decrypt loop.

## 5. Stage 4 – Target Architecture: PIC18F (assumed) ✅/⚠️
Assume a **Microchip PIC18F** microcontroller (consistent with the 18.10.2007 firmware date, 13,440-byte code size, `0xFFFF` erased Flash, 256-byte EEPROM CV space, and `SUBLW`/`SWAPF`-style bootloader math).

- **Likely MCU family:** 16 KB or 32 KB Flash PIC18F with 256 B internal EEPROM and 64-byte Flash write/erase blocks (128-byte bootloader pages = 2 × 64-byte blocks), e.g., **PIC18F2420 / PIC18F4420 / PIC18F2520** class (2006–2007 era, enhanced 16-bit core, up to 10 MIPS / 40 MHz, CCP/ECCP PWM for motor/function outputs, internal/external INT pins for DCC capture). Exact part number will be confirmed once SFR accesses (`0xF80..0xFFF`, e.g. `PORTA/B/C`, `CCP1CON`, `TMR0/1/2`, `EECON1/EEDATA`, `INTCON`, `OSCCON`) are decoded in Stage 5.
- **Instruction set & memory conventions:**
  - Little-endian 16-bit instruction words (2-byte aligned); most instructions 1 word, `CALL` (`0xEC/0xED`), `GOTO` (`0xEF`), `MOVFF` (`0xC0..0xCF`), and `LFSR` (`0xEE`) are 2 words with second word `0xFxxx`.
  - Hardware vectors at `0x0000` (Reset), `0x0008` (High-priority ISR), `0x0018` (Low-priority ISR) — if a bootloader occupies `0x0000..0x07FF` (or `0x0000..0x03FF`), application vectors are relocated by that offset (check whether page headers start at e.g. `0x0400`/`0x0800`, matching `pos 2` values `0x04..0x0b`!).
  - Data RAM banked (`BSR` / `MOVLB`) with Access Bank (`0x00..0x5F` RAM, `0x60..0xFF` SFRs at `0xF60..0xFFF`).
- **Disassembly tooling:** Install `gputils` (`gpdasm -p p18f2420` or `p18f2520`) or use a custom Python PIC18 disassembler + Ghidra (`PIC-18` language module) to disassemble the reconstructed image and score opcode validity (`CALL/GOTO/MOVFF -> 0xFxxx` rate, `RETURN`/`RETFIE` boundaries, valid SFR addresses).

## 6. Stage 5 – Reconstruction & semantic recovery
1. Sort and concatenate the 105 descrambled 128-byte payloads by their decoded Flash address into a flat binary (`out/lp3h0fx_6442.bin`) and Intel HEX (`.hex`).
2. Disassemble as PIC18F (`gpdasm` / Ghidra); identify the exact PIC18F variant from config words (if included), RAM size, and accessed SFRs (`TRIS*`, `ECCP*`, `TMR*`, `ADCON*`, `EEADR/EECON1`).
3. Map the 100 `<dec:variable>` entries (`location="0..234"`) to `EEDATA`/`EEADR` EEPROM read/write routines and RAM shadow variables (CV1 `prot.nmra.adr.pri` at EE `0`, CV29 at EE `28`, `map.*.out.phy.*` function-mapping matrix, dimming/effect CVs).
4. Label core DCC subsystems:
   - Reset & relocated interrupt vectors (high-priority ISR for DCC 58/100 µs edge capture via `INT0/CCP`, low-priority ISR for timers / function PWM / dimming effects).
   - DCC/Motorola preamble & XOR checksum decoder.
   - Service-mode programming & current-pulse ACK handler.
   - Six function output drivers (`LokPilot Fx V3.0` is motor-less, 6 function outputs with dimming/Mars/Gyra/strobe/firebox/coupler timers).
   - Bootloader re-entry trigger (magic sequence / firmware update command).
5. Export the fully commented PIC18F assembly listing (`out/lp3h0fx_6442.asm`) and symbol table.

## 7. Deliverables
- `tools/unpack_fw.py` (Stages 1–2) – AES-256-CBC + GZip → `0-0-6442.xml`.
- `tools/descramble.py` (Stage 3) – exact `Y -> plain` descrambler, header address decoder, trailer verifier, and `.bin`/`.hex` builder.
- `out/lp3h0fx_6442.bin`, `out/lp3h0fx_6442.hex`, `out/lp3h0fx_6442.asm`, `out/symbols.txt`.

## 8. Risks / open questions
- Residual `Y -> plain` non-linearity (`0x4F..0x53` 2nd words and bit 6/7 flips) must be solved before clean PIC18F disassembly.
- Page address encoding in header bytes `0..12` and trailer checksum (`141..143`) are not yet decoded.
- Exact PIC18F chip variant and bootloader-offset (`0x0400`/`0x0800`/etc.) remain to be confirmed from header addresses and SFR usage.

