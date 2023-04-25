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

v.click()
if not clash.exists(timeout=1):
    v.click()
    clash = tray.child_window(title_re="(^Clash.*$)|(^$)", control_type="Button")
    if not clash.exists(timeout=1):
        win32api.SetCursorPos((x, y))
        exit()
else:
    Overflow_flag = True

clash.click_input(button="right")
popmenu = d.window(class_name="Chrome_WidgetWin_2")
popmenu.Menu.Quit.select()
if Overflow_flag:
    v.click_input()
win32api.SetCursorPos((x, y))
