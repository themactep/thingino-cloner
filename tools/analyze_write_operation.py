#!/usr/bin/env python3
"""
Write Operation Analyzer for Ingenic Cloner

Specialized tool to analyze write operations from USB captures and extract
the exact sequence of commands and data needed for firmware writing.

This helps reverse-engineer the correct write implementation for thingino-cloner.

Usage:
    python3 analyze_write_operation.py <capture.pcap> [--extract-sequence]
"""

import sys
import subprocess
import struct
import argparse
from dataclasses import dataclass
from typing import List, Optional, Tuple
from enum import IntEnum

# Import the analyzer
from analyze_usb_capture import USBCaptureAnalyzer, USBTransfer, COMMAND_NAMES

@dataclass
class WriteSequence:
    """Represents a complete write sequence"""
    flash_address: Optional[int] = None
    data_size: Optional[int] = None
    chunk_size: Optional[int] = None
    transfers: List[USBTransfer] = None
    
    def __post_init__(self):
        if self.transfers is None:
            self.transfers = []

class WriteOperationAnalyzer:
    def __init__(self, pcap_file: str):
        self.pcap_file = pcap_file
        self.analyzer = USBCaptureAnalyzer(pcap_file)
        self.write_sequences: List[WriteSequence] = []
    
    def analyze(self):
        """Analyze the capture for write operations"""
        print(f"Analyzing write operations in {self.pcap_file}...")
        
        if not self.analyzer.parse_pcap():
            return False
        
        self._identify_write_sequences()
        return True
    
    def _identify_write_sequences(self):
        """Identify write sequences in the transfers"""
        print("\nIdentifying write sequences...")
        
        current_sequence = WriteSequence()
        in_write_sequence = False
        
        for i, transfer in enumerate(self.analyzer.transfers):
            # Look for SET_DATA_ADDR (0x01) - indicates start of write
            if transfer.transfer_type == 'CONTROL' and transfer.request == 0x01:
                # Save previous sequence if exists
                if in_write_sequence and current_sequence.transfers:
                    self.write_sequences.append(current_sequence)
                
                # Start new sequence
                current_sequence = WriteSequence()
                in_write_sequence = True
                
                # Extract address from value and index
                if transfer.value is not None and transfer.index is not None:
                    current_sequence.flash_address = (transfer.index << 16) | transfer.value
                    print(f"  Found write sequence starting at address: 0x{current_sequence.flash_address:08X}")
                
                current_sequence.transfers.append(transfer)
            
            # Look for SET_DATA_LEN (0x02) - indicates data size
            elif transfer.transfer_type == 'CONTROL' and transfer.request == 0x02 and in_write_sequence:
                if transfer.value is not None and transfer.index is not None:
                    current_sequence.data_size = (transfer.index << 16) | transfer.value
                    print(f"    Data size: {current_sequence.data_size} bytes (0x{current_sequence.data_size:X})")
                
                current_sequence.transfers.append(transfer)
            
            # Look for bulk OUT transfers (actual data)
            elif transfer.transfer_type == 'BULK' and transfer.direction == 'OUT' and in_write_sequence:
                current_sequence.transfers.append(transfer)
                if current_sequence.chunk_size is None:
                    current_sequence.chunk_size = len(transfer.data)
                    print(f"    Chunk size: {current_sequence.chunk_size} bytes")
            
            # Look for write-related vendor requests
            elif transfer.transfer_type == 'CONTROL' and in_write_sequence:
                if transfer.request in [0x12, 0x13, 0x14]:  # WRITE, FW_WRITE1, FW_WRITE2
                    current_sequence.transfers.append(transfer)
                elif transfer.request in [0x16, 0x19, 0x25, 0x26]:  # Status checks
                    current_sequence.transfers.append(transfer)
                elif transfer.request == 0x03:  # FLUSH_CACHE - might indicate end
                    current_sequence.transfers.append(transfer)
                    # End of sequence
                    if current_sequence.transfers:
                        self.write_sequences.append(current_sequence)
                    in_write_sequence = False
                    current_sequence = WriteSequence()
        
        # Save final sequence if exists
        if in_write_sequence and current_sequence.transfers:
            self.write_sequences.append(current_sequence)
        
        print(f"\nFound {len(self.write_sequences)} write sequence(s)")
    
    def print_sequences(self):
        """Print detailed information about write sequences"""
        print("\n" + "="*80)
        print("WRITE SEQUENCES")
        print("="*80)
        
        for seq_num, seq in enumerate(self.write_sequences, 1):
            print(f"\n--- Write Sequence #{seq_num} ---")
            print(f"Flash Address: 0x{seq.flash_address:08X}" if seq.flash_address else "Flash Address: Unknown")
            print(f"Data Size: {seq.data_size} bytes (0x{seq.data_size:X})" if seq.data_size else "Data Size: Unknown")
            print(f"Chunk Size: {seq.chunk_size} bytes" if seq.chunk_size else "Chunk Size: Unknown")
            print(f"Total Transfers: {len(seq.transfers)}")
            
            # Count transfer types
            control_count = sum(1 for t in seq.transfers if t.transfer_type == 'CONTROL')
            bulk_count = sum(1 for t in seq.transfers if t.transfer_type == 'BULK')
            
            print(f"  Control transfers: {control_count}")
            print(f"  Bulk transfers: {bulk_count}")
            
            # Show command sequence
            print(f"\nCommand Sequence:")
            for i, t in enumerate(seq.transfers):
                if t.transfer_type == 'CONTROL':
                    cmd_name = COMMAND_NAMES.get(t.request, f"0x{t.request:02X}") if t.request else "Unknown"
                    value_str = f"value=0x{t.value:04X}" if t.value is not None else ""
                    index_str = f"index=0x{t.index:04X}" if t.index is not None else ""
                    print(f"  {i+1:3d}. {cmd_name:20s} {value_str:15s} {index_str:15s} data_len={len(t.data)}")
                elif t.transfer_type == 'BULK':
                    print(f"  {i+1:3d}. BULK {t.direction:3s}                                              data_len={len(t.data)}")

    def extract_c_code(self, output_file: str = "write_sequence.c"):
        """Generate C code template for the write sequence"""
        if not self.write_sequences:
            print("No write sequences found")
            return

        print(f"\nGenerating C code template to {output_file}...")

        with open(output_file, 'w') as f:
            f.write("/*\n")
            f.write(" * Auto-generated write sequence from USB capture\n")
            f.write(f" * Source: {self.pcap_file}\n")
            f.write(" */\n\n")

            for seq_num, seq in enumerate(self.write_sequences, 1):
                f.write(f"// Write Sequence #{seq_num}\n")
                f.write(f"// Flash Address: 0x{seq.flash_address:08X}\n" if seq.flash_address else "// Flash Address: Unknown\n")
                f.write(f"// Data Size: {seq.data_size} bytes\n" if seq.data_size else "// Data Size: Unknown\n")
                f.write(f"thingino_error_t write_sequence_{seq_num}(usb_device_t* device, const uint8_t* data, uint32_t data_size) {{\n")
                f.write(f"    thingino_error_t result;\n\n")

                for i, t in enumerate(seq.transfers):
                    if t.transfer_type == 'CONTROL':
                        cmd_name = COMMAND_NAMES.get(t.request, f"0x{t.request:02X}") if t.request else "Unknown"

                        if t.request == 0x01:  # SET_DATA_ADDR
                            f.write(f"    // Step {i+1}: Set flash address\n")
                            f.write(f"    result = protocol_set_data_address(device, 0x{seq.flash_address:08X});\n")
                            f.write(f"    if (result != THINGINO_SUCCESS) return result;\n\n")

                        elif t.request == 0x02:  # SET_DATA_LEN
                            f.write(f"    // Step {i+1}: Set data length\n")
                            f.write(f"    result = protocol_set_data_length(device, data_size);\n")
                            f.write(f"    if (result != THINGINO_SUCCESS) return result;\n\n")

                        elif t.request == 0x03:  # FLUSH_CACHE
                            f.write(f"    // Step {i+1}: Flush cache\n")
                            f.write(f"    result = protocol_flush_cache(device);\n")
                            f.write(f"    if (result != THINGINO_SUCCESS) return result;\n\n")

                        elif t.request in [0x13, 0x14]:  # FW_WRITE1, FW_WRITE2
                            f.write(f"    // Step {i+1}: {cmd_name}\n")
                            f.write(f"    result = protocol_fw_write_chunk{t.request - 0x12}(device, data);\n")
                            f.write(f"    if (result != THINGINO_SUCCESS) return result;\n\n")

                        elif t.request in [0x16, 0x19, 0x25, 0x26]:  # Status checks
                            f.write(f"    // Step {i+1}: Check status ({cmd_name})\n")
                            f.write(f"    // TODO: Implement status check\n\n")

                        else:
                            f.write(f"    // Step {i+1}: {cmd_name} (0x{t.request:02X})\n")
                            f.write(f"    // TODO: Implement this command\n\n")

                    elif t.transfer_type == 'BULK' and t.direction == 'OUT':
                        f.write(f"    // Step {i+1}: Bulk OUT transfer ({len(t.data)} bytes)\n")
                        f.write(f"    int transferred;\n")
                        f.write(f"    result = libusb_bulk_transfer(device->handle, ENDPOINT_OUT,\n")
                        f.write(f"        (uint8_t*)data, data_size, &transferred, 5000);\n")
                        f.write(f"    if (result != LIBUSB_SUCCESS) return THINGINO_ERROR_TRANSFER_FAILED;\n\n")

                f.write(f"    return THINGINO_SUCCESS;\n")
                f.write(f"}}\n\n")

        print(f"C code template saved to {output_file}")

    def extract_python_code(self, output_file: str = "write_sequence.py"):
        """Generate Python code template for the write sequence"""
        if not self.write_sequences:
            print("No write sequences found")
            return

        print(f"\nGenerating Python code template to {output_file}...")

        with open(output_file, 'w') as f:
            f.write("#!/usr/bin/env python3\n")
            f.write('"""\n')
            f.write("Auto-generated write sequence from USB capture\n")
            f.write(f"Source: {self.pcap_file}\n")
            f.write('"""\n\n')
            f.write("import usb.core\n")
            f.write("import usb.util\n\n")

            for seq_num, seq in enumerate(self.write_sequences, 1):
                f.write(f"def write_sequence_{seq_num}(dev, data):\n")
                f.write(f'    """Write sequence #{seq_num}\n')
                f.write(f'    Flash Address: 0x{seq.flash_address:08X}\n' if seq.flash_address else '    Flash Address: Unknown\n')
                f.write(f'    Data Size: {seq.data_size} bytes\n' if seq.data_size else '    Data Size: Unknown\n')
                f.write(f'    """\n')

                for i, t in enumerate(seq.transfers):
                    if t.transfer_type == 'CONTROL':
                        cmd_name = COMMAND_NAMES.get(t.request, f"0x{t.request:02X}") if t.request else "Unknown"
                        f.write(f"    # Step {i+1}: {cmd_name}\n")

                        if t.request_type and t.request is not None:
                            value = t.value if t.value is not None else 0
                            index = t.index if t.index is not None else 0
                            data_len = len(t.data)

                            if t.direction == 'OUT':
                                f.write(f"    dev.ctrl_transfer(0x{t.request_type:02X}, 0x{t.request:02X}, "
                                       f"0x{value:04X}, 0x{index:04X}, b'')\n")
                            else:
                                f.write(f"    result = dev.ctrl_transfer(0x{t.request_type:02X}, 0x{t.request:02X}, "
                                       f"0x{value:04X}, 0x{index:04X}, {data_len})\n")
                        f.write("\n")

                    elif t.transfer_type == 'BULK' and t.direction == 'OUT':
                        f.write(f"    # Step {i+1}: Bulk OUT transfer ({len(t.data)} bytes)\n")
                        f.write(f"    dev.write(0x{t.endpoint:02X}, data)\n\n")

                f.write(f"    return True\n\n")

        print(f"Python code template saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description='Analyze write operations from USB captures'
    )
    parser.add_argument('pcap_file', help='Input pcap file')
    parser.add_argument('-e', '--extract-sequence', action='store_true',
                       help='Extract write sequence as C and Python code')
    parser.add_argument('--c-output', default='write_sequence.c',
                       help='Output file for C code (default: write_sequence.c)')
    parser.add_argument('--py-output', default='write_sequence.py',
                       help='Output file for Python code (default: write_sequence.py)')

    args = parser.parse_args()

    analyzer = WriteOperationAnalyzer(args.pcap_file)

    if not analyzer.analyze():
        sys.exit(1)

    analyzer.print_sequences()

    if args.extract_sequence:
        analyzer.extract_c_code(args.c_output)
        analyzer.extract_python_code(args.py_output)

    print("\n" + "="*80)
    print("Analysis complete!")
    print("="*80)

if __name__ == '__main__':
    main()


