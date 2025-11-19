/**
 * Firmware Writer Header
 * 
 * Provides firmware writing functionality for Ingenic SoC devices.
 */

#ifndef FIRMWARE_WRITER_H
#define FIRMWARE_WRITER_H

#include <stdint.h>
#include "../usb/device.h"
#include "firmware_database.h"

/**
 * Write firmware to device
 * 
 * @param device USB device handle
 * @param firmware_file Path to firmware file
 * @param fw_config Firmware configuration for the target SoC
 * @return THINGINO_SUCCESS on success, error code otherwise
 */
thingino_error_t write_firmware_to_device(usb_device_t* device, 
                                         const char* firmware_file,
                                         const firmware_config_t* fw_config);

/**
 * Send bulk data to device
 * 
 * @param device USB device handle
 * @param endpoint USB endpoint address
 * @param data Data to send
 * @param size Size of data in bytes
 * @return THINGINO_SUCCESS on success, error code otherwise
 */
thingino_error_t send_bulk_data(usb_device_t* device, uint8_t endpoint, 
                                const uint8_t* data, uint32_t size);

#endif // FIRMWARE_WRITER_H

