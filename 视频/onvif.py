# coding=utf-8

import re
from pathlib import Path

import zeep
from zeep import Client, Settings, Transport
from zeep.cache import SqliteCache
from zeep.wsse import UsernameToken


class OnvifCam:
    SERVICES = {
        "devicemgmt": {
            "namespace": "http://www.onvif.org/ver10/device/wsdl",
            "wsdl": "devicemgmt.wsdl",
            "binding": "DeviceBinding",
            "ns_prefix": "tds",
        },
        "media": {
            "namespace": "http://www.onvif.org/ver10/media/wsdl",
            "wsdl": "media.wsdl",
            "binding": "MediaBinding",
            "ns_prefix": "trt",
        },
    }

    def __init__(self, ip, port, username, password):
        self.transport = Transport(cache=SqliteCache())
        self.transport.operation_timeout = 10
        self.ip = ip
        self.port = int(port)
        self.username = username
        self.password = password
        self.devicemgmt_service = None
        self.xaddrs = {}
        self.media_profiles = None
        self.media_service = None
        if username:
            self.wsse = UsernameToken(username, password, use_digest=True)
        else:
            self.wsse = None

    def creat_service(self, name, xaddr=None):
        if getattr(self, name + "_service"):
            return

        namespace = self.SERVICES[name]["namespace"]
        wsdl = self.SERVICES[name]["wsdl"]
        binding = self.SERVICES[name]["binding"]
        ns_prefix = self.SERVICES[name]["ns_prefix"]
        xaddr = self.__define_xaddr(name, xaddr)

        wsdl_path = Path(__file__).absolute().parent / "wsdl" / wsdl
        if not wsdl_path.is_file():
            wsdl_path = str(wsdl_path)
        else:
            wsdl_path = namespace.replace("http:", "https:") + "/" + wsdl

        settings = Settings(strict=False, xml_huge_tree=True)
        client = Client(wsdl_path, transport=self.transport, wsse=self.wsse, settings=settings)
        # zeep不能识别wsdl中指定的namespace, wsdl中的参数类型在onvif.xsd(ns:tt)中指定.正确指定后可以使用zeep的多种数据结构构造参数。
        # 对于wsdl中的操作,zeep发送的是关键字参数
        client.set_ns_prefix(ns_prefix, namespace)
        client.set_ns_prefix("tt", "http://www.onvif.org/ver10/schema")
        service = client.create_service("{{{}}}{}".format(namespace, binding), xaddr)
        setattr(self, name + "_service", service)
        if name == "media":
            self.fetch_media_profiles()

    def fetch_media_profiles(self):
        if not self.media_profiles:
            self.media_profiles = self.media_service.GetProfiles()

    def get_device_info(self):
        info = self.devicemgmt_service.GetDeviceInformation()
        return info

    def __define_xaddr(self, name, xaddr):
        if name == "devicemgmt":  # onvif/device_service 是固定值
            xaddr = "http://{!s}:{!s}/onvif/device_service".format(self.ip, self.port)
        elif xaddr:
            if not xaddr.startswith("http"):
                xaddr = "http://{!s}:{!s}/onvif/{}".format(self.ip, self.port, xaddr)
            else:
                return xaddr
        else:
            self.creat_service("devicemgmt")
            self.__fetch_xaddr()
            xaddr = self.xaddrs[name]
        return xaddr

    def __fetch_xaddr(self):
        capabilities = self.devicemgmt_service.GetCapabilities(Category="All")
        for name in capabilities:
            capability = capabilities[name]
            name = name.lower()
            if name in self.SERVICES and capability is not None:
                # 替换返回内网地址的url
                if self.ip in capability["XAddr"]:
                    self.xaddrs[name] = capability["XAddr"]
                else:
                    self.xaddrs[name] = re.sub(
                        "://.+?/",
                        "://{}:{}/".format(self.ip, self.port),
                        capability["XAddr"],
                    )

    def get_snapshot_urls(self):
        image_uris = []
        video_last_flag = 4321
        for profile in self.media_profiles:
            profiletoken = profile.token
            video_last_flag_ = video_last_flag
            try:
                video_flag = video_last_flag = int(re.findall(r"\d+", profiletoken)[0])
            except IndexError:
                video_flag = video_last_flag
            if video_flag - video_last_flag_ == 1:
                continue
            uri = self.media_service.GetSnapshotUri(profiletoken).Uri
            image_uris.extend(self.format_url(uri))

        return image_uris

    def get_stream_urls(self):
        stream_uris = []
        streamsetup = {"Stream": "RTP-Unicast", "Transport": {"Protocol": "RTSP"}}
        video_last_flag = 4321
        for profile in self.media_profiles:
            profiletoken = profile.token
            video_last_flag_ = video_last_flag
            try:
                video_flag = video_last_flag = int(re.findall(r"\d+", profiletoken)[0])
            except IndexError:
                video_flag = video_last_flag
            if video_flag - video_last_flag_ == 1:
                continue
            uri = self.media_service.GetStreamUri(
                StreamSetup=streamsetup, ProfileToken=profiletoken
            ).Uri
            stream_uris.extend(self.format_url(uri))

        return stream_uris

    def format_url(self, url):
        urls = []
        mult_port = re.findall(r":\d+", url)
        if len(mult_port) > 1:
            mult_port = set(mult_port)
            for x in mult_port:
                right_url = url.replace(x, "")
                if self.password:
                    right_url = right_url.replace(
                        "://", "://{}:{}@".format(self.username, self.password)
                    )
                urls.append(right_url)
        else:
            right_url = url
            if self.password:
                right_url = right_url.replace(
                    "://", "://{}:{}@".format(self.username, self.password)
                )
            urls.append(right_url)
        return urls

    @staticmethod
    def zeep_pythonvalue(xmlvalue):
        return xmlvalue

    # NotImplementedError: AnySimpleType.pytonvalue() not implemented
    zeep.xsd.AnySimpleType.pythonvalue = zeep_pythonvalue
