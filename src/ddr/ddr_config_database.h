/**
 * DDR Configuration Database - Embedded processor and DDR chip configurations
 *
 * This file contains embedded configurations for all supported Ingenic processors
 * and DDR memory chips, eliminating the need to distribute separate config files.
 */

#ifndef DDR_CONFIG_DATABASE_H
#define DDR_CONFIG_DATABASE_H

#include <stdint.h>
#include <stddef.h>

/**
 * Processor platform configuration
 */
typedef struct {
    const char *name;           // Platform name (e.g., "t31x", "t30", "t41")
    uint32_t crystal_freq;      // Crystal oscillator frequency (Hz)
    uint32_t cpu_freq;          // CPU frequency (Hz)
    uint32_t ddr_freq;          // DDR frequency (Hz)
    uint32_t uart_baud;         // UART baud rate
    uint32_t mem_size;          // Default memory size (bytes)
} processor_config_t;

/**
 * DDR chip timing configuration
 */
typedef struct {
    const char *name;           // Chip name (e.g., "M14D1G1664A_DDR2")
    const char *vendor;         // Vendor name (e.g., "ESMT", "Winbond")
    uint32_t ddr_type;          // 0=DDR3, 1=DDR2, 2=LPDDR2, 4=LPDDR3
    uint8_t row_bits;           // Number of row address bits
    uint8_t col_bits;           // Number of column address bits
    uint8_t cl;                 // CAS Latency (cycles)
    uint8_t bl;                 // Burst Length
    uint8_t rl;                 // Read Latency (cycles)
    uint8_t wl;                 // Write Latency (cycles)
    
    // Timing parameters (in picoseconds or cycles)
    uint32_t tRAS;              // Row Active Time (ps)
    uint32_t tRC;               // Row Cycle Time (ps)
    uint32_t tRCD;              // RAS to CAS Delay (ps)
    uint32_t tRP;               // Row Precharge Time (ps)
    uint32_t tRFC;              // Refresh Cycle Time (ps)
    uint32_t tRTP;              // Read to Precharge (ps)
    uint32_t tFAW;              // Four Bank Activate Window (ps)
    uint32_t tRRD;              // Row to Row Delay (ps)
    uint32_t tWTR;              // Write to Read Delay (ps)
    uint32_t tWR;               // Write Recovery Time (ps)
    uint32_t tREFI;             // Refresh Interval (ps)
    uint32_t tCKE;              // CKE minimum pulse width (cycles)
    uint32_t tXP;               // Exit power-down to command (cycles)
} ddr_chip_config_t;

/**
 * Get processor configuration by name
 * 
 * @param name Processor name (e.g., "t31x", "t30", "t41", "a1")
 * @return Pointer to processor config, or NULL if not found
 */
const processor_config_t* processor_config_get(const char *name);

/**
 * Get DDR chip configuration by name
 * 
 * @param name DDR chip name (e.g., "M14D1G1664A_DDR2", "W631GU6NG_DDR3")
 * @return Pointer to DDR chip config, or NULL if not found
 */
const ddr_chip_config_t* ddr_chip_config_get(const char *name);

/**
 * Get default DDR chip for a processor
 * 
 * @param processor_name Processor name (e.g., "t31x")
 * @return Pointer to default DDR chip config, or NULL if not found
 */
const ddr_chip_config_t* ddr_chip_config_get_default(const char *processor_name);

/**
 * List all available processor configurations
 * 
 * @param count Output parameter for number of processors
 * @return Array of processor configs
 */
const processor_config_t* processor_config_list(size_t *count);

/**
 * List all available DDR chip configurations
 * 
 * @param count Output parameter for number of DDR chips
 * @return Array of DDR chip configs
 */
const ddr_chip_config_t* ddr_chip_config_list(size_t *count);

/**
 * List DDR chips compatible with a specific DDR type
 * 
 * @param ddr_type DDR type (0=DDR3, 1=DDR2, 2=LPDDR2, 4=LPDDR3)
 * @param count Output parameter for number of matching chips
 * @return Array of matching DDR chip configs
 */
const ddr_chip_config_t** ddr_chip_config_list_by_type(uint32_t ddr_type, size_t *count);

#endif // DDR_CONFIG_DATABASE_H

