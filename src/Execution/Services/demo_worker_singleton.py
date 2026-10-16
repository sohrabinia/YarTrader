"""Cross-process singleton guard shared by the service-hosted and scheduled DEMO workers."""
import ctypes
import os
from typing import Optional

_MUTEX_HANDLE: Optional[int] = None


def acquire_demo_worker_singleton() -> bool:
    """Return True only for the process that owns the DEMO worker mutex."""
    global _MUTEX_HANDLE
    if os.name != "nt":
        return True
    if _MUTEX_HANDLE is not None:
        return True
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel32.CreateMutexW.argtypes = [ctypes.c_void_p, ctypes.c_bool, ctypes.c_wchar_p]
    kernel32.CreateMutexW.restype = ctypes.c_void_p
    kernel32.CloseHandle.argtypes = [ctypes.c_void_p]
    ctypes.set_last_error(0)
    handle = kernel32.CreateMutexW(None, True, r"Global\YarTrader_BaseBehaviorDemoWorker")
    if not handle:
        raise OSError(f"Could not create DEMO worker singleton mutex (WinError {ctypes.get_last_error()}).")
    if ctypes.get_last_error() == 183:  # ERROR_ALREADY_EXISTS
        kernel32.CloseHandle(handle)
        return False
    _MUTEX_HANDLE = handle
    return True
