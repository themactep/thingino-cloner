/**
 * DDR Binary Builder - Matches Python script format
 *
 * This implementation generates DDR configuration binaries in the format used by
 * Ingenic's cloner tool. The format was reverse-engineered from working binaries
 * extracted via tcpdump and analyzed with Ghidra.
 *
 * Binary Format (324 bytes total):
 * - FIDB section (192 bytes): Platform configuration
 * - RDD section (132 bytes): DDR PHY parameters
 *
 * References:
 * - references/ddr_compiler_final.py (Python implementation)
 * - references/ddr_extracted.bin (Reference binary from working device)
 * - references/cloner-2.5.43-ubuntu_thingino/ddrs/ (DDR config files)
 */

#ifndef DDR_BINARY_BUILDER_H
#define DDR_BINARY_BUILDER_H

#include <stdint.h>
#include <stddef.h>

// Binary format constants
#define DDR_BINARY_SIZE 324  // Total size: FIDB (192 bytes) + RDD (132 bytes)

/**
 * Platform configuration for FIDB section (192 bytes: 8-byte header + 184-byte data)
 *
 * FIDB = "Firmware Information Data Block" (reverse-engineered name)
 *
 * Layout (file offsets):
 *   0x00-0x03: "FIDB" magic marker
 *   0x04-0x07: Size (184 bytes = 0xB8)
 *   0x08-0x0B: Crystal frequency (Hz) - e.g., 24000000 (24 MHz)
 *   0x0C-0x0F: CPU frequency (Hz) - e.g., 576000000 (576 MHz)
 *   0x10-0x13: DDR frequency (Hz) - e.g., 400000000 (400 MHz)
 *   0x14-0x17: Reserved (0x00000000)
 *   0x18-0x1B: Enable flag (0x00000001)
 *   0x1C-0x1F: UART baud rate - e.g., 115200
 *   0x20-0x23: Flag (0x00000001)
 *   0x28-0x2B: Memory size (bytes) - e.g., 8388608 (8 MB)
 *   0x2C-0x2F: Flag (0x00000001)
 *   0x34-0x37: Flag (0x00000011)
 *   0x38-0x3B: Platform ID (0x19800000) - T31-specific?
 *   0x3C-0xBF: Reserved/padding (zeros)
 *
 * Source: Reverse-engineered from references/ddr_extracted.bin
 */
typedef struct {
    uint32_t crystal_freq;  // Crystal oscillator frequency in Hz (typically 24 MHz)
    uint32_t cpu_freq;      // CPU frequency in Hz (e.g., 576 MHz for T31)
    uint32_t ddr_freq;      // DDR memory frequency in Hz (e.g., 400 MHz)
    uint32_t uart_baud;     // UART baud rate for bootloader console (typically 115200)
    uint32_t mem_size;      // Total DDR memory size in bytes (e.g., 8 MB = 8388608)
} platform_config_t;

