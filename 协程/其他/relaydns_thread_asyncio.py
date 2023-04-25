import asyncio
import contextvars
import functools
from socketserver import ThreadingUDPServer, BaseRequestHandler

import dns
from dns import query

dns_servers = {
    "https://cloudflare-dns.com/dns-query",
    "https://dns.google/dns-query",
    "https://dns.quad9.net/dns-query",
    "https://doh.dns.sb/dns-query",
    "https://public.dns.iij.jp/dns-query",
    "https://dns.twnic.tw/dns-query",
}


# python 3.9 以下
async def to_thread(func, /, *args, **kwargs):
    loop = asyncio.get_running_loop()
    ctx = contextvars.copy_context()
    func_call = functools.partial(ctx.run, func, *args, **kwargs)
    return await loop.run_in_executor(None, func_call)


def dns_req(message, url):
    # message = dns.message.make_query(domain, "A")
    try:
        r = query.https(message, url, path="")
    except:
        return None
    return r


class DNSReqHandle(BaseRequestHandler):
    async def getdns(self, message):

        cors = {to_thread(dns_req, message, url) for url in dns_servers}
        # cors = {asyncio.to_thread(dns_req, message, url) for url in dns_servers}
        tasks = {asyncio.create_task(c) for c in cors}

        for f in asyncio.as_completed(tasks):
            result = await f
            if result:
                try:
                    for t in tasks:
                        t.cancel()
                except:
                    pass
                return result
        else:
            message.set_rcode(dns.rcode.SERVFAIL)
            message.flags = dns.flags.QR | dns.flags.RD | dns.flags.RA
            return message

    def handle(self):
        data, socket = self.request
        req_msg = dns.message.from_wire(data)
        # domain = req_msg.question[0].name.to_text()
        try:
            rsp_msg = asyncio.run(self.getdns(req_msg))
        except:
            rsp_msg = req_msg
            rsp_msg.set_rcode(dns.rcode.SERVFAIL)
            rsp_msg.flags = dns.flags.QR | dns.flags.RD | dns.flags.RA
        socket.sendto(rsp_msg.to_wire(), self.client_address)
        return


if __name__ == "__main__":
    dnsserver = ThreadingUDPServer(("0.0.0.0", 5053), DNSReqHandle)
    dnsserver.serve_forever()
