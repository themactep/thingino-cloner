#include "thingino.h"
#include "ddr_param_builder.h"
#include "ddr_generator.h"
#include "ddr_types.h"
#include "ddr_binary_builder.h"

// ============================================================================
// FIRMWARE LOADER IMPLEMENTATION
// ============================================================================
// Loads real firmware files from disk (no fallback to placeholders)
// DDR configuration is now generated dynamically from chip parameters using
// the new ddr_binary_builder API that matches the Python script format

// ============================================================================
// DDR GENERATION USING NEW BINARY BUILDER API
// ============================================================================

/**
 * Generate DDR configuration binary dynamically using the new ddr_binary_builder API
 *
 * This function generates a 324-byte DDR binary in the format:
 *   - FIDB section (192 bytes): Platform configuration (frequencies, UART, memory size)
 *   - RDD section (132 bytes): DDR PHY parameters (timing, geometry, DQ mapping)
 *
 * The format matches the Python script (ddr_compiler_final.py) and has been verified
 * to produce byte-perfect output for M14D1G1664A DDR2 @ 400MHz.
 */
static thingino_error_t firmware_generate_ddr_config(processor_variant_t variant,
    uint8_t** config_buffer, size_t* config_size) {

    if (!config_buffer || !config_size) {
        return THINGINO_ERROR_INVALID_PARAMETER;
    }

    DEBUG_PRINT("firmware_generate_ddr_config: variant=%d (%s)\n",
        variant, processor_variant_to_string(variant));

    // Get platform configuration based on processor variant
    platform_config_t platform_cfg;
    if (ddr_get_platform_config_by_variant(variant, &platform_cfg) != 0) {
        fprintf(stderr, "ERROR: Unsupported processor variant for DDR generation: %d\n", variant);
        return THINGINO_ERROR_INVALID_PARAMETER;
    }

    DEBUG_PRINT("Platform config: crystal=%u Hz, cpu=%u Hz, ddr=%u Hz, uart=%u baud, mem=%u bytes\n",
        platform_cfg.crystal_freq, platform_cfg.cpu_freq, platform_cfg.ddr_freq,
        platform_cfg.uart_baud, platform_cfg.mem_size);

    // Get DDR PHY parameters based on processor variant
    // For now, use M14D1G1664A DDR2 @ 400MHz as default (verified working)
    ddr_phy_params_t phy_params = {
        .ddr_type = 1,      // DDR2 (RDD encoding: 0=DDR3, 1=DDR2, 2=LPDDR2, 4=LPDDR3)
        .row_bits = 13,     // 13 row address bits
        .col_bits = 10,     // 10 column address bits
        .cl = 7,            // CAS Latency = 7 cycles (for 400MHz DDR2)
        .bl = 8,            // Burst Length = 8
        .tRAS = 18,         // Row Active Time = 45ns @ 400MHz = 18 cycles
        .tRC = 23,          // Row Cycle Time = 57.5ns @ 400MHz = 23 cycles
        .tRCD = 6,          // RAS to CAS Delay = 15ns @ 400MHz = 6 cycles
        .tRP = 6,           // Row Precharge Time = 15ns @ 400MHz = 6 cycles
        .tRFC = 52,         // Refresh Cycle Time = 127.5ns @ 400MHz = 52 cycles (special calculation)
        .tRTP = 3,          // Read to Precharge = 7.5ns @ 400MHz = 3 cycles
        .tFAW = 18,         // Four Bank Activate Window = 45ns @ 400MHz = 18 cycles
        .tRRD = 4,          // Row to Row Delay = 10ns @ 400MHz = 4 cycles
        .tWTR = 3           // Write to Read Delay = 7.5ns @ 400MHz = 3 cycles
    };

    DEBUG_PRINT("DDR PHY params: type=%u, row=%u, col=%u, CL=%u, BL=%u\n",
        phy_params.ddr_type, phy_params.row_bits, phy_params.col_bits,
        phy_params.cl, phy_params.bl);

    // Allocate buffer for DDR binary (324 bytes)
    *config_buffer = (uint8_t*)malloc(DDR_BINARY_SIZE);
    if (!*config_buffer) {
        fprintf(stderr, "ERROR: Failed to allocate DDR buffer\n");
        return THINGINO_ERROR_MEMORY;
    }

    // Generate the DDR binary using the new API
    DEBUG_PRINT("Generating 324-byte DDR binary (FIDB + RDD format)\n");
    if (ddr_build_binary(&platform_cfg, &phy_params, *config_buffer) != 0) {
        fprintf(stderr, "ERROR: Failed to generate DDR binary\n");
        free(*config_buffer);
        *config_buffer = NULL;
        return THINGINO_ERROR_PROTOCOL;
    }

    *config_size = DDR_BINARY_SIZE;
    DEBUG_PRINT("Successfully generated %zu bytes DDR binary\n", *config_size);

    return THINGINO_SUCCESS;
}

