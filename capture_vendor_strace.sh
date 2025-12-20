#!/bin/bash

# Script to capture vendor tool execution with strace
# This will help us understand what USB system calls the vendor tool makes
# and potentially reveal why endpoint 0x02 is available for them but not for us

set -e

VENDOR_TOOL="./bin/64bit/cloner_64"
OUTPUT_DIR="vendor_strace"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_FILE="${OUTPUT_DIR}/vendor_strace_${TIMESTAMP}.txt"

# Create output directory
mkdir -p "${OUTPUT_DIR}"

echo "=========================================="
echo "Vendor Tool strace Capture"
echo "=========================================="
echo "Vendor tool: ${VENDOR_TOOL}"
echo "Output file: ${OUTPUT_FILE}"
echo ""

# Check if vendor tool exists
if [ ! -f "${VENDOR_TOOL}" ]; then
    echo "Error: Vendor tool not found at ${VENDOR_TOOL}"
    exit 1
fi

# Check if strace is installed
if ! command -v strace &> /dev/null; then
    echo "Error: strace is not installed"
    echo "Install with: sudo apt-get install strace"
    exit 1
fi

echo "Starting strace capture..."
echo "Press Ctrl+C to stop the capture"
echo ""

# Run vendor tool with strace, filtering for USB-related system calls
# -f: trace child processes
# -e: filter for specific system calls
# -o: output file
# -tt: print absolute timestamps with microseconds
# -T: show time spent in each call
# -s: string size limit (increase to see more data)
# -v: verbose mode (print all fields)

strace -f -tt -T -s 256 -v \
    -e trace=open,openat,close,ioctl,read,write \
    -o "${OUTPUT_FILE}" \
    "${VENDOR_TOOL}" 2>&1 | tee "${OUTPUT_DIR}/vendor_console_${TIMESTAMP}.txt"

echo ""
echo "=========================================="
echo "Capture complete!"
echo "=========================================="
echo "strace output: ${OUTPUT_FILE}"
echo "Console output: ${OUTPUT_DIR}/vendor_console_${TIMESTAMP}.txt"
echo ""
echo "To analyze the strace output:"
echo "  grep 'ioctl.*USBDEVFS' ${OUTPUT_FILE}"
echo "  grep '/dev/bus/usb' ${OUTPUT_FILE}"
echo "  grep 'open.*usb' ${OUTPUT_FILE}"
echo ""
echo "To see USB device operations:"
echo "  grep -E 'open.*3-[0-9]|ioctl.*20' ${OUTPUT_FILE} | less"

