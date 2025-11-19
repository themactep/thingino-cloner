#!/usr/bin/env python3
"""Verify CRC32 calculation matches vendor handshakes"""

import sys
import zlib

def crc32_inverted(data):
    """Calculate inverted CRC32 (matching vendor protocol)"""
    crc = zlib.crc32(data) & 0xFFFFFFFF
    crc_inv = (~crc) & 0xFFFFFFFF
    return crc_inv

def main():
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <firmware_file>")
        sys.exit(1)
    
    firmware_file = sys.argv[1]
    
    with open(firmware_file, 'rb') as f:
        firmware_data = f.read()
    
    chunk_size = 128 * 1024  # 128KB
    
    print(f"Firmware size: {len(firmware_data)} bytes")
    print(f"Chunk size: {chunk_size} bytes")
    print()
    
    # Calculate CRC for first few chunks
    for i in range(min(5, (len(firmware_data) + chunk_size - 1) // chunk_size)):
        offset = i * chunk_size
        chunk_data = firmware_data[offset:offset + chunk_size]
        
        crc_inv = crc32_inverted(chunk_data)
        
        # Format as little-endian bytes
        b0 = (crc_inv >> 0) & 0xFF
        b1 = (crc_inv >> 8) & 0xFF
        b2 = (crc_inv >> 16) & 0xFF
        b3 = (crc_inv >> 24) & 0xFF
        
        print(f"Chunk {i+1} (offset 0x{offset:08X}, size {len(chunk_data)} bytes):")
        print(f"  CRC32 inverted: 0x{crc_inv:08X}")
        print(f"  Bytes 28-31: {b0:02X} {b1:02X} {b2:02X} {b3:02X}")
        print()

if __name__ == '__main__':
    main()

