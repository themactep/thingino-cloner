#!/usr/bin/env python3
"""
Auto-generated write sequence from USB capture
Source: usb_captures/vendor_write_real_20251118_122703.pcap
"""

import usb.core
import usb.util

def write_sequence_1(dev, data):
    """Write sequence #1
    Flash Address: 0x00020100
    Data Size: Unknown
    """
    # Step 1: SET_DATA_ADDR
    dev.ctrl_transfer(0x22, 0x01, 0x0100, 0x0002, b'')

    # Step 2: Bulk OUT transfer (12 bytes)
    dev.write(0x02, data)

    # Step 3: Bulk OUT transfer (12 bytes)
    dev.write(0x02, data)

    # Step 4: Bulk OUT transfer (0 bytes)
    dev.write(0x02, data)

    # Step 5: Bulk OUT transfer (0 bytes)
    dev.write(0x02, data)

    # Step 6: Bulk OUT transfer (12 bytes)
    dev.write(0x02, data)

    # Step 7: Bulk OUT transfer (0 bytes)
    dev.write(0x02, data)

    # Step 8: Bulk OUT transfer (12 bytes)
    dev.write(0x02, data)

    # Step 9: Bulk OUT transfer (0 bytes)
    dev.write(0x02, data)

    return True

def write_sequence_2(dev, data):
    """Write sequence #2
    Flash Address: 0x10008000
    Data Size: 21233664 bytes
    """
    # Step 1: SET_DATA_ADDR
    dev.ctrl_transfer(0x40, 0x01, 0x8000, 0x1000, b'')

    # Step 2: SET_DATA_LEN
    dev.ctrl_transfer(0x40, 0x02, 0x0000, 0x0144, b'')

    # Step 3: Bulk OUT transfer (324 bytes)
    dev.write(0x01, data)

    # Step 4: Bulk OUT transfer (0 bytes)
    dev.write(0x01, data)

    return True

def write_sequence_3(dev, data):
    """Write sequence #3
    Flash Address: 0x18008000
    Data Size: 1879048192 bytes
    """
    # Step 1: SET_DATA_ADDR
    dev.ctrl_transfer(0x40, 0x01, 0x8000, 0x1800, b'')

    # Step 2: SET_DATA_LEN
    dev.ctrl_transfer(0x40, 0x02, 0x0000, 0x276C, b'')

    # Step 3: Bulk OUT transfer (10092 bytes)
    dev.write(0x01, data)

    # Step 4: Bulk OUT transfer (0 bytes)
    dev.write(0x01, data)

    # Step 5: SET_DATA_LEN
    dev.ctrl_transfer(0x40, 0x02, 0x0000, 0x7000, b'')

    return True

def write_sequence_4(dev, data):
    """Write sequence #4
    Flash Address: 0x00008010
    Data Size: 4119068677 bytes
    """
    # Step 1: SET_DATA_ADDR
    dev.ctrl_transfer(0x40, 0x01, 0x8010, 0x0000, b'')

    # Step 2: SET_DATA_LEN
    dev.ctrl_transfer(0x40, 0x02, 0x0005, 0xF584, b'')

    # Step 3: Bulk OUT transfer (245760 bytes)
    dev.write(0x01, data)

    # Step 4: Bulk OUT transfer (0 bytes)
    dev.write(0x01, data)

    # Step 5: FLUSH_CACHE
    dev.ctrl_transfer(0x40, 0x03, 0x0000, 0x0000, b'')

    return True

