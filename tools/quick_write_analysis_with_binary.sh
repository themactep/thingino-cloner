#!/bin/bash
#
# Quick Write Analysis with Binary Correlation
#
# This script automates the process of capturing and analyzing a write operation
# with correlation to the actual binary being written.
#
# Usage:
#   sudo ./quick_write_analysis_with_binary.sh <capture_name> <binary_file>
#
# Example:
#   sudo ./quick_write_analysis_with_binary.sh vendor_write firmware.bin
#

set -e

if [ $# -lt 2 ]; then
    echo "Usage: sudo $0 <capture_name> <binary_file>"
    echo ""
    echo "Example:"
    echo "  sudo $0 vendor_write firmware.bin"
    exit 1
fi

CAPTURE_NAME="$1"
BINARY_FILE="$2"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== Quick Write Analysis with Binary Correlation ===${NC}"
echo -e "${BLUE}Capture name: ${CAPTURE_NAME}${NC}"
echo -e "${BLUE}Binary file: ${BINARY_FILE}${NC}\n"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root${NC}"
    echo "Usage: sudo $0 <capture_name> <binary_file>"
    exit 1
fi

# Check if binary file exists
if [ ! -f "$BINARY_FILE" ]; then
    echo -e "${RED}ERROR: Binary file not found: $BINARY_FILE${NC}"
    exit 1
fi

# Get binary file info
BINARY_SIZE=$(stat -c%s "$BINARY_FILE" 2>/dev/null || stat -f%z "$BINARY_FILE")
echo -e "${YELLOW}Binary file info:${NC}"
echo "  File: $BINARY_FILE"
echo "  Size: $BINARY_SIZE bytes ($((BINARY_SIZE / 1024)) KB)"
echo ""

# Step 1: Start capture
echo -e "${YELLOW}Step 1: Starting USB capture...${NC}"
echo "Press Ctrl+C when the write operation is complete"
echo ""

./capture_usb_traffic.sh "$CAPTURE_NAME"

# Find the most recent capture file
CAPTURE_FILE=$(ls -t usb_captures/${CAPTURE_NAME}_*.pcap 2>/dev/null | head -1)

if [ -z "$CAPTURE_FILE" ]; then
    echo -e "${RED}ERROR: No capture file found${NC}"
    exit 1
fi

echo -e "\n${GREEN}Capture saved: $CAPTURE_FILE${NC}\n"

# Step 2: Analyze with binary correlation
echo -e "${YELLOW}Step 2: Analyzing capture with binary correlation...${NC}\n"
python3 analyze_write_with_binary.py "$CAPTURE_FILE" "$BINARY_FILE" \
    --verbose --report "${CAPTURE_NAME}_correlation_report.txt"

# Step 3: Extract write sequence (traditional analysis)
echo -e "\n${YELLOW}Step 3: Extracting write sequence...${NC}\n"
python3 analyze_write_operation.py "$CAPTURE_FILE" --extract-sequence \
    --c-output "${CAPTURE_NAME}_sequence.c" \
    --py-output "${CAPTURE_NAME}_sequence.py"

# Step 4: Extract data for manual inspection
echo -e "\n${YELLOW}Step 4: Extracting USB data...${NC}\n"
python3 analyze_usb_capture.py "$CAPTURE_FILE" --extract-data -o "extracted_${CAPTURE_NAME}"

# Step 5: Summary
echo -e "\n${GREEN}=== Analysis Complete ===${NC}\n"
echo "Files created:"
echo "  1. Capture: $CAPTURE_FILE"
echo "  2. Correlation report: ${CAPTURE_NAME}_correlation_report.txt"
echo "  3. C code: ${CAPTURE_NAME}_sequence.c"
echo "  4. Python code: ${CAPTURE_NAME}_sequence.py"
echo "  5. Extracted data: extracted_${CAPTURE_NAME}/"
echo ""
echo "Next steps:"
echo "  1. Review correlation: cat ${CAPTURE_NAME}_correlation_report.txt"
echo "  2. Review C code: cat ${CAPTURE_NAME}_sequence.c"
echo "  3. Check if binary matches USB data exactly"
echo "  4. Identify any protocol overhead or transformation"
echo "  5. Implement in thingino-cloner: edit ../src/usb/protocol.c"
echo ""

