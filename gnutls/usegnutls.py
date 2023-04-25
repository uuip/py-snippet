import socket

import gnutls.errors
import socks
from gnutls.connection import *

socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 1080)
socket.socket = socks.socksocket


def getaddrinfo(*args):
    return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (args[0], args[1]))]


socket.getaddrinfo = getaddrinfo


def get(hostname, port=443):
    ctx = TLSContext(X509Credentials())
    sock = socket.create_connection((hostname, port))
    s = ClientSession(sock, ctx)
    s.handshake()
    print(s.peer_certificate.subject)
    print(s.protocol.decode(), s.cipher.decode())
    s.send(
        memoryview(
            f"GET / HTTP/1.1\r\nHost: {hostname}\r\nUser-Agent: chrome 88\r\n\r\n\r\n".encode()
        )
    )
    try:
        print(s.recv(1024).decode())
    except gnutls.errors.GNUTLSError as e:
        if "Rehandshake" in str(e):
            s.handshake()
            print(s.recv(1024).decode())
    s.shutdown()
    s.close()
    print("=" * 30)


if __name__ == "__main__":
    for x in {"www.mycardtamoil.it", "www.baidu.com", "www.google.com"}:
        get(x)
