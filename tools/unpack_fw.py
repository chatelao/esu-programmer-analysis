#!/usr/bin/env python3
"""Stage 1 & 2 unpacker for ESU .fw / DecoderInfo.dat files.

Decrypts the AES-256-CBC + GZip outer container, extracts the embedded XML,
partitions <dec:page> frames by byte length (e.g. 272B vs 145B for ls5l-hv),
and exports the <dec:configuration> CV symbol table.
"""

import argparse
import ctypes
import ctypes.util
import gzip
import struct
import subprocess
import xml.etree.ElementTree as ET
from pathlib import Path

STATIC_AES256_KEY = bytes.fromhex(
    "3d15ed4f0ea1cc7caecd31500333b09728ff2dda41f472fc7115a454119f5625"
)
DEC_NS = {"dec": "http://www.esu.eu/2008/DECODER/specs"}


def aes256_cbc_decrypt(key: bytes, iv: bytes, ciphertext: bytes) -> bytes:
    """Decrypt AES-256-CBC with PKCS#7 unpadding via libcrypto or openssl."""
    lib_path = ctypes.util.find_library("crypto")
    if lib_path:
        lib = ctypes.CDLL(lib_path)
        lib.EVP_CIPHER_CTX_new.restype = ctypes.c_void_p
        lib.EVP_CIPHER_CTX_free.argtypes = [ctypes.c_void_p]
        lib.EVP_DecryptInit_ex.argtypes = [
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.c_char_p,
        ]
        lib.EVP_DecryptUpdate.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_char_p,
            ctypes.c_int,
        ]
        lib.EVP_DecryptFinal_ex.argtypes = [
            ctypes.c_void_p,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_int),
        ]
        lib.EVP_aes_256_cbc.restype = ctypes.c_void_p

        ctx = lib.EVP_CIPHER_CTX_new()
        try:
            if lib.EVP_DecryptInit_ex(ctx, lib.EVP_aes_256_cbc(), None, key, iv) != 1:
                raise RuntimeError("EVP_DecryptInit_ex failed")
            out = ctypes.create_string_buffer(len(ciphertext) + 32)
            out_len1 = ctypes.c_int()
            if lib.EVP_DecryptUpdate(ctx, out, ctypes.byref(out_len1), ciphertext, len(ciphertext)) != 1:
                raise RuntimeError("EVP_DecryptUpdate failed")
            out_len2 = ctypes.c_int()
            final_buf = ctypes.create_string_buffer(32)
            if lib.EVP_DecryptFinal_ex(ctx, final_buf, ctypes.byref(out_len2)) != 1:
                raise RuntimeError("EVP_DecryptFinal_ex failed (bad padding/key)")
            return out.raw[: out_len1.value] + final_buf.raw[: out_len2.value]
        finally:
            lib.EVP_CIPHER_CTX_free(ctx)

    p = subprocess.run(
        ["openssl", "enc", "-aes-256-cbc", "-d", "-K", key.hex(), "-iv", iv.hex()],
        input=ciphertext,
        capture_output=True,
        check=True,
    )
    return p.stdout


def unpack_container(fw_path: Path) -> tuple[str, bytes]:
    data = fw_path.read_bytes()
    if data[:4] != b"ESU ":
        raise ValueError(f"{fw_path}: invalid magic {data[:4]!r}")
    chunk_type, chunk_size = struct.unpack_from("<HI", data, 0x0C)
    if chunk_type != 0x0022:
        raise ValueError(f"{fw_path}: unexpected chunk 1 type 0x{chunk_type:04x}")

    iv = data[0x22:0x32]
    ct_end = 0x0E + chunk_size
    ciphertext = data[0x32:ct_end]

    # Parse directory chunk 0x0020 for internal filename
    dir_name = fw_path.stem + ".xml"
    if ct_end + 6 <= len(data):
        dir_type, dir_size = struct.unpack_from("<HI", data, ct_end)
        if dir_type == 0x0020 and dir_size >= 16:
            raw_name = data[ct_end + 6 : ct_end + 6 + dir_size - 16]
            dir_name = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="replace")

    gz_data = aes256_cbc_decrypt(STATIC_AES256_KEY, iv, ciphertext)
    if gz_data[:3] != b"\x1f\x8b\x08":
        raise ValueError(f"{fw_path}: decrypted payload is not GZip ({gz_data[:4].hex()})")
    return dir_name, gzip.decompress(gz_data)


def extract_pages_and_symbols(xml_bytes: bytes, out_dir: Path, prefix: str) -> None:
    root = ET.fromstring(xml_bytes.decode("utf-8-sig"))
    pages = [bytes.fromhex(p.text.strip()) for p in root.findall(".//dec:page", DEC_NS)]

    by_len: dict[int, list[bytes]] = {}
    for pg in pages:
        by_len.setdefault(len(pg), []).append(pg)

    for plen, plist in sorted(by_len.items()):
        raw_path = out_dir / f"{prefix}_pages_{plen}b.bin"
        raw_path.write_bytes(b"".join(plist))
        print(f"  Wrote {len(plist)} x {plen}B pages -> {raw_path}")

    cfg = root.find(".//dec:configuration", DEC_NS)
    if cfg is not None:
        sym_path = out_dir / f"{prefix}_symbols.txt"
        lines = [f"# configuration {cfg.attrib}"]
        for var in cfg.findall("dec:variable", DEC_NS):
            idx = var.attrib.get("index", "-")
            num = var.attrib.get("number", "?")
            loc = var.attrib.get("location", "?")
            slices = ", ".join(
                f"{c.attrib.get('name', '?')}[{c.attrib.get('slice', '?')}]({c.attrib.get('access', '?')})"
                for c in var
            )
            lines.append(f"loc={loc:>4}  idx={idx:>5}  cv={num:>3}  {slices}")
        sym_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"  Wrote {len(lines)-1} symbols -> {sym_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Unpack ESU .fw files (Stages 1 & 2)")
    parser.add_argument("fw", type=Path, help="Path to .fw file")
    parser.add_argument("-o", "--out", type=Path, default=Path("out"), help="Output directory")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    xml_name, xml_bytes = unpack_container(args.fw)
    xml_path = args.out / xml_name
    xml_path.write_bytes(xml_bytes)
    print(f"Unpacked {args.fw} -> {xml_path} ({len(xml_bytes)} bytes)")

    prefix = args.fw.stem.replace("-", "_")
    extract_pages_and_symbols(xml_bytes, args.out, prefix)


if __name__ == "__main__":
    main()
