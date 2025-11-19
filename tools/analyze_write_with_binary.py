#!/usr/bin/env python3
"""
Write Operation Analyzer with Binary Correlation

This tool analyzes write operations from USB captures and correlates them with
the actual binary file being written. This helps identify:
- Protocol overhead (commands, headers, metadata)
- Data transformations (encryption, compression, checksums)
- Chunking patterns
- Address mapping

Usage:
    python3 analyze_write_with_binary.py <capture.pcap> <binary_file> [options]
"""

import sys
import subprocess
import struct
import argparse
from dataclasses import dataclass, field
from typing import List, Optional, Tuple, Dict
from pathlib import Path

# Import the base analyzer
from analyze_usb_capture import USBCaptureAnalyzer, USBTransfer, COMMAND_NAMES

@dataclass
class BinaryChunk:
    """Represents a chunk of the binary file"""
    offset: int
    size: int
    data: bytes
    flash_address: Optional[int] = None
    
@dataclass
class TransferredChunk:
    """Represents data transferred over USB"""
    transfer: USBTransfer
    data: bytes
    flash_address: Optional[int] = None
    
@dataclass
class ChunkCorrelation:
    """Correlation between binary chunk and USB transfer"""
    binary_chunk: BinaryChunk
    usb_chunk: TransferredChunk
    match_type: str  # "exact", "partial", "transformed", "none"
    match_offset: int = 0
    differences: List[str] = field(default_factory=list)

