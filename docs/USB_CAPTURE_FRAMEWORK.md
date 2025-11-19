# USB Traffic Capture and Analysis Framework

This framework provides tools to capture and analyze USB traffic from Ingenic cloner tools, enabling reverse engineering of the protocol and refinement of thingino-cloner's implementation.

## Overview

The framework consists of five main tools:

1. **capture_usb_traffic.sh** - Generic USB traffic capture script
2. **analyze_usb_capture.py** - Protocol decoder and analyzer
3. **compare_usb_captures.py** - Side-by-side comparison tool
4. **analyze_write_operation.py** - Specialized write operation analyzer
5. **analyze_write_with_binary.py** - Binary correlation analyzer (NEW!)

## Prerequisites

```bash
# Install required tools
sudo apt-get install tcpdump tshark wireshark python3

# Load usbmon kernel module
sudo modprobe usbmon
```

## Quick Start

### 1. Capture Vendor Tool Traffic

```bash
# Terminal 1: Start capture
cd thingino-cloner/tools
sudo ./capture_usb_traffic.sh vendor_write

# Terminal 2: Run vendor tool
cd ../references/cloner-2.5.43-ubuntu_thingino
sudo ./cloner --config configs/t31/t31_sfc_nor_writer.cfg

# Terminal 1: Press Ctrl+C when done
```

### 2. Capture Thingino-Cloner Traffic

```bash
# Terminal 1: Start capture
sudo ./capture_usb_traffic.sh thingino_write

# Terminal 2: Run thingino-cloner
cd ../build
sudo ./thingino-cloner --write firmware.bin

# Terminal 1: Press Ctrl+C when done
```

### 3. Analyze and Compare

```bash
# Analyze vendor capture
python3 analyze_usb_capture.py usb_captures/vendor_write_*.pcap --verbose --extract-data

# Analyze thingino capture
python3 analyze_usb_capture.py usb_captures/thingino_write_*.pcap --verbose --extract-data

# Compare them side-by-side
python3 compare_usb_captures.py \
    usb_captures/vendor_write_*.pcap \
    usb_captures/thingino_write_*.pcap \
    --label1 "Vendor" --label2 "Thingino" \
    --output comparison_report.txt
```

### 4. Correlate with Binary (NEW - RECOMMENDED!)

```bash
# Analyze write with binary correlation
python3 analyze_write_with_binary.py \
    usb_captures/vendor_write_*.pcap \
    firmware.bin \
    --verbose --report correlation_report.txt

# This shows:
# - If USB data matches binary exactly
# - Protocol overhead (headers, footers, metadata)
# - Data transformations (encryption, compression)
# - Chunk-by-chunk correlation
```

### 5. Extract Write Sequence

```bash
# Analyze write operations and generate code templates
python3 analyze_write_operation.py usb_captures/vendor_write_*.pcap --extract-sequence
```

## Tool Details

### capture_usb_traffic.sh

Generic USB capture script that works for any operation.

**Usage:**
```bash
sudo ./capture_usb_traffic.sh [operation_name]
```

**Examples:**
```bash
sudo ./capture_usb_traffic.sh vendor_read
sudo ./capture_usb_traffic.sh vendor_write
sudo ./capture_usb_traffic.sh thingino_bootstrap
sudo ./capture_usb_traffic.sh thingino_read
```

**Output:**
- Creates `usb_captures/[operation_name]_[timestamp].pcap`
- Shows quick statistics (packet counts, transfer types)

### analyze_usb_capture.py

Comprehensive USB protocol analyzer that decodes Ingenic commands.

**Usage:**
```bash
python3 analyze_usb_capture.py <capture.pcap> [options]
```

**Options:**
- `-v, --verbose` - Show full data dumps
- `-e, --extract-data` - Extract bulk transfers to files
- `-o, --output-dir DIR` - Output directory for extracted data

**Output:**
- Transfer summary (counts, directions, commands)
- Detailed transfer log with decoded commands
- Extracted data files (DDR binaries, SPL, U-Boot)
- Automatic identification of special data

**Example:**
```bash
python3 analyze_usb_capture.py vendor_write.pcap --verbose --extract-data
```

