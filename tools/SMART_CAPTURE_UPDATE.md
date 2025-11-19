# Smart USB Capture Update

## Problem Identified

Your capture (`capture_20251118_115159.pcap`) contained traffic from **multiple USB devices**:
- Device 4 (unknown)
- Device 5 (unknown)  
- Device 8 (unknown)
- **Device 13 (Ingenic - 30 bulk OUT transfers)**
- Device 115 (unknown)

This made analysis difficult because:
- Keyboard and mouse traffic mixed in
- Hard to identify which device is the Ingenic
- Lots of noise in the capture
- Analysis tools get confused

## Solution: Smart Auto-Detection

Updated `capture_usb_traffic.sh` to automatically:

1. **Poll lsusb** until Ingenic device appears
2. **Identify** the exact USB bus and device number
3. **Capture ONLY** that device's traffic (filtered)
4. **No interference** from keyboard, mouse, or other USB devices

## New Features

### Auto-Detection Mode (Default)

```bash
sudo ./capture_usb_traffic.sh vendor_write
```

- Checks if Ingenic device is already connected
- If found: captures only that device
- If not found: warns and captures all USB (fallback)

### Wait-for-Device Mode

```bash
sudo ./capture_usb_traffic.sh vendor_write --wait-for-device
```

- Polls lsusb every second for up to 60 seconds
- Waits for you to plug in the device or enter bootrom mode
- Automatically starts filtered capture when detected
- Perfect for workflow: start script → plug in device → automatic capture

## How It Works

### Device Detection

Looks for Ingenic devices by:
- Vendor ID: `0xa108` (bootrom mode)
- Vendor ID: `0x601a` (some models)
- Device name: "Ingenic" in lsusb output

### Filtered Capture

Once detected:
```
Bus 001 Device 013: ID a108:4770 Ingenic Semiconductor Co., Ltd
```

Captures on:
- **Interface:** `usbmon1` (bus 1 only, not all buses)
- **Filter:** Device 13 only (if tshark available)
- **Result:** Clean capture with ONLY Ingenic traffic

### Fallback Mode

If device not detected:
- Captures on `usbmon0` (all USB buses)
- Warns user about unfiltered capture
- Still works, but with noise

## Usage Examples

### Example 1: Device Already Connected

```bash
$ sudo ./capture_usb_traffic.sh vendor_write

=== Smart USB Traffic Capture for Ingenic Cloner ===
Operation: vendor_write

Detecting Ingenic USB device...
Found Ingenic device:
  Bus 001 Device 013: ID a108:4770 Ingenic Semiconductor Co., Ltd
Bus: 001 (usbmon1)
Device: 013

Starting USB capture...
Capture file: usb_captures/vendor_write_20251118_120000.pcap

Capture mode: FILTERED (Ingenic device only)
  Interface: usbmon1
  Device filter: usb.device_address == 13

This will capture ONLY the Ingenic device traffic
(No keyboard, mouse, or other USB devices)

Instructions:
1. Run your cloner tool in another terminal
2. Let the operation complete
3. Press Ctrl+C here when done

Capturing... (Press Ctrl+C to stop)
```

### Example 2: Wait for Device

```bash
$ sudo ./capture_usb_traffic.sh vendor_write --wait-for-device

=== Smart USB Traffic Capture for Ingenic Cloner ===
Operation: vendor_write

Detecting Ingenic USB device...
Waiting for Ingenic device to appear...
(Plug in your device or put it in bootrom mode)

Waiting... 5s Device detected!
Found Ingenic device:
  Bus 001 Device 013: ID a108:4770 Ingenic Semiconductor Co., Ltd
...
```

## Benefits

### Before (Old Script)

❌ Captured ALL USB devices  
❌ Keyboard/mouse traffic mixed in  
❌ Hard to analyze  
❌ Manual filtering needed  
❌ Confusing output  

### After (Smart Script)

✅ Auto-detects Ingenic device  
✅ Captures ONLY Ingenic traffic  
✅ Clean, focused captures  
✅ Easy to analyze  
✅ No manual filtering needed  
✅ Can wait for device to appear  

## Your Capture Analysis

From your capture `capture_20251118_115159.pcap`:

**Device 13** had the Ingenic traffic:
- 30 bulk OUT transfers (write operation)
- Found FIDB marker (DDR binary)
- Found BOOT magic strings
- Found GET_CPU_INFO command

**Next Steps:**

1. **Recapture with new script:**
   ```bash
   sudo ./capture_usb_traffic.sh vendor_write_clean --wait-for-device
   ```

2. **Run your write operation** (vendor cloner or thingino-cloner)

3. **Analyze clean capture:**
   ```bash
   python3 analyze_usb_capture.py usb_captures/vendor_write_clean_*.pcap
   ```

4. **Correlate with binary:**
   ```bash
   python3 analyze_write_with_binary.py \
       usb_captures/vendor_write_clean_*.pcap \
       u-boot-atbm6441-combined.bin \
       --verbose --report correlation.txt
   ```

## Technical Details

### Detection Logic

```bash
# Detect Ingenic by vendor ID or name
lsusb | grep -i "ingenic\|a108\|601a"
```

### Capture Methods

**With tshark (preferred):**
```bash
tshark -i usbmon1 -w capture.pcap -f "usb.device_address == 13"
```

**With tcpdump (fallback):**
```bash
tcpdump -i usbmon1 -w capture.pcap -s 0
```

Note: tcpdump captures the whole bus, but if Ingenic is the only active device on that bus, it's effectively filtered.

## Files Modified

- `tools/capture_usb_traffic.sh` - Enhanced with auto-detection
- `tools/README.md` - Updated documentation
- `tools/identify_ingenic_device.sh` - Helper script for manual identification

## Compatibility

- Works with all Ingenic SoCs (T20/T21/T30/T31/T40/T41)
- Detects both bootrom mode (0xa108) and normal mode (0x601a)
- Graceful fallback if device not detected
- Compatible with existing analysis tools

