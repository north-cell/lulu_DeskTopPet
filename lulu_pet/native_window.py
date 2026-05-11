from __future__ import annotations

import ctypes
import sys


def remove_windows_frame_artifacts(hwnd: int) -> None:
    if sys.platform != "win32" or not hwnd:
        return

    try:
        dwmapi = ctypes.WinDLL("dwmapi")
    except OSError:
        return

    # Windows 11 DWM attributes.
    DWMWA_NCRENDERING_POLICY = 2
    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWA_BORDER_COLOR = 34
    DWMWA_CAPTION_COLOR = 35
    DWMWA_TEXT_COLOR = 36
    DWMWA_SYSTEMBACKDROP_TYPE = 38

    DWMNCRP_DISABLED = 1
    DWMWCP_DONOTROUND = 1
    DWMWA_COLOR_NONE = 0xFFFFFFFE
    DWMSBT_NONE = 1

    _set_dwm_int(dwmapi, hwnd, DWMWA_NCRENDERING_POLICY, DWMNCRP_DISABLED)
    _set_dwm_int(dwmapi, hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_DONOTROUND)
    _set_dwm_int(dwmapi, hwnd, DWMWA_BORDER_COLOR, DWMWA_COLOR_NONE)
    _set_dwm_int(dwmapi, hwnd, DWMWA_CAPTION_COLOR, DWMWA_COLOR_NONE)
    _set_dwm_int(dwmapi, hwnd, DWMWA_TEXT_COLOR, DWMWA_COLOR_NONE)
    _set_dwm_int(dwmapi, hwnd, DWMWA_SYSTEMBACKDROP_TYPE, DWMSBT_NONE)


def _set_dwm_int(dwmapi, hwnd: int, attribute: int, value: int) -> None:
    data = ctypes.c_int(value)
    try:
        dwmapi.DwmSetWindowAttribute(
            ctypes.c_void_p(hwnd),
            ctypes.c_uint(attribute),
            ctypes.byref(data),
            ctypes.sizeof(data),
        )
    except OSError:
        return
