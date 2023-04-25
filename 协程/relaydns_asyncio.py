import asyncio
from asyncio.protocols import DatagramProtocol

import dns
import httpx
from dns.asyncquery import https  # dnspython

dns_servers = {
    "https://cloudflare-dns.com/dns-query",
    "https://dns.google/dns-query",
    "https://dns.quad9.net/dns-query",
    "https://doh.dns.sb/dns-query",
    "https://public.dns.iij.jp/dns-query",
}


# 可等待： async def 协程函数, asyncio.create_task 任务, asyncio.to_thread() 原loop.run_in_executor()的封装--Future对象


class UDPServerProtocol(DatagramProtocol):
    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message = dns.message.from_wire(data)
        # result = message
        # result.set_rcode(dns.rcode.SERVFAIL)
        # result.flags = dns.flags.QR | dns.flags.RD | dns.flags.RA
        asyncio.create_task(self.handle(message, addr))

    async def handle(self, message, addr):
        cors = {https(message, url, client=client) for url in dns_servers}
        tasks = {asyncio.create_task(c) for c in cors}
        for f in asyncio.as_completed(tasks):
            result = await f
            break
        self.transport.sendto(result.to_wire(), addr)
        for x in tasks:
            x.cancel()


async def main():
    transport, protocol = await loop.create_datagram_endpoint(
        lambda: UDPServerProtocol(), local_addr=("127.0.0.1", 5053)
    )


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    client = httpx.AsyncClient(verify=False, timeout=3)
    loop.run_until_complete(main())
    try:
        loop.run_forever()
    except KeyboardInterrupt:
        pass
    loop.run_until_complete(client.aclose())
