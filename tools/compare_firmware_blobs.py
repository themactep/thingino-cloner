#!/usr/bin/env python3
"""Compare Thingino firmware assets against vendor binaries and captured USB payloads.

This script helps validate that our embedded firmware blobs (as compiled into
src/firmware/firmware_<variant>.c), the vendor-distributed binaries, and any
USB capture extracts all match. It reports sizes, SHA-256 hashes, CRC32 values,
and whether the contents are identical across sources.
"""

from __future__ import annotations

import argparse
import binascii
import hashlib
import os
import re
import sys
from glob import glob
from dataclasses import dataclass
from typing import Dict, Optional

REQUIRED_FILES = {
    "spl": "spl_{variant}",
    "uboot": "uboot_{variant}",
}


@dataclass
class Artifact:
    name: str
    our_bytes: Optional[bytes]
    vendor_bytes: Optional[bytes]
    capture_bytes: Optional[bytes]

    def _hash_info(self, data: Optional[bytes]) -> str:
        if not data:
            return "—"
        sha = hashlib.sha256(data).hexdigest()
        crc = f"{binascii.crc32(data) & 0xFFFFFFFF:08x}"
        return f"sha256={sha}  crc32={crc}"

    def _size(self, data: Optional[bytes]) -> str:
        return str(len(data)) if data is not None else "—"

    def _compare(self, a: Optional[bytes], b: Optional[bytes]) -> str:
        if a is None or b is None:
            return "—"
        if a == b:
            return "MATCH"
        # Locate first mismatch
        for idx, (byte_a, byte_b) in enumerate(zip(a, b)):
            if byte_a != byte_b:
                return f"DIFF@{idx}"
        # One array may be a prefix
        return f"DIFF_LEN({len(a)} vs {len(b)})"

    def render(self) -> str:
        lines = [
            f"=== {self.name} ===",
            f" ours   : size={self._size(self.our_bytes)}  {self._hash_info(self.our_bytes)}",
            f" vendor : size={self._size(self.vendor_bytes)}  {self._hash_info(self.vendor_bytes)}",
            f" capture: size={self._size(self.capture_bytes)}  {self._hash_info(self.capture_bytes)}",
            f" ours↔vendor   : {self._compare(self.our_bytes, self.vendor_bytes)}",
            f" ours↔capture  : {self._compare(self.our_bytes, self.capture_bytes)}",
            f" vendor↔capture: {self._compare(self.vendor_bytes, self.capture_bytes)}",
            "",
        ]
        return "\n".join(lines)


def parse_c_array(path: str, symbol: str) -> Optional[bytes]:
    try:
        text = open(path, "r", encoding="utf-8").read()
    except OSError:
        return None

    marker = f"{symbol}[]"
    marker_index = text.find(marker)
    if marker_index == -1:
        return None

    brace_start = text.find("{", marker_index)
    brace_end = text.find("};", brace_start)
    if brace_start == -1 or brace_end == -1:
        return None

    body = text[brace_start + 1 : brace_end]
    values = re.findall(r"0x[0-9a-fA-F]+|\d+", body)
    data = bytearray()
    for value in values:
        if value.startswith("0x") or value.startswith("0X"):
            data.append(int(value, 16) & 0xFF)
        else:
            data.append(int(value, 10) & 0xFF)
    return bytes(data)


def read_file_bytes(path: str) -> Optional[bytes]:
    try:
        with open(path, "rb") as handle:
            return handle.read()
    except OSError:
        return None


def find_capture_blob(capture_dir: str, expected_size: int, override: Optional[str]) -> Optional[bytes]:
    if override:
        return read_file_bytes(override)

    if not os.path.isdir(capture_dir):
        return None

    pattern = os.path.join(capture_dir, "bulk_out_*.bin")
    for candidate in sorted(glob(pattern)):
        try:
            actual_size = os.path.getsize(candidate)
        except OSError:
            continue
        if actual_size == expected_size:
            return read_file_bytes(candidate)
    return None


def reassemble_capture_image(
    capture_dir: str,
    pattern: str,
    chunk_size: int,
    chunk_count: Optional[int],
) -> Optional[bytes]:
    search_pattern = os.path.join(capture_dir, pattern)
    candidates = sorted(glob(search_pattern))

    selected = []
    for path in candidates:
        try:
            size = os.path.getsize(path)
        except OSError:
            continue
        if chunk_size and size != chunk_size:
            continue
        selected.append(path)
        if chunk_count and len(selected) >= chunk_count:
            break

    if not selected:
        return None

    data = bytearray()
    for path in selected:
        chunk = read_file_bytes(path)
        if chunk is None:
            return None
        data.extend(chunk)
    return bytes(data)


