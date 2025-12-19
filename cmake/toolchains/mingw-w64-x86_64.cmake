# Thingino Cloner MinGW-w64 toolchain
# Usage: cmake -S . -B build-windows -DCMAKE_TOOLCHAIN_FILE=cmake/toolchains/mingw-w64-x86_64.cmake

set(CMAKE_SYSTEM_NAME Windows)
set(CMAKE_SYSTEM_PROCESSOR x86_64)

# Prefer the default Debian/Ubuntu MinGW tools but allow callers to override
set(CMAKE_C_COMPILER x86_64-w64-mingw32-gcc CACHE FILEPATH "")
set(CMAKE_CXX_COMPILER x86_64-w64-mingw32-g++ CACHE FILEPATH "")
set(CMAKE_RC_COMPILER x86_64-w64-mingw32-windres CACHE FILEPATH "")

# Ensure CMake looks inside the cross root and the vendored dependencies first
get_filename_component(_THINGINO_ROOT "${CMAKE_CURRENT_LIST_DIR}/../.." ABSOLUTE)
set(_THINGINO_LIBUSB_ROOT "${_THINGINO_ROOT}/third_party/libusb/windows/x86_64")

list(APPEND CMAKE_FIND_ROOT_PATH
    "${_THINGINO_LIBUSB_ROOT}"
    "/usr/x86_64-w64-mingw32"
)

set(CMAKE_FIND_ROOT_PATH_MODE_PROGRAM NEVER)
set(CMAKE_FIND_ROOT_PATH_MODE_LIBRARY ONLY)
set(CMAKE_FIND_ROOT_PATH_MODE_INCLUDE ONLY)
