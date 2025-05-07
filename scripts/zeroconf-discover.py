from zeroconf import ServiceBrowser, Zeroconf
import socket
import asyncio


class KickrListener:
    def __init__(self):
        self.found = []

    def add_service(self, zeroconf, type, name):
        info = zeroconf.get_service_info(type, name)
        ip = socket.inet_ntoa(info.addresses[0])
        self.found.append(ip)



async def discover_kickr():
    zeroconf = Zeroconf()
    listener = KickrListener()
    ServiceBrowser(zeroconf, "_wahoo-fitness-tnp._tcp.local.", listener)
    await asyncio.sleep(2)  # give it a moment to discover
    return listener.found


def main():
    try:
        device_ips = asyncio.run(discover_kickr())
        print(device_ips)
    finally:
        zeroconf.close()

if __name__ == "__main__":
    main()