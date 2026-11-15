# Analysis of ESU LokProgrammer 5.2.17 Setup

This document provides a technical analysis of the ESU LokProgrammer setup package, including its structure, software components, and embedded firmware.

## 1. Package Overview
*   **Source File:** `LokProgrammer_5.2.17_Setup_B26036.zip`
*   **Main Installer:** `LokProgrammer_5.2.17_Setup_B26036.exe` (approx. 226 MB)
*   **Installer Technology:** **NSIS (Nullsoft Scriptable Install System)** archive.
*   **Integrity:**
    *   **MD5:** `0458c722c6f7f89cfab776d9007a5d66`
    *   **SHA256:** `39a0330c2105f6063a84deff02ee7b6ad41d7062b26857e9f0f38cf0d2aa669d`

## 2. Software Components
*   **Main Application:** `LokProgrammer.exe` (Internal Version: `5.2.17.26036`)
*   **Platform:** Built on **Microsoft .NET Framework 4.8**.
*   **Core Dependencies:**
    *   `SharpDX.dll` / `SharpDX.DirectSound.dll`: Used for high-fidelity audio handling.
    *   `iTextSharp.dll`: Used for generating PDF reports/bulletins.
    *   `libFLAC_dynamic.dll`: Used for processing FLAC audio samples.
    *   `System.Reactive.dll`: Used for asynchronous event processing.

## 3. LokPilot 5 & LokSound 5 Firmware Format (`.fw`)
Through structural and entropy analysis, we have reverse-engineered the proprietary `.fw` archive format. The files are not simple encrypted blobs; they are structured packages.

### File Structure
1. **Header (34 bytes):**
   - `[4 bytes]` Magic Bytes: `ESU ` (`45 53 55 20`)
   - `[4 bytes]` Version Identifier (e.g., `00 00 02 00`)
   - `[6 bytes]` Unknown padding/flags (e.g., `00 00 01 00 22 00`)
   - `[4 bytes]` Declared Payload Size (Little Endian)
   - `[16 bytes]` AES Initialization Vector (IV) (e.g., `01 00 00 ... 00`)
2. **Payload (`X` bytes):**
   - The encrypted firmware payload. The actual payload size is exactly `Total File Size - Header Size - Trailer Size`.
   - The payload is likely encrypted with AES-CTR or AES-CFB, as its size is not padded to a 16-byte block multiple.
3. **Trailer (`N + 4` bytes):**
   - `[4 bytes]` Trailer Length (`N`)
   - `[N bytes]` XML Filename (e.g., `5-13-180.xml`) followed by null padding.

## 4. Obfuscation Bypass (Babel.NET)
The LokProgrammer executable is heavily protected by Babel.NET. We successfully bypassed this maze by:
1. Identifying the string decryptor metadata token (`0x0600363A`) via `Mono.Cecil`.
2. Extracting the `KmnL.res.bin` resource, which is the encrypted string and constant database.
3. Parsing the Babel.NET header to extract the AES-256 key (`7c5d7ab7e9ae50329323d2110dae054b37bc0e50085c1dd55e32a1fa94daa67b`) and IV (`5e3f5d94bd3120c03d0a6629f302dd39`).
4. Decrypting the resource and bypassing the proprietary LZW+Huffman decompression routine (`Class794`) using a custom-compiled standalone `.NET 8` C# application (porting the decompression logic dynamically).

## 5. Cryptographic Conclusion
A complete dump of the 4MB decompressed string database revealed no hardcoded keys, passwords, or firmware mappings. A subsequent tracing of the `SerialPort` IO boundaries confirmed that the LokProgrammer PC software **never decrypts** the firmware payload. It merely parses the unencrypted `.fw` trailer to display version metadata to the user, and transmits the raw encrypted payload over serial to the decoder.

Therefore, the AES decryption key resides exclusively inside the read-protected bootloader of the SAMD21 microcontroller on the decoder hardware. Software-only decryption of the LokPilot 5 firmware is cryptographically impossible without extracting the key physically from the hardware (e.g., via fault injection or decapping).

---

## Appendix: Execution Steps for Analysis

The following steps were performed to conduct this analysis:
1.  **Checksum Verification & Archive Inspection:** Identified the NSIS installer.
2.  **File System Mapping:** Recursively mapped the extracted directory structure.
3.  **Binary Signature Analysis:** Identified the `"ESU "` magic bytes.
4.  **Babel.NET Defeat:** Extracted metadata tokens, statically compiled the proprietary LZW decompressor, and dumped 4MB of strings.
5.  **Payload Extraction:** Created python scripts to dissect the `.fw` archive format.
6.  **Known Plaintext Attacks:** Ran AES-CTR/CBC brute force against ARM Vectors and XML headers.
7.  **Protocol Sniffing:** Traced the .NET `SerialPort` logic to confirm the payload is transmitted as-is without software decryption.
