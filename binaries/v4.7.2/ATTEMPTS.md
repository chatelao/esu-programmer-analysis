# Investigation Attempts - LokProgrammer v4.7.2

## Attempt 1: File Discovery
- **Date**: 2026-04-11
- **Method**: `7z` extraction and `file` identification.
- **Results**: Identified .NET assemblies (`ESU.Core.dll`, etc.) and encrypted `.fw` files.
- **Conclusion**: This version is architecturally identical to 5.x but with separate DLLs.

## Attempt 2: Babel.NET Confirmation
- **Date**: 2026-04-11
- **Method**: `strings` search for `BabelAttribute`.
- **Results**: Matches found in `LokProgrammer.exe`, `ESU.Core.dll`, and `ESU.Sound.dll`.
- **Conclusion**: The obfuscation strategy is consistent across the 4.x and 5.x series.

## Attempt 3: Firmware Dissection
- **Date**: 2026-04-11
- **Method**: Hex analysis of `*.fw` and `DecoderInfo.dat`.
- **Results**: Confirmed 34-byte `ESU ` header and plaintext trailer with filename (e.g. `4-1-8829.xml`).
- **Conclusion**: The proprietary archive format was fully established by this version.
