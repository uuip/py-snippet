# coding=utf8

# win指定vlc中libvlc.dll路径
# os.environ['PYTHON_VLC_MODULE_PATH'] = r'C:\Program Files (x86)\VideoLAN\VLC'
# opencv-python
# import cv2

import base64
import hashlib
import re
import socket
import time


def b64(anystr):
    return base64.b64encode(anystr.encode()).decode()


def ftime():
    return time.strftime("%Y%m%dT%H%M%S", time.localtime(time.time()))


class RtspCamera:
    def __init__(self, ip, port, auth="", path="", log=False):
        self.ip = ip
        self.port = port
        self.auth = auth
        self.log = log
        self.host = "rtsp://{}:{}".format(ip, port)
        self.url = self.host + path

        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.settimeout(5)

        self.auth_method = ""
        self.playinfo = {}
        self.session = ""
        self.CSeq = 1

        if self.auth:
            self.username, self.password = self.auth.split(":")

    def basic_auth(self):
        return "Authorization: Basic {}\r\n".format(b64(self.auth))

    def extra_digest_header(self, rsp):
        headers_s = {}
        for line in rsp.splitlines():
            pos = line.find("Digest")
            if pos > -1:
                line = line[pos + 7 :]
                headers = dict(
                    (
                        re.sub(r'[\'"]', "", m).split("=")
                        for m in line.split(",")
                        if m.find("=") > -1
                    )
                )
                for k, v in headers.items():
                    headers_s[k.strip()] = v.strip()
                break
        self.realm = headers_s["realm"]
        self.nonce = headers_s["nonce"]

    def digest_auth(self, method="OPTIONS"):
        part1 = hashlib.md5(
            "{}:{}:{}".format(self.username, self.realm, self.password).encode()
        ).hexdigest()
        part2 = hashlib.md5("{}:{}".format(method, self.host).encode()).hexdigest()
        part_join = hashlib.md5(
            "{0}:{nonce}:{1}".format(part1, part2, nonce=self.nonce).encode()
        ).hexdigest()
        auth = (
            'Authorization: Digest username="{username}", realm="{realm}", '
            'nonce="{nonce}", uri="{uri}", response="{response}"\r\n'.format(
                username=self.username,
                realm=self.realm,
                nonce=self.nonce,
                uri=self.host,
                response=part_join,
            )
        )
        return auth

    def msg(self, method="OPTIONS", headers="", ua="User-Agent: NKPlayer-1.00.00.081112\r\n"):
        if headers and not headers.endswith("\r\n"):
            headers = headers + "\r\n"
        if self.auth_method == "Digest":
            msg = "{} {} RTSP/1.0\r\nCSeq: {}\r\n{}{}{}\r\n".format(
                method, self.url, self.CSeq, headers, self.digest_auth(method), ua
            )
        elif self.auth_method == "Basic":
            msg = "{} {} RTSP/1.0\r\nCSeq: {}\r\n{}{}{}\r\n".format(
                method, self.url, self.CSeq, headers, self.basic_auth(), ua
            )
        else:
            msg = "{} {} RTSP/1.0\r\nCSeq: {}\r\n{}{}\r\n".format(
                method, self.url, self.CSeq, headers, ua
            )
        if self.log:
            print(msg)
        return msg.encode()

    def set_auth_method(self, result):
        for x in result.splitlines():
            if x.strip().startswith("WWW-Authenticate"):
                if "Basic" in x:
                    self.auth_method = "Basic"
                    break
                elif "Digest" in x:
                    self.auth_method = "Digest"
                    self.extra_digest_header(result)
                    break
        else:
            self.auth_method = None

    def connect(self):
        try:
            self.s.connect((self.ip, self.port))
        except Exception as e:
            print(f"libs/rtsp.py {e}")
            self.s.close()
            return 0
        else:
            return 1

    def recive(self):
        tmp = b""
        try:
            rsp = self.s.recv(1024)
            tmp = tmp + rsp
        except Exception as e:
            print(f"{e} ,recive timeout")
        finally:
            if self.log:
                print(tmp.decode())
            return tmp.decode()

    def close(self):
        self.s.close()

    def do_options(self):
        try:
            self.s.send(self.msg("OPTIONS"))
        except Exception as e:
            print(f"{e}, do options error")
            return 0
        self.CSeq = self.CSeq + 1
        rsp = self.recive()
        if rsp:
            rsp_ = rsp.splitlines()
            if "200" in rsp_[0]:
                return 1
            elif "401" in rsp_[0]:
                self.set_auth_method(rsp)
                return self.do_options()
        return 0

    def do_describe(self):
        try:
            self.s.send(self.msg("DESCRIBE", "Accept: application/sdp\r\n"))
        except Exception as e:
            print(f"{e}, do describe error")
            return 0
        self.CSeq = self.CSeq + 1
        rsp = self.recive()
        if rsp:
            rsp_ = rsp.splitlines()
            if "200" in rsp_[0]:
                return self.handle_describe(rsp)
            elif "401" in rsp_[0]:
                self.set_auth_method(rsp)
                return self.do_describe()
        return 0

    def handle_describe(self, rsp):
        rsp = rsp.splitlines()
        self.playinfo = {}  # 重置
        for line in rsp[1:]:  # type:str
            if line.startswith("m=video"):
                tmp = line.replace("m=", "").split(" ")
                for x in tmp:
                    if x.find("/") > 0:
                        self.playinfo.update({"video": x})
                        continue
            if line.startswith("a=control:trackID"):
                if not self.playinfo.get("videotrack"):
                    self.playinfo.update({"videotrack": line.replace("a=control:", "")})
                    continue
            if line.startswith("m=audio"):
                tmp = line.replace("m=", "").split(" ")
                for x in tmp:
                    if x.find("/") > 0:
                        self.playinfo.update({"audio": x})
                        continue
            if line.startswith("a=control:trackID"):
                self.playinfo.update({"audiotrack": line.replace("a=control:", "")})
                continue
        if len(self.playinfo) > 0:
            return 1
        return 0

    def do_setup(self):
        self._url = self.url
        self.url = self._url + "/" + self.playinfo.get("videotrack", "")
        code = 0
        if self.session:
            session = self.session + "\r\n"
        else:
            session = self.session
        playinfo = "{}Transport: {}/TCP;unicast;interleaved=0-1;ssrc=0".format(
            session, self.playinfo.get("video")
        )
        try:
            self.s.send(self.msg("SETUP", playinfo))
        except Exception as e:
            print(f"{e} ,self.url, do setup error")
            return 0
        self.CSeq = self.CSeq + 1
        rsp = self.recive().splitlines()
        if rsp and "200" in rsp[0]:
            for line in rsp:
                if line.startswith("Session:"):
                    self.session = line
                    code = 1
                    break
        if self.playinfo.get("audiotrack", ""):
            self.url = self._url + "/" + self.playinfo.get("audiotrack", "")
            if self.session:
                session = self.session + "\r\n"
            else:
                session = self.session
            playinfo = "{}Transport: {}/TCP;unicast;interleaved=0-1;ssrc=0".format(
                session, self.playinfo.get("audio")
            )
            try:
                self.s.send(self.msg("SETUP", playinfo))
                self.recive().splitlines()
            except Exception as e:
                print(f"{e} , self.url, do setup error2")
                return 0
            self.CSeq = self.CSeq + 1
        self.url = self._url
        return code

    def do_play(self):
        try:
            # 同为,这个可以作为通用的
            tongwei_msg = self.msg("PLAY", self.session + "\r\nRange: npt=0.000-1.000\r\n")
            # 这个海康只是出错后备用
            # Hikvision_msg = self.msg('PLAY', self.session + '\r\nRate-Control:yes\r\nScale:1.000\r\n')
            self.s.send(tongwei_msg)  # npt=now-
        except Exception as e:
            print(f"{e} send play error")
            return 0
        self.CSeq = self.CSeq + 1
        rsp = None
        try:
            rsp = self.recive()
            for x in [0, 1]:
                print(repr(self.s.recv(512)))
        except Exception as e:
            print(f"{e},get play result end {self.ip}")
        finally:
            self.do_teardown()
            if rsp and "200" in rsp.splitlines()[0]:
                return 1
            return 0

    def do_teardown(self):
        try:
            self.s.send(self.msg("TEARDOWN", self.session))
            self.CSeq = self.CSeq + 1
        except Exception:
            print("do_teardown 不论什么异常收尾都算正常")

    def simulate_play(self):
        code = 0
        a = [self.connect(), self.do_options(), self.do_describe(), self.do_setup()]
        if all(a):
            code = self.do_play()
        self.close()
        return code


if __name__ == "__main__":

    # "/cam/realmonitor?channel=1&subtype=0"
    # cam=RtspCamera('192.168.12.14',554,"admin:Admin522522",'')
    cam = RtspCamera("222.175.129.102", 554, "admin:admin", "", True)
    # cam.connect()
    # cam.do_options()
    # cam.do_describe()
    cam.simulate_play()
