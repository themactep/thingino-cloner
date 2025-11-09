/**
 * Test DDR Binary Builder - Matches Python script format
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "ddr/ddr_binary_builder.h"

// Helper to calculate timing cycles from picoseconds
static uint8_t ps2cycle_ceil(uint32_t ps, uint32_t ps_per_tck) {
    if (ps == 0) return 0;
    return (ps + ps_per_tck - 1) / ps_per_tck;
}

int main() {
    printf("=== DDR Binary Builder Test ===\n\n");
    
    // Load reference binary
    FILE *ref_file = fopen("references/ddr_extracted.bin", "rb");
    if (!ref_file) {
        printf("[ERROR] Cannot open reference binary\n");
        return 1;
    }
    
    uint8_t reference[324];
    size_t ref_size = fread(reference, 1, 324, ref_file);
    fclose(ref_file);
    
    printf("[OK] Loaded reference binary: %zu bytes\n\n", ref_size);
    
    // Setup platform configuration (T31)
    platform_config_t platform;
    ddr_get_platform_config("t31", &platform);
    
    printf("Platform Configuration:\n");
    printf("  Crystal: %u Hz (%.1f MHz)\n", platform.crystal_freq, platform.crystal_freq / 1e6);
    printf("  CPU: %u Hz (%.1f MHz)\n", platform.cpu_freq, platform.cpu_freq / 1e6);
    printf("  DDR: %u Hz (%.1f MHz)\n", platform.ddr_freq, platform.ddr_freq / 1e6);
    printf("  UART: %u baud\n", platform.uart_baud);
    printf("  Memory: %u bytes (%u MB)\n\n", platform.mem_size, platform.mem_size / (1024 * 1024));
    
    // Setup DDR PHY parameters (M14D1G1664A DDR2 @ 400MHz)
    ddr_phy_params_t params;
    memset(&params, 0, sizeof(params));
    
    params.ddr_type = 1;  // DDR2
    params.row_bits = 13;
    params.col_bits = 10;
    params.cl = 7;  // From config: CL=7
    params.bl = 8;

    // Calculate timing parameters
    // Clock period at 400 MHz = 2500 ps
    uint32_t ps_per_tck = 1000000000 / (platform.ddr_freq / 1000);

    printf("DDR Configuration:\n");
    printf("  Type: DDR2\n");
    printf("  Frequency: %u MHz\n", platform.ddr_freq / 1000000);
    printf("  Clock period: %u ps\n", ps_per_tck);
    printf("  Row bits: %u\n", params.row_bits);
    printf("  Col bits: %u\n", params.col_bits);
    printf("  CL: %u\n", params.cl);
    printf("  BL: %u\n\n", params.bl);

    // Timing parameters (from M14D1G1664A_DDR2.cfg)
    params.tRAS = ps2cycle_ceil(45000, ps_per_tck);  // 45ns
    params.tRC = ps2cycle_ceil(57000, ps_per_tck);   // 57ns
    params.tRCD = ps2cycle_ceil(16000, ps_per_tck);  // 16ns
    params.tRP = ps2cycle_ceil(16000, ps_per_tck);   // 16ns
    // tRFC: ps2cycle_ceil with div_tck=2, then divide by 2
    params.tRFC = ((127500 + 2 * ps_per_tck - 1) / ps_per_tck) / 2;  // 127.5ns
    params.tRTP = ps2cycle_ceil(7500, ps_per_tck);   // 7.5ns
    params.tFAW = ps2cycle_ceil(45000, ps_per_tck);  // 45ns (from config)
    params.tRRD = ps2cycle_ceil(10000, ps_per_tck);  // 10ns
    params.tWTR = ps2cycle_ceil(7500, ps_per_tck);   // 7.5ns
    
    printf("Timing Parameters (cycles):\n");
    printf("  tRAS: %u\n", params.tRAS);
    printf("  tRC: %u\n", params.tRC);
    printf("  tRCD: %u\n", params.tRCD);
    printf("  tRP: %u\n", params.tRP);
    printf("  tRFC: %u\n", params.tRFC);
    printf("  tRTP: %u\n", params.tRTP);
    printf("  tFAW: %u\n", params.tFAW);
    printf("  tRRD: %u\n", params.tRRD);
    printf("  tWTR: %u\n\n", params.tWTR);
    
    // Build binary
    uint8_t generated[324];
    size_t gen_size = ddr_build_binary(&platform, &params, generated);
    
    printf("[OK] Generated binary: %zu bytes\n\n", gen_size);
    
    // Save generated binary
    FILE *out_file = fopen("build/ddr_generated_new.bin", "wb");
    if (out_file) {
        fwrite(generated, 1, gen_size, out_file);
        fclose(out_file);
        printf("[OK] Saved to: build/ddr_generated_new.bin\n\n");
    }
    
    // Compare with reference
    printf("=== Byte Comparison ===\n\n");
    
    int diff_count = 0;
    for (size_t i = 0; i < 324; i++) {
        if (generated[i] != reference[i]) {
            if (diff_count < 50) {  // Show first 50 differences
                printf("[DIFF] Offset 0x%02zx: Generated 0x%02x, Reference 0x%02x\n", 
                       i, generated[i], reference[i]);
            }
            diff_count++;
        }
    }
    
    if (diff_count == 0) {
        printf("[SUCCESS] ✓ Binary matches reference perfectly!\n");
        return 0;
    } else {
        printf("\n[FAILURE] ✗ Found %d byte differences\n", diff_count);
        return 1;
    }
}

