cmake_minimum_required(VERSION 3.10)
project(thingino-cloner VERSION 1.0.0 LANGUAGES C)

# Set C standard
set(CMAKE_C_STANDARD 99)
set(CMAKE_C_STANDARD_REQUIRED ON)

# Find required packages
set(LIBUSB_PKG_FOUND FALSE)
if (CMAKE_CROSSCOMPILING)
    find_package(PkgConfig QUIET)
else()
    find_package(PkgConfig REQUIRED)
endif()

if (PkgConfig_FOUND)
    pkg_check_modules(LIBUSB_PKG libusb-1.0)
endif()

set(LIBUSB_INCLUDE_DIRS "")
set(LIBUSB_LIBRARIES "")

set(_VENDORED_LIBUSB_ROOT "")
if (CMAKE_SYSTEM_NAME STREQUAL "Windows" OR WIN32 OR CMAKE_CROSSCOMPILING)
    set(_libusb_arch "x86_64")
    if (CMAKE_SYSTEM_PROCESSOR MATCHES "i[3-6]86" OR CMAKE_SYSTEM_PROCESSOR STREQUAL "x86")
        set(_libusb_arch "x86")
    endif()
    set(_vendor_candidate "${CMAKE_CURRENT_SOURCE_DIR}/third_party/libusb/windows/${_libusb_arch}")
    if (EXISTS "${_vendor_candidate}")
        set(_VENDORED_LIBUSB_ROOT "${_vendor_candidate}")
    endif()
endif()

if (LIBUSB_PKG_FOUND AND NOT CMAKE_CROSSCOMPILING)
    set(LIBUSB_INCLUDE_DIRS ${LIBUSB_PKG_INCLUDE_DIRS})
    # Use full linker flags on macOS to ensure library paths are included
    if (APPLE AND LIBUSB_PKG_LDFLAGS)
        set(LIBUSB_LIBRARIES ${LIBUSB_PKG_LDFLAGS})
    else()
        set(LIBUSB_LIBRARIES ${LIBUSB_PKG_LIBRARIES})
    endif()
    # Also add library directories to linker search path
    if (LIBUSB_PKG_LIBRARY_DIRS)
        link_directories(${LIBUSB_PKG_LIBRARY_DIRS})
    endif()
endif()

set(LIBUSB_SEARCH_DIRS)
if (LIBUSB_ROOT)
    list(APPEND LIBUSB_SEARCH_DIRS "${LIBUSB_ROOT}")
endif()
if (_VENDORED_LIBUSB_ROOT)
    list(APPEND LIBUSB_SEARCH_DIRS "${_VENDORED_LIBUSB_ROOT}")
endif()
list(APPEND LIBUSB_SEARCH_DIRS /usr /usr/local /opt/homebrew)
list(REMOVE_DUPLICATES LIBUSB_SEARCH_DIRS)

set(_LIBUSB_MULTIARCH "")
if (UNIX AND NOT APPLE)
    set(_libusb_multiarch_compiler "${CMAKE_C_COMPILER}")
    if (NOT _libusb_multiarch_compiler AND CMAKE_CXX_COMPILER)
        set(_libusb_multiarch_compiler "${CMAKE_CXX_COMPILER}")
    endif()
    if (_libusb_multiarch_compiler)
        execute_process(
            COMMAND ${_libusb_multiarch_compiler} -print-multiarch
            OUTPUT_VARIABLE _LIBUSB_MULTIARCH
            OUTPUT_STRIP_TRAILING_WHITESPACE
            ERROR_QUIET)
    endif()
endif()

if (NOT LIBUSB_INCLUDE_DIRS OR NOT LIBUSB_LIBRARIES)
    set(LIBUSB_INCLUDE_HINTS)
    set(LIBUSB_LIBRARY_HINTS)
    foreach(dir IN LISTS LIBUSB_SEARCH_DIRS)
        list(APPEND LIBUSB_INCLUDE_HINTS "${dir}/include" "${dir}/include/libusb-1.0")
        list(APPEND LIBUSB_LIBRARY_HINTS "${dir}/lib" "${dir}/lib64" "${dir}/lib/libusb-1.0" "${dir}/bin")
        if (_LIBUSB_MULTIARCH)
            list(APPEND LIBUSB_LIBRARY_HINTS
                "${dir}/lib/${_LIBUSB_MULTIARCH}"
                "${dir}/lib/${_LIBUSB_MULTIARCH}/libusb-1.0"
                "${dir}/lib64/${_LIBUSB_MULTIARCH}")
        endif()
    endforeach()

    find_path(LIBUSB_INCLUDE_DIR
        NAMES libusb-1.0/libusb.h libusb.h
        HINTS ${LIBUSB_INCLUDE_HINTS})

    find_library(LIBUSB_LIBRARY
        NAMES usb-1.0 libusb-1.0
        HINTS ${LIBUSB_LIBRARY_HINTS})

    if (LIBUSB_INCLUDE_DIR AND LIBUSB_LIBRARY)
        set(LIBUSB_INCLUDE_DIRS ${LIBUSB_INCLUDE_DIR})
        set(LIBUSB_LIBRARIES ${LIBUSB_LIBRARY})
    endif()
endif()

if (NOT LIBUSB_INCLUDE_DIRS OR NOT LIBUSB_LIBRARIES)
    message(FATAL_ERROR "libusb-1.0 not found. Set LIBUSB_ROOT to the library location or install libusb-1.0.")
endif()

