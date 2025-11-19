#!/bin/bash
# Test write operation with USB capture for comparison

set -e

FIRMWARE_FILE="/home/matteius/output-stable/wyze_vdb2_t31x_sc301iot_atbm6031/images/thingino-wyze_vdb2_t31x_sc301iot_atbm6031.bin"
CAPTURE_DIR="usb_captures"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
CAPTURE_FILE="${CAPTURE_DIR}/thingino_write_${TIMESTAMP}.pcap"

echo "================================================================================"
echo "THINGINO CLONER WRITE TEST WITH USB CAPTURE"
echo "================================================================================"
echo ""
echo "This script will:"
echo "  1. Start USB capture"
echo "  2. Run thingino-cloner write operation"
echo "  3. Stop capture and analyze"
echo ""
echo "IMPORTANT: Make sure device is in firmware stage (already bootstrapped)"
echo ""
read -p "Press Enter to continue or Ctrl+C to abort..."

# Start USB capture in background
echo ""
echo "Starting USB capture..."
sudo tcpdump -i usbmon1 -w "$CAPTURE_FILE" -s 65535 &
TCPDUMP_PID=$!
sleep 2

echo "Running thingino-cloner write..."
echo ""

# Run the write operation
sudo ../build/thingino-cloner -w "$FIRMWARE_FILE" 2>&1 | tee write_test_output.txt

# Stop capture
echo ""
echo "Stopping USB capture..."
sudo kill $TCPDUMP_PID 2>/dev/null || true
sleep 1

# Fix permissions
sudo chmod 644 "$CAPTURE_FILE"

echo ""
echo "================================================================================"
echo "CAPTURE COMPLETE"
echo "================================================================================"
echo ""
echo "Capture saved to: $CAPTURE_FILE"
echo ""
echo "Analyzing capture..."
python3 analyze_usb_capture.py "$CAPTURE_FILE" > "analysis_${TIMESTAMP}.txt"

echo ""
echo "Quick summary:"
echo "---------------"
grep -E "Total Transfers|BULK.*OUT|CONTROL.*OUT" "analysis_${TIMESTAMP}.txt" | head -20

echo ""
echo "Full analysis saved to: analysis_${TIMESTAMP}.txt"
echo ""
echo "To compare with vendor capture:"
echo "  python3 compare_usb_captures.py usb_captures/vendor_write_real_20251118_122703.pcap $CAPTURE_FILE"

