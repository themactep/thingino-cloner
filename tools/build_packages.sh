#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_ROOT="${ROOT}/build-release"
DIST_DIR="${ROOT}/dist"
LINUX_BUILD="${BUILD_ROOT}/linux"
WINDOWS_BUILD="${BUILD_ROOT}/windows"
LINUX_STAGE="${DIST_DIR}/thingino-cloner-linux-x86_64"
WINDOWS_STAGE="${DIST_DIR}/thingino-cloner-windows-x86_64"
WINDOWS_TOOLCHAIN="${ROOT}/cmake/toolchains/mingw-w64-x86_64.cmake"
WINDOWS_LIBUSB_DLL="${ROOT}/third_party/libusb/windows/x86_64/bin/libusb-1.0.dll"
command -v cmake >/dev/null || { echo "cmake is required" >&2; exit 1; }
rm -rf "${BUILD_ROOT}"
mkdir -p "${LINUX_BUILD}" "${WINDOWS_BUILD}" "${DIST_DIR}"
cmake -S "${ROOT}" -B "${LINUX_BUILD}" -DCMAKE_BUILD_TYPE=Release
cmake --build "${LINUX_BUILD}" --config Release
LINUX_BIN="${LINUX_BUILD}/thingino-cloner"
[[ -f "${LINUX_BIN}" ]] || { echo "Linux binary not found" >&2; exit 1; }
rm -rf "${LINUX_STAGE}"
mkdir -p "${LINUX_STAGE}"
cp "${LINUX_BIN}" "${LINUX_STAGE}/thingino-cloner"
if [[ -f "${ROOT}/README.md" ]]; then cp "${ROOT}/README.md" "${LINUX_STAGE}/"; fi
cmake -S "${ROOT}" -B "${WINDOWS_BUILD}" -DCMAKE_BUILD_TYPE=Release -DCMAKE_TOOLCHAIN_FILE="${WINDOWS_TOOLCHAIN}"
cmake --build "${WINDOWS_BUILD}" --config Release
WINDOWS_BIN="${WINDOWS_BUILD}/thingino-cloner.exe"
[[ -f "${WINDOWS_BIN}" ]] || { echo "Windows binary not found" >&2; exit 1; }
[[ -f "${WINDOWS_LIBUSB_DLL}" ]] || { echo "libusb DLL not found" >&2; exit 1; }
rm -rf "${WINDOWS_STAGE}"
mkdir -p "${WINDOWS_STAGE}"
cp "${WINDOWS_BIN}" "${WINDOWS_STAGE}/thingino-cloner.exe"
cp "${WINDOWS_LIBUSB_DLL}" "${WINDOWS_STAGE}/"
if [[ -f "${ROOT}/README.md" ]]; then cp "${ROOT}/README.md" "${WINDOWS_STAGE}/"; fi
cmake -E chdir "${DIST_DIR}" cmake -E tar cfz thingino-cloner-linux-x86_64.tar.gz "$(basename "${LINUX_STAGE}")"
cmake -E chdir "${DIST_DIR}" cmake -E tar cf thingino-cloner-windows-x86_64.zip --format=zip "$(basename "${WINDOWS_STAGE}")"
echo "Linux package: ${DIST_DIR}/thingino-cloner-linux-x86_64.tar.gz"
echo "Windows package: ${DIST_DIR}/thingino-cloner-windows-x86_64.zip"
