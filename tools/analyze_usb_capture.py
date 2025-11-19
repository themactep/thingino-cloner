#!/usr/bin/env python3
"""
USB Capture Analyzer for Ingenic Cloner

This tool analyzes USB traffic captures (pcap files) from Ingenic cloner tools
and decodes the protocol commands, data transfers, and sequences.

Usage:
    python3 analyze_usb_capture.py <capture.pcap> [--verbose] [--extract-data]
"""

import sys
import subprocess
import struct
import argparse
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import IntEnum

# Ingenic USB Protocol Commands
class VendorRequest(IntEnum):
    # Bootrom stage (0x00-0x05)
    VR_GET_CPU_INFO = 0x00
    VR_SET_DATA_ADDR = 0x01
    VR_SET_DATA_LEN = 0x02
    VR_FLUSH_CACHE = 0x03
    VR_PROG_STAGE1 = 0x04
    VR_PROG_STAGE2 = 0x05
    
    # Firmware stage (0x10-0x26)
    VR_FW_READ = 0x10
    VR_FW_HANDSHAKE = 0x11
    VR_WRITE = 0x12
    VR_READ = 0x13
    VR_FW_WRITE1 = 0x13
    VR_FW_WRITE2 = 0x14
    VR_FW_READ_STATUS1 = 0x16
    VR_FW_READ_STATUS2 = 0x19
    VR_FW_READ_STATUS3 = 0x25
    VR_FW_READ_STATUS4 = 0x26
    
    # NAND operations
    VR_NAND_OPS = 0x07

COMMAND_NAMES = {
    0x00: "GET_CPU_INFO",
    0x01: "SET_DATA_ADDR",
    0x02: "SET_DATA_LEN",
    0x03: "FLUSH_CACHE",
    0x04: "PROG_STAGE1",
    0x05: "PROG_STAGE2",
    0x07: "NAND_OPS",
    0x10: "FW_READ",
    0x11: "FW_HANDSHAKE",
    0x12: "WRITE",
    0x13: "READ/FW_WRITE1",
    0x14: "FW_WRITE2",
    0x16: "FW_READ_STATUS1",
    0x19: "FW_READ_STATUS2",
    0x25: "FW_READ_STATUS3",
    0x26: "FW_READ_STATUS4",
}

@dataclass
class USBTransfer:
    """Represents a single USB transfer"""
    frame_number: int
    timestamp: float
    transfer_type: str  # "CONTROL", "BULK", "INTERRUPT"
    direction: str      # "IN", "OUT"
    endpoint: int
    data: bytes
    length: int
    
    # For control transfers
    request_type: Optional[int] = None
    request: Optional[int] = None
    value: Optional[int] = None
    index: Optional[int] = None

@dataclass
class ProtocolSequence:
    """Represents a sequence of related USB transfers"""
    name: str
    transfers: List[USBTransfer]
    description: str

