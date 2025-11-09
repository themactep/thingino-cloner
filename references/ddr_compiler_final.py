#!/usr/bin/env python3
"""
DDR Binary Compiler - Final Version
Combines U-Boot timing logic + reverse-engineered binary format
"""

import struct
import sys
import argparse
from pathlib import Path
import configparser
import zlib

# U-Boot timing converter classes (copied from ddr_compiler_uboot.py)
class DDRParamConverter:
    """Convert DDR timing parameters based on U-Boot logic"""

    def __init__(self, freq_hz):
        self.ps_per_tck = 1000000000 // (freq_hz // 1000)
        self.freq_hz = freq_hz
        print(f"[*] DDR Frequency: {freq_hz / 1e6:.1f} MHz")
        print(f"[*] Clock period: {self.ps_per_tck} ps")

    def ps2cycle_ceil(self, ps, div_tck=1):
        if ps == -1:
            return 0
        return (ps + div_tck * self.ps_per_tck - 1) // self.ps_per_tck

    def ps2cycle_floor(self, ps):
        if ps == -1:
            return 0
        return ps // self.ps_per_tck

    def ns2ps(self, ns):
        return ns * 1000

    def tck2ps(self, tck):
        return tck * self.ps_per_tck

class DDRConfig:
    """Parse and hold DDR configuration from .cfg file"""

    def __init__(self, cfg_path):
        self.path = Path(cfg_path)
        self.params = {}
        self.ddr_type = None
        self._parse()

    def _parse(self):
        config = configparser.ConfigParser()
        config.read(self.path)

        if 'ddr' not in config:
            raise ValueError(f"No [ddr] section in {self.path}")

        for key, value in config['ddr'].items():
            value = value.strip('"')
            parts = value.split(',')

            if len(parts) == 2:
                val_str, unit = parts
                try:
                    val = int(val_str) if val_str != '-1' else -1
                except ValueError:
                    val = val_str

                self.params[key.upper()] = {
                    'value': val,
                    'unit': unit.strip()
                }
            else:
                self.params[key.upper()] = {
                    'value': value,
                    'unit': None
                }

        # Detect DDR type from path
        path_str = str(self.path).lower()
        if 'lpddr3' in path_str:
            self.ddr_type = 'LPDDR3'
        elif 'lpddr2' in path_str:
            self.ddr_type = 'LPDDR2'
        elif 'lpddr' in path_str:
            self.ddr_type = 'LPDDR'
        elif 'ddr3' in path_str:
            self.ddr_type = 'DDR3'
        elif 'ddr2' in path_str:
            self.ddr_type = 'DDR2'
        else:
            self.ddr_type = 'DDR2'

        print(f"[*] Detected DDR type: {self.ddr_type}")

    def get(self, key, default=None):
        if key.upper() in self.params:
            return self.params[key.upper()]['value']
        return default

    def get_ps(self, key, converter, default=0):
        if key.upper() not in self.params:
            return default

        param = self.params[key.upper()]
        value = param['value']
        unit = param['unit']

        if value == -1:
            return -1

        if unit == 'ns':
            return value * 1000
        elif unit == 'ps':
            return value
        elif unit == 'tck':
            return converter.tck2ps(value)
        else:
            return value

