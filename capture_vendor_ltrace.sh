#!/bin/bash

# Script to capture vendor tool execution with strace
# This will help us understand what USB system calls the vendor tool makes
# and potentially reveal why endpoint 0x02 is available for them but not for us

set -e

VENDOR_TOOL="./bin/64bit/core_64"
#CONFIG_FILE="./references/cloner-2.5.43-ubuntu_thingino/configs/t20/t20_sfc_nor_writer_full.cfg"
FIRMWARE_FILE="firmware-t20.bin"
OUTPUT_DIR="vendor_strace"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/vendor_strace_${TIMESTAMP}.txt"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

echo "=========================================="
echo "Vendor Tool strace Capture"
echo "=========================================="
echo "Vendor tool: ${VENDOR_TOOL}"
echo "Config file: ${CONFIG_FILE}"
echo "Firmware file: ${FIRMWARE_FILE}"
echo "Output file: ${OUTPUT_FILE}"
echo ""

# Check if vendor tool exists
if [ ! -f "${VENDOR_TOOL}" ]; then
    echo "Error: Vendor tool not found at ${VENDOR_TOOL}"
    exit 1
fi

# Check if config file exists
if [ ! -f "${CONFIG_FILE}" ]; then
    echo "Error: Config file not found at ${CONFIG_FILE}"
#    exit 1
fi

# Check if firmware file exists
if [ ! -f "${FIRMWARE_FILE}" ]; then
    echo "Error: Firmware file not found at ${FIRMWARE_FILE}"
    #exit 1
fi

# Check if ltrace is installed
if ! command -v ltrace &> /dev/null; then
    echo "Error: ltrace is not installed"
    echo "Install with: sudo apt-get install ltrace"
    exit 1
fi

echo "Starting ltrace capture..."
echo "Press Ctrl+C to stop the capture"
echo ""

# Run vendor tool with ltrace, filtering for USB-related calls
# -f: trace child processes
# -e: filter for specific library calls
# -o: output file
# -tt: print absolute timestamps with microseconds
# -T: show time spent in each call

ltrace -f -tt -T \
    -e 'libusb*' \
    -e 'usb*' \
    -e 'open*' \
    -e 'close*' \
    -e 'ioctl*' \
    -e 'read*' \
    -e 'write*' \
    -o "${OUTPUT_FILE}" \
    "${VENDOR_TOOL}"   2>&1 | tee "${OUTPUT_DIR}/vendor_console_${TIMESTAMP}.txt"

echo ""
echo "=========================================="
echo "Capture complete!"
echo "=========================================="
echo "ltrace output: ${OUTPUT_FILE}"
echo "Console output: ${OUTPUT_DIR}/vendor_console_${TIMESTAMP}.txt"
echo ""
echo "To analyze the ltrace output:"
echo "  grep 'libusb_set_configuration' ${OUTPUT_FILE}"
echo "  grep 'libusb_claim_interface' ${OUTPUT_FILE}"
echo "  grep 'libusb_bulk_transfer' ${OUTPUT_FILE}"
echo "  grep 'endpoint' ${OUTPUT_FILE}"
echo ""
echo "To see all libusb calls in order:"
echo "  grep 'libusb' ${OUTPUT_FILE} | less"

