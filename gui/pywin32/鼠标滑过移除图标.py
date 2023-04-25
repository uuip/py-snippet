import time

import win32api
from pywinauto import Desktop
from pywinauto.timings import Timings

Timings.window_find_timeout = 1
Timings.window_find_retry = 0.5
Overflow_flag = False

d = Desktop(backend="uia")
x, y = win32api.GetCursorPos()

tray = d.window(class_name="Shell_TrayWnd").child_window(class_name="ToolbarWindow32")
v = d.window(class_name="Shell_TrayWnd").child_window(title="通知 V 形", control_type="Button")
Overflow = d.window(class_name="NotifyIconOverflowWindow").child_window(
    class_name="ToolbarWindow32"
)
clash = Overflow.child_window(title_re="(^Clash.*$)|(^$)", control_type="Button")

# clash.wait('visible')
v.click()
if not clash.exists(timeout=1):
    v.click()
    clash = tray.child_window(title_re="(^Clash.*$)|(^$)", control_type="Button")
    if not clash.exists(timeout=1):
        win32api.SetCursorPos((x, y))
        exit()
else:
    Overflow_flag = True

rectangle = clash.rectangle()
left = rectangle.left + 10
top = rectangle.top + 10
win32api.SetCursorPos((left, top))
time.sleep(0.2)
if Overflow_flag:
    v.click_input()
win32api.SetCursorPos((x, y))
# print(Overflow.handle)

# main_tray_toolbar = d.window(class_name='Shell_TrayWnd').child_window(class_name='ToolbarWindow32',
#                                                                       control_type="ToolBar")
# every = main_tray_toolbar.child_window(title_re="Everything.*", control_type="Button")
