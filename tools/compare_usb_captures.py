#!/usr/bin/env python3
"""
USB Capture Comparison Tool

Compares two USB captures (e.g., vendor vs thingino-cloner) to identify
differences in protocol sequences, commands, and data.

Usage:
    python3 compare_usb_captures.py <capture1.pcap> <capture2.pcap> [--output report.txt]
"""

import sys
import subprocess
import struct
import argparse
from dataclasses import dataclass
from typing import List, Dict, Tuple
from difflib import unified_diff

# Import the analyzer
from analyze_usb_capture import USBCaptureAnalyzer, USBTransfer, COMMAND_NAMES

@dataclass
class TransferDiff:
    """Represents a difference between two transfers"""
    index: int
    transfer1: USBTransfer
    transfer2: USBTransfer
    differences: List[str]

class CaptureComparator:
    def __init__(self, pcap1: str, pcap2: str, label1: str = "Capture 1", label2: str = "Capture 2"):
        self.pcap1 = pcap1
        self.pcap2 = pcap2
        self.label1 = label1
        self.label2 = label2
        
        self.analyzer1 = USBCaptureAnalyzer(pcap1)
        self.analyzer2 = USBCaptureAnalyzer(pcap2)
        
        self.diffs: List[TransferDiff] = []
    
    def load_captures(self):
        """Load both captures"""
        print(f"Loading {self.label1}: {self.pcap1}")
        if not self.analyzer1.parse_pcap():
            return False
        
        print(f"Loading {self.label2}: {self.pcap2}")
        if not self.analyzer2.parse_pcap():
            return False
        
        return True
    
    def compare_transfers(self):
        """Compare transfers between the two captures"""
        print("\nComparing transfers...")
        
        transfers1 = self.analyzer1.transfers
        transfers2 = self.analyzer2.transfers
        
        max_len = max(len(transfers1), len(transfers2))
        
        for i in range(max_len):
            t1 = transfers1[i] if i < len(transfers1) else None
            t2 = transfers2[i] if i < len(transfers2) else None
            
            if t1 is None:
                self.diffs.append(TransferDiff(
                    index=i,
                    transfer1=None,
                    transfer2=t2,
                    differences=[f"{self.label2} has extra transfer"]
                ))
                continue
            
            if t2 is None:
                self.diffs.append(TransferDiff(
                    index=i,
                    transfer1=t1,
                    transfer2=None,
                    differences=[f"{self.label1} has extra transfer"]
                ))
                continue
            
            # Compare transfers
            differences = []
            
            if t1.transfer_type != t2.transfer_type:
                differences.append(f"Transfer type: {t1.transfer_type} vs {t2.transfer_type}")
            
            if t1.direction != t2.direction:
                differences.append(f"Direction: {t1.direction} vs {t2.direction}")
            
            if t1.endpoint != t2.endpoint:
                differences.append(f"Endpoint: 0x{t1.endpoint:02X} vs 0x{t2.endpoint:02X}")
            
            if t1.request != t2.request:
                cmd1 = COMMAND_NAMES.get(t1.request, f"0x{t1.request:02X}") if t1.request else "None"
                cmd2 = COMMAND_NAMES.get(t2.request, f"0x{t2.request:02X}") if t2.request else "None"
                differences.append(f"Request: {cmd1} vs {cmd2}")
            
            if t1.value != t2.value:
                v1 = f"0x{t1.value:04X}" if t1.value is not None else "None"
                v2 = f"0x{t2.value:04X}" if t2.value is not None else "None"
                differences.append(f"Value: {v1} vs {v2}")

            if t1.index != t2.index:
                i1 = f"0x{t1.index:04X}" if t1.index is not None else "None"
                i2 = f"0x{t2.index:04X}" if t2.index is not None else "None"
                differences.append(f"Index: {i1} vs {i2}")

            if len(t1.data) != len(t2.data):
                differences.append(f"Data length: {len(t1.data)} vs {len(t2.data)} bytes")
            elif t1.data != t2.data:
                differences.append(f"Data content differs ({len(t1.data)} bytes)")
            
            if differences:
                self.diffs.append(TransferDiff(
                    index=i,
                    transfer1=t1,
                    transfer2=t2,
                    differences=differences
                ))
        
        print(f"Found {len(self.diffs)} differences")
    
    def print_summary(self):
        """Print comparison summary"""
        print("\n" + "="*80)
        print("COMPARISON SUMMARY")
        print("="*80)
        
        print(f"\n{self.label1}: {len(self.analyzer1.transfers)} transfers")
        print(f"{self.label2}: {len(self.analyzer2.transfers)} transfers")
        print(f"\nDifferences: {len(self.diffs)}")
        
        if len(self.diffs) == 0:
            print("\n✓ Captures are identical!")
            return
        
        # Categorize differences
        type_diffs = sum(1 for d in self.diffs if any("Transfer type" in diff for diff in d.differences))
        request_diffs = sum(1 for d in self.diffs if any("Request" in diff for diff in d.differences))
        data_diffs = sum(1 for d in self.diffs if any("Data" in diff for diff in d.differences))
        extra_transfers = sum(1 for d in self.diffs if any("extra transfer" in diff for diff in d.differences))
        
        print(f"\nDifference breakdown:")
        print(f"  Transfer type differences: {type_diffs}")
        print(f"  Request differences: {request_diffs}")
        print(f"  Data differences: {data_diffs}")
        print(f"  Extra transfers: {extra_transfers}")

    def print_detailed_diff(self):
        """Print detailed differences"""
        if len(self.diffs) == 0:
            return

        print("\n" + "="*80)
        print("DETAILED DIFFERENCES")
        print("="*80)

        for diff in self.diffs:
            print(f"\n--- Transfer #{diff.index} ---")

            if diff.transfer1 is None:
                print(f"  {self.label1}: (missing)")
                print(f"  {self.label2}: {self._format_transfer(diff.transfer2)}")
            elif diff.transfer2 is None:
                print(f"  {self.label1}: {self._format_transfer(diff.transfer1)}")
                print(f"  {self.label2}: (missing)")
            else:
                print(f"  {self.label1}: {self._format_transfer(diff.transfer1)}")
                print(f"  {self.label2}: {self._format_transfer(diff.transfer2)}")

            print(f"  Differences:")
            for d in diff.differences:
                print(f"    - {d}")

            # Show data diff if data differs
            if diff.transfer1 and diff.transfer2 and diff.transfer1.data != diff.transfer2.data:
                self._print_data_diff(diff.transfer1.data, diff.transfer2.data)

    def _format_transfer(self, t: USBTransfer) -> str:
        """Format a transfer for display"""
        cmd_name = ""
        if t.transfer_type == 'CONTROL' and t.request is not None:
            cmd_name = COMMAND_NAMES.get(t.request, f"0x{t.request:02X}")

        return f"{t.transfer_type} {t.direction} EP:0x{t.endpoint:02X} {cmd_name} len:{len(t.data)}"

    def _print_data_diff(self, data1: bytes, data2: bytes):
        """Print data differences in hex"""
        print(f"\n    Data comparison:")

        max_len = max(len(data1), len(data2))

        # Show first 256 bytes of differences
        show_len = min(max_len, 256)

        for i in range(0, show_len, 16):
            chunk1 = data1[i:i+16] if i < len(data1) else b''
            chunk2 = data2[i:i+16] if i < len(data2) else b''

            if chunk1 != chunk2:
                hex1 = ' '.join(f'{b:02x}' for b in chunk1).ljust(48)
                hex2 = ' '.join(f'{b:02x}' for b in chunk2).ljust(48)

                marker = "  <--" if chunk1 != chunk2 else ""
                print(f"    {i:04x}: {hex1} | {hex2}{marker}")

        if max_len > 256:
            print(f"    ... ({max_len - 256} more bytes)")

    def save_report(self, output_file: str):
        """Save comparison report to file"""
        with open(output_file, 'w') as f:
            # Redirect stdout to file
            import sys
            old_stdout = sys.stdout
            sys.stdout = f

            self.print_summary()
            self.print_detailed_diff()

            sys.stdout = old_stdout

        print(f"\nReport saved to: {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description='Compare two USB captures from Ingenic cloner tools'
    )
    parser.add_argument('pcap1', help='First pcap file (e.g., vendor capture)')
    parser.add_argument('pcap2', help='Second pcap file (e.g., thingino capture)')
    parser.add_argument('--label1', default='Vendor', help='Label for first capture')
    parser.add_argument('--label2', default='Thingino', help='Label for second capture')
    parser.add_argument('-o', '--output', help='Save report to file')

    args = parser.parse_args()

    comparator = CaptureComparator(
        args.pcap1, args.pcap2,
        label1=args.label1, label2=args.label2
    )

    if not comparator.load_captures():
        sys.exit(1)

    comparator.compare_transfers()
    comparator.print_summary()
    comparator.print_detailed_diff()

    if args.output:
        comparator.save_report(args.output)

    print("\n" + "="*80)
    print("Comparison complete!")
    print("="*80)

if __name__ == '__main__':
    main()


