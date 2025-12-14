#!/usr/bin/env python3
"""
Extract DDR Binary from USB Capture

This script extracts the 324-byte DDR binary (FIDB + RDD format) from a
tcpdump/tshark USB capture of the vendor's cloner tool.

Usage:
    python3 extract_ddr_from_pcap.py <capture.pcap> [output.bin]
"""

import sys
import subprocess
import struct

def extract_usb_data(pcap_file):
    """Extract USB bulk OUT data from pcap file using tshark"""
    print(f"Analyzing {pcap_file}...")
    
    # Use tshark to extract USB bulk OUT data
    cmd = [
        'tshark', '-r', pcap_file,
        '-Y', 'usb.transfer_type == 0x03 && usb.endpoint_address.direction == 0',
        '-T', 'fields',
        '-e', 'usb.capdata'
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
        
        # Combine all hex strings into one binary blob
        all_data = b''
        for line in result.stdout.strip().split('\n'):
            if line:
                # Remove colons and convert hex to bytes
                hex_str = line.replace(':', '')
                try:
                    all_data += bytes.fromhex(hex_str)
                except ValueError:
                    continue
        
        return all_data
    
    except subprocess.CalledProcessError as e:
        print(f"ERROR: tshark failed: {e}")
        return None
    except FileNotFoundError:
        print("ERROR: tshark not found. Install with: sudo apt-get install tshark")
        return None

def find_ddr_binary(data):
    """Find DDR binary in USB data by looking for FIDB marker.

    Supports both classic 324-byte (XBurst1) and extended 384-byte (XBurst2/T41N)
    FIDB+RDD layouts.
    """
    print(f"Searching for DDR binary in {len(data)} bytes of USB data...")

    fidb_marker = b'FIDB'
    pos = 0
    candidates = []

    while True:
        pos = data.find(fidb_marker, pos)
        if pos == -1:
            break

        # Try known DDR binary sizes: 324 bytes (classic) and 384 bytes (extended)
        for size in (324, 384):
            end = pos + size
            if end > len(data):
                continue

            candidate = data[pos:end]

            # Basic header sanity checks
            if candidate[0:4] != fidb_marker:
                continue

            fidb_size = struct.unpack('<I', candidate[4:8])[0]

            # RDD header is always at offset 0xC0 (192)
            rdd_offset = 192
            if len(candidate) < rdd_offset + 8:
                continue

            rdd_magic = candidate[rdd_offset:rdd_offset+4]
            rdd_size = struct.unpack('<I', candidate[rdd_offset+4:rdd_offset+8])[0]

            # Expect RDD magic "\x00RDD"
            if rdd_magic != b"\x00RDD":
                continue

            # Heuristic validation based on expected RDD sizes
            if size == 324 and rdd_size not in (0x7C, 124):
                continue
            if size == 384 and rdd_size not in (0xB8, 184):
                continue

            print(
                f"Found potential DDR binary at offset {pos} "
                f"(size={size} bytes, FIDB={fidb_size}, RDD={rdd_size})"
            )
            candidates.append((pos, candidate))
            # Once we've accepted one size at this position, don't try the others
            break

        pos += 1

    return candidates

def analyze_ddr_binary(data):
    """Analyze and display DDR binary structure (324- or 384-byte)."""
    length = len(data)
    if length not in (324, 384):
        print(f"WARNING: DDR binary is {length} bytes, expected 324 or 384")

    print("\n=== DDR Binary Analysis ===\n")

    # FIDB section (0x00-0xBF, 192 bytes)
    print("FIDB Section (Platform Config):")
    fidb_magic = data[0:4]
    fidb_size = struct.unpack('<I', data[4:8])[0]
    crystal_freq = struct.unpack('<I', data[8:12])[0]
    cpu_freq = struct.unpack('<I', data[12:16])[0]
    ddr_freq = struct.unpack('<I', data[16:20])[0]
    uart_baud = struct.unpack('<I', data[28:32])[0]
    mem_size = struct.unpack('<I', data[40:44])[0]

    print(f"  Magic: {fidb_magic}")
    print(f"  Size: {fidb_size} bytes")
    print(f"  Crystal: {crystal_freq} Hz ({crystal_freq/1000000:.1f} MHz)")
    print(f"  CPU: {cpu_freq} Hz ({cpu_freq/1000000:.1f} MHz)")
    print(f"  DDR: {ddr_freq} Hz ({ddr_freq/1000000:.1f} MHz)")
    print(f"  UART: {uart_baud} baud")
    print(f"  Memory: {mem_size} bytes ({mem_size/1024/1024:.1f} MB)")

    # RDD header (starts at 0xC0)
    print("\nRDD Section (DDR PHY Params):")
    rdd_offset = 192
    if length < rdd_offset + 8:
        print("  RDD header not present (binary too short)")
    else:
        rdd_magic = data[rdd_offset:rdd_offset+4]
        rdd_size = struct.unpack('<I', data[rdd_offset+4:rdd_offset+8])[0]
        rdd_crc = struct.unpack('<I', data[rdd_offset+8:rdd_offset+12])[0]
        ddr_type = struct.unpack('<I', data[rdd_offset+12:rdd_offset+16])[0]

        ddr_type_names = {0: "DDR3", 1: "DDR2", 2: "LPDDR2/LPDDR", 4: "LPDDR3"}
        ddr_type_name = ddr_type_names.get(ddr_type, f"Unknown/raw ({ddr_type})")

        print(f"  Magic: {rdd_magic}")
        print(f"  Size: {rdd_size} bytes")
        print(f"  CRC32: 0x{rdd_crc:08x}")
        print(f"  DDR Type (raw): {ddr_type} -> {ddr_type_name}")

        if length == 324:
            # Classic XBurst1-style 324-byte format - use detailed decode
            cl = data[228]
            bl = data[229]
            row_bits = data[230]
            col_bits = data[231] + 6  # Stored as col_bits - 6

            tRAS = data[232]
            tRC = data[233]
            tRCD = data[234]
            tRP = data[235]
            tRFC = data[236]
            tRTP = data[238]
            tFAW = data[240]
            tRRD = data[242]
            tWTR = data[243]

            print(f"\nMemory Geometry:")
            print(f"  CL: {cl}")
            print(f"  BL: {bl}")
            print(f"  Row bits: {row_bits}")
            print(f"  Col bits: {col_bits}")

            print(f"\nTiming Parameters (cycles):")
            print(f"  tRAS: {tRAS}")
            print(f"  tRC: {tRC}")
            print(f"  tRCD: {tRCD}")
            print(f"  tRP: {tRP}")
            print(f"  tRFC: {tRFC}")
            print(f"  tRTP: {tRTP}")
            print(f"  tFAW: {tFAW}")
            print(f"  tRRD: {tRRD}")
            print(f"  tWTR: {tWTR}")
        elif length == 384:
            print("\nNOTE: Detected extended 384-byte DDR binary (likely XBurst2/T41N).")
            print("      Detailed geometry/timing layout differs from the 324-byte format.")
            print("      See t41n_ddr_analysis.md for a full breakdown of this variant.")

    print("\nFirst 64 bytes (hex):")
    for i in range(0, 64, 16):
        hex_str = ' '.join(f'{b:02x}' for b in data[i:i+16])
        print(f"  {i:04x}: {hex_str}")

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 extract_ddr_from_pcap.py <capture.pcap> [output.bin]")
        sys.exit(1)
    
    pcap_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "vendor_ddr_extracted.bin"
    
    # Extract USB data
    usb_data = extract_usb_data(pcap_file)
    if not usb_data:
        print("ERROR: Failed to extract USB data")
        sys.exit(1)
    
    print(f"Extracted {len(usb_data)} bytes of USB bulk OUT data")
    
    # Find DDR binary
    candidates = find_ddr_binary(usb_data)
    
    if not candidates:
        print("\nERROR: No DDR binary found in capture")
        print("Make sure the capture includes the DDR config upload phase")
        sys.exit(1)
    
    print(f"\nFound {len(candidates)} DDR binary candidate(s)")
    
    # Use the first candidate
    offset, ddr_binary = candidates[0]
    
    # Save to file
    with open(output_file, 'wb') as f:
        f.write(ddr_binary)
    
    print(f"\nSaved DDR binary to: {output_file}")
    
    # Analyze the binary
    analyze_ddr_binary(ddr_binary)
    
    print(f"\n=== Success ===")
    print(f"DDR binary extracted: {output_file}")

if __name__ == '__main__':
    main()

