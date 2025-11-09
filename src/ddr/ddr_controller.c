#include "ddr_controller.h"
#include "ddr_utils.h"
#include <string.h>
#include <stdio.h>

// Helper: Initialize object buffer with config values at vendor source offsets
// Based on vendor tool decompilation at 0x00448af0 (ddrc_generate_register)
void ddr_init_object_buffer(const ddr_config_t *config, uint8_t *obj_buffer) {
    // Store config values at the offsets that vendor functions read from
    // These are input values used by ddrc_generate_register and ddrp_generate_register
    
    // From ddrc_generate_register decompilation:
    *(int *)(obj_buffer + 0x1a4) = config->tWR;      // tWR (Write Recovery)
    *(int *)(obj_buffer + 0x1c0) = config->tWL;      // WL (Write Latency)
    *(int *)(obj_buffer + 0x194) = config->tRAS;     // tRAS (Row Active Time)
    *(int *)(obj_buffer + 0x19c) = config->tRCD;     // tRCD (Row to Column)
    *(int *)(obj_buffer + 0x1bc) = config->tRL;      // tRL (Read Latency)
    *(int *)(obj_buffer + 0x198) = config->tRP;      // tRP (Row Precharge)
    *(int *)(obj_buffer + 0x1a8) = config->tRRD;     // tRRD (Row to Row Delay)
    *(int *)(obj_buffer + 0x1a0) = config->tRC;      // tRC (Row Cycle)
    *(int *)(obj_buffer + 0x1b0) = config->tRFC;     // tRFC (Refresh to Active)
    *(int *)(obj_buffer + 0x1b8) = config->tCKE;     // tCKE (Clock Enable)
    *(int *)(obj_buffer + 0x1b4) = config->tXP;      // tXP (Power Down Exit)
    *(int *)(obj_buffer + 0x1c4) = config->tREFI;    // tREFI (Refresh Interval in ns)
    
    // From ddrp_generate_register decompilation:
    *(uint32_t *)(obj_buffer + 0x26c) = config->clock_mhz;  // Clock MHz
    *(int *)(obj_buffer + 0x188) = config->cas_latency;     // CAS Latency
    *(uint32_t *)(obj_buffer + 0x154) = config->type;       // DDR Type

    // Clock period in picoseconds (for ps2cycle calculations)
    // clock_period_ps = 1,000,000 / clock_mhz
    uint32_t clock_period_ps = 1000000 / config->clock_mhz;
    *(uint32_t *)(obj_buffer + 0x22c) = clock_period_ps;

    // Note: 0x270 is INI config (we set to 0, meaning use defaults)
    *(uint32_t *)(obj_buffer + 0x270) = 0;

    // Initialize ddr_params structure at obj[0x118+]
    // Based on exact Ghidra decompilation - param_3 in ddrc_config_creator points to class offset 0x118
    uint32_t *params = (uint32_t *)(obj_buffer + 0x118);
    uint32_t data_width = config->data_width;
    uint32_t row_bits = config->row_bits;
    uint32_t col_bits = config->col_bits;

    // DDR type: 0=LPDDR, 1=DDR, 4=DDR2, etc.
    uint32_t ddr_type = (config->type == DDR_TYPE_DDR2) ? 4 : (uint32_t)config->type;

    params[0] = ddr_type;                    // obj[0x118 + 0x00] - DDR type
    params[1] = 0;                           // obj[0x118 + 0x04] - Reserved
    params[2] = 0;                           // obj[0x118 + 0x08] - Reserved
    params[3] = 1;                           // obj[0x118 + 0x0c] = obj[0x124] - CS0 enable
    params[4] = 0;                           // obj[0x118 + 0x10] = obj[0x128] - CS1 enable
    params[5] = (data_width == 32) ? 1 : 0;  // obj[0x118 + 0x14] = obj[0x12c] - Data width (0=16-bit, 1=32-bit)
    params[6] = 0;                           // obj[0x118 + 0x18] = obj[0x130] - Reserved
    params[7] = 0;                           // obj[0x118 + 0x1c] = obj[0x134] - Reserved
    params[8] = 8;                           // obj[0x118 + 0x20] = obj[0x138] - Burst length (4 or 8)
    // TXX-specific encoding: COL0 = col_bits - 4, ROW0 = row_bits - 11
    // The formula (row0 * 8 + 0x20) & 0x38 transforms row0 to the output ROW0 field
    // This is different from standard U-Boot (COL0 = col_bits - 8, ROW0 = row_bits - 12)
    params[9] = col_bits - 4;                // obj[0x118 + 0x24] = obj[0x13c] - COL0 (col_bits - 4 for TXX)
    params[10] = row_bits - 11;              // obj[0x118 + 0x28] = obj[0x140] - ROW0 (row_bits - 11 for TXX)
    params[0xb] = col_bits - 4;              // obj[0x118 + 0x2c] = obj[0x144] - COL1 (same as COL0 for single CS)
    params[0xc] = row_bits - 11;             // obj[0x118 + 0x30] = obj[0x148] - ROW1 (same as ROW0 for single CS)
    params[0xd] = 1;                         // obj[0x118 + 0x34] = obj[0x14c] - Bank bits (0=4 banks, 1=8 banks)
    params[0xe] = 0;                         // obj[0x118 + 0x38] = obj[0x150] - CS0 memory size (will be calculated)
    params[0xf] = 0;                         // obj[0x118 + 0x3c] = obj[0x154] - CS1 memory size

    // Calculate CS0 and CS1 memory sizes in MB (not bytes!)
    // memsize = (1 << row_bits) * (1 << col_bits) * (1 << bank_bits) * data_width / 8 / 1024 / 1024
    uint32_t cs0_size_mb = (1 << row_bits) * (1 << col_bits) * 8 * (data_width / 8) / 1024 / 1024;
    uint32_t cs1_size_mb = 0;  // Assume single CS for now

    params[0xe] = cs0_size_mb;               // obj[0x118 + 0x38] = obj[0x150] - CS0 size in MB
    params[0xf] = cs1_size_mb;               // obj[0x118 + 0x3c] = obj[0x154] - CS1 size in MB
}

