# Embedded Configuration Database

## Overview

The thingino-cloner tool now includes an embedded configuration database that eliminates the need to distribute separate configuration files. All processor and DDR chip configurations are compiled directly into the binary.

## Features

- **17 Processor Configurations**: A-series (A1, A1NE, A1NT) and T-series processors (T20, T21, T23, T30, T31, T40, T41 and variants)
- **12 DDR Chip Configurations**: Common DDR2, DDR3, LPDDR2, and LPDDR3 chips
- **Automatic Defaults**: Each processor has a default DDR chip configuration
- **Zero External Files**: No need to distribute .cfg files or DDR parameter files
- **Easy Extension**: Simple to add new processors or DDR chips

## Supported Processors

| Processor | Crystal | CPU Freq | DDR Freq | Memory | Default DDR Chip |
|-----------|---------|----------|----------|--------|------------------|
| A1        | 24 MHz  | 800 MHz  | 400 MHz  | 16 MB  | M15T1G1664A_DDR3 |
| A1NE      | 24 MHz  | 800 MHz  | 400 MHz  | 16 MB  | M15T1G1664A_DDR3 |
| A1NT      | 24 MHz  | 800 MHz  | 400 MHz  | 16 MB  | W632GU6NG_DDR3   |
| T20       | 24 MHz  | 600 MHz  | 200 MHz  | 8 MB   | W9751V6NG_DDR2   |
| T21       | 24 MHz  | 1000 MHz | 300 MHz  | 16 MB  | W9751V6NG_DDR2   |
| T23       | 24 MHz  | 1200 MHz | 300 MHz  | 16 MB  | M14D1G1664A_DDR2 |
| T30       | 24 MHz  | 576 MHz  | 400 MHz  | 8 MB   | M14D1G1664A_DDR2 |
| T30A      | 24 MHz  | 576 MHz  | 400 MHz  | 16 MB  | W631GU6NG_DDR3   |
| T30NL     | 24 MHz  | 576 MHz  | 400 MHz  | 8 MB   | M14D1G1664A_DDR2 |
| T30X      | 24 MHz  | 576 MHz  | 400 MHz  | 8 MB   | M14D1G1664A_DDR2 |
| T31       | 24 MHz  | 576 MHz  | 400 MHz  | 8 MB   | M14D1G1664A_DDR2 |
| T31X      | 24 MHz  | 576 MHz  | 400 MHz  | 8 MB   | M14D1G1664A_DDR2 |
| T31ZX     | 24 MHz  | 576 MHz  | 400 MHz  | 8 MB   | M14D1G1664A_DDR2 |
| T31A      | 24 MHz  | 576 MHz  | 400 MHz  | 16 MB  | W631GU6NG_DDR3   |
| T31NL     | 24 MHz  | 576 MHz  | 400 MHz  | 8 MB   | M14D1G1664A_DDR2 |
| T40       | 24 MHz  | 1000 MHz | 400 MHz  | 16 MB  | W631GU6NG_DDR3   |
| T41       | 24 MHz  | 800 MHz  | 600 MHz  | 32 MB  | H5TQ2G83CFR_DDR3 |

## Supported DDR Chips

### DDR2 Chips
- **M14D1G1664A_DDR2** (ESMT) - 13 row, 10 col, CL=7
- **M14D5121632A_DDR2** (ESMT) - 13 row, 9 col, CL=6
- **M14D2561616A_DDR2** (ESMT) - 13 row, 10 col, CL=6
- **W971GV6NG_DDR2** (Winbond) - 13 row, 10 col, CL=6
- **W9751V6NG_DDR2** (Winbond) - 13 row, 9 col, CL=6

### DDR3 Chips
- **W631GU6NG_DDR3** (Winbond) - 13 row, 10 col, CL=11
- **H5TQ1G83DFR_DDR3** (Hynix) - 13 row, 10 col, CL=11
- **H5TQ2G83CFR_DDR3** (Hynix) - 14 row, 10 col, CL=11
- **M15T1G1664A_DDR3** (ESMT) - 13 row, 10 col, CL=11
- **W632GU6NG_DDR3** (Winbond) - 14 row, 10 col, CL=11

### LPDDR2 Chips
- **W94AD6KB_LPDDR2** (Winbond) - 13 row, 10 col, CL=6

### LPDDR3 Chips
- **W63CH2MBVABE_LPDDR3** (Winbond) - 14 row, 10 col, CL=12

## API Usage

### Get Processor Configuration

```c
#include "ddr_config_database.h"

const processor_config_t *proc = processor_config_get("t31x");
if (proc) {
    printf("CPU: %u Hz, DDR: %u Hz\n", proc->cpu_freq, proc->ddr_freq);
}
```

### Get DDR Chip Configuration

```c
const ddr_chip_config_t *ddr = ddr_chip_config_get("M14D1G1664A_DDR2");
if (ddr) {
    printf("Type: %u, ROW: %u, COL: %u\n", 
           ddr->ddr_type, ddr->row_bits, ddr->col_bits);
}
```

### Get Default DDR for Processor

```c
const ddr_chip_config_t *default_ddr = ddr_chip_config_get_default("t31x");
// Returns M14D1G1664A_DDR2 for T31X
```

### List All Configurations

```c
size_t count;
const processor_config_t *processors = processor_config_list(&count);
for (size_t i = 0; i < count; i++) {
    printf("%s: %u MHz\n", processors[i].name, processors[i].cpu_freq);
}
```

## Adding New Configurations

### Add a New Processor

Edit `src/ddr/ddr_config_database.c` and add to `processor_configs[]`:

```c
{
    .name = "t50",
    .crystal_freq = 24000000,
    .cpu_freq = 1200000000,
    .ddr_freq = 800000000,
    .uart_baud = 115200,
    .mem_size = 64 * 1024 * 1024  // 64 MB
},
```

### Add a New DDR Chip

Add to `ddr_chip_configs[]`:

```c
{
    .name = "NEW_CHIP_DDR3",
    .vendor = "Vendor",
    .ddr_type = 0,  // DDR3
    .row_bits = 14,
    .col_bits = 10,
    .cl = 11,
    .bl = 8,
    .rl = 11,
    .wl = 8,
    .tRAS = 35000,
    .tRC = 48750,
    // ... other timing parameters
},
```

### Set Default DDR for Processor

Add to `default_ddr_mappings[]`:

```c
{"t50", "NEW_CHIP_DDR3"},
```

## Benefits

1. **Single Binary Distribution**: No need to package config files
2. **Faster Startup**: No file I/O for configuration loading
3. **Guaranteed Availability**: Configs always present, can't be lost or corrupted
4. **Type Safety**: Compile-time checking of configuration values
5. **Easy Maintenance**: All configs in one place

## Testing

Run the configuration database test:

```bash
./build/test_config_database
```

This will display all available processors and DDR chips, and test binary generation with different combinations.

## Future Enhancements

- Add more DDR chip variants (Samsung, Micron, etc.)
- Support for A-series processors (A1, AD100, etc.)
- Runtime configuration override via command-line
- Export configurations to JSON/YAML for documentation

