# thingino-cloner

Open-source USB cloner tool for Ingenic SoC devices (T20/T21/T30/T31/T40/T41).

## Features

- ✅ **Bootstrap** - Load DDR config, SPL, and U-Boot to device
- ✅ **Read** - Read firmware from flash memory
- 🚧 **Write** - Write firmware to flash (in development)
- ✅ **Multi-platform** - Supports T20, T21, T30, T31, T40, T41
- ✅ **Embedded configs** - Built-in DDR and firmware configurations

## Quick Start

### Build

```bash
mkdir build && cd build
cmake ..
make
```

### Cross-compile for Windows (MinGW-w64)

```bash
sudo apt-get install mingw-w64
cmake -S . -B build-windows \
   -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/mingw-w64-x86_64.cmake
cmake --build build-windows
```

The toolchain file wires in the bundled libusb binaries (`third_party/libusb/windows/x86_64`). Install the MinGW zlib development package (e.g. `mingw-w64-x86-64-zlib` on Debian) if your distribution does not ship it by default.

### Usage

```bash
# List devices
sudo ./thingino-cloner --list

# Bootstrap device
sudo ./thingino-cloner --bootstrap

# Read firmware
sudo ./thingino-cloner --read output.bin

# Write firmware (in development)
sudo ./thingino-cloner --write firmware.bin
```

## USB Traffic Capture Framework

**NEW:** Complete framework for capturing and analyzing USB traffic to reverse-engineer the protocol and refine the write implementation.

### Quick Write Analysis

```bash
# Capture and analyze vendor write operation
cd tools
sudo ./quick_write_analysis.sh vendor_write

# Follow the prompts, then review generated code
cat ../references/vendor/vendor_write_sequence.c
```

### Tools

- **capture_usb_traffic.sh** - Capture USB traffic from any cloner tool
- **analyze_usb_capture.py** - Decode and analyze protocol
- **compare_usb_captures.py** - Compare vendor vs thingino captures
- **compare_firmware_blobs.py** - Cross-check embedded blobs vs vendor binaries and captured payloads
- **analyze_write_operation.py** - Extract write sequences and generate code

See [USB_CAPTURE_FRAMEWORK_SUMMARY.md](docs/reports/USB_CAPTURE_FRAMEWORK_SUMMARY.md) for details.

#### Firmware blob comparison

After running `analyze_usb_capture.py --extract-data`, verify that our embedded SPL/U-Boot (and optional full images) match the vendor binaries and captured payloads:

```bash
./tools/compare_firmware_blobs.py \
   --variant t31 \
   --image-path vendor/thingino-wyze_vdb1_t31x_sc4236_rtl8189ftv.bin \
   --capture-uboot extracted_data/bulk_out_0002_frame13555_245760bytes.bin
```

The script auto-detects SPL blobs, exposes hash mismatches, and can reassemble 128KB chunks (from `extracted_data/`) into a single firmware image for end-to-end comparison.

## Documentation

- [USB Capture Framework](docs/USB_CAPTURE_FRAMEWORK.md) - Complete capture/analysis guide
- [USB Capture Summary](docs/reports/USB_CAPTURE_FRAMEWORK_SUMMARY.md) - Framework overview
- [Tools Quick Reference](tools/README.md) - Quick command reference
- [T20 Bootstrap Analysis](docs/reports/T20_BOOTSTRAP_ANALYSIS.md) - T20-specific details
- [Write Implementation Summary](docs/reports/WRITE_IMPLEMENTATION_SUMMARY.md) - State of the flash writer
- [Workflow Diagram](docs/reports/WORKFLOW_DIAGRAM.md) - High-level process overview
- [Repository Structure](docs/STRUCTURE.md) - How files are organized and where to add new work
- [DDR Integration](docs/DDR_INTEGRATION_SUMMARY.md) - DDR configuration details
- [Embedded Firmware](docs/EMBEDDED_FIRMWARE.md) - Firmware database details

## Development Workflow

### Implementing Write Functionality

1. **Capture vendor write:**
   ```bash
   cd tools
   sudo ./capture_usb_traffic.sh vendor_write
   # Run vendor cloner in another terminal
   ```

2. **Analyze sequence:**
   ```bash
   python3 analyze_write_operation.py usb_captures/vendor_write_*.pcap --extract-sequence
   ```

3. **Implement in code:**
   - Review `write_sequence.c`
   - Update `src/usb/protocol.c`
   - Add missing commands if needed

4. **Test and validate:**
   ```bash
   sudo ./capture_usb_traffic.sh thingino_write
   # Run thingino-cloner

   python3 compare_usb_captures.py \
       usb_captures/vendor_write_*.pcap \
       usb_captures/thingino_write_*.pcap
   ```

5. **Iterate until captures match**

## Project Structure

```
thingino-cloner/
├── src/                      # Production sources (bootstrap, USB, DDR, firmware)
├── include/                  # Public headers
├── scripts/                  # Lightweight helpers (analysis/ + capture/)
├── tools/                    # Full USB capture + analysis toolchain
├── tests/
│   ├── unit/                 # DDR, firmware, USB unit tests
│   ├── integration/          # High-level workflow tests
│   └── legacy/               # Historical experiments kept for reference
├── docs/
│   ├── reports/              # Deep dives, timelines, and logs
│   └── *.md                  # Architecture + integration guides
├── references/
│   ├── vendor/               # Captures, firmware, DDR blobs, logs
│   └── ddr/                  # Project-authored DDR artifacts
└── build/                    # Generated build output (gitignored)
```

## Requirements

### Build Requirements
- CMake 3.10+
- GCC or Clang
- libusb-1.0-dev

### Runtime Requirements
- libusb-1.0
- Root/sudo access for USB operations

### USB Capture Requirements
- tcpdump
- tshark
- python3
- usbmon kernel module

## Installation

### Ubuntu/Debian

```bash
# Build requirements
sudo apt-get install build-essential cmake libusb-1.0-0-dev

# USB capture tools
sudo apt-get install tcpdump tshark wireshark python3

# Load USB monitoring
sudo modprobe usbmon
```

## Testing

```bash
# Test the build
cd build
./thingino-cloner --help

# Test USB capture framework
cd ../tools
./test_framework.sh
```

## Contributing

Contributions welcome! Areas needing work:

1. **Write implementation** - Use the capture framework to reverse-engineer correct write protocol
2. **Additional SoC support** - Test and add support for more variants
3. **Error handling** - Improve error messages and recovery
4. **Documentation** - Expand guides and examples

## License

See LICENSE file for details.

## Acknowledgments

- Ingenic for the SoC hardware
- Thingino project for inspiration
- Community contributors