thingino_error_t firmware_load(processor_variant_t variant, firmware_files_t* firmware) {
    if (!firmware) {
        return THINGINO_ERROR_INVALID_PARAMETER;
    }
    
    DEBUG_PRINT("firmware_load: variant=%d (%s)\n", variant, processor_variant_to_string(variant));
    
    // Initialize firmware structure
    firmware->config = NULL;
    firmware->config_size = 0;
    firmware->spl = NULL;
    firmware->spl_size = 0;
    firmware->uboot = NULL;
    firmware->uboot_size = 0;
    
    switch (variant) {
        case VARIANT_T31X:
            DEBUG_PRINT("firmware_load: matched VARIANT_T31X (%d)\n", VARIANT_T31X);
            DEBUG_PRINT("firmware_load: calling firmware_load_t31x\n");
            return firmware_load_t31x(firmware);
        case VARIANT_T31ZX:
            DEBUG_PRINT("firmware_load: matched VARIANT_T31ZX (%d)\n", VARIANT_T31ZX);
            DEBUG_PRINT("firmware_load: calling firmware_load_t31x\n");
            return firmware_load_t31x(firmware);
            
        default:
            DEBUG_PRINT("firmware_load: unsupported variant %d\n", variant);
            return THINGINO_ERROR_INVALID_PARAMETER;
    }
}

