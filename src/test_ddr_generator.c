#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include "ddr/ddr_types.h"
#include "ddr/ddr_generator.h"

// Helper function to load binary file
static uint8_t* load_binary_file(const char *path, size_t *size) {
    FILE *file = fopen(path, "rb");
    if (!file) {
        printf("[ERROR] Cannot open file: %s\n", path);
        return NULL;
    }
    
    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return NULL;
    }
    
    long file_size = ftell(file);
    if (file_size < 0) {
        fclose(file);
        return NULL;
    }
    
    if (fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return NULL;
    }
    
    uint8_t *buffer = (uint8_t *)malloc(file_size);
    if (!buffer) {
        fclose(file);
        return NULL;
    }
    
    size_t bytes_read = fread(buffer, 1, file_size, file);
    fclose(file);
    
    if (bytes_read != (size_t)file_size) {
        free(buffer);
        return NULL;
    }
    
    *size = bytes_read;
    return buffer;
}

// Helper to print hex dump
static void print_hex_section(const char *title, const uint8_t *data, size_t len) {
    printf("\n%s:\n", title);
    for (size_t i = 0; i < len; i++) {
        if (i % 16 == 0) printf("%04zx: ", i);
        printf("%02x ", data[i]);
        if ((i + 1) % 16 == 0) printf("\n");
    }
    printf("\n");
}

int main(int argc __attribute__((unused)), char *argv[] __attribute__((unused))) {
    printf("=== DDR Generator Test ===\n\n");
    
    // Load reference binary
    size_t ref_size = 0;
    uint8_t *reference = load_binary_file("references/ddr_extracted.bin", &ref_size);
    if (!reference) {
        printf("[ERROR] Failed to load reference binary\n");
        return 1;
    }
    printf("[OK] Loaded reference binary: %zu bytes\n", ref_size);
    
    // Print reference structure
    printf("\nReference Binary Structure:\n");
    printf("  FIDB: %c%c%c%c\n", reference[0], reference[1], reference[2], reference[3]);
    printf("  DDRC: %d bytes (0x04-0xbf)\n", 0xbc);
    printf("  RDD:  %c%c%c %02x\n", reference[0xc0], reference[0xc1], reference[0xc2], reference[0xc3]);
    printf("  DDRP: %d bytes (0xc4-0x143)\n", 0x80);
    
    // Create a test configuration matching the reference binary
    // Reference: M14D1G1664A_DDR2.cfg from T31X config
    // DDR2 @ 400 MHz: 1 cycle = 2.5 ns
    ddr_config_t config = {
        .type = DDR_TYPE_DDR2,
        .clock_mhz = 400,
        .cas_latency = 7,   // CL from config
        .tWR = 15,          // 15 ns (6 cycles at 400 MHz)
        .tRAS = 45,         // 45 ns (18 cycles at 400 MHz)
        .tRP = 16,          // 16 ns (7 cycles at 400 MHz)
        .tRCD = 16,         // 16 ns (7 cycles at 400 MHz)
        .tRC = 57,          // 56.25 ns rounded up (23 cycles at 400 MHz)
        .tRRD = 10,         // 10 ns (4 cycles at 400 MHz)
        .tWTR = 8,          // 7.5 ns rounded up (3 cycles at 400 MHz, PHY valid: 1-6)
        .tRFC = 128,        // 127.5 ns rounded up (51 cycles at 400 MHz)
        .tXP = 8,           // 3 tck = 7.5 ns rounded up
        .tCKE = 8,          // 3 tck = 7.5 ns rounded up
        .tRL = 7,           // Read latency = CL = 7
        .tWL = 6,           // Write latency from config
        .tREFI = 7800,      // 7.8 us
        .banks = 8,
        .row_bits = 13,     // ROW=13 from config
        .col_bits = 10,     // COL=10 from config
        .data_width = 16,
        .total_size_bytes = 128 * 1024 * 1024,  // 128MB (1Gb / 8)
    };
    
    printf("\nTest Configuration (matching reference M14D1G1664A_DDR2.cfg):\n");
    printf("  Type: DDR%d\n", config.type == DDR_TYPE_DDR2 ? 2 : (config.type == DDR_TYPE_DDR3 ? 3 : 2));
    printf("  Clock: %u MHz\n", config.clock_mhz);
    printf("  CAS Latency: %u\n", config.cas_latency);
    printf("  tWR: %u ns\n", config.tWR);
    printf("  tRAS: %u ns\n", config.tRAS);
    printf("  tRP: %u ns\n", config.tRP);
    printf("  tRCD: %u ns\n", config.tRCD);
    printf("  tRC: %u ns\n", config.tRC);
    
    // Test generation
    printf("\n=== Testing Generator ===\n");

    // Generate binary
    uint8_t generated[324];
    ddr_generate_binary(&config, generated, 324);

    // Save generated binary to file
    const char *output_path = "build/ddr_generated.bin";
    FILE *out_file = fopen(output_path, "wb");
    if (out_file) {
        fwrite(generated, 1, 324, out_file);
        fclose(out_file);
        printf("[OK] Generated binary saved to: %s\n", output_path);
    } else {
        printf("[ERROR] Failed to save generated binary\n");
    }

    int result = ddr_test_against_reference(&config, reference, ref_size);

    if (result == 0) {
        printf("\n✓ Test PASSED - Generated binary matches reference!\n");
    } else {
        printf("\n✗ Test FAILED - Differences detected\n");
        
        printf("\n=== Byte Comparison ===\n");
        
        // Show DDRC sections
        printf("\nDDRC Section (0x04-0xbf):\n");
        printf("Offset  Generated    Reference\n");
        for (int i = 0x04; i < 0xc0; i++) {
            if (generated[i] != reference[i]) {
                printf("  0x%02x:    0x%02x          0x%02x      ← DIFF\n", i, generated[i], reference[i]);
            }
        }
        
        // Show DDRP sections
        printf("\nDDRP Section (0xc4-0x143):\n");
        printf("Offset  Generated    Reference\n");
        for (int i = 0xc4; i < 0x144; i++) {
            if (generated[i] != reference[i]) {
                printf("  0x%02x:    0x%02x          0x%02x      ← DIFF\n", i, generated[i], reference[i]);
            }
        }
        
        // Show hex dumps for analysis
        print_hex_section("Generated DDRC (0x04-0xbf)", generated + 0x04, 0xbc);
        print_hex_section("Reference DDRC (0x04-0xbf)", reference + 0x04, 0xbc);
        print_hex_section("Generated DDRP (0xc4-0x143)", generated + 0xc4, 0x80);
        print_hex_section("Reference DDRP (0xc4-0x143)", reference + 0xc4, 0x80);
    }
    
    free(reference);
    return result;
}