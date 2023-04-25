import time

import requests
import win32gui
from bs4 import BeautifulSoup
from colorama import init, Fore, Style

wnd = win32gui.GetForegroundWindow()
win32gui.SetWindowText(wnd, "检查流星更新")
# w = win32console.GetStdHandle(win32console.STD_OUTPUT_HANDLE)
# w.SetConsoleTextAttribute(win32console.FOREGROUND_GREEN)
init()
while 1:
    rsp = requests.get("https://apps.apple.com/cn/app/id1381385225")
    html = BeautifulSoup(rsp.text, "html5lib")
    subtitle = html.body.select_one(".app-header__subtitle").text
    if subtitle != "硬核动作手游·乾坤一棍":
        print(Fore.GREEN + Style.BRIGHT + "游戏有更新")
        break
    else:
        print(Fore.LIGHTRED_EX + Style.BRIGHT + "没有没有没有")
        time.sleep(5)
win32gui.SetForegroundWindow(wnd)
input()
