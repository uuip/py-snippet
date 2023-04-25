import re
import sys
import winreg

import requests
from PySide6.QtCore import (
    QCoreApplication,
    Qt,
    QThreadPool,
    QRunnable,
    Signal,
    QObject,
    SignalInstance,
    Slot,
)
from PySide6.QtGui import QIcon, QCursor, QAction, QActionGroup
from PySide6.QtWidgets import QSystemTrayIcon, QApplication, QMenu, QDialog

from clash_ui import Ui_Dialog


def read_setting():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"SOFTWARE\myclash") as key:
            hostport = winreg.QueryValueEx(key, "hostport")[0]
            token = winreg.QueryValueEx(key, "token")[0]
            include = winreg.QueryValueEx(key, "include")[0]
            exclude = winreg.QueryValueEx(key, "exclude")[0]
    except FileNotFoundError:
        hostport = "127.0.0.1:5555"
        token = ""
        include = ""
        exclude = ""
    return hostport, token, include, exclude


def write_setting(hostport, token, include, exclude):
    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, r"SOFTWARE\myclash") as key:
        winreg.SetValueEx(key, "hostport", 0, winreg.REG_SZ, hostport)
        winreg.SetValueEx(key, "token", 0, winreg.REG_SZ, token)
        winreg.SetValueEx(key, "include", 0, winreg.REG_SZ, include)
        winreg.SetValueEx(key, "exclude", 0, winreg.REG_SZ, exclude)
        winreg.FlushKey(key)


class TaskSignal(QObject):
    finished: SignalInstance = Signal()
    result: SignalInstance = Signal(object)
    error: SignalInstance = Signal(int)
    # note:
    # QObject.connect(obj1, SIGNAL('foo(int)'), self.callback)
    # QObject.disconnect(obj1, SIGNAL('foo(int)'), self.callback)
    # group['q_group'].disconnect(None, None, None)


class Task(QRunnable):
    def __init__(self, fun):
        super().__init__()
        self.fun = fun
        self.signals = TaskSignal()

    def run(self):
        return self.fun()


class SettingDialog(QDialog, Ui_Dialog):
    def __init__(self):
        QDialog.__init__(self)
        self.setupUi(self)
        self.retranslateUi(self)
        self.update_setting()

    def update_setting(self):
        hostport, token, include, exclude = read_setting()
        self.hostport.setText(hostport)
        self.token.setText(token)
        self.include.setText(include)
        self.exclude.setText(exclude)

    def closeEvent(self, event):
        event.ignore()
        self.hide()

    def showEvent(self, event):
        self.update_setting()

    @Slot()
    def accept(self) -> None:
        hostport = self.hostport.text().replace("：", ":")
        token = self.token.text()
        include = self.include.text().replace("，", ",")
        exclude = self.exclude.text().replace("，", ",")
        write_setting(hostport, token, include, exclude)
        self.hide()

    @Slot()
    def reject(self) -> None:
        self.hide()