/**
 * DDR PHY parameters for RDD section (132 bytes: 8-byte header + 124-byte data)
 *
 * RDD = "RAM Device Descriptor" (reverse-engineered name)
 *
 * Layout (file offsets from 0xC0):
 *   0xC0-0xC3: Header (0x00 + "RDD")
 *   0xC4-0xC7: Size (124 bytes = 0x7C)
 *   0xC8-0xCB: CRC32 checksum (calculated over bytes 0xCC-0x143)
 *   0xCC-0xCF: DDR type (RDD format encoding):
 *                0 = DDR3
 *                1 = DDR2
 *                2 = LPDDR2 / LPDDR
 *                4 = LPDDR3
 *              NOTE: Different from DDRC CFG register (6=DDR3, 4=DDR2, 5=LPDDR2, 3=LPDDR)
 *              NOTE: Different from DDRP DCR register (3=DDR3, 2=DDR2, 4=LPDDR2, 0=LPDDR)
 *              See references/ddr_compiler_final.py line 351 for RDD encoding
 *   0xD0-0xD7: Reserved (zeros)
 *   0xD8-0xDB: Frequency value (ddr_freq / 100000) - e.g., 4000 for 400 MHz
 *   0xDC-0xDF: Frequency value 2 (0x00002800 = 10240) - purpose unknown, possibly tREFI-related
 *   0xE0-0xE3: Fixed values (0x01, 0x00, 0xC2, 0x00) - purpose unknown
 *   0xE4:      CL (CAS Latency) - e.g., 6 or 7 for DDR2
 *   0xE5:      BL (Burst Length) - typically 8 for DDR2/DDR3
 *   0xE6:      ROW bits (stored directly) - e.g., 13
 *                NOTE: Different from DDRC CFG register which uses (row - 12)
 *   0xE7:      COL bits (encoded as col_bits - 6) - e.g., 4 for 10 columns
 *                NOTE: Different from DDRC CFG register which uses (col - 8)
 *   0xE8:      tRAS (Active to Precharge delay, in cycles)
 *   0xE9:      tRC (Active to Active/Refresh delay, in cycles)
 *   0xEA:      tRCD (RAS to CAS delay, in cycles)
 *   0xEB:      tRP (Precharge command period, in cycles)
 *   0xEC:      tRFC (Refresh cycle time, in cycles)
 *   0xED:      Unknown (0x04) - purpose unknown
 *   0xEE:      tRTP (Read to Precharge, in cycles)
 *   0xEF:      Unknown (0x20 = 32) - purpose unknown
 *   0xF0:      tFAW (Four Activate Window, in cycles)
 *   0xF1:      Unknown (0x00) - purpose unknown
 *   0xF2:      tRRD (Active bank A to Active bank B, in cycles)
 *   0xF3:      tWTR (Write to Read delay, in cycles)
 *   0xF4-0x12F: Reserved/unknown fields
 *   0x130-0x143: DQ mapping table (20 bytes) - maps logical DQ pins to physical pins
 *                Default: {12,13,14,3,4,5,6,7,8,9,10,11,0,1,2,15,16,17,18,19}
 *                This is board/hardware-specific and may need customization
 *
 * NOTE: This RDD format is NOT the same as DDRC/DDRP hardware registers!
 *       The DDRC CFG register uses different encoding:
 *       - ROW: stored as (row_bits - 12)
 *       - COL: stored as (col_bits - 8)
 *       See references/ingenic-u-boot-xburst1/tools/ingenic-tools/ddr_params_creator.c
 *       lines 192-208 for DDRC register generation
 *
 * Timing Calculation:
 *   Most timing values are calculated using: ps2cycle_ceil(time_ps, ps_per_tck)
 *   where ps2cycle_ceil(ps, ps_per_tck) = (ps + ps_per_tck - 1) / ps_per_tck
 *
 *   Exception: tRFC uses ps2cycle_ceil with div_tck=2, then divides result by 2:
 *   tRFC = ((time_ps + 2*ps_per_tck - 1) / ps_per_tck) / 2
 *
 *   This formula is documented in:
 *   references/ingenic-u-boot-xburst1/tools/ingenic-tools/ddr_params_creator.c
 *   lines 21-24 (ps2cycle_ceil function) and line 132 (tRFC calculation)
 *
 * Source:
 *   - Reverse-engineered from references/ddr_extracted.bin
 *   - references/ddr_compiler_final.py (Python implementation)
 *   - references/ingenic-u-boot-xburst1/tools/ingenic-tools/ddr_params_creator.c
 *     (Official Ingenic u-boot DDR parameter creator tool)
 */
typedef struct {
    // DDR type (RDD format encoding - different from DDRC/DDRP registers!)
    // 0=DDR3, 1=DDR2, 2=LPDDR2/LPDDR, 4=LPDDR3
    // See references/ddr_compiler_final.py line 351 for mapping
    uint32_t ddr_type;

    // Memory geometry (from config file)
    uint8_t row_bits;       // ROW field - number of row address bits (e.g., 13)
    uint8_t col_bits;       // COL field - number of column address bits (e.g., 10)
    uint8_t cl;             // CL field - CAS Latency in cycles (e.g., 6 or 7 for DDR2)
    uint8_t bl;             // BL field - Burst Length (typically 8 for DDR2/DDR3)

    // Timing parameters in clock cycles (calculated from config file timing values)
    // All values from config are in ps (picoseconds) or ns (nanoseconds)
    uint8_t tRAS;           // tRAS field - Active to Precharge delay
    uint8_t tRC;            // tRC field - Active to Active/Refresh delay
    uint8_t tRCD;           // tRCD field - RAS to CAS delay
    uint8_t tRP;            // tRP field - Precharge command period
    uint8_t tRFC;           // tRFC field - Refresh cycle time (special calculation)
    uint8_t tRTP;           // tRTP field - Read to Precharge
    uint8_t tFAW;           // tFAW field - Four Activate Window
    uint8_t tRRD;           // tRRD field - Active bank A to Active bank B
    uint8_t tWTR;           // tWTR field - Write to Read delay
} ddr_phy_params_t;

