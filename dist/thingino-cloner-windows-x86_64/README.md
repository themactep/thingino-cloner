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
cat vendor_write_sequence.c
```

### Tools

- **capture_usb_traffic.sh** - Capture USB traffic from any cloner tool
- **analyze_usb_capture.py** - Decode and analyze protocol
- **compare_usb_captures.py** - Compare vendor vs thingino captures
- **analyze_write_operation.py** - Extract write sequences and generate code

See [USB_CAPTURE_FRAMEWORK_SUMMARY.md](USB_CAPTURE_FRAMEWORK_SUMMARY.md) for details.

## Documentation

- [USB Capture Framework](docs/USB_CAPTURE_FRAMEWORK.md) - Complete capture/analysis guide
- [USB Capture Summary](USB_CAPTURE_FRAMEWORK_SUMMARY.md) - Framework overview
- [Tools Quick Reference](tools/README.md) - Quick command reference
- [T20 Bootstrap Analysis](T20_BOOTSTRAP_ANALYSIS.md) - T20-specific details
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
├── src/                    # Source code
│   ├── usb/               # USB protocol implementation
│   ├── ddr/               # DDR configuration
│   ├── firmware/          # Firmware database
│   └── bootstrap.c        # Bootstrap implementation
├── include/               # Header files
├── tools/                 # USB capture and analysis tools
├── docs/                  # Documentation
├── references/            # Reference implementations and captures
└── build/                 # Build output
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