### compare_usb_captures.py

Side-by-side comparison of two captures to identify differences.

**Usage:**
```bash
python3 compare_usb_captures.py <capture1.pcap> <capture2.pcap> [options]
```

**Options:**
- `--label1 NAME` - Label for first capture (default: "Vendor")
- `--label2 NAME` - Label for second capture (default: "Thingino")
- `-o, --output FILE` - Save report to file

**Output:**
- Comparison summary (transfer counts, difference counts)
- Detailed differences (transfer type, commands, data)
- Hex dumps of differing data

**Example:**
```bash
python3 compare_usb_captures.py vendor.pcap thingino.pcap \
    --label1 "Vendor v2.5.43" --label2 "Thingino v0.1" \
    --output diff_report.txt
```

### analyze_write_operation.py

Specialized analyzer for write operations that extracts the exact sequence.

**Usage:**
```bash
python3 analyze_write_operation.py <capture.pcap> [options]
```

**Options:**
- `-e, --extract-sequence` - Generate C and Python code templates
- `--c-output FILE` - C code output file (default: write_sequence.c)
- `--py-output FILE` - Python code output file (default: write_sequence.py)

**Output:**
- Write sequence details (address, size, chunk size)
- Command sequence breakdown
- Auto-generated C code template
- Auto-generated Python code template

**Example:**
```bash
python3 analyze_write_operation.py vendor_write.pcap --extract-sequence
```

### analyze_write_with_binary.py (NEW!)

Binary correlation analyzer that compares USB traffic with the actual binary being written.

**Usage:**
```bash
python3 analyze_write_with_binary.py <capture.pcap> <binary_file> [options]
```

**Options:**
- `-v, --verbose` - Verbose output with detailed hex dumps
- `-r, --report FILE` - Generate detailed correlation report

**Output:**
- Binary vs USB data comparison
- Protocol overhead identification
- Data transformation detection
- Chunk-by-chunk correlation
- Detailed correlation report

**What it detects:**
- **Exact match** - USB data equals binary (best case, no transformation)
- **Binary with overhead** - Binary found in USB data with extra protocol bytes
- **Partial write** - Only part of binary is being written
- **Transformed data** - Data is encrypted, compressed, or otherwise modified
- **No match** - Wrong binary or complex transformation

**Example:**
```bash
# Basic analysis
python3 analyze_write_with_binary.py vendor_write.pcap firmware.bin

# Detailed analysis with report
python3 analyze_write_with_binary.py vendor_write.pcap firmware.bin \
    --verbose --report correlation_report.txt
```

**Use cases:**
- Verify binary is sent unmodified
- Identify protocol headers/footers
- Detect encryption or compression
- Find chunk boundaries
- Validate flash address mapping

## Common Workflows

### Workflow 1: Reverse Engineer Write Implementation

1. **Capture vendor write operation:**
   ```bash
   sudo ./capture_usb_traffic.sh vendor_write_test
   # Run vendor tool to write firmware
   ```

2. **Analyze the write sequence:**
   ```bash
   python3 analyze_write_operation.py usb_captures/vendor_write_test_*.pcap \
       --extract-sequence
   ```

3. **Review generated code:**
   - Check `write_sequence.c` for C implementation
   - Check `write_sequence.py` for Python reference
   - Identify command order, parameters, and timing

4. **Implement in thingino-cloner:**
   - Update `src/usb/protocol.c` with correct sequence
   - Add missing commands if needed
   - Match timing and parameters

5. **Test and compare:**
   ```bash
   # Capture thingino-cloner write
   sudo ./capture_usb_traffic.sh thingino_write_test

   # Compare with vendor
   python3 compare_usb_captures.py \
       usb_captures/vendor_write_test_*.pcap \
       usb_captures/thingino_write_test_*.pcap
   ```

### Workflow 2: Debug Read Implementation

1. **Capture vendor read operation:**
   ```bash
   sudo ./capture_usb_traffic.sh vendor_read_16mb
   # Run vendor tool to read 16MB flash
   ```

2. **Analyze the capture:**
   ```bash
   python3 analyze_usb_capture.py usb_captures/vendor_read_16mb_*.pcap \
       --verbose --extract-data -o vendor_read_data
   ```

