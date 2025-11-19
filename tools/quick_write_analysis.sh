#!/bin/bash
#
# Quick Write Analysis Helper
#
# This script automates the process of capturing and analyzing a write operation.
# It's designed to make it easy to reverse-engineer the write protocol.
#
# Usage:
#   sudo ./quick_write_analysis.sh [capture_name]
#
# Example:
#   sudo ./quick_write_analysis.sh vendor_write_test
#

set -e

CAPTURE_NAME="${1:-write_analysis}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== Quick Write Analysis ===${NC}"
echo -e "${BLUE}Capture name: ${CAPTURE_NAME}${NC}\n"

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}ERROR: This script must be run as root${NC}"
    echo "Usage: sudo $0 [capture_name]"
    exit 1
fi

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

# Step 2: Analyze the capture
echo -e "${YELLOW}Step 2: Analyzing capture...${NC}\n"
python3 analyze_usb_capture.py "$CAPTURE_FILE" --extract-data -o "extracted_${CAPTURE_NAME}"

# Step 3: Extract write sequence
echo -e "\n${YELLOW}Step 3: Extracting write sequence...${NC}\n"
python3 analyze_write_operation.py "$CAPTURE_FILE" --extract-sequence \
    --c-output "${CAPTURE_NAME}_sequence.c" \
    --py-output "${CAPTURE_NAME}_sequence.py"

# Step 4: Summary
echo -e "\n${GREEN}=== Analysis Complete ===${NC}\n"
echo "Files created:"
echo "  1. Capture: $CAPTURE_FILE"
echo "  2. Extracted data: extracted_${CAPTURE_NAME}/"
echo "  3. C code: ${CAPTURE_NAME}_sequence.c"
echo "  4. Python code: ${CAPTURE_NAME}_sequence.py"
echo ""
echo "Next steps:"
echo "  1. Review the C code: cat ${CAPTURE_NAME}_sequence.c"
echo "  2. Check extracted data: ls -lh extracted_${CAPTURE_NAME}/"
echo "  3. Implement in thingino-cloner: edit ../src/usb/protocol.c"
echo "  4. Test and compare with: ./compare_usb_captures.py"
echo ""