class WriteWithBinaryAnalyzer:
    def __init__(self, pcap_file: str, binary_file: str, verbose: bool = False):
        self.pcap_file = pcap_file
        self.binary_file = binary_file
        self.verbose = verbose
        
        self.analyzer = USBCaptureAnalyzer(pcap_file)
        self.binary_data = None
        self.binary_size = 0
        
        self.write_sequences = []
        self.bulk_transfers = []
        self.correlations = []
        
    def load_binary(self):
        """Load the binary file"""
        print(f"Loading binary file: {self.binary_file}")
        
        try:
            with open(self.binary_file, 'rb') as f:
                self.binary_data = f.read()
            
            self.binary_size = len(self.binary_data)
            print(f"Binary size: {self.binary_size} bytes ({self.binary_size/1024:.1f} KB)")
            
            # Show binary header
            if len(self.binary_data) >= 64:
                print("\nBinary header (first 64 bytes):")
                for i in range(0, 64, 16):
                    chunk = self.binary_data[i:i+16]
                    hex_str = ' '.join(f'{b:02x}' for b in chunk)
                    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
                    print(f"  {i:04x}: {hex_str:<48} {ascii_str}")
            
            return True
            
        except FileNotFoundError:
            print(f"ERROR: Binary file not found: {self.binary_file}")
            return False
        except Exception as e:
            print(f"ERROR: Failed to load binary: {e}")
            return False
    
    def analyze(self):
        """Analyze the capture"""
        print(f"\nAnalyzing USB capture: {self.pcap_file}")
        
        if not self.analyzer.parse_pcap():
            return False
        
        self._extract_write_sequences()
        self._extract_bulk_transfers()
        self._correlate_data()
        
        return True
    
    def _extract_write_sequences(self):
        """Extract write sequences from transfers"""
        print("\nExtracting write sequences...")
        
        current_flash_addr = None
        current_data_size = None
        
        for transfer in self.analyzer.transfers:
            # SET_DATA_ADDR (0x01)
            if transfer.transfer_type == 'CONTROL' and transfer.request == 0x01:
                if transfer.value is not None and transfer.index is not None:
                    current_flash_addr = (transfer.index << 16) | transfer.value
                    print(f"  Flash address set to: 0x{current_flash_addr:08X}")
            
            # SET_DATA_LEN (0x02)
            elif transfer.transfer_type == 'CONTROL' and transfer.request == 0x02:
                if transfer.value is not None and transfer.index is not None:
                    current_data_size = (transfer.index << 16) | transfer.value
                    print(f"  Data size set to: {current_data_size} bytes (0x{current_data_size:X})")
            
            # Store sequence info
            if current_flash_addr is not None or current_data_size is not None:
                self.write_sequences.append({
                    'flash_addr': current_flash_addr,
                    'data_size': current_data_size,
                    'transfer': transfer
                })
    
    def _extract_bulk_transfers(self):
        """Extract bulk OUT transfers (actual data)"""
        print("\nExtracting bulk OUT transfers...")
        
        current_flash_addr = None
        
        for transfer in self.analyzer.transfers:
            # Track current flash address
            if transfer.transfer_type == 'CONTROL' and transfer.request == 0x01:
                if transfer.value is not None and transfer.index is not None:
                    current_flash_addr = (transfer.index << 16) | transfer.value
            
            # Extract bulk OUT data
            if transfer.transfer_type == 'BULK' and transfer.direction == 'OUT' and len(transfer.data) > 0:
                chunk = TransferredChunk(
                    transfer=transfer,
                    data=transfer.data,
                    flash_address=current_flash_addr
                )
                self.bulk_transfers.append(chunk)
                
                if self.verbose:
                    print(f"  Bulk OUT: {len(transfer.data)} bytes at flash 0x{current_flash_addr:08X}" 
                          if current_flash_addr else f"  Bulk OUT: {len(transfer.data)} bytes")
        
        print(f"Found {len(self.bulk_transfers)} bulk OUT transfers")
        total_transferred = sum(len(t.data) for t in self.bulk_transfers)
        print(f"Total data transferred: {total_transferred} bytes ({total_transferred/1024:.1f} KB)")

    def _correlate_data(self):
        """Correlate USB transfers with binary data"""
        print("\n" + "="*80)
        print("CORRELATING USB TRANSFERS WITH BINARY DATA")
        print("="*80)

        if not self.binary_data:
            print("ERROR: Binary data not loaded")
            return

        # Concatenate all bulk OUT data
        all_usb_data = b''.join(t.data for t in self.bulk_transfers)
        print(f"\nTotal USB data: {len(all_usb_data)} bytes")
        print(f"Binary size: {self.binary_size} bytes")

        # Check if USB data matches binary exactly
        if all_usb_data == self.binary_data:
            print("\n✓ USB data matches binary EXACTLY!")
            print("  No transformation, encryption, or compression detected")
            self._analyze_exact_match()
            return

        # Check if binary is contained in USB data
        if self.binary_data in all_usb_data:
            print("\n✓ Binary found within USB data")
            offset = all_usb_data.find(self.binary_data)
            print(f"  Binary starts at offset {offset} in USB stream")
            self._analyze_with_overhead(all_usb_data, offset)
            return

        # Check if USB data is contained in binary (partial write)
        if all_usb_data in self.binary_data:
            print("\n✓ USB data is subset of binary (partial write)")
            offset = self.binary_data.find(all_usb_data)
            print(f"  USB data corresponds to binary offset {offset}")
            self._analyze_partial_write(offset)
            return

        # Check for chunk-by-chunk correlation
        print("\nChecking chunk-by-chunk correlation...")
        self._analyze_chunked_correlation()

    def _analyze_exact_match(self):
        """Analyze when USB data matches binary exactly"""
        print("\nChunk Analysis:")

        binary_offset = 0

        for i, chunk in enumerate(self.bulk_transfers):
            chunk_size = len(chunk.data)
            binary_chunk = self.binary_data[binary_offset:binary_offset + chunk_size]

            if chunk.data == binary_chunk:
                status = "✓ MATCH"
            else:
                status = "✗ MISMATCH"

            flash_addr_str = f"0x{chunk.flash_address:08X}" if chunk.flash_address else "Unknown"

            print(f"  Chunk {i+1:3d}: {chunk_size:6d} bytes at flash {flash_addr_str:12s} "
                  f"binary[0x{binary_offset:06X}:0x{binary_offset+chunk_size:06X}] {status}")

            binary_offset += chunk_size

    def _analyze_with_overhead(self, all_usb_data: bytes, binary_offset: int):
        """Analyze when binary is found within USB data (has overhead)"""
        print("\nProtocol Overhead Analysis:")

        # Analyze data before binary
        if binary_offset > 0:
            overhead_before = all_usb_data[:binary_offset]
            print(f"\nData BEFORE binary ({binary_offset} bytes):")
            self._analyze_overhead_data(overhead_before, "HEADER/PREFIX")

        # Analyze data after binary
        overhead_after_offset = binary_offset + self.binary_size
        if overhead_after_offset < len(all_usb_data):
            overhead_after = all_usb_data[overhead_after_offset:]
            print(f"\nData AFTER binary ({len(overhead_after)} bytes):")
            self._analyze_overhead_data(overhead_after, "FOOTER/SUFFIX")

        # Show which chunks contain overhead
        print("\nChunk Breakdown:")
        usb_offset = 0
        for i, chunk in enumerate(self.bulk_transfers):
            chunk_size = len(chunk.data)
            chunk_end = usb_offset + chunk_size

            # Determine what this chunk contains
            if chunk_end <= binary_offset:
                content = "OVERHEAD (before binary)"
            elif usb_offset >= overhead_after_offset:
                content = "OVERHEAD (after binary)"
            elif usb_offset >= binary_offset and chunk_end <= overhead_after_offset:
                binary_start = usb_offset - binary_offset
                content = f"BINARY [0x{binary_start:06X}:0x{binary_start+chunk_size:06X}]"
            else:
                content = "MIXED (overhead + binary)"

            flash_addr_str = f"0x{chunk.flash_address:08X}" if chunk.flash_address else "Unknown"
            print(f"  Chunk {i+1:3d}: {chunk_size:6d} bytes at flash {flash_addr_str:12s} - {content}")

            usb_offset += chunk_size

    def _analyze_overhead_data(self, data: bytes, label: str):
        """Analyze overhead/protocol data"""
        print(f"\n{label} Data Analysis:")
        print(f"  Size: {len(data)} bytes")

        # Show hex dump
        print(f"  Hex dump:")
        for i in range(0, min(len(data), 128), 16):
            chunk = data[i:i+16]
            hex_str = ' '.join(f'{b:02x}' for b in chunk)
            ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in chunk)
            print(f"    {i:04x}: {hex_str:<48} {ascii_str}")

        if len(data) > 128:
            print(f"    ... ({len(data) - 128} more bytes)")

        # Look for patterns
        self._identify_patterns(data, label)

    def _identify_patterns(self, data: bytes, label: str):
        """Identify common patterns in overhead data"""
        print(f"\n  Pattern Analysis:")

        # Check for common markers
        markers = {
            b'FIDB': 'DDR configuration marker',
            b'RDD': 'DDR PHY params marker',
            b'\x00\x00\x00\x00': 'Null padding',
            b'\xFF\xFF\xFF\xFF': 'Flash erase pattern',
        }

        for marker, description in markers.items():
            if marker in data:
                pos = data.find(marker)
                print(f"    Found '{marker.hex()}' at offset {pos}: {description}")

        # Check if it looks like a header structure
        if len(data) >= 16:
            # Try to parse as potential header
            try:
                magic = struct.unpack('<I', data[0:4])[0]
                size = struct.unpack('<I', data[4:8])[0]

                if size > 0 and size < 100*1024*1024:  # Reasonable size
                    print(f"    Possible header: magic=0x{magic:08X}, size={size} bytes")
            except:
                pass

    def _analyze_partial_write(self, binary_offset: int):
        """Analyze when only part of binary is written"""
        print(f"\nPartial Write Analysis:")
        print(f"  Writing binary[0x{binary_offset:06X}:0x{binary_offset + len(all_usb_data):06X}]")
        print(f"  This is {len(all_usb_data)} bytes out of {self.binary_size} total")

        # Show which part of binary is being written
        percentage = (len(all_usb_data) / self.binary_size) * 100
        print(f"  Writing {percentage:.1f}% of the binary")

    def _analyze_chunked_correlation(self):
        """Analyze chunk-by-chunk to find correlations"""
        print("\nSearching for binary chunks in USB transfers...")

        matches_found = 0

        for i, usb_chunk in enumerate(self.bulk_transfers):
            # Search for this USB chunk in the binary
            if usb_chunk.data in self.binary_data:
                offset = self.binary_data.find(usb_chunk.data)
                matches_found += 1

                flash_addr_str = f"0x{usb_chunk.flash_address:08X}" if usb_chunk.flash_address else "Unknown"
                print(f"  ✓ Chunk {i+1}: {len(usb_chunk.data)} bytes at flash {flash_addr_str} "
                      f"matches binary[0x{offset:06X}:0x{offset+len(usb_chunk.data):06X}]")
            else:
                # Try to find partial matches
                match_size = self._find_largest_match(usb_chunk.data, self.binary_data)

                if match_size > 64:  # Significant partial match
                    print(f"  ~ Chunk {i+1}: {len(usb_chunk.data)} bytes has {match_size} byte partial match")
                else:
                    print(f"  ✗ Chunk {i+1}: {len(usb_chunk.data)} bytes - NO MATCH (transformed?)")

                    # Show first 64 bytes for analysis
                    if self.verbose and len(usb_chunk.data) >= 16:
                        print(f"      First 64 bytes:")
                        for j in range(0, min(len(usb_chunk.data), 64), 16):
                            chunk = usb_chunk.data[j:j+16]
                            hex_str = ' '.join(f'{b:02x}' for b in chunk)
                            print(f"        {j:04x}: {hex_str}")

        print(f"\nMatched {matches_found} out of {len(self.bulk_transfers)} chunks")

        if matches_found == 0:
            print("\n⚠ WARNING: No chunks matched!")
            print("  Possible reasons:")
            print("  - Data is encrypted")
            print("  - Data is compressed")
            print("  - Wrong binary file")
            print("  - Capture is from a different operation")

    def _find_largest_match(self, needle: bytes, haystack: bytes) -> int:
        """Find the largest contiguous match between needle and haystack"""
        max_match = 0

        # Try different starting positions in needle
        for start in range(0, len(needle), 16):
            for size in range(len(needle) - start, 0, -16):
                chunk = needle[start:start+size]
                if chunk in haystack:
                    max_match = max(max_match, size)
                    break

        return max_match

    def generate_report(self, output_file: str):
        """Generate detailed correlation report"""
        print(f"\nGenerating detailed report: {output_file}")

        with open(output_file, 'w') as f:
            f.write("="*80 + "\n")
            f.write("USB WRITE OPERATION WITH BINARY CORRELATION REPORT\n")
            f.write("="*80 + "\n\n")

            f.write(f"Capture File: {self.pcap_file}\n")
            f.write(f"Binary File: {self.binary_file}\n")
            f.write(f"Binary Size: {self.binary_size} bytes ({self.binary_size/1024:.1f} KB)\n\n")

            # USB transfer summary
            f.write("USB Transfer Summary:\n")
            f.write(f"  Total transfers: {len(self.analyzer.transfers)}\n")
            f.write(f"  Bulk OUT transfers: {len(self.bulk_transfers)}\n")

            total_usb = sum(len(t.data) for t in self.bulk_transfers)
            f.write(f"  Total data transferred: {total_usb} bytes ({total_usb/1024:.1f} KB)\n\n")

            # Correlation summary
            f.write("Correlation Analysis:\n")
            all_usb_data = b''.join(t.data for t in self.bulk_transfers)

            if all_usb_data == self.binary_data:
                f.write("  ✓ USB data matches binary EXACTLY\n")
                f.write("  No transformation detected\n")
            elif self.binary_data in all_usb_data:
                offset = all_usb_data.find(self.binary_data)
                f.write(f"  ✓ Binary found in USB data at offset {offset}\n")
                f.write(f"  Protocol overhead: {len(all_usb_data) - self.binary_size} bytes\n")
            elif all_usb_data in self.binary_data:
                offset = self.binary_data.find(all_usb_data)
                f.write(f"  ✓ Partial write detected\n")
                f.write(f"  Writing binary[{offset}:{offset+len(all_usb_data)}]\n")
            else:
                f.write("  ⚠ No direct correlation found\n")
                f.write("  Data may be transformed (encrypted/compressed)\n")

            f.write("\n" + "="*80 + "\n")
            f.write("DETAILED CHUNK ANALYSIS\n")
            f.write("="*80 + "\n\n")

            # Detailed chunk analysis
            usb_offset = 0
            for i, chunk in enumerate(self.bulk_transfers):
                f.write(f"Chunk {i+1}:\n")
                f.write(f"  USB offset: 0x{usb_offset:06X}\n")
                f.write(f"  Size: {len(chunk.data)} bytes\n")

                if chunk.flash_address:
                    f.write(f"  Flash address: 0x{chunk.flash_address:08X}\n")

                # Check if chunk is in binary
                if chunk.data in self.binary_data:
                    bin_offset = self.binary_data.find(chunk.data)
                    f.write(f"  ✓ Matches binary[0x{bin_offset:06X}:0x{bin_offset+len(chunk.data):06X}]\n")
                else:
                    f.write(f"  ✗ No exact match in binary\n")

                # Show first 64 bytes
                f.write(f"  First 64 bytes:\n")
                for j in range(0, min(len(chunk.data), 64), 16):
                    line = chunk.data[j:j+16]
                    hex_str = ' '.join(f'{b:02x}' for b in line)
                    ascii_str = ''.join(chr(b) if 32 <= b < 127 else '.' for b in line)
                    f.write(f"    {j:04x}: {hex_str:<48} {ascii_str}\n")

                f.write("\n")
                usb_offset += len(chunk.data)

        print(f"Report saved to: {output_file}")

    def print_summary(self):
        """Print summary of analysis"""
        print("\n" + "="*80)
        print("ANALYSIS SUMMARY")
        print("="*80)

        print(f"\nBinary: {self.binary_file}")
        print(f"  Size: {self.binary_size} bytes ({self.binary_size/1024:.1f} KB)")

        print(f"\nUSB Capture: {self.pcap_file}")
        print(f"  Total transfers: {len(self.analyzer.transfers)}")
        print(f"  Bulk OUT transfers: {len(self.bulk_transfers)}")

        total_usb = sum(len(t.data) for t in self.bulk_transfers)
        print(f"  Total data: {total_usb} bytes ({total_usb/1024:.1f} KB)")

        # Correlation result
        all_usb_data = b''.join(t.data for t in self.bulk_transfers)

        print(f"\nCorrelation Result:")
        if all_usb_data == self.binary_data:
            print("  ✓ EXACT MATCH - USB data equals binary")
            print("  → No transformation, ready to implement")
        elif self.binary_data in all_usb_data:
            overhead = len(all_usb_data) - self.binary_size
            print(f"  ✓ BINARY FOUND - with {overhead} bytes overhead")
            print("  → Identify and strip protocol overhead")
        elif all_usb_data in self.binary_data:
            print("  ✓ PARTIAL WRITE - USB data is subset of binary")
            print("  → Identify which part is being written")
        else:
            print("  ⚠ NO MATCH - Data may be transformed")
            print("  → Check for encryption/compression")

