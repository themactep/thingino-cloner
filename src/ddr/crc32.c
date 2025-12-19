#include "crc32.h"

#include <stdbool.h>

static uint32_t crc32_table[256];
static bool crc32_table_ready = false;

static void crc32_init_table(void) {
    for (uint32_t i = 0; i < 256; ++i) {
        uint32_t crc = i;
        for (uint32_t j = 0; j < 8; ++j) {
            if (crc & 1U) {
                crc = (crc >> 1) ^ 0xEDB88320U;
            } else {
                crc >>= 1;
            }
        }
        crc32_table[i] = crc;
    }
    crc32_table_ready = true;
}

uint32_t thingino_crc32(const uint8_t *data, size_t length) {
    if (!crc32_table_ready) {
        crc32_init_table();
    }

    if (!data || length == 0) {
        return 0U;
    }

    uint32_t crc = 0xFFFFFFFFU;
    for (size_t i = 0; i < length; ++i) {
        uint8_t index = (uint8_t)((crc ^ data[i]) & 0xFFU);
        crc = (crc >> 8) ^ crc32_table[index];
    }

    return crc ^ 0xFFFFFFFFU;
}