def build_artifacts(args: argparse.Namespace) -> Dict[str, Artifact]:
    variant = args.variant.lower()
    firmware_path = os.path.join(args.repo_root, "src", "firmware", f"firmware_{variant}.c")
    vendor_variant_dir = os.path.join(args.vendor_root, "firmwares", variant)
    capture_dir = args.capture_dir

    artifacts: Dict[str, Artifact] = {}

    for key, symbol_template in REQUIRED_FILES.items():
        symbol = symbol_template.format(variant=variant)
        our_bytes = parse_c_array(firmware_path, symbol)

        vendor_file = os.path.join(vendor_variant_dir, f"{key}.bin")
        vendor_bytes = read_file_bytes(vendor_file)

        capture_override = getattr(args, f"capture_{key}")
        capture_bytes = None
        if our_bytes is not None:
            capture_bytes = find_capture_blob(capture_dir, len(our_bytes), capture_override)
        elif vendor_bytes is not None:
            capture_bytes = find_capture_blob(capture_dir, len(vendor_bytes), capture_override)

        artifacts[key] = Artifact(
            name=key.upper(),
            our_bytes=our_bytes,
            vendor_bytes=vendor_bytes,
            capture_bytes=capture_bytes,
        )

    if args.image_path:
        vendor_image = read_file_bytes(args.image_path)
        capture_image = None
        chunk_count = args.image_chunk_count
        if vendor_image is not None and chunk_count is None and args.image_chunk_size:
            if len(vendor_image) % args.image_chunk_size == 0:
                chunk_count = len(vendor_image) // args.image_chunk_size
        if args.image_chunk_size:
            capture_image = reassemble_capture_image(
                capture_dir,
                args.image_chunk_glob,
                args.image_chunk_size,
                chunk_count,
            )
        else:
            capture_image = reassemble_capture_image(
                capture_dir,
                args.image_chunk_glob,
                0,
                chunk_count,
            )

        artifacts["image"] = Artifact(
            name="IMAGE",
            our_bytes=None,
            vendor_bytes=vendor_image,
            capture_bytes=capture_image,
        )

    return artifacts


def parse_args(argv: Optional[list[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare firmware blobs between our repo, vendor binaries, and USB captures.")
    parser.add_argument("--variant", default="t31", help="Target firmware variant (e.g., t31, t31x).")
    parser.add_argument(
        "--repo-root",
        default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        help="Path to the repository root (auto-detected).",
    )
    parser.add_argument(
        "--vendor-root",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "vendor", "cloner-2.5.43"),
        help="Path to the unpacked vendor cloner directory.",
    )
    parser.add_argument(
        "--capture-dir",
        default=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "extracted_data"),
        help="Directory containing extracted bulk_out_*.bin files.",
    )
    parser.add_argument("--capture-spl", help="Override path for the capture SPL blob (defaults to first size match).")
    parser.add_argument("--capture-uboot", help="Override path for the capture U-Boot blob (defaults to first size match).")
    parser.add_argument("--image-path", help="Optional vendor image (complete firmware) to compare against captures.")
    parser.add_argument(
        "--image-chunk-size",
        type=int,
        default=131072,
        help="Size in bytes of each sequential capture chunk for the image (default 128KB).",
    )
    parser.add_argument(
        "--image-chunk-count",
        type=int,
        help="Number of capture chunks to concatenate (defaults to vendor image size / chunk size).",
    )
    parser.add_argument(
        "--image-chunk-glob",
        default="bulk_out_*.bin",
        help="Glob (relative to capture dir) for selecting capture chunks to concatenate.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[list[str]] = None) -> int:
    args = parse_args(argv)
    artifacts = build_artifacts(args)

    missing = [
        name
        for name, art in artifacts.items()
        if not art.our_bytes or not art.vendor_bytes or art.capture_bytes is None
    ]
    for artifact in artifacts.values():
        print(artifact.render())

    if missing:
        print("Warning: Missing data for:", ", ".join(missing))
    return 0


if __name__ == "__main__":
    sys.exit(main())