class USBCaptureAnalyzer:
    def __init__(self, pcap_file: str, verbose: bool = False):
        self.pcap_file = pcap_file
        self.verbose = verbose
        self.transfers: List[USBTransfer] = []
        self.sequences: List[ProtocolSequence] = []
        
    def parse_pcap(self):
        """Parse pcap file and extract USB transfers"""
        print(f"Analyzing {self.pcap_file}...")

        # Use fields that work across tshark versions; prefer explicit setup fields when available
        cmd = [
            'tshark', '-r', self.pcap_file,
            '-T', 'fields',
            '-e', 'frame.number',
            '-e', 'frame.time_relative',
            '-e', 'usb.transfer_type',
            '-e', 'usb.endpoint_address.direction',
            '-e', 'usb.endpoint_address.number',
            '-e', 'usb.data_len',
            '-e', 'usb.capdata',
            # Control setup fields (may be empty on some frames)
            '-e', 'usb.bmRequestType',
            '-e', 'usb.setup.bRequest',
            '-e', 'usb.setup.wValue',
            '-e', 'usb.setup.wIndex',
            '-e', 'usb.setup.wLength',
            '-E', 'separator=|',
            '-Y', 'usb'
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)

            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue

                fields = line.split('|')
                if len(fields) < 7:
                    continue

                # Base fields from tshark output
                frame_num_str = fields[0]
                time_str = fields[1]
                transfer_type_code = fields[2]
                direction_code = fields[3]
                endpoint_str = fields[4]
                data_len_str = fields[5]
                capdata_hex = fields[6]

                # Optional control-setup fields (may be empty)
                bm_req_str = fields[7] if len(fields) > 7 else ''
                b_req_str = fields[8] if len(fields) > 8 else ''
                w_value_str = fields[9] if len(fields) > 9 else ''
                w_index_str = fields[10] if len(fields) > 10 else ''
                w_length_str = fields[11] if len(fields) > 11 else ''

                # Parse basic values
                frame_num = int(frame_num_str) if frame_num_str else 0
                timestamp = float(time_str) if time_str else 0.0
                endpoint = int(endpoint_str, 16) if endpoint_str else 0
                data_len = int(data_len_str) if data_len_str else 0
                data = bytes.fromhex(capdata_hex.replace(':', '')) if capdata_hex else b''

                # Decode transfer type
                transfer_type_map = {'0x02': 'CONTROL', '0x03': 'BULK', '0x01': 'INTERRUPT'}
                transfer_type = transfer_type_map.get(transfer_type_code, 'UNKNOWN')

                # Decode direction
                direction = 'IN' if direction_code == '1' else 'OUT'

                # For control transfers, populate setup fields
                request_type = None
                request = None
                value = None
                index = None

                if transfer_type == 'CONTROL':
                    # Prefer explicit setup fields from tshark when available
                    if bm_req_str:
                        try:
                            request_type = int(bm_req_str, 16)
                        except ValueError:
                            request_type = None

                    if b_req_str:
                        try:
                            # usb.setup.bRequest is BASE_DEC
                            request = int(b_req_str)
                        except ValueError:
                            request = None

                    if w_value_str:
                        try:
                            # usb.setup.wValue is BASE_HEX
                            value = int(w_value_str, 16)
                        except ValueError:
                            value = None

                    if w_index_str:
                        try:
                            # usb.setup.wIndex is BASE_DEC_HEX (e.g., 4096 or 0x1000)
                            index = int(w_index_str, 0)
                        except ValueError:
                            index = None

                    # Fallback: parse setup packet from capdata when setup fields are missing
                    if request is None and len(data) >= 8:
                        # USB control setup packet format:
                        # Byte 0: bmRequestType
                        # Byte 1: bRequest
                        # Bytes 2-3: wValue (little-endian)
                        # Bytes 4-5: wIndex (little-endian)
                        # Bytes 6-7: wLength (little-endian)
                        request_type = data[0]
                        request = data[1]
                        value = struct.unpack('<H', data[2:4])[0]
                        index = struct.unpack('<H', data[4:6])[0]
                        # Data after setup packet (if any)
                        if len(data) > 8:
                            data = data[8:]
                        else:
                            data = b''

                transfer = USBTransfer(
                    frame_number=frame_num,
                    timestamp=timestamp,
                    transfer_type=transfer_type,
                    direction=direction,
                    endpoint=endpoint,
                    data=data,
                    length=data_len,
                    request_type=request_type,
                    request=request,
                    value=value,
                    index=index
                )

                self.transfers.append(transfer)

            print(f"Parsed {len(self.transfers)} USB transfers")
            return True

        except subprocess.CalledProcessError as e:
            print(f"ERROR: tshark failed: {e}")
            return False
        except FileNotFoundError:
            print("ERROR: tshark not found. Install with: sudo apt-get install tshark")
            return False

    def identify_sequences(self):
        """Identify protocol sequences in the transfers"""
        print("\nIdentifying protocol sequences...")

        current_sequence = []
        sequence_name = None

        for transfer in self.transfers:
            # Identify bootstrap sequence
            if transfer.transfer_type == 'CONTROL' and transfer.request == 0x00:
                if sequence_name != "Bootstrap":
                    if current_sequence:
                        self.sequences.append(ProtocolSequence(
                            name=sequence_name or "Unknown",
                            transfers=current_sequence,
                            description=""
                        ))
                    current_sequence = []
                    sequence_name = "Bootstrap"

            # Identify firmware read sequence
            elif transfer.transfer_type == 'CONTROL' and transfer.request in [0x10, 0x11]:
                if sequence_name != "Firmware Read":
                    if current_sequence:
                        self.sequences.append(ProtocolSequence(
                            name=sequence_name or "Unknown",
                            transfers=current_sequence,
                            description=""
                        ))
                    current_sequence = []
                    sequence_name = "Firmware Read"

            # Identify firmware write sequence
            elif transfer.transfer_type == 'CONTROL' and transfer.request in [0x13, 0x14]:
                if sequence_name != "Firmware Write":
                    if current_sequence:
                        self.sequences.append(ProtocolSequence(
                            name=sequence_name or "Unknown",
                            transfers=current_sequence,
                            description=""
                        ))
                    current_sequence = []
                    sequence_name = "Firmware Write"

            current_sequence.append(transfer)

        # Add final sequence
        if current_sequence:
            self.sequences.append(ProtocolSequence(
                name=sequence_name or "Unknown",
                transfers=current_sequence,
                description=""
            ))

        print(f"Identified {len(self.sequences)} protocol sequences")

    def print_summary(self):
        """Print summary of the capture"""
        print("\n" + "="*80)
        print("USB CAPTURE SUMMARY")
        print("="*80)

        # Count transfer types
        control_count = sum(1 for t in self.transfers if t.transfer_type == 'CONTROL')
        bulk_count = sum(1 for t in self.transfers if t.transfer_type == 'BULK')
        interrupt_count = sum(1 for t in self.transfers if t.transfer_type == 'INTERRUPT')

        print(f"\nTotal Transfers: {len(self.transfers)}")
        print(f"  Control:   {control_count}")
        print(f"  Bulk:      {bulk_count}")
        print(f"  Interrupt: {interrupt_count}")

        # Count directions
        in_count = sum(1 for t in self.transfers if t.direction == 'IN')
        out_count = sum(1 for t in self.transfers if t.direction == 'OUT')

        print(f"\nDirections:")
        print(f"  IN:  {in_count}")
        print(f"  OUT: {out_count}")

        # Count commands
        print(f"\nVendor Requests:")
        command_counts = {}
        for t in self.transfers:
            if t.transfer_type == 'CONTROL' and t.request is not None:
                cmd_name = COMMAND_NAMES.get(t.request, f"0x{t.request:02X}")
                command_counts[cmd_name] = command_counts.get(cmd_name, 0) + 1

        for cmd, count in sorted(command_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"  {cmd:20s}: {count}")

        # Data transfer summary
        total_data_out = sum(len(t.data) for t in self.transfers if t.direction == 'OUT')
        total_data_in = sum(len(t.data) for t in self.transfers if t.direction == 'IN')

        print(f"\nData Transferred:")
        print(f"  OUT: {total_data_out:,} bytes ({total_data_out/1024:.1f} KB)")
        print(f"  IN:  {total_data_in:,} bytes ({total_data_in/1024:.1f} KB)")

    def print_detailed_log(self):
        """Print detailed transfer log"""
        print("\n" + "="*80)
        print("DETAILED TRANSFER LOG")
        print("="*80)
        print(f"\n{'Frame':<6} {'Time':<10} {'Type':<10} {'Dir':<4} {'EP':<4} {'Request':<20} {'Value':<8} {'Index':<8} {'Len':<6} {'Data'}")
        print("-"*120)

        for t in self.transfers:
            cmd_name = ""
            if t.transfer_type == 'CONTROL' and t.request is not None:
                cmd_name = COMMAND_NAMES.get(t.request, f"0x{t.request:02X}")

            value_str = f"0x{t.value:04X}" if t.value is not None else ""
            index_str = f"0x{t.index:04X}" if t.index is not None else ""

            # Format data preview
            data_preview = ""
            if len(t.data) > 0:
                if len(t.data) <= 16:
                    data_preview = ' '.join(f'{b:02x}' for b in t.data)
                else:
                    data_preview = ' '.join(f'{b:02x}' for b in t.data[:16]) + "..."

            print(f"{t.frame_number:<6} {t.timestamp:<10.6f} {t.transfer_type:<10} {t.direction:<4} "
                  f"0x{t.endpoint:02X}  {cmd_name:<20} {value_str:<8} {index_str:<8} {t.length:<6} {data_preview}")

            # Print full data in verbose mode
            if self.verbose and len(t.data) > 16:
                for i in range(0, len(t.data), 16):
                    chunk = t.data[i:i+16]
                    hex_str = ' '.join(f'{b:02x}' for b in chunk)
                    print(f"       {' '*60} {hex_str}")

    def extract_data_transfers(self, output_dir: str = "extracted_data"):
        """Extract bulk data transfers to files"""
        import os
        os.makedirs(output_dir, exist_ok=True)

        print(f"\nExtracting data transfers to {output_dir}/...")

        bulk_out_count = 0
        bulk_in_count = 0

        for t in self.transfers:
            if t.transfer_type == 'BULK' and len(t.data) > 0:
                if t.direction == 'OUT':
                    filename = f"{output_dir}/bulk_out_{bulk_out_count:04d}_frame{t.frame_number}_{len(t.data)}bytes.bin"
                    with open(filename, 'wb') as f:
                        f.write(t.data)
                    bulk_out_count += 1
                    if self.verbose:
                        print(f"  Saved: {filename}")

                elif t.direction == 'IN':
                    filename = f"{output_dir}/bulk_in_{bulk_in_count:04d}_frame{t.frame_number}_{len(t.data)}bytes.bin"
                    with open(filename, 'wb') as f:
                        f.write(t.data)
                    bulk_in_count += 1
                    if self.verbose:
                        print(f"  Saved: {filename}")

        print(f"Extracted {bulk_out_count} bulk OUT transfers and {bulk_in_count} bulk IN transfers")

        # Try to identify special data
        self._identify_special_data(output_dir)

    def _identify_special_data(self, output_dir: str):
        """Identify special data like DDR binaries, SPL, U-Boot"""
        import os

        print("\nIdentifying special data...")

        for filename in os.listdir(output_dir):
            if not filename.endswith('.bin'):
                continue

            filepath = os.path.join(output_dir, filename)
            with open(filepath, 'rb') as f:
                data = f.read()

            # Check for DDR binary (FIDB marker)
            if b'FIDB' in data and len(data) >= 324:
                pos = data.find(b'FIDB')
                if pos >= 0 and pos + 324 <= len(data):
                    ddr_data = data[pos:pos+324]
                    # Verify RDD marker
                    if b'RDD' in ddr_data[192:196] or b'RD\x00' in ddr_data[192:196]:
                        ddr_file = os.path.join(output_dir, "ddr_binary.bin")
                        with open(ddr_file, 'wb') as f:
                            f.write(ddr_data)
                        print(f"  ✓ Found DDR binary (324 bytes) -> {ddr_file}")
                        self._analyze_ddr_binary(ddr_data)

            # Check for SPL (usually 8-16KB, starts with specific patterns)
            if len(data) >= 8192 and len(data) <= 32768:
                # SPL often has ARM/MIPS code patterns
                print(f"  ? Possible SPL/bootloader: {filename} ({len(data)} bytes)")

            # Check for U-Boot (usually 200-500KB)
            if len(data) >= 200000 and len(data) <= 600000:
                print(f"  ? Possible U-Boot: {filename} ({len(data)} bytes)")

    def _analyze_ddr_binary(self, data: bytes):
        """Quick analysis of DDR binary"""
        if len(data) != 324:
            return

        try:
            # Parse FIDB section
            crystal_freq = struct.unpack('<I', data[8:12])[0]
            cpu_freq = struct.unpack('<I', data[12:16])[0]
            ddr_freq = struct.unpack('<I', data[16:20])[0]

            print(f"    Crystal: {crystal_freq/1000000:.1f} MHz")
            print(f"    CPU: {cpu_freq/1000000:.1f} MHz")
            print(f"    DDR: {ddr_freq/1000000:.1f} MHz")

            # Parse RDD section
            ddr_type = struct.unpack('<I', data[204:208])[0]
            ddr_type_names = {0: "DDR3", 1: "DDR2", 2: "LPDDR2/LPDDR", 4: "LPDDR3"}
            print(f"    DDR Type: {ddr_type_names.get(ddr_type, f'Unknown ({ddr_type})')}")
        except:
            pass

def main():
    parser = argparse.ArgumentParser(
        description='Analyze USB traffic captures from Ingenic cloner tools'
    )
    parser.add_argument('pcap_file', help='Input pcap file')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output with full data dumps')
    parser.add_argument('-e', '--extract-data', action='store_true',
                       help='Extract bulk data transfers to files')
    parser.add_argument('-o', '--output-dir', default='extracted_data',
                       help='Output directory for extracted data (default: extracted_data)')

    args = parser.parse_args()

    analyzer = USBCaptureAnalyzer(args.pcap_file, verbose=args.verbose)

    if not analyzer.parse_pcap():
        sys.exit(1)

    analyzer.identify_sequences()
    analyzer.print_summary()
    analyzer.print_detailed_log()

    if args.extract_data:
        analyzer.extract_data_transfers(args.output_dir)

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)

if __name__ == '__main__':
    main()


