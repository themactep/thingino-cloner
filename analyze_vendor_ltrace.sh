#!/bin/bash

# Script to analyze vendor tool ltrace output
# Extracts key USB operations and their sequence

if [ $# -lt 1 ]; then
    echo "Usage: $0 <ltrace_output_file>"
    echo ""
    echo "Example: $0 vendor_ltrace/vendor_ltrace_20251110_123456.txt"
    exit 1
fi

LTRACE_FILE="$1"

if [ ! -f "${LTRACE_FILE}" ]; then
    echo "Error: File not found: ${LTRACE_FILE}"
    exit 1
fi

echo "=========================================="
echo "Vendor Tool ltrace Analysis"
echo "=========================================="
echo "Input file: ${LTRACE_FILE}"
echo ""

echo "=== USB Device Initialization Sequence ==="
echo ""
grep -E 'libusb_(init|open|get_device|set_configuration|claim_interface|detach_kernel_driver)' "${LTRACE_FILE}" | head -30
echo ""

echo "=== SET_CONFIGURATION Calls ==="
echo ""
grep 'libusb_set_configuration' "${LTRACE_FILE}"
echo ""

echo "=== Interface Claim/Release ==="
echo ""
grep -E 'libusb_(claim|release)_interface' "${LTRACE_FILE}" | head -20
echo ""

echo "=== Kernel Driver Operations ==="
echo ""
grep -E 'libusb_(detach|attach)_kernel_driver' "${LTRACE_FILE}"
echo ""

echo "=== Control Transfers (Vendor Requests) ==="
echo ""
grep 'libusb_control_transfer' "${LTRACE_FILE}" | head -50
echo ""

echo "=== Bulk Transfers ==="
echo ""
echo "First 20 bulk transfers:"
grep 'libusb_bulk_transfer' "${LTRACE_FILE}" | head -20
echo ""
echo "Bulk transfers to endpoint 0x02:"
grep 'libusb_bulk_transfer.*0x02' "${LTRACE_FILE}" | head -10
echo ""

echo "=== Endpoint-related Calls ==="
echo ""
grep -iE 'endpoint|0x02' "${LTRACE_FILE}" | grep -v 'bulk_transfer' | head -20
echo ""

echo "=== Device Descriptor Queries ==="
echo ""
grep -E 'libusb_get.*descriptor' "${LTRACE_FILE}" | head -20
echo ""

echo "=== Summary Statistics ==="
echo ""
echo "Total libusb calls: $(grep -c 'libusb' "${LTRACE_FILE}")"
echo "SET_CONFIGURATION calls: $(grep -c 'libusb_set_configuration' "${LTRACE_FILE}")"
echo "CLAIM_INTERFACE calls: $(grep -c 'libusb_claim_interface' "${LTRACE_FILE}")"
echo "BULK_TRANSFER calls: $(grep -c 'libusb_bulk_transfer' "${LTRACE_FILE}")"
echo "CONTROL_TRANSFER calls: $(grep -c 'libusb_control_transfer' "${LTRACE_FILE}")"
echo "Transfers to endpoint 0x02: $(grep -c 'libusb_bulk_transfer.*0x02' "${LTRACE_FILE}")"
echo ""

echo "=== Timeline of Key Events ==="
echo ""
echo "Looking for sequence: init -> open -> set_config -> claim -> transfers"
grep -E 'libusb_(init|open_device_with|set_configuration|claim_interface|bulk_transfer.*0x02)' "${LTRACE_FILE}" | \
    awk '{print NR": "$0}' | head -40
echo ""

echo "=========================================="
echo "Analysis complete!"
echo "=========================================="