int ddr_generate_ddrc_with_object(const ddr_config_t *config, uint8_t *obj_buffer, uint8_t *ddrc_regs) {
    uint32_t clock_mhz = config->clock_mhz;
    int errors = 0;

    // Initialize DDRC register buffer (188 bytes = 0xbc)
    // We'll populate this with calculated register values
    memset(ddrc_regs, 0, 0xbc);

    // Ensure buffer is large enough for all intermediate offsets
    // The vendor object is at least 0x20c bytes, but we're only filling what's needed
    if (obj_buffer == NULL) return -1;

    // ========================================
    // DDRC SECTION GENERATION
    // ========================================
    // The DDRC section (file 0x08-0xBF, 184 bytes) should be generated using
    // the U-Boot ddrc_config_creator algorithm, NOT the TXX mapping!
    // The TXX mapping only applies to the DDRP section.
    //
    // Based on Ingenic U-Boot tools/ingenic-tools/ddr_params_creator.c
    // The DDRC section contains a serialized struct ddrc_reg:
    //   - cfg (4 bytes)
    //   - ctrl (4 bytes)
    //   - refcnt (4 bytes)
    //   - mmap[2] (8 bytes)
    //   - remap[5] (20 bytes)
    //   - timing1-6 (24 bytes)
    //   - autosr_en (4 bytes)
    //   - clkstp_cfg (4 bytes)
    //   Total: 72 bytes, rest is padding/zeros

    // For now, generate TXX DDRC registers in obj_buffer for DDRP section use
    if (config->type == DDR_TYPE_DDR2) {
        extern int ddr_generate_ddrc_txx_ddr2(const ddr_config_t *config, uint8_t *obj_buffer);
        if (ddr_generate_ddrc_txx_ddr2(config, obj_buffer) != 0) {
            return -1;
        }
    }

    // ========================================
    // Apply TXX ddr_convert_param mapping
    // Based on Ghidra decompilation @ 0x0046ba40
    // ========================================
    uint32_t *ddrc_out = (uint32_t *)ddrc_regs;
    uint32_t *obj = (uint32_t *)obj_buffer;

    ddrc_out[0] = obj[0x7c / 4];    // obj[0x7c]
    ddrc_out[1] = obj[0x80 / 4];    // obj[0x80]
    ddrc_out[2] = obj[0x8c / 4];    // obj[0x8c]
    ddrc_out[3] = obj[0x84 / 4];    // obj[0x84]
    ddrc_out[4] = obj[0x90 / 4];    // obj[0x90]
    ddrc_out[5] = obj[0x94 / 4];    // obj[0x94]
    ddrc_out[6] = obj[0x88 / 4];    // obj[0x88]
    ddrc_out[7] = obj[0xac / 4];    // obj[0xac]
    ddrc_out[8] = obj[0xb0 / 4];    // obj[0xb0]
    ddrc_out[9] = obj[0xb4 / 4];    // obj[0xb4]
    ddrc_out[10] = obj[0xb8 / 4];   // obj[0xb8]
    ddrc_out[11] = obj[0xbc / 4];   // obj[0xbc]
    ddrc_out[12] = obj[0xc0 / 4];   // obj[0xc0]
    ddrc_out[13] = obj[0xc4 / 4];   // obj[0xc4]
    ddrc_out[14] = obj[0xd0 / 4];   // obj[0xd0]
    ddrc_out[15] = obj[0xd8 / 4];   // obj[0xd8]
    ddrc_out[16] = obj[0xdc / 4];   // obj[0xdc]
    ddrc_out[17] = obj[0x1d4 / 4];  // obj[0x1d4]
    ddrc_out[18] = obj[0x1dc / 4];  // obj[0x1dc]
    ddrc_out[19] = obj[0x1e4 / 4];  // obj[0x1e4]
    ddrc_out[20] = obj[0x1e8 / 4];  // obj[0x1e8]
    ddrc_out[21] = obj[0x1ec / 4];  // obj[0x1ec]
    ddrc_out[22] = obj[0x1f0 / 4];  // obj[0x1f0]
    ddrc_out[23] = obj[0x1f4 / 4];  // obj[0x1f4]
    ddrc_out[24] = obj[0x150 / 4];  // obj[0x150]
    ddrc_out[25] = obj[0x154 / 4];  // obj[0x154]
    ddrc_out[26] = obj[0x1c0 / 4];  // obj[0x1c0]
    ddrc_out[27] = obj[0x1c4 / 4];  // obj[0x1c4]
    ddrc_out[28] = obj[0x1c8 / 4];  // obj[0x1c8]
    ddrc_out[29] = obj[0x1cc / 4];  // obj[0x1cc]
    ddrc_out[30] = obj[0x1d0 / 4];  // obj[0x1d0]

    return 0;
    
    // STAGE 1: Calculate all timing parameters from input config
    uint32_t t_wr = ddr_ns_to_cycles(config->tWR, clock_mhz);
    uint32_t t_wl = ddr_ns_to_cycles(config->tWL, clock_mhz);
    uint32_t t_ras = ddr_ns_to_cycles(config->tRAS, clock_mhz);
    uint32_t t_rcd = ddr_ns_to_cycles(config->tRCD, clock_mhz);
    uint32_t t_rl = ddr_ns_to_cycles(config->tRL, clock_mhz);
    uint32_t t_rp = ddr_ns_to_cycles(config->tRP, clock_mhz);
    uint32_t t_rrd = ddr_ns_to_cycles(config->tRRD, clock_mhz);
    uint32_t t_rc = ddr_ns_to_cycles(config->tRC, clock_mhz);
    
    // Validate all values
    if (!ddr_validate_timing("tWR", t_wr, 1, 127)) errors++;
    if (!ddr_validate_timing("tWL", t_wl, 1, 127)) errors++;
    if (!ddr_validate_timing("tRAS", t_ras, 1, 127)) errors++;
    if (!ddr_validate_timing("tRCD", t_rcd, 1, 127)) errors++;
    if (!ddr_validate_timing("tRL", t_rl, 1, 127)) errors++;
    if (!ddr_validate_timing("tRP", t_rp, 1, 127)) errors++;
    if (!ddr_validate_timing("tRRD", t_rrd, 1, 127)) errors++;
    if (!ddr_validate_timing("tRC", t_rc, 1, 127)) errors++;
    
    // tRFC special handling (from vendor decompilation)
    uint32_t t_rfc = ddr_ns_to_cycles(config->tRFC, clock_mhz);
    if (t_rfc > 0x7f) {
        errors++;
        t_rfc = 0x3f;
    }
    
    // tCKE and tXP from vendor decompilation
    uint32_t t_cke = ddr_ns_to_cycles(config->tCKE, clock_mhz);
    uint32_t t_xp = ddr_ns_to_cycles(config->tXP, clock_mhz);
    if (!ddr_validate_timing("tCKE", t_cke, 1, 15)) errors++;
    if (!ddr_validate_timing("tXP", t_xp, 1, 15)) errors++;
    
    // STAGE 2: Pack calculated values into object buffer offsets
    // Following vendor decompilation at 0x00448af0
    
    obj_buffer[0xad] = (obj_buffer[0xad] & 0xc0) | (t_wr & 0x3f);
    obj_buffer[0xac] = (obj_buffer[0xac] & 0xc0) | (t_wl & 0x3f);
    obj_buffer[0xb2] = (obj_buffer[0xb2] & 0xc0) | (t_ras & 0x3f);
    obj_buffer[0xb1] = (obj_buffer[0xb1] & 0xc0) | (t_rcd & 0x3f);
    obj_buffer[0xb0] = (obj_buffer[0xb0] & 0xc0) | (t_rl & 0x3f);
    obj_buffer[0xb7] = (obj_buffer[0xb7] & 0x87) | 0x20;
    obj_buffer[0xb6] = (obj_buffer[0xb6] & 0xc0) | (t_rp & 0x3f);
    obj_buffer[0xb5] = (obj_buffer[0xb5] & 0xc0) | (t_rrd & 0x3f);
    obj_buffer[0xb4] = (obj_buffer[0xb4] & 0xc0) | (t_rc & 0x3f);
    obj_buffer[0xba] = (obj_buffer[0xba] & 0x07) | 0x60;
    obj_buffer[0xbb] = (obj_buffer[0xbb] & 0xc0) | (t_rfc & 0x3f);
    obj_buffer[0xbf] = 0xff;
    obj_buffer[0xb8] = (obj_buffer[0xb8] & 0x8f) | ((t_xp & 0x07) << 4);
    obj_buffer[0xc1] = (obj_buffer[0xc1] & 0xc0) | 0x05;
    obj_buffer[0xc0] = (obj_buffer[0xc0] & 0xc0) | 0x05;
    obj_buffer[0xba] = (obj_buffer[0xba] & 0xf8) | (t_cke & 0x07);
    
    // tREFI calculation (from vendor decompilation)
    uint32_t trefi_cycles = (config->tREFI / clock_mhz) - 16;
    if ((int)trefi_cycles >= 0) {
        int ivar13 = 0;
        uint32_t ivar12 = trefi_cycles;
        
        while (ivar12 > 255 && ivar13 < 7) {
            ivar12 = ivar12 / 16;
            ivar13++;
        }
        *(uint32_t *)(obj_buffer + 0x88) = (ivar12 << 16) | (ivar13 * 2) | 1;
    } else {
        *(uint32_t *)(obj_buffer + 0x88) = 1;
    }
    
    // Auto-SR (default not enabled)
    *(uint32_t *)(obj_buffer + 0xc4) = 0;
    
    // DDR type and CAS latency
    uint8_t ddr_type_field = 0;
    if (config->type == DDR_TYPE_DDR2) {
        ddr_type_field = 3;
    } else if (config->type == DDR_TYPE_DDR3) {
        ddr_type_field = 0;
    } else if (config->type == DDR_TYPE_LPDDR || config->type == DDR_TYPE_LPDDR2) {
        ddr_type_field = 4;
    } else if (config->type == DDR_TYPE_LPDDR3) {
        ddr_type_field = 2;
    }
    *(uint32_t *)(obj_buffer + 0xcc) = (config->cas_latency << 3) | ddr_type_field;
    
    // STAGE 3: Copy object buffer offsets to DDRC output via ddr_convert_param logic
    // This exactly matches the decompilation of DDRBaseParam::ddr_convert_param()
    
    *(uint32_t *)(ddrc_regs + 0x00) = *(uint32_t *)(obj_buffer + 0x7c);
    *(uint32_t *)(ddrc_regs + 0x04) = *(uint32_t *)(obj_buffer + 0x80);
    *(uint32_t *)(ddrc_regs + 0x08) = *(uint32_t *)(obj_buffer + 0x90);
    *(uint32_t *)(ddrc_regs + 0x0c) = *(uint32_t *)(obj_buffer + 0x94);
    *(uint32_t *)(ddrc_regs + 0x10) = *(uint32_t *)(obj_buffer + 0x88);
    *(uint32_t *)(ddrc_regs + 0x14) = *(uint32_t *)(obj_buffer + 0xac);
    *(uint32_t *)(ddrc_regs + 0x18) = *(uint32_t *)(obj_buffer + 0xb0);
    *(uint32_t *)(ddrc_regs + 0x1c) = *(uint32_t *)(obj_buffer + 0xb4);
    *(uint32_t *)(ddrc_regs + 0x20) = *(uint32_t *)(obj_buffer + 0xb8);
    *(uint32_t *)(ddrc_regs + 0x24) = *(uint32_t *)(obj_buffer + 0xbc);
    *(uint32_t *)(ddrc_regs + 0x28) = *(uint32_t *)(obj_buffer + 0xc0);
    *(uint32_t *)(ddrc_regs + 0x2c) = *(uint32_t *)(obj_buffer + 0xc4);
    *(uint32_t *)(ddrc_regs + 0x30) = *(uint32_t *)(obj_buffer + 0xcc);
    *(uint32_t *)(ddrc_regs + 0x34) = *(uint32_t *)(obj_buffer + 0xd0);
    *(uint32_t *)(ddrc_regs + 0x38) = *(uint32_t *)(obj_buffer + 0xd4);
    *(uint32_t *)(ddrc_regs + 0x3c) = *(uint32_t *)(obj_buffer + 0xd8);
    *(uint32_t *)(ddrc_regs + 0x40) = *(uint32_t *)(obj_buffer + 0xdc);
    *(uint32_t *)(ddrc_regs + 0x44) = *(uint32_t *)(obj_buffer + 0xe4);
    *(uint32_t *)(ddrc_regs + 0x48) = *(uint32_t *)(obj_buffer + 0xe4);
    *(uint32_t *)(ddrc_regs + 0x4c) = *(uint32_t *)(obj_buffer + 0xe4);
    *(uint32_t *)(ddrc_regs + 0x50) = *(uint32_t *)(obj_buffer + 0xf0);
    *(uint32_t *)(ddrc_regs + 0x54) = *(uint32_t *)(obj_buffer + 0xf4);
    *(uint32_t *)(ddrc_regs + 0x58) = *(uint32_t *)(obj_buffer + 0xf8);
    *(uint32_t *)(ddrc_regs + 0x5c) = *(uint32_t *)(obj_buffer + 0xe0);
    *(uint32_t *)(ddrc_regs + 0x60) = *(uint32_t *)(obj_buffer + 0xfc);
    *(uint32_t *)(ddrc_regs + 0x64) = *(uint32_t *)(obj_buffer + 0x100);
    *(uint32_t *)(ddrc_regs + 0x68) = *(uint32_t *)(obj_buffer + 0x108);
    *(uint32_t *)(ddrc_regs + 0x6c) = *(uint32_t *)(obj_buffer + 0x110);
    *(uint32_t *)(ddrc_regs + 0x70) = *(uint32_t *)(obj_buffer + 0x118);
    *(uint32_t *)(ddrc_regs + 0x74) = *(uint32_t *)(obj_buffer + 0x120);
    *(uint32_t *)(ddrc_regs + 0x78) = *(uint32_t *)(obj_buffer + 0x124);
    *(uint32_t *)(ddrc_regs + 0x7c) = *(uint32_t *)(obj_buffer + 0x128);
    *(uint32_t *)(ddrc_regs + 0x80) = *(uint32_t *)(obj_buffer + 0x12c);
    *(uint32_t *)(ddrc_regs + 0x84) = *(uint32_t *)(obj_buffer + 0x130);
    
    // Copy 32-byte array from 0x134-0x153 to 0x88-0xa7
    memcpy(ddrc_regs + 0x88, obj_buffer + 0x134, 0x20);
    
    *(uint32_t *)(ddrc_regs + 0xa8) = *(uint32_t *)(obj_buffer + 0x18c);
    *(uint32_t *)(ddrc_regs + 0xac) = *(uint32_t *)(obj_buffer + 0x1a0);
    *(uint32_t *)(ddrc_regs + 0xb0) = *(uint32_t *)(obj_buffer + 0x1fc);
    *(uint32_t *)(ddrc_regs + 0xb4) = *(uint32_t *)(obj_buffer + 0x200);
    *(uint32_t *)(ddrc_regs + 0xb8) = *(uint32_t *)(obj_buffer + 0x204);
    *(uint32_t *)(ddrc_regs + 0xbc) = *(uint32_t *)(obj_buffer + 0x208);
    // Note: 0xc0 would be part of RDD marker in the final output, so we skip it
    
    return errors > 0 ? -1 : 0;
}