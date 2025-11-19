#!/bin/bash
#
# Test USB Capture Framework
#
# This script tests that all the framework tools are working correctly.
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Testing USB Capture Framework ===${NC}\n"

# Test 1: Check if tools exist
echo -e "${YELLOW}Test 1: Checking if tools exist...${NC}"
TOOLS=(
    "capture_usb_traffic.sh"
    "analyze_usb_capture.py"
    "compare_usb_captures.py"
    "analyze_write_operation.py"
)

for tool in "${TOOLS[@]}"; do
    if [ -f "$tool" ]; then
        echo -e "  ${GREEN}✓${NC} $tool exists"
    else
        echo -e "  ${RED}✗${NC} $tool missing"
        exit 1
    fi
done

# Test 2: Check if tools are executable
echo -e "\n${YELLOW}Test 2: Checking if tools are executable...${NC}"
for tool in "${TOOLS[@]}"; do
    if [ -x "$tool" ]; then
        echo -e "  ${GREEN}✓${NC} $tool is executable"
    else
        echo -e "  ${RED}✗${NC} $tool is not executable"
        echo "  Run: chmod +x $tool"
        exit 1
    fi
done

# Test 3: Check Python dependencies
echo -e "\n${YELLOW}Test 3: Checking Python...${NC}"
if command -v python3 &> /dev/null; then
    echo -e "  ${GREEN}✓${NC} python3 found: $(python3 --version)"
else
    echo -e "  ${RED}✗${NC} python3 not found"
    exit 1
fi

# Test 4: Check system tools
echo -e "\n${YELLOW}Test 4: Checking system tools...${NC}"
SYSTEM_TOOLS=("tcpdump" "tshark")
for tool in "${SYSTEM_TOOLS[@]}"; do
    if command -v "$tool" &> /dev/null; then
        echo -e "  ${GREEN}✓${NC} $tool found"
    else
        echo -e "  ${YELLOW}⚠${NC} $tool not found (install with: sudo apt-get install $tool)"
    fi
done

# Test 5: Check usbmon module
echo -e "\n${YELLOW}Test 5: Checking usbmon module...${NC}"
if lsmod | grep -q usbmon; then
    echo -e "  ${GREEN}✓${NC} usbmon module loaded"
else
    echo -e "  ${YELLOW}⚠${NC} usbmon module not loaded (load with: sudo modprobe usbmon)"
fi

# Test 6: Test Python scripts syntax
echo -e "\n${YELLOW}Test 6: Testing Python scripts syntax...${NC}"
PYTHON_SCRIPTS=(
    "analyze_usb_capture.py"
    "compare_usb_captures.py"
    "analyze_write_operation.py"
)

for script in "${PYTHON_SCRIPTS[@]}"; do
    if python3 -m py_compile "$script" 2>/dev/null; then
        echo -e "  ${GREEN}✓${NC} $script syntax OK"
    else
        echo -e "  ${RED}✗${NC} $script has syntax errors"
        exit 1
    fi
done

# Test 7: Test help output
echo -e "\n${YELLOW}Test 7: Testing help output...${NC}"
if python3 analyze_usb_capture.py --help &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} analyze_usb_capture.py --help works"
else
    echo -e "  ${RED}✗${NC} analyze_usb_capture.py --help failed"
fi

if python3 compare_usb_captures.py --help &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} compare_usb_captures.py --help works"
else
    echo -e "  ${RED}✗${NC} compare_usb_captures.py --help failed"
fi

if python3 analyze_write_operation.py --help &>/dev/null; then
    echo -e "  ${GREEN}✓${NC} analyze_write_operation.py --help works"
else
    echo -e "  ${RED}✗${NC} analyze_write_operation.py --help failed"
fi

# Test 8: Check if test pcap exists
echo -e "\n${YELLOW}Test 8: Checking for test data...${NC}"
if [ -f "../references/t41n.pcap" ]; then
    echo -e "  ${GREEN}✓${NC} Test pcap found: ../references/t41n.pcap"
    
    # Try to analyze it
    echo -e "\n${YELLOW}Test 9: Testing analysis on real pcap...${NC}"
    if python3 analyze_usb_capture.py ../references/t41n.pcap > /tmp/test_analysis.txt 2>&1; then
        echo -e "  ${GREEN}✓${NC} Successfully analyzed test pcap"
        
        # Check if output contains expected content
        if grep -q "USB CAPTURE SUMMARY" /tmp/test_analysis.txt; then
            echo -e "  ${GREEN}✓${NC} Output contains expected summary"
        else
            echo -e "  ${YELLOW}⚠${NC} Output format may be unexpected"
        fi
    else
        echo -e "  ${YELLOW}⚠${NC} Analysis failed (may need tshark)"
    fi
else
    echo -e "  ${YELLOW}⚠${NC} No test pcap found (optional)"
fi

# Summary
echo -e "\n${GREEN}=== Framework Test Complete ===${NC}\n"
echo "All critical tests passed!"
echo ""
echo "Next steps:"
echo "  1. Capture USB traffic: sudo ./capture_usb_traffic.sh test_capture"
echo "  2. Analyze capture: python3 analyze_usb_capture.py usb_captures/test_capture_*.pcap"
echo "  3. See README.md for more examples"
echo ""