set(_LIBUSB_INCLUDE_DIRS_NORMALIZED)
foreach(dir IN LISTS LIBUSB_INCLUDE_DIRS)
    list(APPEND _LIBUSB_INCLUDE_DIRS_NORMALIZED "${dir}")
    get_filename_component(_libusb_dir_name "${dir}" NAME)
    if (_libusb_dir_name STREQUAL "libusb-1.0")
        get_filename_component(_libusb_parent "${dir}" DIRECTORY)
        list(APPEND _LIBUSB_INCLUDE_DIRS_NORMALIZED "${_libusb_parent}")
    endif()
endforeach()
list(REMOVE_DUPLICATES _LIBUSB_INCLUDE_DIRS_NORMALIZED)
set(LIBUSB_INCLUDE_DIRS ${_LIBUSB_INCLUDE_DIRS_NORMALIZED})

# Include directories
include_directories(${LIBUSB_INCLUDE_DIRS})
include_directories(include)
include_directories(src)
include_directories(src/ddr)
include_directories(src/firmware)

# Compiler flags
add_compile_options(-Wall -Wextra -Werror)
if (LIBUSB_PKG_FOUND AND LIBUSB_PKG_CFLAGS_OTHER)
    add_compile_options(${LIBUSB_PKG_CFLAGS_OTHER})
endif()

# Source files
set(SOURCES
    src/main.c
    src/usb/manager.c
    src/usb/device.c
    src/usb/protocol.c
    src/firmware/loader.c
    src/firmware/reader.c
    src/firmware/writer.c
    src/firmware/handshake.c
    src/firmware/flash_descriptor.c
    src/ddr/parser.c
    src/ddr/ddr_utils.c
    src/ddr/ddr_controller.c
    src/ddr/ddr_param_builder.c
    src/ddr/ddr_phy.c
    src/ddr/ddr_phy_ddr2.c
    src/ddr/ddr_ctrl_txx.c
    src/ddr/ddr_generator.c
    src/ddr/ddr_binary_builder.c
    src/ddr/crc32.c
    src/ddr/ddr_config_database.c
    src/utils.c
    src/bootstrap.c
)

# Firmware database files (auto-generated)
file(GLOB FIRMWARE_SOURCES "src/firmware/firmware_*.c")
list(APPEND SOURCES ${FIRMWARE_SOURCES})

# Create executable
add_executable(thingino-cloner ${SOURCES})

# Link libraries
target_link_libraries(thingino-cloner ${LIBUSB_LIBRARIES})

# Test executable for DDR generator
add_executable(test_ddr_generator
    tests/unit/ddr/test_ddr_generator.c
    src/ddr/ddr_utils.c
    src/ddr/ddr_controller.c
    src/ddr/ddr_param_builder.c
    src/ddr/ddr_phy.c
    src/ddr/ddr_phy_ddr2.c
    src/ddr/ddr_ctrl_txx.c
    src/ddr/ddr_generator.c
)

# Test executable for multi-chip DDR generation
add_executable(test_ddr_multiplechip
    tests/unit/ddr/test_ddr_multiplechip.c
    src/ddr/ddr_utils.c
    src/ddr/ddr_controller.c
    src/ddr/ddr_param_builder.c
    src/ddr/ddr_phy.c
    src/ddr/ddr_phy_ddr2.c
    src/ddr/ddr_ctrl_txx.c
    src/ddr/ddr_generator.c
)

# Test executable for reference binary analysis
add_executable(test_ddr_reference_analysis
    tests/unit/ddr/test_ddr_reference_analysis.c
)

# Test executable for DDR mapping analysis
add_executable(test_ddr_mapping_analysis
    tests/unit/ddr/test_ddr_mapping_analysis.c
    src/ddr/ddr_utils.c
    src/ddr/ddr_controller.c
    src/ddr/ddr_param_builder.c
    src/ddr/ddr_phy.c
    src/ddr/ddr_phy_ddr2.c
    src/ddr/ddr_ctrl_txx.c
    src/ddr/ddr_generator.c
)

# Test executable for TXX mapping analysis
add_executable(test_txx_mapping_analysis
    tests/unit/ddr/test_txx_mapping_analysis.c
)

# Test executable for DDRC analysis
add_executable(test_ddrc_analysis
    tests/unit/ddr/test_ddrc_analysis.c
)

# Test executable for new binary builder
add_executable(test_binary_builder
    tests/unit/ddr/test_binary_builder.c
    src/ddr/ddr_binary_builder.c
    src/ddr/crc32.c
    src/ddr/ddr_config_database.c
)

# Test executable for DDR integration
add_executable(test_ddr_integration
    tests/unit/ddr/test_ddr_integration.c
    src/ddr/ddr_binary_builder.c
    src/ddr/crc32.c
    src/ddr/ddr_config_database.c
)

# Test executable for configuration database
add_executable(test_config_database
    tests/unit/ddr/test_config_database.c
    src/ddr/ddr_binary_builder.c
    src/ddr/crc32.c
    src/ddr/ddr_config_database.c
)

# Test firmware database
add_executable(test_firmware_database
    tests/unit/firmware/test_firmware_database.c
    ${FIRMWARE_SOURCES}
)

# Installation
install(TARGETS thingino-cloner DESTINATION bin)

# Platform-specific settings
if(WIN32)
    # Windows-specific settings
    target_compile_definitions(thingino-cloner PRIVATE _WIN32)
elseif(APPLE)
    # macOS-specific settings
    target_compile_definitions(thingino-cloner PRIVATE __APPLE__)
else()
    # Linux-specific settings
    target_compile_definitions(thingino-cloner PRIVATE __linux__)
endif()