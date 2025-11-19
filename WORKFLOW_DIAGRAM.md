# USB Capture Framework - Workflow Diagram

## Complete Write Implementation Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: CAPTURE VENDOR TRAFFIC                  │
└─────────────────────────────────────────────────────────────────────┘

    Terminal 1                          Terminal 2
    ┌──────────────┐                   ┌──────────────┐
    │ Start Capture│                   │ Run Vendor   │
    │              │                   │ Cloner Tool  │
    │ sudo ./      │                   │              │
    │ capture_usb_ │                   │ sudo ./cloner│
    │ traffic.sh   │◄──────────────────┤ --config ... │
    │ vendor_write │   USB Traffic     │              │
    │              │                   │              │
    └──────┬───────┘                   └──────────────┘
           │
           ▼
    ┌──────────────┐
    │ vendor_write_│
    │ TIMESTAMP.   │
    │ pcap         │
    └──────┬───────┘
           │
           │
┌──────────┴────────────────────────────────────────────────────────┐
│                    PHASE 2: ANALYZE CAPTURE                       │
└───────────────────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────────────────────────┐
    │ python3 analyze_write_operation.py                   │
    │         vendor_write_*.pcap --extract-sequence       │
    └──────────────────────────────────────────────────────┘
           │
           ├─────────────────┬─────────────────┬──────────────────┐
           ▼                 ▼                 ▼                  ▼
    ┌──────────┐      ┌──────────┐     ┌──────────┐      ┌──────────┐
    │ Console  │      │ write_   │     │ write_   │      │extracted_│
    │ Analysis │      │ sequence.│     │ sequence.│      │ data/    │
    │          │      │ c        │     │ py       │      │          │
    │ - Address│      │          │     │          │      │ - DDR    │
    │ - Size   │      │ C code   │     │ Python   │      │ - SPL    │
    │ - Commands│     │ template │     │ template │      │ - U-Boot │
    └──────────┘      └──────────┘     └──────────┘      └──────────┘
           │
           │
┌──────────┴────────────────────────────────────────────────────────┐
│                    PHASE 3: IMPLEMENT IN CODE                     │
└───────────────────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────────────────────────┐
    │ Review write_sequence.c                              │
    │                                                      │
    │ Identify:                                            │
    │ - Command sequence (SET_ADDR → SET_LEN → BULK_OUT)  │
    │ - Parameters (address, size, chunk size)            │
    │ - Status checks (if any)                            │
    │ - Timing requirements                               │
    └──────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────────────────────────┐
    │ Edit src/usb/protocol.c                              │
    │                                                      │
    │ Update:                                              │
    │ - protocol_proper_firmware_write()                   │
    │ - Add missing vendor requests                        │
    │ - Match command sequence exactly                     │
    │ - Add proper error handling                          │
    └──────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────────────────────────┐
    │ Rebuild thingino-cloner                              │
    │                                                      │
    │ cd build                                             │
    │ make                                                 │
    └──────────────────────────────────────────────────────┘
           │
           │
┌──────────┴────────────────────────────────────────────────────────┐
│                    PHASE 4: TEST & VALIDATE                       │
└───────────────────────────────────────────────────────────────────┘
           │
           ▼
    Terminal 1                          Terminal 2
    ┌──────────────┐                   ┌──────────────┐
    │ Start Capture│                   │ Run Thingino │
    │              │                   │ Cloner       │
    │ sudo ./      │                   │              │
    │ capture_usb_ │                   │ sudo ./      │
    │ traffic.sh   │◄──────────────────┤ thingino-    │
    │ thingino_    │   USB Traffic     │ cloner       │
    │ write        │                   │ --write ...  │
    └──────┬───────┘                   └──────────────┘
           │
           ▼
    ┌──────────────┐
    │ thingino_    │
    │ write_       │
    │ TIMESTAMP.   │
    │ pcap         │
    └──────┬───────┘
           │
           │
