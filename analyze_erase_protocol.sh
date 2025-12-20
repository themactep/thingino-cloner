#!/bin/bash

# Comprehensive analysis of the erase protocol in vendor pcap

echo "=== Analyzing Erase Protocol in vendor_t20_write.pcap ==="
echo ""

echo "1. Checking USB configuration changes around firmware stage:"
tshark -r vendor_t20_write.pcap -Y "usb.setup.bRequest == 0x09" -T fields -e frame.number -e frame.time_relative -e usb.setup.wValue 2>/dev/null | tail -5
echo ""

echo "2. Checking what endpoints are available after SET_CONFIGURATION:"
echo "   Looking at frames around 188821 (SET_CONFIGURATION)..."
tshark -r vendor_t20_write.pcap -Y "frame.number >= 188821 && frame.number <= 188830" -V 2>/dev/null | grep -E "Frame [0-9]+:|bRequest|Configuration|Endpoint" | head -30
echo ""

echo "3. Checking if there are any vendor requests between flash descriptor and erase:"
echo "   Frames 189363-189370:"
tshark -r vendor_t20_write.pcap -Y "frame.number >= 189363 && frame.number <= 189370" -T fields -e frame.number -e usb.setup.bRequest -e usb.endpoint_address -e frame.len 2>/dev/null
echo ""

echo "4. Checking first 5 erase packets to see if they're all the same:"
for i in 189370 189374 189376 189380 189384; do
    echo "Frame $i:"
    tshark -r vendor_t20_write.pcap -Y "frame.number == $i" -T fields -e usb.capdata 2>/dev/null | xxd -r -p | xxd | head -3
done
echo ""

echo "5. Checking if device responds between erase packets:"
tshark -r vendor_t20_write.pcap -Y "frame.number >= 189370 && frame.number <= 189400 && usb.endpoint_address == 0x81" -T fields -e frame.number -e frame.time_relative 2>/dev/null | head -10
echo ""

echo "=== Analysis complete ==="
echo ""
echo "Key questions to answer:"
echo "1. Does the vendor tool do SET_CONFIGURATION before firmware write?"
echo "2. What endpoints are available after SET_CONFIGURATION?"
echo "3. Are there any vendor requests between flash descriptor and erase?"
echo "4. Does the device send any responses during erase sequence?"