def main():
    parser = argparse.ArgumentParser(
        description='Analyze write operations with binary correlation'
    )
    parser.add_argument('pcap_file', help='Input pcap file from USB capture')
    parser.add_argument('binary_file', help='Binary file that was written')
    parser.add_argument('-v', '--verbose', action='store_true',
                       help='Verbose output with detailed hex dumps')
    parser.add_argument('-r', '--report', help='Generate detailed report file')

    args = parser.parse_args()

    # Check files exist
    if not Path(args.pcap_file).exists():
        print(f"ERROR: Capture file not found: {args.pcap_file}")
        sys.exit(1)

    if not Path(args.binary_file).exists():
        print(f"ERROR: Binary file not found: {args.binary_file}")
        sys.exit(1)

    # Create analyzer
    analyzer = WriteWithBinaryAnalyzer(args.pcap_file, args.binary_file, verbose=args.verbose)

    # Load binary
    if not analyzer.load_binary():
        sys.exit(1)

    # Analyze capture
    if not analyzer.analyze():
        sys.exit(1)

    # Print summary
    analyzer.print_summary()

    # Generate report if requested
    if args.report:
        analyzer.generate_report(args.report)

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)

    # Provide recommendations
    print("\nRecommendations:")
    all_usb_data = b''.join(t.data for t in analyzer.bulk_transfers)

    if all_usb_data == analyzer.binary_data:
        print("  1. Implement direct binary transfer (no transformation needed)")
        print("  2. Use the chunking pattern from the capture")
        print("  3. Match the flash addresses from SET_DATA_ADDR commands")
    elif analyzer.binary_data in all_usb_data:
        print("  1. Identify and document the protocol overhead")
        print("  2. Determine if overhead is per-chunk or per-transfer")
        print("  3. Implement overhead generation in thingino-cloner")
    else:
        print("  1. Investigate data transformation (encryption/compression)")
        print("  2. Compare chunk-by-chunk to find patterns")
        print("  3. May need to reverse-engineer transformation algorithm")

if __name__ == '__main__':
    main()


