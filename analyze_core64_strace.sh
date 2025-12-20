#!/bin/bash

# Script to analyze core_64 strace output
# Extracts key USB operations and their sequence

if [ $# -lt 1 ]; then
    echo "Usage: $0 <strace_output_file>"
    echo ""
    echo "Example: $0 vendor_strace/core64_strace_20251110_123456.txt"
    exit 1
fi

STRACE_FILE="$1"

if [ ! -f "${STRACE_FILE}" ]; then
    echo "Error: File not found: ${STRACE_FILE}"
    exit 1
fi

echo "=========================================="
echo "core_64 strace Analysis"
echo "=========================================="
echo "Input file: ${STRACE_FILE}"
echo ""

echo "=== USB Device File Operations ==="
echo ""
echo "Opening USB device:"
grep -E 'open.*(/dev/bus/usb|/sys/bus/usb)' "${STRACE_FILE}" | head -20
echo ""

echo "=== USB Device File Descriptor ==="
echo ""
echo "Finding which FD is the USB device:"
grep -E 'open.*3-[0-9].*= [0-9]+' "${STRACE_FILE}" | tail -5
echo ""

echo "=== ioctl Operations (USB Control) ==="
echo ""
echo "All ioctl calls (first 50):"
grep 'ioctl' "${STRACE_FILE}" | head -50
echo ""

echo "=== Decoding ioctl Numbers ==="
echo ""
echo "SET_CONFIGURATION (0x80045505 = 2147767557):"
grep -E 'ioctl.*0x80045505|ioctl.*2147767557' "${STRACE_FILE}"
echo ""

echo "CLAIM_INTERFACE (0x8004550f = 2147767567):"
grep -E 'ioctl.*0x8004550f|ioctl.*2147767567' "${STRACE_FILE}"
echo ""

echo "SUBMITURB (0x8038550a = 2151175434):"
grep -E 'ioctl.*0x8038550a|ioctl.*2151175434' "${STRACE_FILE}" | head -20
echo ""

echo "REAPURBNDELAY (0x4008550d = 1074287885):"
grep -E 'ioctl.*0x4008550d|ioctl.*1074287885' "${STRACE_FILE}" | head -20
echo ""

echo "=== USB Descriptor Reads ==="
echo ""
grep -E 'read.*descriptor' "${STRACE_FILE}" | head -10
echo ""

echo "=== Timeline of Key USB Operations ==="
echo ""
echo "Showing sequence: open device -> claim interface -> submit URBs"
grep -E 'open.*/dev/bus/usb/[0-9]|ioctl.*(0x8004550f|0x8038550a)' "${STRACE_FILE}" | head -30
echo ""

echo "=== Summary Statistics ==="
echo ""
echo "Total ioctl calls: $(grep -c 'ioctl' "${STRACE_FILE}")"
echo "USB device opens: $(grep -c 'open.*/dev/bus/usb' "${STRACE_FILE}")"
echo "SET_CONFIGURATION calls: $(grep -cE 'ioctl.*0x80045505' "${STRACE_FILE}")"
echo "CLAIM_INTERFACE calls: $(grep -cE 'ioctl.*0x8004550f' "${STRACE_FILE}")"
echo "SUBMITURB calls: $(grep -cE 'ioctl.*0x8038550a' "${STRACE_FILE}")"
echo ""

echo "=== Looking for Endpoint Information ==="
echo ""
echo "Searching for endpoint addresses in ioctl data..."
echo "Note: Endpoint 0x02 would appear as '\\x02' in the data"
grep -E 'ioctl.*\\x02' "${STRACE_FILE}" | head -10
echo ""

echo "=========================================="
echo "Analysis complete!"
echo "=========================================="
echo ""
echo "Key things to look for:"
echo "1. Does vendor call SET_CONFIGURATION? (should be 0 or 1 calls)"
echo "2. What's the sequence of operations before endpoint 0x02 is used?"
echo "3. Are there any special ioctl calls we're missing?"
echo "4. What data is sent in SUBMITURB calls?"

