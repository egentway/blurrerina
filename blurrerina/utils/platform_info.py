import functools
import platform

from cuda.bindings import driver
from cuda.bindings import runtime


@functools.cache
def is_wsl():
    with open("/proc/version", "r") as version_file:
        version_info = version_file.readline().lower()
        return "microsoft" in version_info


@functools.cache
def is_integrated_gpu():
    result, = driver.cuInit(0)
    if result != driver.CUresult.CUDA_SUCCESS:
        raise RuntimeError(f"cuInit failed: {result}")

    result, devices_count = driver.cuDeviceGetCount()
    if result != driver.CUresult.CUDA_SUCCESS:
        raise RuntimeError(f"cuDeviceGetCount failed: {result}")
    if devices_count < 1:
        raise RuntimeError("No cuda devices found")

    result, properties = runtime.cudaGetDeviceProperties(0)
    if result != runtime.cudaError_t.cudaSuccess:
        raise RuntimeError(f"cudaDeviceGetProperties failed: {result}")

    return properties.integrated


@functools.cache
def is_platform_aarch64():
    return platform.uname()[4] == 'aarch64'