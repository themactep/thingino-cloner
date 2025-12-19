# DDR Dynamic Configuration Integration

## Overview

The DDR binary generation has been successfully integrated into the firmware reading tool using the new `ddr_binary_builder` API. This replaces the old DDR generation code with a cleaner, well-documented implementation that matches the Python script format.

## Changes Made

### 1. New DDR Binary Builder API (`src/ddr/ddr_binary_builder.{c,h}`)

The new API provides:
- **`ddr_build_binary()`**: Generates complete 324-byte DDR binary (FIDB + RDD)
- **`ddr_get_platform_config()`**: Returns platform-specific configuration (frequencies, UART, memory)
- **`ddr_get_platform_config_by_variant()`**: Wrapper that accepts `processor_variant_t` enum

Binary format (324 bytes total):
- **FIDB section (192 bytes)**: Platform configuration
  - Crystal frequency (24 MHz)
  - CPU frequency (576 MHz for T31, 800 MHz for T41)
  - DDR frequency (400 MHz default)
  - UART baud rate (115200)
  - Memory size (8 MB default)
- **RDD section (132 bytes)**: DDR PHY parameters
  - DDR type (DDR2/DDR3/LPDDR2/LPDDR3)
  - Memory geometry (row/col bits, CL, BL)
  - Timing parameters (tRAS, tRC, tRCD, tRP, tRFC, etc.)
  - DQ pin mapping (board-specific)

### 2. Firmware Loader Integration (`src/firmware/loader.c`)

Updated `firmware_generate_ddr_config()` to:
- Use new `ddr_binary_builder` API instead of old `ddr_generator`
- Call `ddr_get_platform_config_by_variant()` to get platform defaults
- Use hardcoded M14D1G1664A DDR2 @ 400MHz parameters (verified working)
- Generate 324-byte binary with proper FIDB + RDD format

### 3. Build System (`CMakeLists.txt`)

- Added `src/ddr/ddr_binary_builder.c` to main executable sources
- Introduced `src/ddr/crc32.c` so CRC32 generation no longer depends on zlib
- Created `test_ddr_integration` test executable

## Testing

### Integration Test (`src/test_ddr_integration.c`)

Verifies:
- Platform configuration retrieval for T31X
- DDR binary generation (324 bytes)
- FIDB header presence ("FIDB" at offset 0x00)
- RDD header presence ("RDD" at offset 0xC1-0xC3)

**Test Result**: ✅ PASS

```
$ ./build/test_ddr_integration
=== DDR Integration Test ===

Testing T31X DDR generation...
[OK] Platform config retrieved
  Crystal: 24000000 Hz
  CPU: 576000000 Hz
  DDR: 400000000 Hz
  UART: 115200 baud
  Memory: 8388608 bytes
[OK] DDR binary generated: 324 bytes
[OK] FIDB header found
[OK] RDD header found at offset 0xC0

[SUCCESS] DDR integration test passed!
```

## Usage

The DDR generation is now automatic when bootstrapping a device:

```bash
# Bootstrap with dynamic DDR generation
./thingino-cloner -i 0 -b

# Skip DDR configuration (use existing)
./thingino-cloner -i 0 -b --skip-ddr

# Use custom DDR config file
./thingino-cloner -i 0 -b --config custom_ddr.bin
```

## Default DDR Configuration

Currently uses M14D1G1664A DDR2 @ 400MHz parameters:
- **Type**: DDR2 (RDD encoding: 1)
- **Frequency**: 400 MHz (2.5ns clock period)
- **Geometry**: 13 row bits, 10 col bits
- **CAS Latency**: 7 cycles
- **Burst Length**: 8
- **Timing**: tRAS=18, tRC=23, tRCD=6, tRP=6, tRFC=52, tRTP=3, tFAW=18, tRRD=4, tWTR=3

These parameters have been verified to work on T31X hardware.

## Future Enhancements

1. **Multi-chip support**: Add DDR chip database with different configurations
2. **Auto-detection**: Detect DDR chip from device and select appropriate parameters
3. **Configuration files**: Support loading DDR parameters from config files
4. **Board-specific DQ mapping**: Allow customization of DQ pin mapping for different boards

## References

- `src/ddr/ddr_binary_builder.h` - Complete API documentation with byte-by-byte layout
- `references/ddr_compiler_final.py` - Python reference implementation
- `references/ddr_extracted.bin` - Working reference binary (324 bytes)
- `docs/llm_instructions.md` - Project guidelines

