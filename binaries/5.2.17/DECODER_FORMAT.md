# ESU Decoder Firmware File Format (.fw) - In-Depth Documentation

This document describes the binary format of ESU firmware files (`.fw`) used by the LokProgrammer software (v5.x).

## 1. High-Level Structure

The `.fw` file is a container format that bundles binary firmware and metadata.

| Offset | Length | Description |
| :--- | :--- | :--- |
| `0x00` | 34 bytes | Global Header |
| `0x22` | 182 bytes | Metadata / Signature Section (Encrypted) |
| `0xD8` | Variable | Encrypted/Compressed Payload (ARM Binary) |
| EOF - 32 | 32 bytes | Footer (Fixed-size) |

## 2. Global Header (34 Bytes)

The header is consistent across all generations (V3, V4, V5).

| Offset | Type | Value / Description |
| :--- | :--- | :--- |
| `0x00` | String | `"ESU "` (Magic Number) |
| `0x04` | uint32 | File Size (Little Endian) |
| `0x08` | uint16 | Header Type (Always `0x0002`?) |
| `0x0A` | uint16 | Sub-header Type (Always `0x0001`?) |
| `0x0C` | uint16 | Header Size (Always `0x0022` = 34 bytes) |
| `0x0E` | uint16 | **Minor Version / Build ID** |
| `0x10` | uint8 | **Generation ID** (`0x00`=V3, `0x01`=V4, `0x02`=V5) |
| `0x11` | uint8 | Hardware/Model ID |
| `0x12` | uint16 | Constant (`0x0001`) |
| `0x14` | 14 bytes | Padding / Reserved (Mostly `0x00`) |

## 3. Metadata / Signature Section (182 Bytes)

This section starts at `0x22`. It contains a cryptographic signature or a proprietary metadata block. Analysis shows high entropy and no plain-text strings, indicating it is likely encrypted or signed using a hash like SHA-256 (confirmed by `System.Data.HashFunction` dependencies in the software).

## 4. Payload Section (ARM Binary)

The payload begins at `0xD8`.

- **Target Architecture:** ARM Cortex-M (confirmed by "ARM Controller" references in release notes). Specifically, the LokSound 5 family uses modern ARM silicon.
- **Data State:** Encrypted. Standard ARM vector tables (Stack Pointer / Reset Vector) are not visible at the start of the payload, indicating a cipher layer (likely AES, as `CreateDecryptor` is called by `LokProgrammer.exe`).
- **Entropy:** 0.998+ (Maximum). This confirms the payload is either encrypted or compressed with a high-ratio algorithm.

## 5. Footer (32 Bytes)

The last 32 bytes contain the internal XML descriptor name.

| Offset | Description |
| :--- | :--- |
| EOF - 32 | Unknown 4-byte value |
| EOF - 28 | **Filename String** (e.g., `5-13-180.xml`) |
| EOF - 12 | Constant (`0x00000001`) |
| EOF - 08 | Padding |

## 6. Software Internals (Reverse Engineering Notes)

- **Platform:** .NET 4.8 (UPX Packed).
- **Namespaces of Interest:**
    - `ESU.Sound.LokSound5`: Likely contains the high-level logic for V5 decoders.
    - `LokSound5Native`: Suggests a native interop layer for low-level firmware processing.
    - `System.Security.Cryptography`: Used for validating and potentially decrypting the `.fw` payload.
- **Dependencies:**
    - `System.Data.HashFunction.CRC`: Used for checking the integrity of data segments.
    - `SharpDX`: Audio processing for the "Virtual Driver's Cab".

## 7. Architecture Mapping (ARM Cortex-M)

Based on the "ARM controller" silicon revision notes (v5.2.1, v5.2.2), the newer generations (V5) are transitioning to more advanced ARM cores. The firmware update process likely involves:
1.  **Validation:** Checking the 182-byte header signature.
2.  **Decryption:** Decrypting the payload starting at `0xD8` into memory.
3.  **Bootloading:** Sending the raw ARM binary to the decoder via the LokProgrammer hardware (using FTDI USB-to-Serial).

## 7. Status
Decryption of the .fw payload is currently **UNRESOLVED**. Previous reports of successful extraction were based on misinterpretations of entropy data. The correct AES key is still being sought within the obfuscated .NET application.