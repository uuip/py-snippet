from ctypes import *
from ctypes import wintypes as w

import commctrl
import win32api
import win32con
import win32gui
import win32process

ReadProcessMemory = windll.kernel32.ReadProcessMemory
ReadProcessMemory.argtypes = [
    w.HANDLE,
    w.LPCVOID,
    w.LPVOID,
    c_size_t,
    POINTER(c_size_t),
]
ReadProcessMemory.restype = w.BOOL

tray_handles = set()


class TBBUTTON(Structure):
    _fields_ = [
        ("iBitmap", w.INT),
        ("idCommand", w.INT),
        ("fsState", w.BYTE),
        ("fsStyle", w.BYTE),
        ("bReserved", w.BYTE * 6),  # 32位是*2  w.byte*6
        ("dwData", w.DWORD),
        ("iString", w.INT),
    ]


class TRAYDATA64(Structure):
    _fields_ = [
        ("hWnd", w.HWND),
        ("uID", w.UINT),
        ("uCallbackMessage", w.UINT),
        ("Reserved22", w.WORD * 4),  # w.DWORD * 2
        ("hIcon", w.HICON),
        ("Reserved2", w.DWORD * 4),
        ("szExePath", w.WCHAR * w.MAX_PATH),
        ("szTip", w.WCHAR * 128),
    ]


def print_strc(icon_data):
    for attrib in icon_data.__dir__():
        if not attrib.startswith("_"):
            data = getattr(icon_data, attrib)
            if attrib.startswith("Reserved"):
                continue
                # data = [x for x in data]
            print(attrib, data, sep=":", end=", ")
    print("\n")


tray_paths = [
    "Shell_TrayWnd/TrayNotifyWnd/SysPager/ToolbarWindow32",
    "NotifyIconOverflowWindow/ToolbarWindow32",
]

for classpath in tray_paths:
    name = classpath.split("/")
    hwnd = 0
    for n in name:
        if hwnd == 0:
            hwnd = win32gui.FindWindow(n, None)
        else:
            hwnd = win32gui.FindWindowEx(hwnd, 0, n, None)
    tray_handles.add(hwnd)

for tray_hwnd in tray_handles:
    pid = win32process.GetWindowThreadProcessId(tray_hwnd)[1]
    hProcess = win32api.OpenProcess(
        win32con.PROCESS_VM_WRITE | win32con.PROCESS_VM_READ | win32con.PROCESS_VM_OPERATION,
        0,
        pid,
    )
    lpPointer = win32process.VirtualAllocEx(
        hProcess, 0, sizeof(TBBUTTON), win32con.MEM_COMMIT, win32con.PAGE_READWRITE
    )
    tbbutton = TBBUTTON()
    icon_data = TRAYDATA64()

    count = win32gui.SendMessage(tray_hwnd, commctrl.TB_BUTTONCOUNT, 0, 0)
    icon_data_del = []
    for i in range(count):
        win32gui.SendMessage(tray_hwnd, commctrl.TB_GETBUTTON, i, lpPointer)
        # struct unpack field bReserved to six independent item, so use kernel32 module instead
        # info = win32process.ReadProcessMemory(hProcess, lpPointer, sizeof(TBBUTTON))
        # BOOL ReadProcessMemory(
        #   [in]  HANDLE  hProcess,
        #   [in]  LPCVOID lpBaseAddress,
        #   [out] LPVOID  lpBuffer,
        #   [in]  SIZE_T  nSize,
        #   [out] SIZE_T  *lpNumberOfBytesRead
        # );
        ReadProcessMemory(hProcess.handle, lpPointer, addressof(tbbutton), sizeof(TBBUTTON), None)
        # read the 1st 4 bytes from the dwData into the butHandle var
        ReadProcessMemory(
            hProcess.handle,
            tbbutton.dwData,
            addressof(icon_data),
            sizeof(TRAYDATA64),
            None,
        )
        threadId, processId = win32process.GetWindowThreadProcessId(icon_data.hWnd)
        # print_strc(icon_data)
        if threadId == 0 or processId == 244737584 or processId == 0:
            icon_data_del.append((icon_data.hWnd, icon_data.uID))
    for item in icon_data_del:
        win32gui.Shell_NotifyIcon(win32gui.NIM_DELETE, item)

    win32process.VirtualFreeEx(hProcess, lpPointer, sizeof(TBBUTTON), win32con.MEM_DECOMMIT)
    win32process.VirtualFreeEx(hProcess, lpPointer, 0, win32con.MEM_RELEASE)
    win32api.CloseHandle(hProcess)
