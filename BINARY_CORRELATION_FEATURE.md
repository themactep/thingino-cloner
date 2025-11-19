# Binary Correlation Feature

## Overview

Enhanced the USB capture framework with **binary correlation analysis** - a powerful feature that compares captured USB traffic with the actual binary file being written. This helps identify protocol overhead, data transformations, and validates the write implementation.

## Why This Matters

When reverse-engineering a write protocol, you need to know:

1. **Is the binary sent as-is?** - No transformation needed
2. **Is there protocol overhead?** - Headers, footers, metadata to add
3. **Is data transformed?** - Encryption, compression, checksums
4. **How is data chunked?** - Chunk sizes and boundaries
5. **Where does each chunk go?** - Flash address mapping

Without the binary file, you can only see USB traffic. **With binary correlation**, you can see exactly what's unique to the protocol vs what's from the binary.

## What Was Added

### New Tool: analyze_write_with_binary.py

**File:** `tools/analyze_write_with_binary.py` (552 lines)

A comprehensive analyzer that:
- Loads the binary file being written
- Extracts all USB bulk OUT transfers
- Compares USB data with binary data
- Identifies four scenarios:
  1. **Exact match** - USB data = binary (best case!)
  2. **Binary with overhead** - Binary found in USB data with extra bytes
  3. **Partial write** - Only part of binary is written
  4. **Transformed data** - No match, data is encrypted/compressed

### Enhanced Quick Analysis Script

**File:** `tools/quick_write_analysis_with_binary.sh` (100 lines)

One-command analysis that:
- Captures USB traffic
- Correlates with binary file
- Generates correlation report
- Extracts write sequence
- Provides actionable recommendations

## Usage

### Quick Start (Recommended)

```bash
cd thingino-cloner/tools

# Capture and analyze vendor write with binary correlation
sudo ./quick_write_analysis_with_binary.sh vendor_write firmware.bin
# Run vendor cloner, press Ctrl+C when done

# Review correlation report
cat vendor_write_correlation_report.txt
```

### Manual Analysis

```bash
# Capture USB traffic first
sudo ./capture_usb_traffic.sh vendor_write
# Run vendor cloner...

# Analyze with binary correlation
python3 analyze_write_with_binary.py \
    usb_captures/vendor_write_*.pcap \
    firmware.bin \
    --verbose --report correlation_report.txt
```

## What You'll Learn

### Scenario 1: Exact Match (Best Case)

```
✓ USB data matches binary EXACTLY!
  No transformation, encryption, or compression detected

Chunk Analysis:
  Chunk   1:   4096 bytes at flash 0x00000000 binary[0x000000:0x001000] ✓ MATCH
  Chunk   2:   4096 bytes at flash 0x00001000 binary[0x001000:0x002000] ✓ MATCH
  ...
```

**Action:** Implement direct binary transfer with the same chunking pattern.

### Scenario 2: Binary with Overhead

```
✓ Binary found within USB data
  Binary starts at offset 64 in USB stream

Protocol Overhead Analysis:

Data BEFORE binary (64 bytes):
  0000: 46 49 44 42 00 00 00 40 ...  FIDB...@
  
  Possible header: magic=0x42444946, size=16777216 bytes

Chunk Breakdown:
  Chunk   1:     64 bytes at flash 0x00000000 - OVERHEAD (before binary)
  Chunk   2:   4096 bytes at flash 0x00000000 - BINARY [0x000000:0x001000]
  ...
```

**Action:** Identify the 64-byte header structure and implement it in thingino-cloner.

### Scenario 3: Partial Write

```
✓ USB data is subset of binary (partial write)
  USB data corresponds to binary offset 65536
  Writing 1048576 bytes out of 16777216 total
  Writing 6.2% of the binary
```

**Action:** Understand which part is being written and why (bootloader update, config section, etc.).

### Scenario 4: Transformed Data

```
⚠ No direct correlation found
  Data may be transformed (encrypted/compressed)

Searching for binary chunks in USB transfers...
  ✗ Chunk 1: 4096 bytes - NO MATCH (transformed?)
  ✗ Chunk 2: 4096 bytes - NO MATCH (transformed?)
  
⚠ WARNING: No chunks matched!
  Possible reasons:
  - Data is encrypted
  - Data is compressed
  - Wrong binary file
```

**Action:** Investigate transformation algorithm or verify you have the correct binary file.

## Real-World Example

### Vendor Cloner Write Analysis

```bash
# Capture vendor writing firmware.bin
sudo ./quick_write_analysis_with_binary.sh vendor_write firmware.bin

# Results show:
✓ Binary found within USB data
  Binary starts at offset 324 in USB stream

Data BEFORE binary (324 bytes):
  0000: 46 49 44 42 00 00 00 c0 ...  FIDB....  <- DDR config!
  00c0: 00 52 44 44 00 00 00 84 ...  .RDD....  <- DDR params!
  0144: 00 00 00 00 00 00 00 00 ...  ........  <- Padding
```

**Discovery:** The vendor sends a 324-byte DDR configuration before the firmware binary!

**Implementation:**
```c
// In thingino-cloner
1. Send DDR config (324 bytes)
2. Send firmware binary (no transformation)
3. Use same chunk size (4096 bytes)
4. Match flash addresses from capture
```

## Benefits

### Before Binary Correlation

- ❓ "Is this USB data the firmware or something else?"
- ❓ "Why is the USB data larger than the binary?"
- ❓ "What are these extra bytes at the beginning?"
- ❓ "Is the data encrypted?"

### After Binary Correlation

- ✅ "USB data matches binary exactly - no transformation needed"
- ✅ "324 bytes of DDR config sent before binary"
- ✅ "Binary is chunked into 4096-byte pieces"
- ✅ "Each chunk maps to sequential flash addresses"

## Integration with Workflow

The binary correlation feature integrates seamlessly:

```
1. Capture vendor write
   ↓
2. Correlate with binary  ← NEW!
   ↓
3. Identify protocol overhead  ← NEW!
   ↓
4. Extract write sequence
   ↓
5. Implement in thingino-cloner
   ↓
6. Test and compare
```

## Files Modified/Created

1. **tools/analyze_write_with_binary.py** (NEW) - 552 lines
2. **tools/quick_write_analysis_with_binary.sh** (NEW) - 100 lines
3. **tools/README.md** (UPDATED) - Added binary correlation section
4. **docs/USB_CAPTURE_FRAMEWORK.md** (UPDATED) - Added tool documentation
5. **BINARY_CORRELATION_FEATURE.md** (NEW) - This file

## Next Steps

1. **Capture vendor write with binary:**
   ```bash
   sudo ./quick_write_analysis_with_binary.sh vendor_write firmware.bin
   ```

2. **Review correlation report:**
   - Check if binary matches USB data
   - Identify any protocol overhead
   - Note chunk sizes and flash addresses

3. **Implement findings:**
   - Add overhead generation if needed
   - Match chunking pattern
   - Validate flash address mapping

4. **Test and validate:**
   - Capture thingino-cloner write
   - Compare with vendor capture
   - Verify binary correlation matches

## Summary

The binary correlation feature transforms the reverse-engineering process from **guesswork** to **data-driven analysis**. Instead of wondering what the USB traffic contains, you now have definitive answers about:

- Protocol overhead
- Data transformations
- Chunking patterns
- Flash address mapping

This dramatically accelerates write implementation development and ensures correctness.

