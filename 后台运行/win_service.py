import servicemanager
import win32event
import win32service
import win32serviceutil


class PySvc(win32serviceutil.ServiceFramework):
    _svc_name_ = "svc_name"
    _svc_display_name_ = "svc_display_name"
    _svc_description_ = "svc_description"

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        # create an event to listen for stop requests on
        self.hWaitStop = win32event.CreateEvent(None, 0, 0, None)

    # core logic of the service
    def SvcDoRun(self):
        self.start()
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STARTED,
            (self._svc_name_, ""),
        )
        # WaitForSingleObject 必须在后面, 否则启动出错
        win32event.WaitForSingleObject(self.hWaitStop, win32event.INFINITE)

    # called when we're being shut down
    def SvcStop(self):
        # tell the SCM we're shutting down，后面不需要汇报stoped状态，加了后在日志查看器是错误
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        # 这些语句的顺序固定，否则停止出错，并在Windows日志查看器中报错
        self.stop()
        # fire the stop event
        win32event.SetEvent(self.hWaitStop)
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, ""),
        )

    def start(self):
        # 在新线程启动
        pass

    def stop(self):
        pass


if __name__ == "__main__":
    # 1. 复制 'site-packages\pywin32_system32\pywintypes39.dll' 到
    #   site-packages\win32
    # 2. pywin32不会加载用户目录的包 C:\Users\username\AppData\Roaming\Python\Python39\site-packages
    # 3. 手动添加Windows防火墙例外 "site-packages\win32\pythonservice.exe"
    # 4. 其他类继承了PySvc，则下面要写子类的名称！！
    # 5. python filename.py install 执行安装服务，此服务的工作目录为执行install时所在的目录。

    # if len(sys.argv) == 1:  # 这段没必要，装好服务后，通过Windows的服务管理器操作
    #     servicemanager.Initialize()
    #     servicemanager.PrepareToHostSingle(PySvc)
    #     servicemanager.StartServiceCtrlDispatcher()
    # else:
    win32serviceutil.HandleCommandLine(PySvc)
