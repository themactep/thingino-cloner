#!/bin/bash

# Capture USB traffic during our firmware write attempt
# This will help us see what's different from the vendor tool

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="our_write_capture"
PCAP_FILE="${OUTPUT_DIR}/our_write_${TIMESTAMP}.pcap"

mkdir -p "$OUTPUT_DIR"

echo "Starting USB capture..."
echo "Output will be saved to: $PCAP_FILE"
echo ""
echo "Press Ctrl+C to stop capture after the write attempt fails"
echo ""

# Start tcpdump in background
sudo tcpdump -i usbmon3 -w "$PCAP_FILE" -s 65535 &
TCPDUMP_PID=$!

echo "Capture started (PID: $TCPDUMP_PID)"
echo ""
echo "Now run: sudo ./build/thingino-cloner -w firmware-t20.bin"
echo ""
echo "After it fails, press Ctrl+C here to stop capture"

# Wait for user to stop
trap "sudo kill $TCPDUMP_PID; echo 'Capture stopped'; exit 0" INT
wait $TCPDUMP_PID

