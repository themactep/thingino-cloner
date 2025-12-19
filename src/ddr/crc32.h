#ifndef THINGINO_DDR_CRC32_H
#define THINGINO_DDR_CRC32_H

#include <stddef.h>
#include <stdint.h>

uint32_t thingino_crc32(const uint8_t *data, size_t length);

#endif