┌──────────┴────────────────────────────────────────────────────────┐
│                    PHASE 5: COMPARE CAPTURES                      │
└───────────────────────────────────────────────────────────────────┘
           │
           ▼
    ┌──────────────────────────────────────────────────────┐
    │ python3 compare_usb_captures.py                      │
    │         vendor_write_*.pcap                          │
    │         thingino_write_*.pcap                        │
    └──────────────────────────────────────────────────────┘
           │
           ├─────────────────┬─────────────────┐
           ▼                 ▼                 ▼
    ┌──────────┐      ┌──────────┐     ┌──────────┐
    │ Summary  │      │ Detailed │     │ Hex Dump │
    │          │      │ Diff     │     │ of Data  │
    │ - Total  │      │          │     │ Diffs    │
    │   diffs  │      │ - Command│     │          │
    │ - Types  │      │   diffs  │     │          │
    │          │      │ - Param  │     │          │
    │          │      │   diffs  │     │          │
    └──────────┘      └──────────┘     └──────────┘
           │
           │
           ▼
    ┌──────────────────────────────────────────────────────┐
    │              Are captures identical?                 │
    └──────────────────────────────────────────────────────┘
           │
           ├─────────YES──────┐         ┌────NO─────┐
           │                  │         │           │
           ▼                  ▼         ▼           │
    ┌──────────┐      ┌──────────┐  ┌──────────┐  │
    │ SUCCESS! │      │ Test on  │  │ Review   │  │
    │          │      │ Real     │  │ Diffs    │  │
    │ Write    │      │ Hardware │  │          │  │
    │ protocol │      │          │  │ Update   │  │
    │ correct  │      │          │  │ Code     │──┘
    └──────────┘      └──────────┘  └──────────┘
                                           │
                                           │
                                    Back to PHASE 3


┌─────────────────────────────────────────────────────────────────────┐
│                    QUICK WORKFLOW (AUTOMATED)                       │
└─────────────────────────────────────────────────────────────────────┘

    ┌──────────────────────────────────────────────────────┐
    │ sudo ./quick_write_analysis.sh vendor_write          │
    └──────────────────────────────────────────────────────┘
           │
           │ (Automatically runs PHASE 1 & 2)
           │
           ▼
    ┌──────────────────────────────────────────────────────┐
    │ Output:                                              │
    │ - vendor_write_TIMESTAMP.pcap                        │
    │ - vendor_write_sequence.c                            │
    │ - vendor_write_sequence.py                           │
    │ - extracted_vendor_write/                            │
    └──────────────────────────────────────────────────────┘
           │
           │ (Continue with PHASE 3)
           ▼
```

## Tool Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                         TOOL ECOSYSTEM                          │
└─────────────────────────────────────────────────────────────────┘

    capture_usb_traffic.sh
           │
           │ Produces
           ▼
    *.pcap files
           │
           ├──────────────────┬──────────────────┬──────────────┐
           │                  │                  │              │
           ▼                  ▼                  ▼              ▼
    analyze_usb_      analyze_write_     compare_usb_    Wireshark
    capture.py        operation.py       captures.py     (manual)
           │                  │                  │
           │                  │                  │
           ▼                  ▼                  ▼
    - Summary          - C code          - Diff report
    - Detailed log     - Python code     - Side-by-side
    - Extracted data   - Sequence info   - Hex dumps
```

## Data Flow

```
Vendor Cloner ──USB──► usbmon ──► tcpdump ──► .pcap ──► tshark ──► Python ──► Analysis
                                                                              │
Thingino      ──USB──► usbmon ──► tcpdump ──► .pcap ──► tshark ──► Python ──┤
                                                                              │
                                                                              ▼
                                                                         Comparison
                                                                              │
                                                                              ▼
                                                                         Refinement
                                                                              │
                                                                              ▼
                                                                    Updated thingino-cloner
```