/**
 * Build FIDB section (192 bytes: 8-byte header + 184-byte data)
 *
 * Generates the platform configuration section with:
 * - Magic marker "FIDB"
 * - Platform frequencies (crystal, CPU, DDR)
 * - UART configuration
 * - Memory size
 * - Various flags (reverse-engineered, purpose partially unknown)
 *
 * @param platform Platform configuration structure
 * @param output Output buffer (must be at least 192 bytes)
 * @return Number of bytes written (always 192)
 */
size_t ddr_build_fidb(const platform_config_t *platform, uint8_t *output);

/**
 * Build RDD section (132 bytes: 8-byte header + 124-byte data)
 *
 * Generates the DDR PHY parameters section with:
 * - Magic marker "RDD" (with 0x00 prefix)
 * - CRC32 checksum
 * - DDR type and geometry (row/col bits, CL, BL)
 * - Timing parameters (tRAS, tRC, tRCD, tRP, tRFC, etc.)
 * - DQ pin mapping table (hardware-specific)
 *
 * Note: Contains several hardcoded values that were reverse-engineered
 * from working binaries. These may be hardware or platform-specific.
 *
 * @param platform Platform configuration (used for DDR frequency)
 * @param params DDR PHY parameters (geometry and timing)
 * @param output Output buffer (must be at least 132 bytes)
 * @return Number of bytes written (always 132)
 */
size_t ddr_build_rdd(const platform_config_t *platform, const ddr_phy_params_t *params, uint8_t *output);

/**
 * Build complete DDR binary (324 bytes = 192 FIDB + 132 RDD)
 *
 * Generates a complete DDR configuration binary in the format expected by
 * Ingenic's bootloader/cloner tool. The binary can be uploaded to the device
 * during the bootstrap process.
 *
 * Binary structure:
 *   Offset 0x000-0x0BF: FIDB section (platform config)
 *   Offset 0x0C0-0x143: RDD section (DDR PHY params)
 *
 * @param platform Platform configuration
 * @param params DDR PHY parameters
 * @param output Output buffer (must be at least 324 bytes)
 * @return Number of bytes written (always 324)
 */
size_t ddr_build_binary(const platform_config_t *platform, const ddr_phy_params_t *params, uint8_t *output);

/**
 * Get default platform configuration for a given Ingenic SoC
 *
 * Returns default values for:
 * - Crystal frequency (24 MHz for all platforms)
 * - CPU frequency (576 MHz for T30/T31/T41)
 * - DDR frequency (400 MHz default)
 * - UART baud rate (115200)
 * - Memory size (8 MB default)
 *
 * These defaults match the values found in reference binaries but may need
 * adjustment for specific hardware configurations.
 *
 * @param platform_name Platform name ("t31", "t30", "t41", or NULL for default)
 * @param config Output platform configuration structure
 * @return 0 on success, -1 on error (NULL pointer)
 */
int ddr_get_platform_config(const char *platform_name, platform_config_t *config);

/**
 * Get default platform configuration for a processor variant
 *
 * This is a convenience wrapper around ddr_get_platform_config() that accepts
 * processor_variant_t enum values from the main thingino codebase.
 *
 * @param variant Processor variant enum (VARIANT_T31X, VARIANT_T31ZX, etc.)
 * @param config Output platform configuration structure
 * @return 0 on success, -1 on error (unsupported variant or NULL pointer)
 */
int ddr_get_platform_config_by_variant(int variant, platform_config_t *config);

#endif // DDR_BINARY_BUILDER_H