thingino_error_t firmware_load_t31x(firmware_files_t* firmware) {
    thingino_error_t result;
    
    DEBUG_PRINT("Loading T31X firmware...\n");
    
    // Try to generate DDR configuration dynamically first
    DEBUG_PRINT("Attempting to generate DDR configuration dynamically\n");
    thingino_error_t gen_result = firmware_generate_ddr_config(VARIANT_T31X, 
        &firmware->config, &firmware->config_size);
    
    if (gen_result == THINGINO_SUCCESS) {
        printf("✓ DDR configuration generated dynamically: %zu bytes\n", firmware->config_size);
    } else {
        // Fall back to reference binary
        DEBUG_PRINT("Dynamic generation failed, falling back to reference binary\n");
        printf("Note: Using reference binary for DDR configuration\n");
        
        const char* config_paths[] = {
            "./references/ddr_extracted.bin",
            "../references/ddr_extracted.bin",
            NULL
        };
        
        // Try to load reference binary
        result = THINGINO_ERROR_FILE_IO;
        for (int i = 0; config_paths[i]; i++) {
            DEBUG_PRINT("Trying to load DDR config from: %s\n", config_paths[i]);
            result = load_file(config_paths[i], &firmware->config, &firmware->config_size);
            if (result == THINGINO_SUCCESS) {
                DEBUG_PRINT("Loaded DDR config: %zu bytes\n", firmware->config_size);
                printf("✓ DDR configuration loaded from reference binary: %zu bytes\n", firmware->config_size);
                break;
            }
        }
        
        if (result != THINGINO_SUCCESS) {
            fprintf(stderr, "ERROR: Could not generate DDR or load reference binary\n");
            fprintf(stderr, "  Generation issue: %s\n", thingino_error_to_string(gen_result));
            fprintf(stderr, "  Reference binary expected at: ./references/ddr_extracted.bin\n");
            return result;
        }
    }
    
    // Define SPL and U-Boot paths
    const char* spl_paths[] = {
        "./references/cloner-2.5.43-ubuntu_thingino/firmwares/t31x/spl.bin",
        "../references/cloner-2.5.43-ubuntu_thingino/firmwares/t31x/spl.bin",
        NULL
    };
    
    const char* uboot_paths[] = {
        "./references/cloner-2.5.43-ubuntu_thingino/firmwares/t31x/uboot.bin",
        "../references/cloner-2.5.43-ubuntu_thingino/firmwares/t31x/uboot.bin",
        NULL
    };
    
    // Load SPL binary
    result = THINGINO_ERROR_FILE_IO;
    for (int i = 0; spl_paths[i]; i++) {
        DEBUG_PRINT("Trying to load SPL from: %s\n", spl_paths[i]);
        result = load_file(spl_paths[i], &firmware->spl, &firmware->spl_size);
        if (result == THINGINO_SUCCESS) {
            DEBUG_PRINT("Loaded SPL: %zu bytes\n", firmware->spl_size);
            break;
        }
    }
    
    if (result != THINGINO_SUCCESS) {
        fprintf(stderr, "ERROR: Failed to load SPL file\n");
        fprintf(stderr, "  Expected at: ./references/cloner-2.5.43-ubuntu_thingino/firmwares/t31x/spl.bin\n");
        firmware_cleanup(firmware);
        return result;
    }
    
    // Load U-Boot binary (separate from SPL)
    result = THINGINO_ERROR_FILE_IO;
    for (int i = 0; uboot_paths[i]; i++) {
        DEBUG_PRINT("Trying to load U-Boot from: %s\n", uboot_paths[i]);
        result = load_file(uboot_paths[i], &firmware->uboot, &firmware->uboot_size);
        if (result == THINGINO_SUCCESS) {
            DEBUG_PRINT("Loaded U-Boot: %zu bytes\n", firmware->uboot_size);
            break;
        }
    }
    
    if (result != THINGINO_SUCCESS) {
        fprintf(stderr, "ERROR: Failed to load U-Boot file\n");
        fprintf(stderr, "  Expected at: ./references/cloner-2.5.43-ubuntu_thingino/firmwares/t31x/uboot.bin\n");
        firmware_cleanup(firmware);
        return result;
    }
    
    DEBUG_PRINT("T31X firmware loaded successfully (official cloner files)\n");
    DEBUG_PRINT("DDR config: %zu bytes, SPL: %zu bytes, U-Boot: %zu bytes\n", 
           firmware->config_size, firmware->spl_size, firmware->uboot_size);
    
    return THINGINO_SUCCESS;
}

void firmware_cleanup(firmware_files_t* firmware) {
    if (!firmware) {
        return;
    }
    
    if (firmware->config) {
        free(firmware->config);
        firmware->config = NULL;
        firmware->config_size = 0;
    }
    
    if (firmware->spl) {
        free(firmware->spl);
        firmware->spl = NULL;
        firmware->spl_size = 0;
    }
    
    if (firmware->uboot) {
        free(firmware->uboot);
        firmware->uboot = NULL;
        firmware->uboot_size = 0;
    }
}