3. **Examine the sequence:**
   - Check command order (handshake pattern)
   - Verify chunk sizes
   - Look for status checks between reads
   - Note timing between transfers

4. **Capture thingino-cloner read:**
   ```bash
   sudo ./capture_usb_traffic.sh thingino_read_16mb
   # Run thingino-cloner read
   ```

5. **Compare and identify issues:**
   ```bash
   python3 compare_usb_captures.py \
       usb_captures/vendor_read_16mb_*.pcap \
       usb_captures/thingino_read_16mb_*.pcap \
       --output read_comparison.txt

   # Review differences
   less read_comparison.txt
   ```

### Workflow 3: Extract DDR Configuration

1. **Capture bootstrap sequence:**
   ```bash
   sudo ./capture_usb_traffic.sh vendor_bootstrap_t31
   # Run vendor tool (it will bootstrap automatically)
   ```

2. **Extract DDR binary:**
   ```bash
   python3 analyze_usb_capture.py usb_captures/vendor_bootstrap_t31_*.pcap \
       --extract-data -o ddr_extraction

   # The DDR binary will be auto-detected and saved as ddr_binary.bin
   ```

3. **Analyze DDR binary:**
   ```bash
   # Use the existing DDR extraction tool
   python3 ../extract_ddr_from_pcap.py usb_captures/vendor_bootstrap_t31_*.pcap vendor_ddr.bin

   # Compare with our generated DDR
   xxd vendor_ddr.bin > vendor_ddr.hex
   xxd our_generated_ddr.bin > our_ddr.hex
   diff -y vendor_ddr.hex our_ddr.hex
   ```

### Workflow 4: Validate Bootstrap Sequence

1. **Capture vendor bootstrap:**
   ```bash
   sudo ./capture_usb_traffic.sh vendor_bootstrap
   ```

2. **Capture thingino bootstrap:**
   ```bash
   sudo ./capture_usb_traffic.sh thingino_bootstrap
   ```

3. **Compare sequences:**
   ```bash
   python3 compare_usb_captures.py \
       usb_captures/vendor_bootstrap_*.pcap \
       usb_captures/thingino_bootstrap_*.pcap
   ```

4. **Look for differences in:**
   - DDR binary content
   - SPL loading address and size
   - U-Boot loading address and size
   - Execution parameters (d2i_len)
   - Command timing and order

## Understanding the Output

### Transfer Types

- **CONTROL** - USB control transfers (vendor requests)
  - Used for commands like GET_CPU_INFO, SET_DATA_ADDR, etc.
  - Contains request code, value, and index parameters

- **BULK** - USB bulk transfers
  - Used for large data transfers (firmware, flash data)
  - High throughput, no guaranteed timing

- **INTERRUPT** - USB interrupt transfers
  - Rarely used in Ingenic protocol
  - For status notifications

### Common Commands

| Code | Name | Description |
|------|------|-------------|
| 0x00 | GET_CPU_INFO | Get CPU variant and stage |
| 0x01 | SET_DATA_ADDR | Set memory/flash address |
| 0x02 | SET_DATA_LEN | Set data length |
| 0x03 | FLUSH_CACHE | Flush CPU cache |
| 0x04 | PROG_STAGE1 | Execute stage 1 (SPL) |
| 0x05 | PROG_STAGE2 | Execute stage 2 (U-Boot) |
| 0x10 | FW_READ | Firmware read command |
| 0x11 | FW_HANDSHAKE | Firmware handshake |
| 0x13 | FW_WRITE1 | Firmware write chunk 1 |
| 0x14 | FW_WRITE2 | Firmware write chunk 2 |
| 0x16 | FW_READ_STATUS1 | Read status 1 |
| 0x19 | FW_READ_STATUS2 | Read status 2 |

### Interpreting Differences

When comparing captures, focus on:

1. **Command order** - Must match exactly for proper operation
2. **Parameters** - Value and index fields encode addresses/sizes
3. **Data content** - Especially for DDR, SPL, U-Boot
4. **Timing** - Some operations need delays between commands
5. **Status checks** - Vendor may check status more frequently