class Main(QSystemTrayIcon):
    def __init__(self):
        QSystemTrayIcon.__init__(self, QIcon("proxy.png"))
        self.pool = QThreadPool()
        self.menu = QMenu()
        self.proxies = {}
        self.has_sep = None
        self.setting = SettingDialog()
        self.setting.buttonBox.accepted.connect(self.update_menu)
        self.activated.connect(self.icon_activated)
        self.read_reg_setting()
        self.setVisible(True)
        self.setToolTip("proxy")
        self.init_menu()

    def filter_node(self, proxies):
        for k, v in proxies.copy().items():
            if v["type"] != "Selector":
                proxies.pop(k)
                continue
            if set(v.get("all", [])) & set(proxies.keys()):
                proxies[k]["isbaseproxygroup"] = False
                continue
            for node in v["all"][:]:
                if (not self.include.search(node)) or self.exclude.search(node):
                    proxies[k]["all"].remove(node)
            proxies[k]["all"].sort(key=self.sort_node)
            proxies[k]["isbaseproxygroup"] = True
        return proxies

    def sort_node(self, item):
        if "港" in item:
            return 0, item
        return 1, item

    def read_reg_setting(self):
        self.hostport, token, include, exclude = read_setting()
        self.auth = {"Authorization": f"Bearer {token}"}
        self.include = re.compile(re.sub("(\s|,)+", "|", include))
        self.exclude = re.compile(re.sub("(\s|,)+", "|", exclude) or "^$")

    def init_menu(self):
        menu = self.menu
        menu.addSeparator()
        self.update_nodes()
        mode = requests.get(f"http://{self.hostport}/configs", headers=self.auth).json()["mode"]
        group_mode = QActionGroup(menu)
        group_mode.triggered.connect(self.select_mode)
        group_mode.setExclusive(True)
        for x in ["Global", "Rule", "Direct"]:
            action = QAction(x, self, checkable=True, checked=x.lower() == mode.lower())
            menu.addAction(action)
            group_mode.addAction(action)
        menu.addSeparator()

        menu.addAction("设置", self.setting.show)
        menu.addAction("退出", app.exit)
        self.setContextMenu(menu)

    @Slot()
    def update_nodes(self):
        proxies = requests.get(f"http://{self.hostport}/proxies", headers=self.auth).json()[
            "proxies"
        ]
        mode = requests.get(f"http://{self.hostport}/configs", headers=self.auth).json()["mode"]
        proxies = self.filter_node(proxies)

        # 更新模式
        for x in self.menu.children():
            if isinstance(x, QActionGroup):
                for y in x.actions():
                    if y.text().lower() == mode.lower():
                        y.setChecked(True)
                        break

        last_base = None
        for i, k in enumerate(
            sorted(
                proxies,
                key=lambda x: (not proxies[x]["isbaseproxygroup"], x),
                reverse=True,
            )
        ):
            v = proxies[k]
            if k in self.proxies:
                menu_k: QMenu = self.proxies[k]["menu"]
                group_k: QActionGroup = self.proxies[k]["group"]
                for node in menu_k.actions():  # type:QAction
                    menu_k.removeAction(node)
                    group_k.removeAction(node)
                menu_k.clear()
            else:
                menu_k = QMenu(k)
                self.menu.insertMenu(self.menu.actions()[0], menu_k)
                group_k = QActionGroup(menu_k)
                group_k.setProperty("name", k)
                group_k.setExclusive(True)
                group_k.triggered.connect(self.select_proxy)
            for p in sorted(v["all"], key=self.sort_node):
                action = QAction(p, menu_k, checkable=True, checked=p == v["now"])
                menu_k.addAction(action)
                group_k.addAction(action)
            self.proxies[k] = v | {"group": group_k, "menu": menu_k}
            if (
                not self.has_sep
                and last_base is not None
                and last_base != v["isbaseproxygroup"]
                and i > 1
            ):
                self.menu.insertSeparator(self.menu.actions()[i - 1])
                self.has_sep = True
            else:
                last_base = v["isbaseproxygroup"]

        for k in set(self.proxies.keys()) - set(proxies.keys()):
            menu_k = self.proxies[k]["menu"]
            group_k = self.proxies[k]["group"]
            for node in menu_k.actions():
                menu_k.removeAction(node)
                group_k.removeAction(node)
            menu_k.clear()
            menu_k.destroy()
            group_k.triggered.disconnect(self.select_proxy)
            group_k.deleteLater()
            for ak in self.menu.actions():
                if ak.text() == k:
                    self.menu.removeAction(ak)
            self.proxies.pop(k)

    @Slot()
    def update_menu(self):
        self.read_reg_setting()
        self.update_nodes()

    @Slot()
    def icon_activated(self, reason):
        self.update_nodes()
        if reason in {QSystemTrayIcon.Trigger, QSystemTrayIcon.Context}:
            self.contextMenu().popup(QCursor.pos())

    @Slot()
    def select_mode(self, action):
        # self.sender()对象不能用在lambda中
        mode = action.text()
        req = lambda: requests.patch(f"http://{self.hostport}/configs", json={"mode": mode})
        self.pool.start(Task(req))

    @Slot()
    def select_proxy(self, action):
        group = action.actionGroup().property("name")
        proxy = action.text()
        req = lambda: requests.put(f"http://{self.hostport}/proxies/{group}", json={"name": proxy})
        self.pool.start(Task(req))


if __name__ == "__main__":
    QCoreApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
    QCoreApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
    app = QApplication()
    gallery = Main()
    sys.exit(app.exec())
