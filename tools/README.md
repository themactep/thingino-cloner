# USB Traffic Capture Tools - Quick Reference

## Quick Start

### Option A: With Binary Correlation (RECOMMENDED)

```bash
# One command to capture and analyze with binary correlation
sudo ./quick_write_analysis_with_binary.sh vendor_write firmware.bin
# Run vendor cloner, press Ctrl+C when done
# Review vendor_write_correlation_report.txt
```

### Option B: Without Binary

```bash
# One command to capture and analyze
sudo ./quick_write_analysis.sh vendor_write
# Run vendor cloner, press Ctrl+C when done
# Review vendor_write_sequence.c
```

### Manual Workflow

### 1. Capture Vendor Write Operation
```bash
# Terminal 1
sudo ./capture_usb_traffic.sh vendor_write

# Terminal 2
cd ../references/cloner-2.5.43-ubuntu_thingino
sudo ./cloner --config configs/t31/t31_sfc_nor_writer.cfg

# Terminal 1: Press Ctrl+C when done
```

### 2. Analyze with Binary Correlation
```bash
python3 analyze_write_with_binary.py \
    usb_captures/vendor_write_*.pcap \
    firmware.bin \
    --verbose --report correlation_report.txt
```

### 3. Analyze Write Sequence
```bash
python3 analyze_write_operation.py usb_captures/vendor_write_*.pcap --extract-sequence
```

### 3. Capture Thingino Write
```bash
# Terminal 1
sudo ./capture_usb_traffic.sh thingino_write

# Terminal 2
cd ../build
sudo ./thingino-cloner --write firmware.bin

# Terminal 1: Press Ctrl+C when done
```

### 4. Compare Captures
```bash
python3 compare_usb_captures.py \
    usb_captures/vendor_write_*.pcap \
    usb_captures/thingino_write_*.pcap
```

## Tools Overview

| Tool | Purpose | Output |
|------|---------|--------|
| `capture_usb_traffic.sh` | Capture USB traffic | `.pcap` file |
| `analyze_usb_capture.py` | Decode protocol | Summary + extracted data |
| `compare_usb_captures.py` | Compare two captures | Difference report |
| `analyze_write_operation.py` | Extract write sequence | C/Python code templates |
| `analyze_write_with_binary.py` | **Correlate USB with binary** | **Correlation report** |
| `quick_write_analysis.sh` | Automated analysis | All outputs |
| `quick_write_analysis_with_binary.sh` | **Automated with binary** | **All outputs + correlation** |

## Common Commands

### Capture Operations

**NEW: Smart Auto-Detection!** The capture script now automatically detects Ingenic devices and captures ONLY their traffic (no keyboard/mouse interference).

```bash
# Auto-detect and capture (recommended)
sudo ./capture_usb_traffic.sh vendor_write

# Wait for device to appear, then auto-capture
sudo ./capture_usb_traffic.sh vendor_write --wait-for-device

# Different operations
sudo ./capture_usb_traffic.sh vendor_read
sudo ./capture_usb_traffic.sh thingino_bootstrap
sudo ./capture_usb_traffic.sh thingino_read
```

**How it works:**
1. Polls `lsusb` to detect Ingenic device (vendor ID 0xa108 or 0x601a)
2. Identifies the USB bus and device number
3. Captures ONLY that device's traffic (filtered)
4. No more keyboard/mouse/other USB noise!

### Analyze Captures
```bash
# Basic analysis
python3 analyze_usb_capture.py capture.pcap

# Verbose with data extraction
python3 analyze_usb_capture.py capture.pcap --verbose --extract-data

# Extract to specific directory
python3 analyze_usb_capture.py capture.pcap -e -o my_data
```

### Compare Captures
```bash
# Basic comparison
python3 compare_usb_captures.py vendor.pcap thingino.pcap

# With custom labels
python3 compare_usb_captures.py vendor.pcap thingino.pcap \
    --label1 "Vendor v2.5.43" --label2 "Thingino v0.1"

# Save report
python3 compare_usb_captures.py vendor.pcap thingino.pcap -o report.txt
```