## Troubleshooting

### "tshark not found"
```bash
sudo apt-get install tshark wireshark
```

### "Permission denied" on usbmon
```bash
sudo modprobe usbmon
sudo chmod a+r /dev/usbmon*
```

### No USB traffic captured
- Make sure device is plugged in during capture
- Check that usbmon module is loaded: `lsmod | grep usbmon`
- Try capturing all USB buses: `tcpdump -i usbmon0`

### Capture file is huge
- This is normal for read operations (captures all flash data)
- Use tshark filters to reduce size:
  ```bash
  tshark -r huge.pcap -Y "usb.transfer_type == 0x02" -w control_only.pcap
  ```

### Can't find DDR binary in capture
- DDR is sent very early (before SPL)
- Make sure capture starts before running cloner tool
- Look for 324-byte transfer with "FIDB" marker
- Use: `strings capture.pcap | grep FIDB`

## Advanced Usage

### Filter Specific USB Bus

If you have multiple USB devices, filter by bus number:

```bash
# Find Ingenic device bus
lsusb | grep -i ingenic

# Capture only that bus (e.g., bus 1)
sudo tcpdump -i usbmon1 -w capture.pcap -s 0
```

### Extract Specific Transfer

```bash
# Extract only bulk OUT transfers
tshark -r capture.pcap \
    -Y "usb.transfer_type == 0x03 && usb.endpoint_address.direction == 0" \
    -T fields -e usb.capdata | xxd -r -p > bulk_out.bin
```

### Analyze with Wireshark GUI

```bash
wireshark capture.pcap
```

Useful filters:
- `usb.transfer_type == 0x02` - Control transfers only
- `usb.transfer_type == 0x03` - Bulk transfers only
- `usb.bRequest == 0x01` - SET_DATA_ADDR commands
- `usb.endpoint_address.direction == 0` - OUT transfers
- `usb.endpoint_address.direction == 1` - IN transfers

## Integration with Development

### Using Captured Data for Testing

1. Extract vendor's DDR binary and use it for testing:
   ```bash
   python3 analyze_usb_capture.py vendor.pcap --extract-data
   # Use extracted_data/ddr_binary.bin for testing
   ```

2. Compare firmware read data:
   ```bash
   # Extract vendor's read data
   python3 analyze_usb_capture.py vendor_read.pcap --extract-data

   # Compare with thingino-cloner's read
   diff extracted_data/bulk_in_*.bin thingino_read_output.bin
   ```

### Automating Capture and Analysis

Create a test script:

```bash
#!/bin/bash
# test_write_implementation.sh

# Capture vendor write
sudo ./capture_usb_traffic.sh vendor_write_test &
CAPTURE_PID=$!
sleep 2
cd ../references/cloner-2.5.43-ubuntu_thingino
sudo ./cloner --config configs/t31/writer.cfg
kill $CAPTURE_PID

# Capture thingino write
cd ../../tools
sudo ./capture_usb_traffic.sh thingino_write_test &
CAPTURE_PID=$!
sleep 2
cd ../build
sudo ./thingino-cloner --write test.bin
kill $CAPTURE_PID

# Compare
cd ../tools
python3 compare_usb_captures.py \
    usb_captures/vendor_write_test_*.pcap \
    usb_captures/thingino_write_test_*.pcap \
    --output test_results.txt

# Show results
cat test_results.txt
```

## Next Steps

After capturing and analyzing USB traffic:

1. **Identify protocol differences** - Use comparison tool
2. **Update protocol implementation** - Modify `src/usb/protocol.c`
3. **Test changes** - Capture new traffic and compare
4. **Iterate** - Repeat until captures match
5. **Validate on hardware** - Test actual read/write operations

## References

- [Ingenic USB Boot Protocol](../T20_BOOTSTRAP_ANALYSIS.md)
- [DDR Binary Format](../../DDR_BINARY_FORMAT.md)
- [Wireshark USB Capture Guide](https://wiki.wireshark.org/CaptureSetup/USB)
- [Linux usbmon Documentation](https://www.kernel.org/doc/Documentation/usb/usbmon.txt)


