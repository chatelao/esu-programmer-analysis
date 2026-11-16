# LokProgrammer v4.7.2 Analysis

## Summary
Version 4.7.2 is a .NET-based application from 2018. It marks a major shift towards encrypted data formats and .NET assemblies, being very similar in structure to the current 5.x version.

## Key Findings
- **Architecture**: .NET Mono/.Net assembly.
- **Obfuscation**: Babel.NET (confirmed by `BabelAttribute` strings).
- **Data Storage**: Uses encrypted `ESU ` magic format (0x45 53 55 20) for most metadata and firmware.
- **Entropy**: High (>7.9) for `.fw` and `DecoderInfo.dat` files, indicating strong encryption (likely AES) or compression.
- **File Structure**: Decoders are split into subfolders like `loksound4h0`, `lokpilot4`, etc., with corresponding `.fw` files.
- **Header Structure**: 34-byte `ESU ` header.
- **Trailer**: Some `.fw` files contain an unencrypted filename at the very end (e.g., `4-1-8829.xml`).

## Important Files
- `LokProgrammer.exe`: Main .NET assembly (Babel-obfuscated).
- `ESU.Core.dll` & `ESU.Sound.dll`: Core logic (also Babel-obfuscated).
- `DecoderInfo.dat`: Encrypted global decoder list (ESU magic).
- `*.fw`: Encrypted firmware and configuration files (ESU magic).