thingino_error_t firmware_load_from_files(processor_variant_t variant,
    const char* config_file, const char* spl_file, const char* uboot_file,
    firmware_files_t* firmware) {
    
    if (!firmware) {
        return THINGINO_ERROR_INVALID_PARAMETER;
    }
    
    // Initialize firmware structure
    firmware->config = NULL;
    firmware->config_size = 0;
    firmware->spl = NULL;
    firmware->spl_size = 0;
    firmware->uboot = NULL;
    firmware->uboot_size = 0;
    
    // Load or generate configuration file
    if (config_file) {
        // User provided custom DDR config file
        thingino_error_t result = load_file(config_file, &firmware->config, &firmware->config_size);
        if (result != THINGINO_SUCCESS) {
            firmware_cleanup(firmware);
            return result;
        }
        DEBUG_PRINT("Loaded custom DDR config from: %s (%zu bytes)\n", config_file, firmware->config_size);
        printf("✓ Loaded custom DDR config: %s (%zu bytes)\n", config_file, firmware->config_size);
    } else {
        // No custom config provided - try dynamic generation, fall back to reference
        DEBUG_PRINT("No custom DDR config provided, attempting dynamic generation for variant %d\n", variant);
        thingino_error_t gen_result = firmware_generate_ddr_config(variant, 
            &firmware->config, &firmware->config_size);
        
        if (gen_result == THINGINO_SUCCESS) {
            printf("✓ Generated DDR configuration dynamically: %zu bytes\n", firmware->config_size);
        } else {
            // Generation failed - try reference binary fallback
            DEBUG_PRINT("Dynamic generation failed, attempting reference binary fallback\n");
            
            // For now, continue without DDR config if no file provided and generation fails
            // (Reference binary paths depend on processor type which we may not know)
            DEBUG_PRINT("Warning: Failed to generate DDR config, continuing without it\n");
            firmware->config = NULL;
            firmware->config_size = 0;
        }
    }
    
    // Load SPL file
    if (spl_file) {
        // User provided custom SPL file
        thingino_error_t result = load_file(spl_file, &firmware->spl, &firmware->spl_size);
        if (result != THINGINO_SUCCESS) {
            firmware_cleanup(firmware);
            return result;
        }
        DEBUG_PRINT("Loaded custom SPL from: %s (%zu bytes)\n", spl_file, firmware->spl_size);
        printf("✓ Loaded custom SPL: %s (%zu bytes)\n", spl_file, firmware->spl_size);
    } else {
        // No custom SPL provided - load default based on variant
        DEBUG_PRINT("No custom SPL provided, loading default for variant %d\n", variant);
        const char* spl_paths[] = {
            "./references/cloner-2.5.43-ubuntu_thingino/firmwares/t31x/spl.bin",
            "../references/cloner-2.5.43-ubuntu_thingino/firmwares/t31x/spl.bin",
            NULL
        };

        thingino_error_t result = THINGINO_ERROR_FILE_IO;
        for (int i = 0; spl_paths[i]; i++) {
            DEBUG_PRINT("Trying to load SPL from: %s\n", spl_paths[i]);
            result = load_file(spl_paths[i], &firmware->spl, &firmware->spl_size);
            if (result == THINGINO_SUCCESS) {
                DEBUG_PRINT("Loaded default SPL: %zu bytes\n", firmware->spl_size);
                printf("✓ Loaded default SPL: %zu bytes\n", firmware->spl_size);
                break;
            }
        }

        if (result != THINGINO_SUCCESS) {
            fprintf(stderr, "ERROR: Failed to load SPL file\n");
            fprintf(stderr, "  Expected at: ./references/cloner-2.5.43-ubuntu_thingino/firmwares/t31x/spl.bin\n");
            firmware_cleanup(firmware);
            return result;
        }
    }

    // Load U-Boot file
    if (uboot_file) {
        // User provided custom U-Boot file
        thingino_error_t result = load_file(uboot_file, &firmware->uboot, &firmware->uboot_size);
        if (result != THINGINO_SUCCESS) {
            firmware_cleanup(firmware);
            return result;
        }
        DEBUG_PRINT("Loaded custom U-Boot from: %s (%zu bytes)\n", uboot_file, firmware->uboot_size);
        printf("✓ Loaded custom U-Boot: %s (%zu bytes)\n", uboot_file, firmware->uboot_size);
    } else {
        // No custom U-Boot provided - load default based on variant
        DEBUG_PRINT("No custom U-Boot provided, loading default for variant %d\n", variant);
        const char* uboot_paths[] = {
            "./references/cloner-2.5.43-ubuntu_thingino/firmwares/t31x/uboot.bin",
            "../references/cloner-2.5.43-ubuntu_thingino/firmwares/t31x/uboot.bin",
            NULL
        };

        thingino_error_t result = THINGINO_ERROR_FILE_IO;
        for (int i = 0; uboot_paths[i]; i++) {
            DEBUG_PRINT("Trying to load U-Boot from: %s\n", uboot_paths[i]);
            result = load_file(uboot_paths[i], &firmware->uboot, &firmware->uboot_size);
            if (result == THINGINO_SUCCESS) {
                DEBUG_PRINT("Loaded default U-Boot: %zu bytes\n", firmware->uboot_size);
                printf("✓ Loaded default U-Boot: %zu bytes\n", firmware->uboot_size);
                break;
            }
        }

        if (result != THINGINO_SUCCESS) {
            fprintf(stderr, "ERROR: Failed to load U-Boot file\n");
            fprintf(stderr, "  Expected at: ./references/cloner-2.5.43-ubuntu_thingino/firmwares/t31x/uboot.bin\n");
            firmware_cleanup(firmware);
            return result;
        }
    }

    return THINGINO_SUCCESS;
}

