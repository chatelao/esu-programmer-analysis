#!/usr/bin/env python3
"""Stage 3.2 descrambler for the 41 x 145-byte (0x20-prefixed) pages.

Applies the solved position-dependent XOR bijection:
    Y[p] = ((page[p] + 4) & 0xFF) ^ ((p - 13) & 0xFF)   for p = 1..144
and separates the 12-byte header, 128-byte payload, and 4-byte trailer.
"""

import argparse
from pathlib import Path


def descramble_frame(frame: bytes) -> tuple[bytes, bytes, bytes]:
    if len(frame) != 145 or frame[0] != 0x20:
        raise ValueError(f"Expected 145-byte 0x20-prefixed frame, got len={len(frame)} b0=0x{frame[0]:02x}")
    y = bytes(((frame[p] + 4) & 0xFF) ^ ((p - 13) & 0xFF) for p in range(1, 145))
    return y[:12], y[12:140], y[140:144]


def main() -> None:
    parser = argparse.ArgumentParser(description="Descramble 145-byte 0x20-prefixed ESU pages")
    parser.add_argument("input", type=Path, help="Path to *_pages_145b.bin")
    parser.add_argument("-o", "--out", type=Path, default=Path("out/5_13_180_145b_Y.bin"), help="Output 5248-byte payload")
    args = parser.parse_args()

    raw = args.input.read_bytes()
    if len(raw) % 145 != 0:
        raise ValueError(f"Input size {len(raw)} is not a multiple of 145")

    n = len(raw) // 145
    payloads = []
    for i in range(n):
        hdr, pay, trl = descramble_frame(raw[i * 145 : (i + 1) * 145])
        payloads.append(pay)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(b"".join(payloads))
    print(f"Descrambled {n} frames -> {args.out} ({n * 128} payload bytes)")


if __name__ == "__main__":
    main()
