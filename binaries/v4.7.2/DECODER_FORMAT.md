# ESU Firmware Format (.fw) - v4.7.2 Analysis

## File Structure
The `.fw` format in version 4.7.2 is identical to the format used in 5.x. It consists of a fixed header, an encrypted payload, and a descriptive trailer.

### 1. Header (34 bytes)
| Offset | Size | Value (Hex) | Description |
| :--- | :--- | :--- | :--- |
| 0x00 | 4 | `45 53 55 20` | Magic: "ESU " |
| 0x04 | 4 | `00 00 02 00` | Format Version (v2) |
| 0x08 | 4 | `00 00 01 00` | Unknown (Flags?) |
| 0x0C | 2 | `22 00` | Header Size (34 bytes) |
| 0x0E | 4 | `Varies` | Payload ID / Size Indicator |
| 0x12 | 16 | `00...00` | Padding or potential IV (often all zeros in v4) |

### 2. Payload (Variable Size)
The encrypted payload follows the header. It is high-entropy (~7.99), indicating strong encryption (likely AES).
- **Size calculation**: `Total Size - 34 (Header) - 32 (Trailer)`

### 3. Trailer (32 bytes)
The trailer contains the metadata about the encrypted content.
| Offset | Size | Description |
| :--- | :--- | :--- |
| -32 | 4 | Trailer Length (0x1C = 28 bytes) |
| -28 | Var | Original Filename (e.g., `4-1-8829.xml`) |
| -4 | 4 | Padding / Alignment |

## Findings
In version 4.7.2, most `.fw` files appear to contain encrypted XML decoder definitions, as indicated by the `.xml` extension in the trailers.