thingino_error_t load_file(const char* filename, uint8_t** data, size_t* size) {
    if (!filename || !data || !size) {
        return THINGINO_ERROR_INVALID_PARAMETER;
    }
    
    FILE* file = fopen(filename, "rb");
    if (!file) {
        return THINGINO_ERROR_FILE_IO;
    }
    
    // Get file size
    if (fseek(file, 0, SEEK_END) != 0) {
        fclose(file);
        return THINGINO_ERROR_FILE_IO;
    }
    
    long file_size = ftell(file);
    if (file_size < 0) {
        fclose(file);
        return THINGINO_ERROR_FILE_IO;
    }
    
    if (fseek(file, 0, SEEK_SET) != 0) {
        fclose(file);
        return THINGINO_ERROR_FILE_IO;
    }
    
    // Allocate buffer
    *data = (uint8_t*)malloc(file_size);
    if (!*data) {
        fclose(file);
        return THINGINO_ERROR_MEMORY;
    }
    
    // Read file
    size_t bytes_read = fread(*data, 1, file_size, file);
    fclose(file);
    
    if (bytes_read != (size_t)file_size) {
        free(*data);
        *data = NULL;
        return THINGINO_ERROR_FILE_IO;
    }
    
    *size = bytes_read;
    return THINGINO_SUCCESS;
}

thingino_error_t firmware_validate(const firmware_files_t* firmware) {
    if (!firmware) {
        return THINGINO_ERROR_INVALID_PARAMETER;
    }
    
    // Validate DDR configuration
    if (firmware->config && firmware->config_size > 0) {
        thingino_error_t result = ddr_validate_binary(firmware->config, firmware->config_size);
        if (result != THINGINO_SUCCESS) {
            return result;
        }
    }
    
    // Validate SPL (basic checks)
    if (firmware->spl && firmware->spl_size > 0) {
        // Check for minimum SPL size
        if (firmware->spl_size < 1024) {
            return THINGINO_ERROR_PROTOCOL;
        }
    }
    
    // Validate U-Boot (basic checks)
    if (firmware->uboot && firmware->uboot_size > 0) {
        // Check for minimum U-Boot size
        if (firmware->uboot_size < 4096) {
            return THINGINO_ERROR_PROTOCOL;
        }
    }
    
    return THINGINO_SUCCESS;
}