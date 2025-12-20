#!/bin/bash

# Script to capture core_64 execution with strace
# This will show us the actual USB system calls including ioctl operations

set -e

CORE_TOOL="./references/cloner-2.5.43-ubuntu_thingino/bin/64bit/core_64"
CONFIG_DIR="./references/cloner-2.5.43-ubuntu_thingino/configs/t20"
FIRMWARE_FILE="firmware-t20.bin"
OUTPUT_DIR="vendor_strace"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/core64_strace_${TIMESTAMP}.txt"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

echo "=========================================="
echo "core_64 strace Capture"
echo "=========================================="
echo "Core tool: ${CORE_TOOL}"
echo "Config dir: ${CONFIG_DIR}"
echo "Firmware file: ${FIRMWARE_FILE}"
echo "Output file: ${OUTPUT_FILE}"
echo ""

# Check if core tool exists
if [ ! -f "${CORE_TOOL}" ]; then
    echo "Error: core_64 not found at ${CORE_TOOL}"
#    exit 1
fi

# Check if config dir exists
if [ ! -d "${CONFIG_DIR}" ]; then
    echo "Error: Config directory not found at ${CONFIG_DIR}"
#    exit 1
fi

# Check if firmware file exists
if [ ! -f "${FIRMWARE_FILE}" ]; then
    echo "Error: Firmware file not found at ${FIRMWARE_FILE}"
#    exit 1
fi

# Check if strace is installed
if ! command -v strace &> /dev/null; then
    echo "Error: strace is not installed"
    echo "Install with: sudo apt-get install strace"
    exit 1
fi

echo "Starting strace capture..."
echo "This will capture all system calls including USB ioctl operations"
echo ""

# Run core_64 with strace
# -f: trace child processes
# -o: output file
# -tt: print absolute timestamps with microseconds
# -T: show time spent in each call
# -s: string size limit (increase to see more ioctl data)
# -v: verbose mode (print all ioctl structures)
# -e trace=...: trace specific system calls
#   - open,openat,close: file operations
#   - ioctl: USB device control (this is the key one!)
#   - read,write: data transfers
#   - mmap,munmap: memory operations (for USB buffers)

cd references/cloner-2.5.43-ubuntu_thingino

strace -f -tt -T -s 512 -v \
    -e trace=open,openat,close,ioctl,read,write,mmap,munmap \
    -o "../../${OUTPUT_FILE}" \
    ./bin/64bit/core_64 2>&1 | tee "../../${OUTPUT_DIR}/core64_console_${TIMESTAMP}.txt"

cd ../..

echo ""
echo "=========================================="
echo "Capture complete!"
echo "=========================================="
echo "strace output: ${OUTPUT_FILE}"
echo "Console output: ${OUTPUT_DIR}/core64_console_${TIMESTAMP}.txt"
echo ""
echo "To find USB device operations:"
echo "  grep '/dev/bus/usb' ${OUTPUT_FILE}"
echo ""
echo "To find ioctl calls (USB control operations):"
echo "  grep 'ioctl' ${OUTPUT_FILE} | head -100"
echo ""
echo "To decode ioctl numbers:"
echo "  # USBDEVFS_SETCONFIGURATION = 0x80045505"
echo "  # USBDEVFS_CLAIMINTERFACE = 0x8004550f"
echo "  # USBDEVFS_SUBMITURB = 0x8038550a"
echo "  # USBDEVFS_REAPURBNDELAY = 0x4008550d"
echo "  grep 'ioctl.*0x80045505' ${OUTPUT_FILE}  # SET_CONFIGURATION"
echo "  grep 'ioctl.*0x8004550f' ${OUTPUT_FILE}  # CLAIM_INTERFACE"

