#!/bin/bash
#
# Identify Ingenic Device in USB Capture
#
# This script helps identify which USB device in a capture is the Ingenic device
#

if [ $# -lt 1 ]; then
    echo "Usage: $0 <capture.pcap>"
    exit 1
fi

PCAP_FILE="$1"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${GREEN}=== Identifying Ingenic Device in Capture ===${NC}\n"

# First, show what Ingenic devices are currently connected
echo -e "${YELLOW}Currently connected Ingenic devices:${NC}"
lsusb | grep -i "ingenic\|601a\|a108" || echo "  None found"
echo ""

# Extract unique device addresses from capture
echo -e "${YELLOW}USB devices in capture:${NC}"
tshark -r "$PCAP_FILE" -T fields -e usb.device_address -e usb.bus_id 2>/dev/null | \
    sort -u | grep -v "^$" | while read addr bus; do
    echo "  Bus $bus Device $addr"
done
echo ""

# Look for Ingenic-specific patterns in the capture
echo -e "${YELLOW}Looking for Ingenic-specific patterns...${NC}"

# Check for GET_CPU_INFO command (0x00)
echo -e "${BLUE}Checking for GET_CPU_INFO (vendor request 0x00):${NC}"
tshark -r "$PCAP_FILE" -Y "usb.capdata contains c0:00" 2>/dev/null | head -5 || echo "  Not found"
echo ""

# Check for BOOT magic strings
echo -e "${BLUE}Checking for BOOT magic strings:${NC}"
tshark -r "$PCAP_FILE" -T fields -e usb.capdata 2>/dev/null | \
    grep -i "424f4f54" | head -3 | while read data; do
    echo "  Found: $data"
done
echo ""

# Check for DDR binary (FIDB marker)
echo -e "${BLUE}Checking for DDR binary (FIDB marker):${NC}"
tshark -r "$PCAP_FILE" -T fields -e usb.capdata 2>/dev/null | \
    grep -i "46494442" | head -3 | while read data; do
    echo "  Found FIDB: ${data:0:60}..."
done
echo ""

# Show bulk OUT transfers by device
echo -e "${YELLOW}Bulk OUT transfers by device:${NC}"
tshark -r "$PCAP_FILE" -T fields \
    -e usb.device_address \
    -e usb.transfer_type \
    -e usb.endpoint_address.direction \
    -Y "usb.transfer_type == 0x03 && usb.endpoint_address.direction == 0" 2>/dev/null | \
    awk '{print $1}' | sort | uniq -c | sort -rn | while read count addr; do
    echo "  Device $addr: $count bulk OUT transfers"
done
echo ""

echo -e "${GREEN}=== Recommendations ===${NC}"
echo ""
echo "To capture ONLY the Ingenic device:"
echo "  1. Find the Ingenic device: lsusb | grep -i ingenic"
echo "  2. Note the bus and device number (e.g., Bus 001 Device 115)"
echo "  3. Capture only that bus: sudo tcpdump -i usbmon1 -w capture.pcap"
echo ""
echo "Or use tshark with a filter:"
echo "  sudo tshark -i usbmon0 -w capture.pcap -f 'usb.device_address == 115'"
echo ""

