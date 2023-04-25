import base64
import json
import re
import sys
import threading
from hashlib import md5
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, unquote

sys.path.append(
    r"C:\Users\sharp\AppData\Local\pypoetry\Cache\virtualenvs\clash-venv-TJP2DPxi-py3.9\Lib\site-packages"
)
sys.path.append(
    r"C:\Users\sharp\AppData\Local\pypoetry\Cache\virtualenvs\clash-venv-TJP2DPxi-py3.9\Lib\site-packages\win32\lib"
)
import requests
import yaml

from win_service import PySvc

include_re = re.compile("[港日]")
sip008_server_keys = [
    "id",
    "remarks",
    "server",
    "server_port",
    "password",
    "method",
    "plugin",
    "plugin_opts",
]

requests.adapters.DEFAULT_RETRIES = 3


def decode_b64(data):
    if len(data) % 4:
        data += "=" * (4 - (len(data) % 4))
    data = data.replace("-", "+").replace("_", "/")
    return base64.b64decode(data, validate=True).decode("utf-8")


def sort_node(item):
    name = item["name"]
    if re.search("(港|HK|Hong Kong)", name, re.IGNORECASE):
        return 0
    if re.search("(日|JP)", name, re.IGNORECASE):
        return 1
    if re.search("(台|TW)", name, re.IGNORECASE):
        return 2
    if re.search("(美|US)", name, re.IGNORECASE):
        return 3
    else:
        return 9


def parse_clash(data):
    clash = yaml.safe_load(data)
    clash.pop("rules")
    clash.pop("proxy-groups")
    proxies = [
        x
        for x in clash["proxies"]
        if include_re.search(x["name"]) and not re.search("公益", x["name"])
    ]
    proxies.sort(key=lambda x: x["name"])
    proxies.sort(key=sort_node)
    clash["proxies"] = proxies
    return yaml.safe_dump(clash, allow_unicode=True, encoding="utf-8", sort_keys=False)


def parse_ssr(text):
    proxies = []
    links = text.split("\n")
    for link in links:
        body = decode_b64(link[6:])
        if remark := re.search("remarks=(.*?)(&|$)", body):
            remark = decode_b64(remark[1])
            if include_re.search(remark):
                proxies.append(link)
        else:
            proxies.append(link)
    return base64.urlsafe_b64encode("\n".join(proxies).encode("utf-8"))


def parse_sip002to8(text, headers):
    sip008 = {"version": 1}
    proxies = []
    links = text.split("\n")
    for link in links:
        link = unquote(link)
        if not link:
            continue
        sip002 = "ss://(.*?)@(.*?):(.*?)(/\?plugin=(.*?);(.*))?#(.*)"
        userinfo, server, server_port, _nouse, plugin, plugin_opts, remarks = re.match(
            sip002, link
        ).groups()
        method, password = decode_b64(userinfo).split(":")
        id = md5(f"{server}:{server_port}".encode("utf-8")).hexdigest()
        server_port = int(server_port)
        loc = locals().copy()
        if (remarks and include_re.search(remarks)) or not remarks:
            sip008_dict = {k: loc[k] for k in sip008_server_keys}
            proxies.append(sip008_dict)
    sip008["servers"] = proxies
    if headers:
        h_dict = {x.split("=")[0].strip(): int(x.split("=")[1]) for x in headers.split(";")}
        sip008["bytes_used"] = h_dict["upload"] + h_dict["download"]
        sip008["bytes_remaining"] = h_dict["total"]
    return json.dumps(sip008, ensure_ascii=False).encode("utf-8")


def parse_sip008(data):
    pass


class HttpRequestHandle(BaseHTTPRequestHandler):
    default_request_version = "HTTP/1.1"

    def version_string(self) -> str:
        return "server for ss"

    def log_message(self, format, *args):
        # 使用了sys.stderr.write, win服务会在此处中断
        pass

    def do_GET(self):
        query = urlparse(self.path)
        # parameters = dict(parse_qsl(query.query))
        try:
            url = re.search("url=(.*)", query.query).groups()[0]
            req = requests.get(
                url,
                headers={
                    # "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0"})
                    "user-agent": "ClashforWindows/0.18.7"
                },
            )
        except Exception:
            self.send_response(500)
            self.send_header("Content-type", "text/html; charset=UTF-8")
            self.end_headers()
            self.wfile.write("can not get remote url".encode())
            return

        try:
            rsp = parse_clash(req.content)
            suffix = "yaml"
        except Exception:
            text = decode_b64(req.text)
            node_type = text.split("://")[0]
            if node_type == "ssr":
                rsp = parse_ssr(text)
                suffix = "txt"
            elif node_type == "ss":
                rsp = parse_sip002to8(text, req.headers.get("subscription-userinfo"))
                suffix = "json"
            else:
                self.send_response(500)
                self.send_header("Content-type", "text/html; charset=UTF-8")
                self.end_headers()
                self.wfile.write("error node type".encode())
                return

        self.send_response(200)
        self.send_header("Content-type", "application/octet-stream")
        self.send_header(
            "Content-Disposition",
            f"attachment; filename={urlparse(url).hostname}.{suffix}",
        )
        if info := req.headers.get("subscription-userinfo"):
            self.send_header("subscription-userinfo", info)
        self.end_headers()
        self.wfile.write(rsp)


class LinkService(PySvc):
    _svc_name_ = "linkparse"
    _svc_display_name_ = "linkparse"
    _svc_description_ = "This service filter ss nodes"

    def start(self):
        self.server = ThreadingHTTPServer(("0.0.0.0", 5000), HttpRequestHandle)
        t = threading.Thread(target=self.server.serve_forever)
        t.start()

    def stop(self):
        self.server.shutdown()


if __name__ == "__main__":
    # linkserver = ThreadingHTTPServer(('0.0.0.0', 5000), HttpRequestHandle)
    # linkserver.serve_forever()
    import win32serviceutil

    win32serviceutil.HandleCommandLine(LinkService)
