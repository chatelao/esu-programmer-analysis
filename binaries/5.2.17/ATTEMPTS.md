# Decryption Attempts Log

All attempts so far have produced **high-entropy garbage** (no valid ARM vectors).

| Attempt | Date | Key Source | Mode | Key (Hex) | IV (Hex) | Result |
|---------|------|------------|------|-----------|----------|--------|
| 1-5 | 2026-03-30 | Memory (0x8BA0C3) | AES-128/256 CBC/ECB | 6a1dcc78404381dc... | 638075cdbad1c1ae... | **FAILED** (Entropy > 7.7) |
| 6 | 2026-04-11 | static strings | AES-128-ECB | ESU LokProgrammer... | N/A | **FAILED** |
| 7 | 2026-04-11 | tool installation | N/A | N/A | N/A | **SUCCESSFUL** (Installed AvaloniaILSpy, ilspycmd, de4dot, and .NET diagnostic tools) |

## Summary of Findings
- The key `6A 1D CC 78...` found at offset `0x2c3` in the `exe_blob.txt` is **NOT** the firmware decryption key.
- The payload at `0xD8` is encrypted (Entropy > 7.8).
- Valid ARM vectors (SAMD21) should have:
    - SP: `0x2000xxxx` (Little Endian: `xx xx 00 20`)
    - PC: `0x0000xxxx` (Little Endian: `xx xx 00 00` with LSB=1)
