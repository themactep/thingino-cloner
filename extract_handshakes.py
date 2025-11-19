#!/usr/bin/env python3
"""Extract VR_WRITE (0x12) handshake bytes from vendor capture"""

import subprocess
import sys

def extract_handshakes(pcap_file):
    """Extract all VR_WRITE handshakes from pcap"""

    # Find all frames with bRequest == 0x12
    cmd = ['tshark', '-r', pcap_file, '-Y', 'usb.setup.bRequest == 0x12',
           '-T', 'fields', '-e', 'frame.number']
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"Error: {result.stderr}", file=sys.stderr)
        return

    frame_numbers = [int(x.strip()) for x in result.stdout.strip().split('\n') if x.strip()]
    print(f"Found {len(frame_numbers)} VR_WRITE (0x12) handshakes")
    print(f"Frame numbers: {frame_numbers}\n")

    for i, frame_num in enumerate(frame_numbers):
        # Extract the raw hex data for this frame using usb.data_fragment
        cmd = ['tshark', '-r', pcap_file, '-Y', f'frame.number == {frame_num}',
               '-T', 'fields', '-e', 'usb.data_fragment']
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0 and result.stdout.strip():
            hex_data = result.stdout.strip().replace(':', '')

            # Convert to bytes
            data_bytes = bytes.fromhex(hex_data)

            print(f"Handshake {i+1} (frame {frame_num}): {len(data_bytes)} bytes")

            # Print in groups of 8 bytes
            for j in range(0, len(data_bytes), 8):
                chunk = data_bytes[j:j+8]
                hex_str = ' '.join(f'{b:02X}' for b in chunk)
                print(f"  Bytes {j:2d}-{min(j+7, len(data_bytes)-1):2d}: {hex_str}")

            print()

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(f"Usage: {sys.argv[0]} <pcap_file>")
        sys.exit(1)
    
    extract_handshakes(sys.argv[1])