### Analyze Write Operations
```bash
# Analyze write sequence
python3 analyze_write_operation.py vendor_write.pcap

# Extract code templates
python3 analyze_write_operation.py vendor_write.pcap --extract-sequence

# Custom output files
python3 analyze_write_operation.py vendor_write.pcap -e \
    --c-output my_write.c --py-output my_write.py
```

### Analyze Write with Binary Correlation (NEW!)
```bash
# Basic correlation analysis
python3 analyze_write_with_binary.py capture.pcap firmware.bin

# Verbose with detailed report
python3 analyze_write_with_binary.py capture.pcap firmware.bin \
    --verbose --report correlation_report.txt

# This will show:
# - If USB data matches binary exactly
# - Protocol overhead (headers, footers)
# - Data transformations (encryption, compression)
# - Chunk-by-chunk correlation
```

## Typical Workflow for Write Implementation

### NEW: With Binary Correlation (Recommended)

```bash
# 1. Capture vendor write with binary correlation
sudo ./quick_write_analysis_with_binary.sh vendor_write firmware.bin
# Run vendor tool...

# 2. Review correlation report
cat vendor_write_correlation_report.txt
# Check if:
# - USB data matches binary exactly (best case)
# - Binary found with overhead (need to identify overhead)
# - No match (data is transformed)

# 3. Review generated code
cat vendor_write_sequence.c

# 4. Implement in thingino-cloner
# Edit src/usb/protocol.c based on findings

# 5. Test implementation
sudo ./quick_write_analysis_with_binary.sh thingino_write firmware.bin
# Run thingino-cloner...

# 6. Compare results
python3 compare_usb_captures.py \
    usb_captures/vendor_write_*.pcap \
    usb_captures/thingino_write_*.pcap \
    --output comparison.txt

# 7. Review differences
less comparison.txt
```

### Traditional Workflow (Without Binary)

```bash
# 1. Capture vendor write
sudo ./capture_usb_traffic.sh vendor_write_test
# Run vendor tool...

# 2. Extract write sequence
python3 analyze_write_operation.py usb_captures/vendor_write_test_*.pcap \
    --extract-sequence

# 3. Review generated code
cat write_sequence.c
cat write_sequence.py

# 4. Implement in thingino-cloner
# Edit src/usb/protocol.c based on write_sequence.c

# 5. Test implementation
sudo ./capture_usb_traffic.sh thingino_write_test
# Run thingino-cloner...

# 6. Compare results
python3 compare_usb_captures.py \
    usb_captures/vendor_write_test_*.pcap \
    usb_captures/thingino_write_test_*.pcap \
    --output comparison.txt

# 7. Review differences
less comparison.txt
```

## Prerequisites

```bash
# Install tools
sudo apt-get install tcpdump tshark wireshark python3

# Load USB monitoring
sudo modprobe usbmon
```

## Troubleshooting

### Permission Denied
```bash
# Run with sudo
sudo ./capture_usb_traffic.sh operation_name
```

### No Traffic Captured
```bash
# Check usbmon is loaded
lsmod | grep usbmon

# Load if needed
sudo modprobe usbmon
```

### tshark Not Found
```bash
sudo apt-get install tshark
```

## Output Files

### Capture Script
- `usb_captures/[operation]_[timestamp].pcap` - Raw USB capture

### Analyze Script
- Console output with summary and detailed log
- `extracted_data/bulk_out_*.bin` - Bulk OUT transfers
- `extracted_data/bulk_in_*.bin` - Bulk IN transfers
- `extracted_data/ddr_binary.bin` - Auto-detected DDR binary

### Write Analyzer
- `write_sequence.c` - C code template
- `write_sequence.py` - Python code template

### Compare Script
- Console output with differences
- Optional report file with `-o` option

## See Also

- [Full Documentation](../docs/USB_CAPTURE_FRAMEWORK.md)
- [Bootstrap Analysis](../T20_BOOTSTRAP_ANALYSIS.md)
- [DDR Extraction Guide](../CAPTURE_VENDOR_T20.md)