class DDR2Encoder:
    """Encode DDR2 parameters"""

    def __init__(self, config, converter):
        self.config = config
        self.conv = converter

    def encode_timing_params(self):
        timing = {}

        timing['tRTP'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRTP', self.conv, 7500))

        timing['tWTR'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tWTR', self.conv, 7500))

        timing['tRAS'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRAS', self.conv, 42000))

        timing['tRC'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRC', self.conv, 60000))

        timing['tRCD'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRCD', self.conv, 15000))

        timing['tRP'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRP', self.conv, 15000))

        timing['tRFC'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRFC', self.conv, 127500), 2) // 2

        timing['tREFI'] = self.conv.ps2cycle_floor(
            self.config.get_ps('tREFI', self.conv, 7800000))

        timing['tRRD'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRRD', self.conv, 10000))

        timing['tFAW'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tFAW', self.conv, 50000))

        return timing

class DDR3Encoder:
    """Encode DDR3 parameters"""

    def __init__(self, config, converter):
        self.config = config
        self.conv = converter

    def encode_timing_params(self):
        timing = {}

        timing['tRTP'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRTP', self.conv, 7500))

        timing['tWTR'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tWTR', self.conv, 7500))

        timing['tRAS'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRAS', self.conv, 35000))

        timing['tRC'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRC', self.conv, 48750))

        timing['tRCD'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRCD', self.conv, 13750))

        timing['tRP'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRP', self.conv, 13750))

        timing['tRFC'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRFC', self.conv, 160000), 2) // 2

        timing['tREFI'] = self.conv.ps2cycle_floor(
            self.config.get_ps('tREFI', self.conv, 7800000))

        timing['tRRD'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRRD', self.conv, 6000))

        timing['tFAW'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tFAW', self.conv, 40000))

        return timing

class LPDDR2Encoder:
    """Encode LPDDR2 parameters"""

    def __init__(self, config, converter):
        self.config = config
        self.conv = converter

    def encode_rl_wl(self):
        """
        Encode RL/WL according to LPDDR2 spec
        From ingenic-tools/lpddr2_params.c lines 100-127

        Encoding table:
          RL=3, WL=1 → 1
          RL=4, WL=2 → 2
          RL=5, WL=2 → 3
          RL=6, WL=3 → 4
          RL=7, WL=4 → 5
          RL=8, WL=4 → 6
        """
        rl = self.config.get('RL', 3)
        wl = self.config.get('WL', 1)

        # Create combined value: WL in low nibble, RL in high nibble
        combined = wl | (rl << 4)

        # Encoding table
        encoding_table = {
            0x31: 1,  # RL=3, WL=1
            0x42: 2,  # RL=4, WL=2
            0x52: 3,  # RL=5, WL=2
            0x63: 4,  # RL=6, WL=3
            0x74: 5,  # RL=7, WL=4
            0x84: 6,  # RL=8, WL=4
        }

        encoded = encoding_table.get(combined, 1)  # Default to 1

        return encoded

    def encode_timing_params(self):
        timing = {}

        timing['tRTP'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRTP', self.conv, 7500))

        timing['tWTR'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tWTR', self.conv, 7500))

        timing['tRAS'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRAS', self.conv, 42000))

        timing['tRC'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRC', self.conv, 57000))

        timing['tRCD'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRCD', self.conv, 18000))

        timing['tRP'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRP', self.conv, 18000))

        timing['tRFC'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRFC', self.conv, 90000))

        timing['tREFI'] = self.conv.ps2cycle_floor(
            self.config.get_ps('tREFI', self.conv, 7800000))

        timing['tRRD'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tRRD', self.conv, 10000))

        timing['tFAW'] = self.conv.ps2cycle_ceil(
            self.config.get_ps('tFAW', self.conv, 50000))

        return timing

class BinaryBuilder:
    """Build the final 324-byte DDR binary"""
    
    def __init__(self, platform='t31'):
        self.platform_config = {
            't31': {
                'crystal_freq': 24000000,
                'cpu_freq': 576000000,
                'ddr_freq': 400000000,
                'uart_baud': 115200,
                'mem_size': 8 * 1024 * 1024,  # 8 MB
            },
            't30': {
                'crystal_freq': 24000000,
                'cpu_freq': 576000000,
                'ddr_freq': 400000000,
                'uart_baud': 115200,
                'mem_size': 8 * 1024 * 1024,
            },
            't41': {
                'crystal_freq': 24000000,
                # Stock cloner shows CPU 576 MHz (0x22551000) on T41/T41N
                'cpu_freq': 576000000,
                'ddr_freq': 400000000,  # Stock cloner uses 400 MHz for T41N + W631GU6NG
                'uart_baud': 115200,
                # Vendor FIDB uses 8MB here (likely a working SRAM/region size, not total DRAM)
                'mem_size': 8 * 1024 * 1024,
            },
        }

        if platform not in self.platform_config:
            platform = 't31'

        self.config = self.platform_config[platform]
    
    def build_fidb(self, ddr_freq=None):
        """
        Build FIDB section (192 bytes total: 8 header + 184 data)
        Based on reverse engineering of ddr_extracted.bin
        """
        fidb_data = bytearray(184)

        # Use passed frequency if available, otherwise use platform default
        freq_hz = ddr_freq if ddr_freq is not None else self.config['ddr_freq']

        # Fill in known fields from reverse engineering
        struct.pack_into('<I', fidb_data, 0x00, self.config['crystal_freq'])
        struct.pack_into('<I', fidb_data, 0x04, self.config['cpu_freq'])
        struct.pack_into('<I', fidb_data, 0x08, freq_hz)
        struct.pack_into('<I', fidb_data, 0x0c, 0x00000000)  # Reserved
        struct.pack_into('<I', fidb_data, 0x10, 0x00000001)  # Enable flag
        struct.pack_into('<I', fidb_data, 0x14, self.config['uart_baud'])
        struct.pack_into('<I', fidb_data, 0x18, 0x00000001)  # Flag
        struct.pack_into('<I', fidb_data, 0x20, self.config['mem_size'])
        struct.pack_into('<I', fidb_data, 0x24, 0x00000001)
        struct.pack_into('<I', fidb_data, 0x2c, 0x00000011)
        struct.pack_into('<I', fidb_data, 0x30, 0x19800000)  # Platform ID

        # Build header
        header = b'FIDB' + struct.pack('<I', len(fidb_data))

        return header + bytes(fidb_data)
    
    def build_rdd(self, ddr_config, timing_params, ddr_freq=None):
        """
        Build RDD section (132 bytes total: 8 header + 124 data)
        Uses U-Boot calculated timing + reverse-engineered structure
        """
        rdd_data = bytearray(124)

        # DDR type mapping (discovered from reverse engineering)
        # Reference binary has type=2 for LPDDR2
        # Vendor mapping observed from stock logs: DDR3 reports as type 0
        ddr_type_map = {
            'DDR3': 0,
            'DDR2': 1,
            'LPDDR2': 2,
            'LPDDR': 2,
            'LPDDR3': 4,
        }

        # Offset 0x00: CRC (fill in later)
        # Offset 0x04: DDR type
        ddr_type = ddr_type_map.get(ddr_config.ddr_type, 0)
        struct.pack_into('<I', rdd_data, 0x04, ddr_type)

        # Offset 0x08-0x0f: Reserved

        # Offset 0x10: Frequency-related value
        # Use passed frequency if available, otherwise use platform default
        freq_hz = ddr_freq if ddr_freq is not None else self.config['ddr_freq']
        freq_val = freq_hz // 100000  # Divide by 100k
        struct.pack_into('<I', rdd_data, 0x10, freq_val)
        
        # Offset 0x14: Another frequency value
        struct.pack_into('<I', rdd_data, 0x14, 0x00002800)
        
        # Offset 0x18+: Timing parameters (byte-level encoding)
        # Based on analysis of ddr_extracted.bin and U-Boot source
        
        # These are educated guesses based on reverse engineering
        # Will need refinement based on testing
        rdd_data[0x18] = 0x01
        rdd_data[0x19] = 0x00
        rdd_data[0x1a] = 0xc2
        rdd_data[0x1b] = 0x00
        
        # Memory geometry
        row = ddr_config.get('ROW', 13)
        col = ddr_config.get('COL', 10)

        # Encoding rules discovered from reverse engineering:
        # COL: encoded as (col - 6), e.g., COL=9 → 3, COL=10 → 4
        # ROW: direct encoding

        # For LPDDR2: use RL/WL encoding
        # For DDR2/DDR3: use CL/BL
        if ddr_config.ddr_type in ['LPDDR2', 'LPDDR']:
            # LPDDR2 uses RL/WL instead of CL/BL
            rl = ddr_config.get('RL', 3)
            wl = ddr_config.get('WL', 1)

            # Encode RL/WL according to LPDDR2 spec
            combined = wl | (rl << 4)
            encoding_table = {
                0x31: 1,  # RL=3, WL=1
                0x42: 2,  # RL=4, WL=2
                0x52: 3,  # RL=5, WL=2
                0x63: 4,  # RL=6, WL=3
                0x74: 5,  # RL=7, WL=4
                0x84: 6,  # RL=8, WL=4
            }
            rl_wl_encoded = encoding_table.get(combined, 1)

            # Both 0x1c and 0x1d use the same RL/WL encoding
            rdd_data[0x1c] = rl_wl_encoded & 0xFF
            rdd_data[0x1d] = rl_wl_encoded & 0xFF
        else:
            # DDR2/DDR3 use CL/BL
            bl = ddr_config.get('BL', 8)
            cl = ddr_config.get('CL', 6)
            rdd_data[0x1c] = cl & 0xFF
            rdd_data[0x1d] = bl & 0xFF

        rdd_data[0x1e] = row & 0xFF
        rdd_data[0x1f] = (col - 6) & 0xFF  # COL encoding: subtract 6
        
        # Timing parameters from U-Boot calculations
        rdd_data[0x20] = timing_params.get('tRAS', 18) & 0xFF
        rdd_data[0x21] = timing_params.get('tRC', 24) & 0xFF
        rdd_data[0x22] = timing_params.get('tRCD', 6) & 0xFF
        rdd_data[0x23] = timing_params.get('tRP', 6) & 0xFF
        
        rdd_data[0x24] = timing_params.get('tRFC', 21) & 0xFF
        rdd_data[0x25] = 0x04
        rdd_data[0x26] = timing_params.get('tRTP', 4) & 0xFF
        rdd_data[0x27] = 0x20
        
        rdd_data[0x28] = timing_params.get('tFAW', 18) & 0xFF
        rdd_data[0x29] = 0x00
        rdd_data[0x2a] = timing_params.get('tRRD', 4) & 0xFF
        rdd_data[0x2b] = timing_params.get('tWTR', 3) & 0xFF
        
        # DQ mapping table (last 20 bytes)
        # Default sequential mapping with some swaps
        dq_mapping = [12, 13, 14, 3, 4, 5, 6, 7, 8, 9, 10, 11, 0, 1, 2, 15, 16, 17, 18, 19]
        dq_start = len(rdd_data) - 20
        for i, val in enumerate(dq_mapping):
            rdd_data[dq_start + i] = val
        
        # Calculate CRC32 checksum
        crc = zlib.crc32(bytes(rdd_data[4:])) & 0xFFFFFFFF
        struct.pack_into('<I', rdd_data, 0x00, crc)
        
        # Build header: padding + "RDD" + size (matches vendor layout)
        header = b'\x00' + b'RDD' + struct.pack('<I', len(rdd_data))

        return header + bytes(rdd_data)

    def build(self, ddr_config, timing_params, ddr_freq=None):
        """Build complete 324-byte binary"""
        fidb = self.build_fidb(ddr_freq)
        rdd = self.build_rdd(ddr_config, timing_params, ddr_freq)

        binary = fidb + rdd

        # Verify size
        if len(binary) != 324:
            print(f"[!] Warning: Binary size is {len(binary)}, expected 324")

        return binary

def main():
    parser = argparse.ArgumentParser(
        description='DDR Binary Compiler - Final Version'
    )
    parser.add_argument('config', help='Input .cfg file')
    parser.add_argument('output', help='Output .bin file')
    parser.add_argument('--platform', '-p', default='t31',
                       choices=['t31', 't30', 't41'],
                       help='Target platform (default: t31)')
    parser.add_argument('--freq', type=int, default=None,
                       help='DDR frequency in Hz (default: from platform config)')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='Verbose output')
    
    args = parser.parse_args()
    
    print("=" * 70)
    print("DDR Binary Compiler - Final Version")
    print("=" * 70)
    print()
    
    # Load config
    print(f"[*] Loading config: {args.config}")
    config = DDRConfig(args.config)

    # Build binary builder to get platform config
    builder = BinaryBuilder(args.platform)

    # Use platform DDR freq if not specified
    ddr_freq = args.freq if args.freq else builder.config['ddr_freq']

    # Create converter
    converter = DDRParamConverter(ddr_freq)
    print()

    # Select encoder based on DDR type
    if config.ddr_type == 'DDR2':
        encoder = DDR2Encoder(config, converter)
    elif config.ddr_type == 'DDR3':
        encoder = DDR3Encoder(config, converter)
    elif config.ddr_type in ['LPDDR2', 'LPDDR']:
        encoder = LPDDR2Encoder(config, converter)
    else:
        print(f"[!] DDR type {config.ddr_type} not fully implemented")
        print("[!] Using DDR2 encoder as fallback")
        encoder = DDR2Encoder(config, converter)

    # Encode parameters
    print("[*] Encoding parameters...")
    timing = encoder.encode_timing_params()

    if args.verbose:
        print("\nTiming Parameters (in clock cycles):")
        for key, value in sorted(timing.items()):
            print(f"  {key:10s} = {value:3d} cycles")
        print()

    # Build binary
    print("[*] Building binary...")
    binary = builder.build(config, timing, ddr_freq)
    
    # Write output
    with open(args.output, 'wb') as f:
        f.write(binary)
    
    print(f"[+] Generated: {args.output} ({len(binary)} bytes)")
    
    # Calculate SHA256
    import hashlib
    sha256 = hashlib.sha256(binary).hexdigest()
    print(f"[+] SHA256: {sha256}")
    
    print()
    print("=" * 70)
    print("SUCCESS!")
    print("=" * 70)
    print()
    print("Next steps:")
    print("  1. Compare with reference binary (if available)")
    print("  2. Analyze with: ./analyze_ddr_binary.py", args.output)
    print("  3. Test on hardware (carefully!)")
    print()

if __name__ == '__main__':
    main()

